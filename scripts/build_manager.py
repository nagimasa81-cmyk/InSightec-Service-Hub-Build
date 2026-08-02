from __future__ import annotations
import argparse, json, os, re, shutil, sys, time, traceback, zipfile
from dataclasses import dataclass
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from common.build_common import latest_source_zip,extract_zip,metadata,write_json,sha256,copy_payload,zip_dir,verify_payload,smoke_test_exe,deploy_qt_runtime
from builders import BUILDERS
from sonication_pipeline import SonicationPipeline, build_stage
@dataclass
class Context:
 module:str; module_dir:Path; source_zip:Path; source_root:Path; workspace:Path; output_root:Path; log_path:Path
 registry:dict; module_config:dict; runtime:str; builder_name:str; engine:str; entry_point:str; exe_stem:str
 version:dict; build_config:dict; guide:bool=False; hub_variant:str="card_launcher"; include_sonication:bool=True; include_complaint:bool=True; build_stage:str=""
def load_registry():
 registry=json.loads((ROOT/"config/module_registry.json").read_text(encoding="utf-8"))
 # module.json is the canonical per-module contract. Merge it over the central
 # registry so every route (standalone, Hub assembly, reuse and audit) resolves
 # the same SOURCE entry, build script and output executables.
 for module_dir in sorted((ROOT/"Module").iterdir()):
  manifest=module_dir/"module.json"
  if not manifest.is_file():
   continue
  data=json.loads(manifest.read_text(encoding="utf-8-sig"))
  module_id=str(data.get("id") or module_dir.name)
  if module_id != module_dir.name:
   raise ValueError(f"module.json id mismatch: {module_dir.name} != {module_id}")
  current=dict(registry.get("modules",{}).get(module_id,{}) or {})
  current.update(data)
  # Canonical names. entry_point is retained only as a compatibility alias.
  # IMPORTANT: merely having module.json must not convert a SOURCE-contract module
  # into a registry-only module.  Modules containing insightec_build_contract.json
  # are resolved from that contract after extraction.  registry_contract is only
  # enabled when the manifest explicitly opts in (Complaint legacy layout).
  source_entry=str(current.get("source_entry_point") or current.get("source_entry") or current.get("entry_point") or "").strip()
  if source_entry:
   current["source_entry_point"]=source_entry
   current["entry_point"]=source_entry
  current["registry_contract"]=bool(data.get("registry_contract", current.get("registry_contract", False)))
  registry.setdefault("modules",{})[module_id]=current
 return registry
def modules(reg):
 configured=[reg["workflow_selection"]["hub_module"], *reg["workflow_selection"]["standalone_modules"]]
 return [name for name in configured if (ROOT/"Module"/name).is_dir() and any((ROOT/"Module"/name).glob("*.zip"))]
def choose_engine(version,cfg,builder):
 raw=str(cfg.get("build_engine") or version.get("build_engine") or "").lower()
 script=str(cfg.get("build_script") or "").lower()
 if "nuitka" in raw or "nuitka" in script:return "nuitka"
 if "pyinstaller" in raw or "pyinstaller" in script:return "pyinstaller"
 return "nuitka" if builder in {"do","fft","hub"} else "pyinstaller"
def canonical_source_entry(mc:dict)->str:
 return str(mc.get("source_entry_point") or mc.get("source_entry") or mc.get("entry_point") or "").strip()

def canonical_build_script(mc:dict)->str:
 return str(mc.get("build_script") or "").strip()

def version_value(v, source_name=""):
 version=str(v.get("version") or v.get("app_version") or "").strip()
 commit=str(v.get("commit") or "").strip()
 build=str(v.get("build") or "").strip()
 # Prefer concise RC notation when an alpha version also contains RC information.
 rc=re.search(r"(?i)rc[._-]?(\d+(?:[._-]\d+)*)",version)
 if rc and ("alpha" in version.lower() or len(version)>18):
  version="RC"+rc.group(1).replace("_",".").replace("-",".")
 if not version:
  m=re.search(r"(?i)(RC\d+(?:[_-]\d+)*)",source_name)
  if m: version=m.group(1).replace("_",".")
 if not version:
  m=re.search(r"(?i)(?:^|[_-])R(\d+(?:[_-]\d+)*)",source_name)
  if m: version="R"+m.group(1).replace("_",".")
 if not version:
  m=re.search(r"(\d+\.\d+(?:\.\d+){0,2}[a-z]?)",source_name)
  if m: version=m.group(1)
 if not version: version="0"
 version=version.lstrip("vV").replace("_",".")
 # Collapse verbose commit wording while retaining traceability.
 version=re.sub(r"(?i)-?commit0*(\d+)",r"-C\1",version)
 cm=re.search(r"(?i)(?:commit|C|R)?\s*0*(\d+)$",commit.replace("_",""))
 if cm and not re.search(rf"(?i)(?:C|R)0*{re.escape(cm.group(1))}(?:$|[^0-9])",version):
  version += f"-C{cm.group(1)}"
 version=re.sub(r"[^0-9A-Za-z.-]+","",version)
 return version[:28] or "0"

def gh_output(k,v):
 p=os.getenv("GITHUB_OUTPUT")
 if p:
  with open(p,"a",encoding="utf-8") as f:f.write(f"{k}={v}\n")
def cache_dir(signature: str) -> Path:
 return ROOT/".artifact-cache"/signature

def restore_cached_build(signature: str):
 cdir=cache_dir(signature); meta_path=cdir/"cache_metadata.json"
 if not signature or not meta_path.is_file(): return None
 meta=json.loads(meta_path.read_text(encoding="utf-8"))
 cached_zip=cdir/meta["artifact_file"]
 cached_sha=cdir/meta["sha256_file"]
 if not cached_zip.is_file() or not cached_sha.is_file(): return None
 expected=str(meta.get("artifact_sha256") or meta.get("summary",{}).get("artifact_sha256") or "")
 if expected and sha256(cached_zip).lower()!=expected.lower():
  print("CACHE REJECTED: SHA256 mismatch")
  return None
 try:
  with zipfile.ZipFile(cached_zip) as z:
   if z.testzip() is not None: return None
 except Exception:
  return None
 artifacts=ROOT/"artifacts"; artifacts.mkdir(parents=True,exist_ok=True)
 target=artifacts/cached_zip.name; sha_target=artifacts/cached_sha.name
 shutil.copy2(cached_zip,target); shutil.copy2(cached_sha,sha_target)
 publish_dir=artifacts/target.stem
 if publish_dir.exists(): shutil.rmtree(publish_dir,ignore_errors=True)
 with zipfile.ZipFile(target) as z: z.extractall(publish_dir)
 summary=meta.get("summary",{})
 summary.update(status="reused_cache",artifact=str(target),publish_directory=str(publish_dir),cache_signature=signature,duration_seconds=0)
 gh_output("artifact_name",target.stem); gh_output("artifact_path",str(publish_dir))
 return summary

def save_cached_build(signature: str, target: Path, result: dict):
 if not signature: return
 cdir=cache_dir(signature)
 if cdir.exists(): shutil.rmtree(cdir)
 cdir.mkdir(parents=True,exist_ok=True)
 sha_file=target.with_suffix(target.suffix+".sha256")
 shutil.copy2(target,cdir/target.name); shutil.copy2(sha_file,cdir/sha_file.name)
 write_json(cdir/"cache_metadata.json",{
  "cache_signature":signature,"artifact_file":target.name,"sha256_file":sha_file.name,
  "created_at":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),"artifact_sha256":result.get("artifact_sha256",""),"summary":result
 })



def reconcile_sonication_metadata(source_root:Path, diagnostics_dir:Path)->dict:
 """Normalize Sonication release metadata before invoking its fixed build BAT.

 version.json is the authoritative release record. VERSION and
 src/common/constants.py are synchronized to it. This prevents a stale file
 inside an otherwise valid SOURCE ZIP from aborting the complete Hub build.
 """
 import re
 versions=list(source_root.rglob("version.json"))
 constants=list(source_root.rglob("src/common/constants.py"))
 version_files=list(source_root.rglob("VERSION"))
 if len(versions)!=1 or len(constants)!=1 or len(version_files)!=1:
  raise RuntimeError(
   "Sonication metadata files must be unique: "
   f"version.json={len(versions)}, constants.py={len(constants)}, VERSION={len(version_files)}"
  )
 version_data=json.loads(versions[0].read_text(encoding="utf-8-sig"))
 expected_version=str(version_data.get("version","")).strip()
 expected_commit=str(version_data.get("commit","")).strip()
 if not expected_version or not expected_commit:
  raise RuntimeError("Sonication version.json must contain non-empty version and commit")
 version_before=version_files[0].read_text(encoding="utf-8-sig").strip()
 constants_text=constants[0].read_text(encoding="utf-8-sig")
 m_ver=re.search(r'(?m)^APP_VERSION\s*=\s*["\']([^"\']+)["\']',constants_text)
 m_commit=re.search(r'(?m)^APP_COMMIT\s*=\s*["\']([^"\']+)["\']',constants_text)
 constants_version_before=m_ver.group(1) if m_ver else ""
 constants_commit_before=m_commit.group(1) if m_commit else ""
 if not m_ver or not m_commit:
  raise RuntimeError("Sonication constants.py must define APP_VERSION and APP_COMMIT")
 repaired=False
 if version_before != expected_version:
  version_files[0].write_text(expected_version+"\n",encoding="utf-8")
  repaired=True
 if constants_version_before != expected_version:
  constants_text=re.sub(r'(?m)^(APP_VERSION\s*=\s*)["\'][^"\']+["\']',lambda m:m.group(1)+repr(expected_version),constants_text,count=1)
  repaired=True
 if constants_commit_before != expected_commit:
  constants_text=re.sub(r'(?m)^(APP_COMMIT\s*=\s*)["\'][^"\']+["\']',lambda m:m.group(1)+repr(expected_commit),constants_text,count=1)
  repaired=True
 constants[0].write_text(constants_text,encoding="utf-8")
 report={
  "authoritative_file":str(versions[0].relative_to(source_root)).replace("\\","/"),
  "expected_version":expected_version,"expected_commit":expected_commit,
  "version_before":version_before,"app_version_before":constants_version_before,
  "app_commit_before":constants_commit_before,"repaired":repaired,
 }
 diagnostics_dir.mkdir(parents=True,exist_ok=True)
 write_json(diagnostics_dir/"sonication_metadata_reconciliation.json",report)
 return report

HUB_TOOL_FOLDERS={
 "Complaint_service_hub":"ComplaintServiceHub",
 "DO_Analysis":"DOanalysis",
 "Log_explorer":"LogExplorer",
 "FFT":"FUSImageExplore",
 "trackerSNR":"TrackerSNR",
 "VIMeasure":"VIMeasure",
 "Soni":"SonicationAnalysis",
}

def _component_context(name,args,reg,workspace_suffix="component"):
 mc=reg["modules"].get(name,{})
 module_dir=ROOT/"Module"/name
 source=latest_source_zip(module_dir,"")
 ws=ROOT/".build_work"/"hub_components"/name
 extracted=extract_zip(source,ws/"source")
 ver,cfg=metadata(extracted)
 runtime=str(cfg.get("runtime") or ver.get("runtime") or mc.get("runtime") or reg["defaults"]["runtime"])
 builder=str(cfg.get("builder") or mc.get("builder") or reg["defaults"]["builder"])
 engine=choose_engine(ver,cfg,builder)
 entry=canonical_source_entry(mc) or str(cfg.get("entrypoint") or cfg.get("entry_point") or ver.get("entry_point") or "")
 log=ws/"diagnostics"/"build.log"
 ctx=Context(name,module_dir,source,extracted,ws,ROOT/"artifacts",log,reg,mc,runtime,builder,engine,entry,str(mc.get("artifact_name") or name),ver,cfg,args.guide,"standalone_module",True,True)
 if name == "Soni":
  reconcile_sonication_metadata(extracted,ws/"diagnostics")
 return ctx

MODULE_CACHE_ROOT=ROOT/".module-cache"/"verified-payloads"

def _module_signature(ctx:Context)->str:
 # Cache the effective contract, not only module.json.  SOURCE-contract modules
 # such as VIMeasure may place their BAT/entry point below a nested contract root.
 cfg=ctx.build_config
 effective_entry=str(cfg.get("entry_point") or canonical_source_entry(ctx.module_config) or ctx.entry_point or "")
 effective_script=str(cfg.get("build_script") or canonical_build_script(ctx.module_config) or "")
 effective_expected=cfg.get("expected_exe_patterns",[]) or ctx.module_config.get("expected_exe_patterns",[])
 effective_outputs=cfg.get("output_directories",[]) or ctx.module_config.get("output_directories",[])
 raw="|".join([
  ctx.module,sha256(ctx.source_zip),ctx.runtime,ctx.builder_name,ctx.engine,
  effective_entry,effective_script,json.dumps(effective_expected,sort_keys=True),
  json.dumps(effective_outputs,sort_keys=True),
  json.dumps(ctx.module_config.get("required_executables",[]),sort_keys=True),
  str(ctx.module_config.get("smoke_executable") or ""),"Nuitka==4.1.3","module-cache-v3"
 ])
 import hashlib
 return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]

def _restore_module_payload(ctx:Context):
 sig=_module_signature(ctx); cdir=MODULE_CACHE_ROOT/ctx.module/sig; meta=cdir/"metadata.json"; payload=cdir/"payload"
 if not meta.is_file() or not payload.is_dir(): return None
 data=json.loads(meta.read_text(encoding="utf-8")); exe=payload/data.get("exe_name","")
 if not exe.is_file(): return None
 return payload,exe,sig

def _save_module_payload(ctx:Context,payload:Path,exe:Path):
 sig=_module_signature(ctx); cdir=MODULE_CACHE_ROOT/ctx.module/sig
 if cdir.exists(): shutil.rmtree(cdir,ignore_errors=True)
 copy_payload(payload,cdir/"payload")
 write_json(cdir/"metadata.json",{"module":ctx.module,"signature":sig,"source_sha256":sha256(ctx.source_zip),"exe_name":exe.name,"verified":True})
 return sig

def assemble_hub_tools(hub_root:Path,args,reg,hub_ctx:Context)->tuple[list[dict],SonicationPipeline|None]:
 """Build repository modules and integrate only verified payloads.

 Sonication is intentionally excluded from the generic loop.  Its dedicated
 six-stage pipeline owns validation, compilation, smoke testing and integration.
 """
 results=[]
 tools_root=hub_root/"tools"
 tools_root.mkdir(parents=True,exist_ok=True)
 selected_modules=list(reg["workflow_selection"]["service_hub_modules"])
 selected_modules=[name for name in selected_modules if name != "Soni"]
 if not args.include_complaint:
  selected_modules=[name for name in selected_modules if name != "Complaint_service_hub"]
 for name in selected_modules:
  ctx=_component_context(name,args,reg)
  started=time.time(); reused=False
  cached=_restore_module_payload(ctx) if args.reuse_existing and bool(ctx.module_config.get("supports_reuse",True)) else None
  if cached:
   payload,exe,module_signature=cached; qt_deploy={"status":"reused_verified_payload"}; reused=True
  else:
   payload,exe=BUILDERS[ctx.builder_name](ctx).build()
   qt_deploy=deploy_qt_runtime(payload,exe,ctx.source_root,ctx.workspace/"diagnostics"/"qt_deploy.log")
   verify_payload(payload,exe,ctx.source_root)
   smoke_test_exe(exe,ctx.workspace/"diagnostics"/"smoke_test.log",seconds=12)
   module_signature=_save_module_payload(ctx,payload,exe)
  target=tools_root/HUB_TOOL_FOLDERS[name]
  preserved={}
  if target.is_dir():
   for n in ("manifest.json","README.txt","release_notes.md"):
    q=target/n
    if q.is_file(): preserved[n]=q.read_bytes()
  copy_payload(payload,target)
  for n,data in preserved.items(): (target/n).write_bytes(data)
  results.append({"module":name,"exe":exe.name,"target":str(target.relative_to(hub_root)),"qt_deploy":qt_deploy,"reused":reused,"module_signature":module_signature,"seconds":round(time.time()-started,2)})

 pipeline=None
 if args.include_sonication:
  soni_ctx=_component_context("Soni",args,reg)
  cached=_restore_module_payload(soni_ctx) if args.reuse_existing else None
  pipeline=SonicationPipeline(hub_ctx,soni_ctx,hub_root)
  try:
   if cached:
    pipeline.payload,pipeline.exe,module_signature=cached
    pipeline.mark_stage(1,"source_validation","reused",{"module_signature":module_signature})
    pipeline.mark_stage(2,"sonication_build","reused",{"payload":str(pipeline.payload)})
    pipeline.mark_stage(3,"sonication_smoke","reused",{"verified_cache":True})
   else:
    pipeline.stage1_source_validation()
    pipeline.stage2_build()
    pipeline.stage3_smoke()
    module_signature=_save_module_payload(soni_ctx,pipeline.payload,pipeline.exe)
   target=tools_root/HUB_TOOL_FOLDERS["Soni"]
   preserved={}
   if target.is_dir():
    for n in ("manifest.json","README.txt","release_notes.md"):
     q=target/n
     if q.is_file(): preserved[n]=q.read_bytes()
   pipeline.stage4_integrate(target,preserved)
   results.append({"module":"Soni","exe":pipeline.exe.name,"target":str(target.relative_to(hub_root)),"pipeline":"dedicated_v1","reused":bool(cached),"module_signature":module_signature})
  except Exception as exc:
   pipeline.mark_stage(5,"hub_build","skipped",{"reason":"Sonication stage failed","error":f"{type(exc).__name__}: {exc}"})
   pipeline.mark_stage(6,"hub_smoke","skipped",{"reason":"Sonication stage failed"})
   pipeline.finalize()
   raise
 else:
  target=tools_root/HUB_TOOL_FOLDERS["Soni"]
  if target.exists(): shutil.rmtree(target,ignore_errors=True)

 if not args.include_complaint:
  complaint_target=tools_root/HUB_TOOL_FOLDERS["Complaint_service_hub"]
  if complaint_target.exists(): shutil.rmtree(complaint_target,ignore_errors=True)

 write_json(hub_root/"HUB_TOOL_ASSEMBLY.json",{"schema":"insightec.hub.repository-assembly.v3","include_sonication":bool(args.include_sonication),"include_complaint":bool(args.include_complaint),"tools":results})
 return results,pipeline

def build_one(name,args,reg):
 started=time.time(); mc=reg["modules"].get(name,{})
 module_dir=ROOT/"Module"/name; source=latest_source_zip(module_dir,args.source_zip if args.module==name else "")
 ws=ROOT/".build_work"/name; extracted=extract_zip(source,ws/"source")
 ver,cfg=metadata(extracted); runtime=str(cfg.get("runtime") or ver.get("runtime") or mc.get("runtime") or reg["defaults"]["runtime"])
 builder=str(cfg.get("builder") or mc.get("builder") or reg["defaults"]["builder"]); engine=choose_engine(ver,cfg,builder)
 entry=canonical_source_entry(mc) or str(cfg.get("entrypoint") or cfg.get("entry_point") or ver.get("entry_point") or "")
 artifact=str(mc.get("artifact_name") or name)
 mode_tag=""
 if name == reg["workflow_selection"]["hub_module"]:
  mode_tag = "ZD" if args.hub_variant == "zip_drop" else "CL"
 soni_tag = "S" if args.include_sonication else "NS"
 complaint_tag = "C" if args.include_complaint else "NC"
 guide_tag = "G" if args.guide else "N"
 artifact = "-".join(x for x in (artifact,mode_tag,soni_tag,complaint_tag,guide_tag) if x)
 log=ws/"diagnostics"/"build.log"
 ctx=Context(name,module_dir,source,extracted,ws,ROOT/"artifacts",log,reg,mc,runtime,builder,engine,entry,artifact,ver,cfg,args.guide,args.hub_variant,args.include_sonication,args.include_complaint,"")
 pipeline=None
 result={"module":name,"source_zip":source.name,"source_sha256":sha256(source),"runtime":runtime,"builder":builder,"engine":engine,"entry_point_requested":entry,"started":started,"include_sonication":bool(args.include_sonication),"include_complaint":bool(args.include_complaint)}
 try:
  if name == "Soni":
   reconcile_sonication_metadata(extracted,ws/"diagnostics")
  if name == reg["workflow_selection"]["hub_module"]:
   _,pipeline=assemble_hub_tools(extracted,args,reg,ctx)
   if pipeline is None:
    StageLoggerPath=ws/"diagnostics"/"sonication"
    StageLoggerPath.mkdir(parents=True,exist_ok=True)
    (StageLoggerPath/"stage1_source_validation.log").write_text("SKIPPED: Sonication excluded\n",encoding="utf-8")
    (StageLoggerPath/"stage2_build.log").write_text("SKIPPED: Sonication excluded\n",encoding="utf-8")
    (StageLoggerPath/"stage3_smoke.log").write_text("SKIPPED: Sonication excluded\n",encoding="utf-8")
    (StageLoggerPath/"stage4_integration.log").write_text("SKIPPED: Sonication excluded\n",encoding="utf-8")
  with build_stage("hub_build" if name == reg["workflow_selection"]["hub_module"] else "module_build"):
   ctx.build_stage="hub_build" if name == reg["workflow_selection"]["hub_module"] else "module_build"
   payload,exe=BUILDERS[builder](ctx).build()
  if pipeline:
   pipeline.mark_stage(5,"hub_build","pass",{"exe":str(exe),"payload":str(payload)})
  # Validate the complete registered payload and select the intended launcher for smoke testing.
  required_executables=[str(x) for x in mc.get("required_executables",[]) if str(x).strip()]
  missing_required=[]
  for required_name in required_executables:
   matches=[p for p in payload.rglob(required_name) if p.is_file()]
   if len(matches)!=1:
    missing_required.append({"name":required_name,"matches":len(matches)})
  if missing_required:
   raise FileNotFoundError(f"Registered payload executables are missing or ambiguous: {missing_required}")
  smoke_name=str(mc.get("smoke_executable") or "").strip()
  if smoke_name:
   smoke_matches=[p for p in payload.rglob(smoke_name) if p.is_file()]
   if len(smoke_matches)!=1:
    raise FileNotFoundError(f"Registered smoke executable must resolve exactly once: {smoke_name}; found {len(smoke_matches)}")
   exe=smoke_matches[0]
  qt_deploy=deploy_qt_runtime(payload,exe,extracted,ws/"diagnostics"/"qt_deploy.log")
  payload_check=verify_payload(payload,exe,extracted)
  payload_check["required_executables"] = required_executables
  payload_check["smoke_executable"] = exe.name
  with build_stage("hub_smoke" if name == reg["workflow_selection"]["hub_module"] else "module_smoke"):
   smoke=smoke_test_exe(exe,ws/"diagnostics"/"smoke_test.log",seconds=12)
  if pipeline:
   pipeline.mark_stage(6,"hub_smoke","pass",{"smoke":smoke})
   pipeline.finalize()
  elif name == reg["workflow_selection"]["hub_module"]:
   sd=ws/"diagnostics"/"sonication"
   (sd/"stage5_hub_build.log").write_text(f"PASS: {exe}\n",encoding="utf-8")
   (sd/"stage6_hub_smoke.log").write_text(json.dumps(smoke,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
  release=ROOT/"artifacts"/name
  copy_payload(payload,release)
  vv=version_value(ver,source.name)
  version_json={"module":name,"display_name":mc.get("display_name",name),"version":vv,"runtime":runtime,"builder":builder,"engine":engine,"source_zip":source.name,"source_sha256":result["source_sha256"],"executable":exe.name,"built_at":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),"include_sonication":bool(args.include_sonication),"include_complaint":bool(args.include_complaint)}
  write_json(release/"version.json",version_json)
  manifest={**version_json,"files":[{"path":str(p.relative_to(release)).replace("\\","/"),"size":p.stat().st_size,"sha256":sha256(p)} for p in release.rglob("*") if p.is_file()]}
  write_json(release/"manifest.json",manifest)
  target=ROOT/"artifacts"/f"{artifact}-v{vv}.zip"; zip_dir(release,target)
  digest=sha256(target); (target.with_suffix(target.suffix+".sha256")).write_text(f"{digest}  {target.name}\n",encoding="ascii")
  result.update(status="success",exe=str(exe),qt_deploy=qt_deploy,payload_check=payload_check,smoke_test=smoke,artifact=str(target),publish_directory=str(release),artifact_sha256=digest,cache_signature=args.cache_signature,duration_seconds=round(time.time()-started,2))
  save_cached_build(args.cache_signature,target,result)
  gh_output("artifact_name",target.stem); gh_output("artifact_path",str(release)); return result
 except Exception as e:
  result.update(status="failure",failure_reason=f"{type(e).__name__}: {e}",duration_seconds=round(time.time()-started,2))
  (ws/"diagnostics").mkdir(parents=True,exist_ok=True); (ws/"diagnostics"/"failure.txt").write_text(traceback.format_exc(),encoding="utf-8")
  if pipeline:
   current=[x.get("stage") for x in pipeline.summary.get("stages",[])]
   error={"error":f"{type(e).__name__}: {e}"}
   if "hub_build" not in current:
    pipeline.mark_stage(5,"hub_build","fail",error)
   if "hub_smoke" not in current:
    hub_build_pass=any(x.get("stage")=="hub_build" and x.get("status")=="pass" for x in pipeline.summary.get("stages",[]))
    pipeline.mark_stage(6,"hub_smoke","fail" if hub_build_pass else "skipped",error if hub_build_pass else {"reason":"Hub build did not complete"})
   pipeline.finalize()
  raise
 finally: write_json(ws/"diagnostics"/"summary.json",result)

def main():
 p=argparse.ArgumentParser(); p.add_argument("--module",default=os.getenv("INPUT_MODULE_NAME","")); p.add_argument("--all",action="store_true"); p.add_argument("--source-zip",default=os.getenv("INPUT_SOURCE_ZIP","")); p.add_argument("--guide",action="store_true",default=os.getenv("INPUT_MODULE_GUIDE","").lower()=="true"); p.add_argument("--hub-variant",default=os.getenv("INPUT_HUB_VARIANT","card_launcher")); p.add_argument("--cache-signature",default=os.getenv("INPUT_CACHE_SIGNATURE","")); p.add_argument("--exclude-sonication",dest="include_sonication",action="store_false",default=os.getenv("INPUT_INCLUDE_SONICATION","true").lower()=="true"); p.add_argument("--exclude-complaint",dest="include_complaint",action="store_false",default=os.getenv("INPUT_INCLUDE_COMPLAINT","true").lower()=="true"); p.add_argument("--reuse-existing",action="store_true"); p.add_argument("--list",action="store_true"); a=p.parse_args(); reg=load_registry(); available=modules(reg)
 if a.list: print("\n".join(available)); return
 # Safety normalization: zip_drop is intentionally analyzer-only. Even when
 # build_manager is called outside build_selected.yml, it must force Complaint
 # exclusion and guide/tour removal before cache lookup, assembly, and Hub build.
 if a.module == "InSightec_Service_hub" and a.hub_variant == "zip_drop":
  a.guide = False
  a.include_complaint = False
 selected=available if a.all else [a.module]
 if not selected or not selected[0]: raise SystemExit("--module is required (or use --all)")
 summary=[]; failed=[]
 if a.reuse_existing and not a.all and a.module != reg["workflow_selection"]["hub_module"]:
  cached=restore_cached_build(a.cache_signature)
  if cached:
   summary.append(cached)
   write_json(ROOT/"artifacts"/"build_summary.json",{"results":summary,"failures":[],"generated_at":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())})
   print(f"CACHE HIT: reused completed artifact for {a.module}")
   return
 for name in selected:
  if name not in available: failed.append({"module":name,"error":"module not found"}); continue
  try: summary.append(build_one(name,a,reg))
  except Exception as e: failed.append({"module":name,"error":f"{type(e).__name__}: {e}"})
 write_json(ROOT/"artifacts"/"build_summary.json",{"results":summary,"failures":failed,"generated_at":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())})
 if failed: raise SystemExit(1)
if __name__=="__main__": main()
