const $=id=>document.getElementById(id); const canvas=$('canvas'),ctx=canvas.getContext('2d',{willReadFrequently:true});
let sourceImage=null,sourceReady=false,roi=null,roiManual=false,currentResult=null,cameraStream=null,cameraBusy=false,sourceGuideCropped=false,autoPipelineToken=0;
let analysisBaseCanvas=null,analysisBaseImageData=null,stablePanelCache=null,analysisFrameGeneration=0;
let canonicalRegistration=null,canonicalMode=false;
let activeDetectedPanel=null;
let v6DeskewAngle=0,v6DeskewApplied=false,v6LastChannelCrop=null,v6LastEnergyCrop=null;
let manualRotationDeg=null,manualChannelROI=null,manualEnergyROI=null,manualEditTarget='energy';
let originalMasterCanvas=null,originalMasterImageData=null,originalMasterWidth=0,originalMasterHeight=0;
let workingRotationDeg=0;
let manualFinalChannel=null;
let roiEditorState={active:false,target:'energy',energy:null,channel:null};
const els={stage:$('stage'),roi:$('roi'),status:$('status'),mode:$('modeSelect'),result:$('resultCard'),camera:$('cameraInput'),photo:$('photoInput'),cameraBtn:$('cameraBtn'),cameraModal:$('cameraModal'),cameraVideo:$('cameraVideo'),cameraState:$('cameraState'),cameraShutter:$('cameraShutter'),cameraGuide:document.querySelector('.camera-guide-frame')};
$('resetBtn').onclick=reset;
$('autoDetectBtn').onclick=()=>{autoPipelineToken++;if(!sourceReady)return;
  setStatus('Auto ROI searching…');
  $('autoDetectBtn').disabled=true;
  // Let iOS paint the status before the CPU-heavy search starts.
  requestAnimationFrame(()=>setTimeout(()=>{
    try{
      redrawSource();
      let found=detectGraph();
      if(found){
        found=v6EstimateAndApplyDeskew(found)||found; // suggestion only; no rotation
        const refined=v6RefineBlackEnergyCrop(found)||found;
        refined.plot=found.plot||refined.plot;
        activeDetectedPanel={...refined,plot:refined.plot?{...refined.plot}:null};
        roi={x:refined.x,y:refined.y,w:refined.w,h:refined.h};
        roiEditorState.energy={...roi};
        manualEnergyROI={...roi};
        // Auto Energy ROI must not overwrite or initialize Channel ROI.
        v63SyncLegacyROIState();
        roiManual=false;els.roi.classList.remove('manual');renderROI();
        setStatus(`Auto ROI: Energy per Band panel/plotを固定しました (${Math.round((found.confidence||0)*100)}%)。Analyzeでは再探索しません。`);
      }else{
        setStatus('Auto ROI候補を確定できませんでした。現在のROIを手動調整してください。');
      }
    }finally{$('autoDetectBtn').disabled=false}
  },20));
};
$('manualBtn').onclick=()=>{
  autoPipelineToken++;
  activeDetectedPanel=activeDetectedPanel;
  // Energy editor always restores/derives the Energy-specific ROI.
  if(!v632EnergySeed()){
    setStatus('Energy ROI is not initialized. Run Auto ROI first.');
    return;
  }
  v63ActivateROIEditor('energy');
};

$('manualGeometryBtn').onclick=()=>{
  $('manualGeometryPanel').classList.toggle('hidden');
  const ang=manualRotationDeg==null?v6DeskewAngle:manualRotationDeg;
  $('rotationRange').value=String(ang);$('rotationNumber').value=Number(ang).toFixed(1);
  v61DrawFullPreviews();
};
$('rotationRange').oninput=()=>{$('rotationNumber').value=$('rotationRange').value};
$('rotationNumber').oninput=()=>{$('rotationRange').value=$('rotationNumber').value};
$('applyRotationBtn').onclick=()=>{
  const ang=Number($('rotationNumber').value||0);
  manualRotationDeg=ang;
  applyRotationFromImmutableOriginal(ang,{remapROI:true});
  // Force both previews and editable main ROI to the newly transformed coordinates.
  const target=roiEditorState.target==='channel'?roiEditorState.channel:roiEditorState.energy;
  if(target){roi={...target};roiManual=true;els.roi.classList.add('manual');renderROI()}
  v61DrawFullPreviews();
  setStatus(`Manual rotation ${ang.toFixed(1)}° applied from immutable Original. Energy/Channel ROI coordinates were remapped.`);
};

$('autoTiltBtn').onclick=()=>{
  try{
    restoreOriginalMasterToWorking();
    let seed=activeDetectedPanel||detectGraph();
    if(!seed?.plot)throw Error('Energy per Band plot not found for tilt estimation.');
    const rot=EGSAnalysisV2.rotationAwareHorizontalGridRows(ctx,canvas,{plot:seed.plot}),
          ang=Number(rot?.angle||0);
    if(!Number.isFinite(ang)||Math.abs(ang)>12)throw Error('Reliable tilt angle not found.');
    manualRotationDeg=ang;
    $('rotationRange').value=String(ang);
    $('rotationNumber').value=Number(ang).toFixed(1);
    applyRotationFromImmutableOriginal(ang,{remapROI:true});
    // Re-detect only because user explicitly requested auto tilt.
    const rerun=detectGraph();
    if(rerun){
      const refined=v6RefineBlackEnergyCrop(rerun)||rerun;
      refined.plot=rerun.plot||refined.plot;
      activeDetectedPanel={...refined,plot:refined.plot?{...refined.plot}:null};
      if(!roiManual){
        roi={x:refined.x,y:refined.y,w:refined.w,h:refined.h};
        renderROI();
      }
    }
    v61DrawFullPreviews();
    setStatus(`Auto tilt correction applied: ${ang.toFixed(2)}°. No automatic rotation is performed on capture.`);
  }catch(e){
    setStatus(`Auto tilt correction failed: ${e?.message||e}`);
  }
};

$('editEnergyROI').onclick=()=>{v63ActivateROIEditor('energy')};
$('editChannelROI').onclick=()=>{v63ActivateROIEditor('channel')};
$('autoGeometryBtn').onclick=()=>{
  manualRotationDeg=null;manualChannelROI=null;manualEnergyROI=null;manualEditTarget='energy';manualFinalChannel=null;roiEditorState={active:false,target:'energy',energy:null,channel:null};
  v6DeskewApplied=false;v6DeskewAngle=0;workingRotationDeg=0;activeDetectedPanel=null;
  restoreOriginalMasterToWorking();
  const found=detectGraph();
  if(found){
    const suggested=v6EstimateAndApplyDeskew(found)||found,
          refined=v6RefineBlackEnergyCrop(suggested)||suggested;
    refined.plot=suggested.plot||refined.plot;
    activeDetectedPanel={...refined,plot:refined.plot?{...refined.plot}:null};
    roi={x:refined.x,y:refined.y,w:refined.w,h:refined.h};roiManual=false;
    els.roi.classList.remove('manual');renderROI();
  }
  v61DrawFullPreviews();
  setStatus('Auto rotation / ROI restored.');
};


$('manualChannelSelect').onchange=()=>{
  const v=$('manualChannelSelect').value;
  manualFinalChannel=v===''?null:Number(v);
  if(currentResult){
    currentResult.channel=manualFinalChannel==null?currentResult.channel:manualFinalChannel;
    currentResult.channelSource=manualFinalChannel==null?'auto':'manual final channel';
    showResult(currentResult);
  }
};

$('analyzeBtn').onclick=async()=>{
  const b=$('analyzeBtn');
  if(b.disabled)return;
  b.disabled=true;
  const oldText=b.textContent;
  b.textContent='Processing…';
  try{await analyzeV6()}
  finally{b.disabled=false;b.textContent=oldText}
};
els.photo.addEventListener('change',e=>{const f=e.target.files?.[0];if(f){loadFile(f);e.target.value='';}});
// Standard-camera input is fallback only. It must never appear as a normal file button.
els.camera.addEventListener('change',e=>{const f=e.target.files?.[0];if(f){loadFile(f);e.target.value='';}});
els.cameraBtn.addEventListener('click',()=>openCamera());
$('cameraCancel').addEventListener('click',closeCamera);
$('cameraRetry').addEventListener('click',()=>startCameraStream());
els.cameraShutter.addEventListener('click',captureCameraFrame);

function cameraMessage(text,error=false){if(els.cameraState){els.cameraState.textContent=text;els.cameraState.classList.toggle('error',!!error)}}
async function openCamera(){
  if(cameraBusy)return;
  // Show the overlay first so every tap has immediate visible feedback.
  els.cameraModal.classList.remove('hidden');els.cameraModal.setAttribute('aria-hidden','false');
  document.body.classList.add('camera-open');
  cameraMessage('カメラ準備中…');
  els.cameraShutter.disabled=true;
  await startCameraStream();
}
async function startCameraStream(){
  if(cameraBusy)return; cameraBusy=true;
  try{
    stopCameraStream();
    if(!window.isSecureContext)throw new Error('Camera requires HTTPS');
    if(!navigator.mediaDevices?.getUserMedia)throw new Error('Camera API unavailable');
    let stream;
    try{
      stream=await navigator.mediaDevices.getUserMedia({video:{facingMode:{ideal:'environment'},width:{ideal:1920},height:{ideal:1080}},audio:false});
    }catch(firstErr){
      // Some iOS/PWA builds reject detailed constraints. Retry with the
      // simplest video request before declaring failure.
      stream=await navigator.mediaDevices.getUserMedia({video:true,audio:false});
    }
    cameraStream=stream; els.cameraVideo.srcObject=stream;
    await new Promise((resolve,reject)=>{
      const done=()=>{cleanup();resolve()}; const fail=()=>{cleanup();reject(new Error('Video could not start'))};
      const cleanup=()=>{els.cameraVideo.removeEventListener('loadedmetadata',done);els.cameraVideo.removeEventListener('error',fail)};
      if(els.cameraVideo.readyState>=1)return resolve();
      els.cameraVideo.addEventListener('loadedmetadata',done,{once:true});els.cameraVideo.addEventListener('error',fail,{once:true});
      setTimeout(()=>{cleanup();resolve()},2500);
    });
    await els.cameraVideo.play();
    cameraMessage('ガイド枠内に Energy per Band と Channel欄が入るように撮影してください');
    els.cameraShutter.disabled=false;
  }catch(e){
    console.error('camera start failed',e);
    cameraMessage('アプリ内カメラを開始できません。Safari/ホーム画面アプリのカメラ許可を確認して「再試行」してください。',true);
    els.cameraShutter.disabled=true;
  }finally{cameraBusy=false}
}
function stopCameraStream(){if(cameraStream){for(const t of cameraStream.getTracks())try{t.stop()}catch(_){}cameraStream=null}els.cameraVideo.srcObject=null}
function closeCamera(){stopCameraStream();els.cameraModal.classList.add('hidden');els.cameraModal.setAttribute('aria-hidden','true');document.body.classList.remove('camera-open');cameraBusy=false}
function cameraGuideSourceRect(){
  const v=els.cameraVideo,g=els.cameraGuide;
  if(!v||!g||!v.videoWidth||!v.videoHeight)return null;
  const vr=v.getBoundingClientRect(),gr=g.getBoundingClientRect();
  if(vr.width<=0||vr.height<=0||gr.width<=0||gr.height<=0)return null;

  // <video> uses object-fit:cover. Convert the visible guide-frame rectangle
  // back to intrinsic camera pixels, including the portions cropped by cover.
  const scale=Math.max(vr.width/v.videoWidth,vr.height/v.videoHeight);
  const renderedW=v.videoWidth*scale,renderedH=v.videoHeight*scale;
  const cropX=(renderedW-vr.width)/2,cropY=(renderedH-vr.height)/2;

  let sx=(gr.left-vr.left+cropX)/scale;
  let sy=(gr.top-vr.top+cropY)/scale;
  let sw=gr.width/scale,sh=gr.height/scale;

  // Small inward margin prevents the yellow guide border itself from entering
  // the analysis image.
  const mx=sw*.012,my=sh*.025;
  sx+=mx;sy+=my;sw-=2*mx;sh-=2*my;

  sx=Math.max(0,Math.min(v.videoWidth-2,sx));
  sy=Math.max(0,Math.min(v.videoHeight-2,sy));
  sw=Math.max(2,Math.min(v.videoWidth-sx,sw));
  sh=Math.max(2,Math.min(v.videoHeight-sy,sh));
  return{sx,sy,sw,sh};
}
function captureCameraFrame(){
  const v=els.cameraVideo;
  if(!v.videoWidth||!v.videoHeight){cameraMessage('カメラ画像を取得できません。再試行してください。',true);return}
  const r=cameraGuideSourceRect();
  if(!r){cameraMessage('撮影枠の位置を取得できません。再試行してください。',true);return}

  els.cameraShutter.disabled=true;
  cameraMessage('撮影枠内だけを切り出しています…');

  // Analyze only the guide-frame crop.  This avoids decoding and scanning the
  // entire iPhone camera frame, which was the main post-capture freeze source.
  const maxOutW=2800;
  const scale=Math.min(1,maxOutW/r.sw);
  const outW=Math.max(2,Math.round(r.sw*scale));
  const outH=Math.max(2,Math.round(r.sh*scale));
  const c=document.createElement('canvas');
  c.width=outW;c.height=outH;
  const cctx=c.getContext('2d',{alpha:false});
  cctx.imageSmoothingEnabled=true;
  cctx.imageSmoothingQuality='high';
  cctx.drawImage(v,r.sx,r.sy,r.sw,r.sh,0,0,outW,outH);

  // Let iOS paint the status text before JPEG encoding starts.
  requestAnimationFrame(()=>setTimeout(()=>{
    c.toBlob(blob=>{
      if(!blob){
        els.cameraShutter.disabled=false;
        cameraMessage('撮影画像の切り出しに失敗しました。',true);
        return;
      }
      closeCamera();
      loadCapturedBlob(blob,true);
    },'image/jpeg',.98);
  },0));
}
function loadCapturedBlob(blob,guideCropped=false){
  // Do not route a captured frame back through <input type=file>. On iOS that
  // can lose the selected file when control returns from the camera/PWA.
  const url=URL.createObjectURL(blob),img=new Image();
  img.onload=()=>{
    // Safari/iOS: copy decoded pixels BEFORE revoking the object URL.
    // Revoking first can leave a later drawImage() with an InvalidStateError.
    useImage(img,{guideCropped});
    setTimeout(()=>URL.revokeObjectURL(url),0);
  };
  img.onerror=()=>{URL.revokeObjectURL(url);setStatus('Could not read captured image.')};img.src=url;
}

function setStatus(s){els.status.textContent=s}

function snapshotOriginalMasterFromCanvas(){
  if(canvas.width<2||canvas.height<2)throw new Error('Original canvas has invalid dimensions');
  originalMasterWidth=canvas.width;originalMasterHeight=canvas.height;
  originalMasterImageData=ctx.getImageData(0,0,canvas.width,canvas.height);
  const c=document.createElement('canvas');
  c.width=canvas.width;c.height=canvas.height;
  const q=c.getContext('2d',{willReadFrequently:true,alpha:false});
  q.putImageData(originalMasterImageData,0,0);
  originalMasterCanvas=c;
  workingRotationDeg=0;
}

function restoreOriginalMasterToWorking(){
  if(!originalMasterCanvas)throw new Error('Immutable Original is unavailable');
  canvas.width=originalMasterWidth;canvas.height=originalMasterHeight;
  ctx.clearRect(0,0,canvas.width,canvas.height);
  ctx.drawImage(originalMasterCanvas,0,0);
  snapshotAnalysisBase();
  workingRotationDeg=0;
}

function rotatedFrameGeometry(angleDeg){
  const W=originalMasterWidth,H=originalMasterHeight,
        r=-Number(angleDeg||0)*Math.PI/180,
        c=Math.abs(Math.cos(r)),s=Math.abs(Math.sin(r));
  return{
    angle:Number(angleDeg||0),
    width:Math.max(2,Math.ceil(W*c+H*s)),
    height:Math.max(2,Math.ceil(W*s+H*c))
  };
}

function originalPointToRotated(x,y,angleDeg){
  const g=rotatedFrameGeometry(angleDeg),
        r=-Number(angleDeg||0)*Math.PI/180,
        co=Math.cos(r),si=Math.sin(r),
        dx=x-originalMasterWidth/2,dy=y-originalMasterHeight/2;
  return{x:g.width/2+dx*co-dy*si,y:g.height/2+dx*si+dy*co};
}
function rotatedPointToOriginal(x,y,angleDeg){
  const g=rotatedFrameGeometry(angleDeg),
        r=Number(angleDeg||0)*Math.PI/180,
        co=Math.cos(r),si=Math.sin(r),
        dx=x-g.width/2,dy=y-g.height/2;
  return{x:originalMasterWidth/2+dx*co-dy*si,y:originalMasterHeight/2+dx*si+dy*co};
}
function transformRectBetweenRotations(R,fromDeg,toDeg){
  if(!R)return null;
  const corners=[
    [R.x,R.y],[R.x+R.w,R.y],[R.x+R.w,R.y+R.h],[R.x,R.y+R.h]
  ].map(([x,y])=>{
    const p=rotatedPointToOriginal(x,y,fromDeg);
    return originalPointToRotated(p.x,p.y,toDeg);
  });
  const xs=corners.map(p=>p.x),ys=corners.map(p=>p.y),
        g=rotatedFrameGeometry(toDeg),
        x0=Math.max(0,Math.min(...xs)),y0=Math.max(0,Math.min(...ys)),
        x1=Math.min(g.width,Math.max(...xs)),y1=Math.min(g.height,Math.max(...ys));
  return{x:x0,y:y0,w:Math.max(2,x1-x0),h:Math.max(2,y1-y0)};
}

function buildRotatedMasterCanvas(angleDeg){
  if(!originalMasterCanvas)throw new Error('Immutable Original is unavailable');
  const g=rotatedFrameGeometry(angleDeg),
        out=document.createElement('canvas');
  out.width=g.width;out.height=g.height;
  const q=out.getContext('2d',{willReadFrequently:true,alpha:false});
  q.fillStyle='#000';q.fillRect(0,0,out.width,out.height);
  q.save();
  q.translate(out.width/2,out.height/2);
  q.rotate(-Number(angleDeg||0)*Math.PI/180);
  q.imageSmoothingEnabled=true;
  q.imageSmoothingQuality='high';
  q.drawImage(originalMasterCanvas,-originalMasterWidth/2,-originalMasterHeight/2);
  q.restore();
  return out;
}

function applyRotationFromImmutableOriginal(angleDeg,{remapROI=true}={}){
  const oldDeg=workingRotationDeg||0,newDeg=Number(angleDeg||0);
  const oldEnergy=manualEnergyROI?{...manualEnergyROI}:null,
        oldChannel=manualChannelROI?{...manualChannelROI}:null,
        oldMain=roi?{...roi}:null;
  const rot=buildRotatedMasterCanvas(newDeg);

  canvas.width=rot.width;canvas.height=rot.height;
  ctx.clearRect(0,0,canvas.width,canvas.height);
  ctx.drawImage(rot,0,0);
  snapshotAnalysisBase();
  workingRotationDeg=newDeg;
  v6DeskewAngle=newDeg;v6DeskewApplied=true;
  canonicalMode=false;canonicalRegistration=null;stablePanelCache=null;activeDetectedPanel=null;

  if(remapROI){
    if(oldEnergy)manualEnergyROI=transformRectBetweenRotations(oldEnergy,oldDeg,newDeg);
    if(oldChannel)manualChannelROI=transformRectBetweenRotations(oldChannel,oldDeg,newDeg);
    if(oldMain)roi=transformRectBetweenRotations(oldMain,oldDeg,newDeg);
    roiEditorState.energy=manualEnergyROI?{...manualEnergyROI}:null;
    roiEditorState.channel=manualChannelROI?{...manualChannelROI}:null;
    roiEditorState.target=manualEditTarget;
    const target=manualEditTarget==='channel'?manualChannelROI:manualEnergyROI;
    if(roiManual&&target)roi={...target};
  }
  if(roi)renderROI();
  v61DrawFullPreviews();
}

function snapshotAnalysisBase(){
  // v6.3.4: immutable raw RGBA pixels are the only analysis source.
  // Do not depend on Canvas->Canvas drawImage during Analyze on iOS Safari.
  if(canvas.width<2||canvas.height<2)throw new Error('Analysis canvas has invalid dimensions');
  analysisBaseImageData=ctx.getImageData(0,0,canvas.width,canvas.height);
  // Keep a canvas copy only for compatibility/debug; analysis restore never uses it.
  const c=document.createElement('canvas');
  c.width=canvas.width;c.height=canvas.height;
  const q=c.getContext('2d',{willReadFrequently:true});
  if(q)q.putImageData(analysisBaseImageData,0,0);
  analysisBaseCanvas=c;
  stablePanelCache=null;
  analysisFrameGeneration++;
}
function redrawSource(){
  if(!analysisBaseImageData)throw new Error('Stable analysis ImageData unavailable');
  if(canvas.width!==analysisBaseImageData.width||canvas.height!==analysisBaseImageData.height){
    // A size change is only valid immediately after canonical registration; snapshot
    // must have been refreshed before any analysis step.
    throw new Error(`Analysis pixel size mismatch ${canvas.width}x${canvas.height} vs ${analysisBaseImageData.width}x${analysisBaseImageData.height}`);
  }
  ctx.putImageData(analysisBaseImageData,0,0);
}
function withCleanAnalysisPixels(fn){
  redrawSource();
  return fn();
}

function stableEnergyPanel(){
  if(stablePanelCache)return stablePanelCache;
  try{
    withCleanAnalysisPixels(()=>null);
    if(canonicalMode&&canonicalRegistration?.ok){
      const ep=canonicalRegistration.energyPanel,
            pp=canonicalRegistration.energyPlot;
      stablePanelCache={
        x:ep.x,y:ep.y,w:ep.w,h:ep.h,
        plot:{x:pp.x,y:pp.y,w:pp.w,h:pp.h},
        confidence:canonicalRegistration.confidence||.95,
        source:'canonical-fixed-stable-panel'
      };
    }else{
      stablePanelCache=EGSAnalysisV2.autoPanelDetect(ctx,canvas)||null;
    }
  }catch(e){
    console.warn('stableEnergyPanel non-fatal failure',e);
    stablePanelCache=null;
  }
  return stablePanelCache;
}
function reset(){closeCamera();sourceImage=null;sourceReady=false;roi=null;currentResult=null;activeDetectedPanel=null;v6DeskewAngle=0;v6DeskewApplied=false;v6LastChannelCrop=null;v6LastEnergyCrop=null;manualRotationDeg=null;manualChannelROI=null;manualEnergyROI=null;manualEditTarget='energy';manualFinalChannel=null;analysisBaseCanvas=null;analysisBaseImageData=null;originalMasterCanvas=null;originalMasterImageData=null;originalMasterWidth=0;originalMasterHeight=0;workingRotationDeg=0;stablePanelCache=null;analysisFrameGeneration++;ctx.clearRect(0,0,canvas.width,canvas.height);els.stage.classList.add('empty');els.roi.classList.add('hidden');els.roi.classList.remove('manual');els.result.classList.add('hidden');$('placeholder').classList.remove('hidden');['autoDetectBtn','manualBtn','analyzeBtn'].forEach(id=>$(id).disabled=true);els.camera.value='';els.photo.value='';setStatus('Ready')}
async function loadFile(file){
  setStatus('Loading image…');
  const url=URL.createObjectURL(file),img=new Image();
  img.onload=()=>{
    useImage(img);
    setTimeout(()=>URL.revokeObjectURL(url),0);
  };
  img.onerror=()=>{URL.revokeObjectURL(url);setStatus('Could not read image.')}
  img.src=url;
}
// Core color classifier used by ROI/grid/foreground analysis.
function isGreen(r,g,b){
  return g>42 && g>r*1.24 && g>b*1.12 && (g-Math.min(r,b))>18;
}

function guideCropSeed(){
  const W=canvas.width,H=canvas.height;
  // Camera guide crop already contains the target application region.
  // Start with a lightweight editable seed around the upper-right Energy per Band
  // plot including the left Y-axis labels and the Channel/Bands row.
  const x=Math.round(W*.47), y=Math.round(H*.06);
  const w=Math.round(W*.52), h=Math.round(H*.60);
  return{
    x:EGSCore.clamp(x,0,Math.max(0,W-80)),
    y:EGSCore.clamp(y,0,Math.max(0,H-60)),
    w:Math.min(W-x,Math.max(80,w)),
    h:Math.min(H-y,Math.max(60,h)),
    manualSeed:true
  };
}


function applyCanonicalRegistration(){
  canonicalRegistration=null;canonicalMode=false;
  try{
    const reg=EGSCanonicalV4.register(ctx,canvas,null);
    if(!reg?.ok)return reg||{ok:false,reason:'registration failed'};
    const c=reg.canonical;
    canvas.width=c.width;canvas.height=c.height;
    ctx.drawImage(c,0,0);
    canonicalRegistration=reg;canonicalMode=true;
    // Critical: canonical pixels become the immutable analysis source.
    // Never redraw the original photo into canonical coordinates afterwards.
    snapshotAnalysisBase();
    sourceImage=analysisBaseCanvas;
    sourceReady=true;
    const p=reg.energyPanel;
    roi={x:p.x,y:p.y,w:p.w,h:p.h};
    roiManual=false;els.roi.classList.remove('manual');renderROI();
    return reg;
  }catch(e){return{ok:false,reason:String(e?.message||e)}}
}
function runPostCapturePipeline(){
  const token=++autoPipelineToken;
  // v6.3.4 unified input path:
  // Camera and Library both analyze the same immutable ImageData first.
  // Canonical registration is fallback only, never the primary camera path.
  setStatus('Energy per Bandを共通Auto detectorで検索しています…');
  requestAnimationFrame(()=>setTimeout(()=>{
    if(token!==autoPipelineToken||!sourceReady)return;

    let found=null;
    try{
      redrawSource();
      found=detectGraph();
    }catch(e){console.warn('direct post-capture detector failed',e)}

    if(found){
      found=v6EstimateAndApplyDeskew(found)||found; // suggestion only; no rotation
      const refined=v6RefineBlackEnergyCrop(found)||found;
      refined.plot=found.plot||refined.plot;
      activeDetectedPanel={...refined,plot:refined.plot?{...refined.plot}:null};
      roi={x:refined.x,y:refined.y,w:refined.w,h:refined.h};
      roiManual=false;els.roi.classList.remove('manual');renderROI();
      setStatus(`Camera/Library共通Auto ROI確定 (${Math.round((found.confidence||0)*100)}%)。同じplot geometryで解析中…`);
      requestAnimationFrame(()=>setTimeout(()=>{
        if(token!==autoPipelineToken||!sourceReady)return;
        analyzeV6();
      },20));
      return;
    }

    // Fallback only: registration may rescue heavily tilted captures.
    setStatus('直接検出が不確実なため、Screen Registrationをfallbackとして試行しています…');
    const reg=applyCanonicalRegistration();
    if(reg?.ok){
      const p=reg.energyPanel,pp=reg.energyPlot;
      activeDetectedPanel={
        x:p.x,y:p.y,w:p.w,h:p.h,plot:{x:pp.x,y:pp.y,w:pp.w,h:pp.h},
        confidence:reg.confidence||.80,source:'canonical-fallback-v6.3.4'
      };
      roi={x:p.x,y:p.y,w:p.w,h:p.h};
      roiManual=false;els.roi.classList.remove('manual');renderROI();
      setStatus('Registration fallbackでpanel/plotを固定しました。解析中…');
    }else{
      roiManual=true;activeDetectedPanel=null;els.roi.classList.add('manual');renderROI();
      setStatus('Auto検出が不確実です。ROIを調整してAnalyzeしてください。');
    }

    requestAnimationFrame(()=>setTimeout(()=>{
      if(token!==autoPipelineToken||!sourceReady||!roi)return;
      analyzeV6();
    },25));
  },30));
}
function useImage(img,opts={}){
  activeDetectedPanel=null;v6DeskewAngle=0;v6DeskewApplied=false;v6LastChannelCrop=null;v6LastEnergyCrop=null;manualRotationDeg=null;manualChannelROI=null;manualEnergyROI=null;manualEditTarget='energy';manualFinalChannel=null;
  sourceImage=img;sourceGuideCropped=!!opts.guideCropped;
  const maxW=2800,scale=Math.min(1,maxW/img.naturalWidth);
  canvas.width=Math.max(2,Math.round(img.naturalWidth*scale));
  canvas.height=Math.max(2,Math.round(img.naturalHeight*scale));
  // Establish exactly one immutable working frame for this image.
  ctx.clearRect(0,0,canvas.width,canvas.height);
  ctx.imageSmoothingEnabled=true;ctx.imageSmoothingQuality='high';
  ctx.drawImage(sourceImage,0,0,canvas.width,canvas.height);
  snapshotOriginalMasterFromCanvas();
  snapshotAnalysisBase();
  // From this point onward, NEVER depend on the HTMLImageElement. Safari may
  // invalidate its backing resource after URL.revokeObjectURL(). A Canvas copy
  // is deterministic and remains drawable for Auto ROI, manual ROI and Analyze.
  sourceImage=analysisBaseCanvas;
  sourceReady=true;;setTimeout(()=>v61DrawFullPreviews(),0)
  redrawSource();
  els.stage.classList.remove('empty');
  $('placeholder').classList.add('hidden');

  if(sourceGuideCropped){
    roi=guideCropSeed();
  }else{
    roi={
      x:Math.round(canvas.width*.48),
      y:Math.round(canvas.height*.06),
      w:Math.round(canvas.width*.50),
      h:Math.round(canvas.height*.50),
      manualSeed:true
    };
    roi.w=Math.min(canvas.width-roi.x,Math.max(80,roi.w));
    roi.h=Math.min(canvas.height-roi.y,Math.max(60,roi.h));
  }

  roiManual=true;
  els.roi.classList.add('manual');
  renderROI();
  ['autoDetectBtn','manualBtn','analyzeBtn'].forEach(id=>$(id).disabled=false);

  if(sourceGuideCropped){
    // Default camera workflow: capture -> crop -> auto ROI -> analyze.
    runPostCapturePipeline();
  }else{
    setStatus('画像を読み込みました。ROIを確認してAnalyzeしてください。');
  }
}


function v61MakeRotatedCanvas(angleDeg){
  return buildRotatedMasterCanvas(angleDeg);
}

function v61DrawFullPreviews(){
  const o=$('originalPreview'),r=$('rotatedPreview');
  if(!o||!r||!sourceReady||!originalMasterCanvas)return;

  // 1. Original = exact guide-frame crop captured/loaded before any deskew/ROI work.
  o.width=originalMasterWidth;o.height=originalMasterHeight;
  const oq=o.getContext('2d');
  oq.clearRect(0,0,o.width,o.height);
  oq.imageSmoothingEnabled=false;
  oq.drawImage(originalMasterCanvas,0,0);

  // 2. Rotation-corrected FULL image, expanded so no corner is clipped.
  const angle=manualRotationDeg==null?workingRotationDeg:manualRotationDeg,
        rot=buildRotatedMasterCanvas(angle);
  r.width=rot.width;r.height=rot.height;
  const rq=r.getContext('2d');
  rq.clearRect(0,0,r.width,r.height);
  rq.drawImage(rot,0,0);
  $('rotationCaption').textContent=
    `Rotation correction: ${Number(angle||0).toFixed(2)}° — full ${r.width}×${r.height}; Original ${originalMasterWidth}×${originalMasterHeight}`;

  rq.save();
  rq.lineWidth=Math.max(2,r.width/500);
  if(manualEnergyROI){
    rq.strokeStyle='#ff3c4b';
    rq.strokeRect(manualEnergyROI.x,manualEnergyROI.y,manualEnergyROI.w,manualEnergyROI.h);
    rq.fillStyle='#ff3c4b';rq.font=`${Math.max(14,r.width/45)}px sans-serif`;
    rq.fillText('Energy ROI',manualEnergyROI.x+4,Math.max(16,manualEnergyROI.y-6));
  }
  if(manualChannelROI){
    rq.strokeStyle='#ff6a6a';rq.setLineDash([8,5]);
    rq.strokeRect(manualChannelROI.x,manualChannelROI.y,manualChannelROI.w,manualChannelROI.h);
    rq.setLineDash([]);
    rq.fillStyle='#ff6a6a';rq.font=`${Math.max(14,r.width/45)}px sans-serif`;
    rq.fillText('Channel ROI',manualChannelROI.x+4,Math.max(16,manualChannelROI.y-6));
  }
  rq.restore();
}

function v61UseRotatedWorkingFrame(angleDeg){
  applyRotationFromImmutableOriginal(angleDeg,{remapROI:true});
}

function v63SyncLegacyROIState(){
  manualEditTarget=roiEditorState.target;
  manualEnergyROI=roiEditorState.energy?{...roiEditorState.energy}:null;
  manualChannelROI=roiEditorState.channel?{...roiEditorState.channel}:null;
}
function v632RectNearlySame(A,B){
  if(!A||!B)return false;
  const tol=Math.max(2,Math.min(canvas.width,canvas.height)*.004);
  return Math.abs(A.x-B.x)<=tol&&Math.abs(A.y-B.y)<=tol&&
         Math.abs(A.w-B.w)<=tol&&Math.abs(A.h-B.h)<=tol;
}

function v632EnergySeed(){
  // Energy ROI may ONLY originate from Energy-specific geometry.
  if(roiEditorState.energy)return{...roiEditorState.energy};
  if(manualEnergyROI)return{...manualEnergyROI};
  if(v6LastEnergyCrop)return{x:v6LastEnergyCrop.x,y:v6LastEnergyCrop.y,w:v6LastEnergyCrop.w,h:v6LastEnergyCrop.h};
  if(activeDetectedPanel)return{x:activeDetectedPanel.x,y:activeDetectedPanel.y,w:activeDetectedPanel.w,h:activeDetectedPanel.h};
  return null;
}

function v632ChannelSeed(){
  // Channel ROI may ONLY originate from Channel-specific detection/derivation.
  if(roiEditorState.channel)return{...roiEditorState.channel};
  if(manualChannelROI)return{...manualChannelROI};
  if(v6LastChannelCrop)return{...v6LastChannelCrop};

  const energy=v632EnergySeed();
  if(energy){
    try{
      const anchored=v62DetectChannelROI(energy);
      if(anchored)return{x:anchored.x,y:anchored.y,w:anchored.w,h:anchored.h};
    }catch(_){}
    try{
      const derived=v6ChannelCropForEnergy(energy);
      if(derived)return{...derived};
    }catch(_){}
  }
  return null;
}

function v63StoreROI(target,R){
  if(!R)return false;
  const q=v6ClampRect(R),
        other=target==='channel'?roiEditorState.energy:roiEditorState.channel;

  // Hard isolation: a target-switch bug must never clone the opposite ROI.
  if(other&&v632RectNearlySame(q,other)){
    const seed=target==='channel'?v632ChannelSeed():v632EnergySeed();
    if(seed&&!v632RectNearlySame(seed,other)){
      const fixed=v6ClampRect(seed);
      if(target==='channel')roiEditorState.channel={...fixed};
      else roiEditorState.energy={...fixed};
      v63SyncLegacyROIState();
      return true;
    }
    // Reject accidental cross-assignment if no target-specific seed exists.
    return false;
  }

  if(target==='channel')roiEditorState.channel={...q};
  else roiEditorState.energy={...q};
  v63SyncLegacyROIState();
  return true;
}

function v63DefaultROIForTarget(target){
  // Never fall back to the generic current `roi`: it belongs to whichever
  // editor target is active and was the cause of Channel/Energy aliasing.
  return target==='channel'?v632ChannelSeed():v632EnergySeed();
}

function v632EnsureROIIsolation(){
  const E=roiEditorState.energy,C=roiEditorState.channel;
  if(!E||!C||!v632RectNearlySame(E,C))return true;

  const channelSeed=v632ChannelSeed();
  if(channelSeed&&!v632RectNearlySame(channelSeed,E)){
    roiEditorState.channel=v6ClampRect(channelSeed);
    v63SyncLegacyROIState();
    return true;
  }
  const energySeed=v632EnergySeed();
  if(energySeed&&!v632RectNearlySame(energySeed,C)){
    roiEditorState.energy=v6ClampRect(energySeed);
    v63SyncLegacyROIState();
    return true;
  }
  return false;
}

function v63RefreshActiveManualCrop(){
  if(!roiEditorState.active)return;
  if(roiEditorState.target==='energy'&&roiEditorState.energy){
    $('energyPreviewWrap')?.classList.remove('hidden');
    v6DrawCropPreview('energyPreview',roiEditorState.energy,null,
      'Manual Energy per Band ROI — authoritative analysis crop');
  }else if(roiEditorState.target==='channel'&&roiEditorState.channel){
    $('channelPreviewWrap')?.classList.remove('hidden');
    const det=v621DetectCheckedChannelsFromKnownLayout(roiEditorState.channel);
    v6DrawCropPreview('channelPreview',roiEditorState.channel,null,
      `Manual Channel ROI — ${det.channels.length?det.channels.map(c=>'CH'+c).join(', '):'no checked enabled channel'}`);
    v61BoxCheckedChannelsInCrop($('channelPreview'),roiEditorState.channel,det.channels,det.boxes);
  }
}
function v63ActivateROIEditor(target){
  const next=target==='channel'?'channel':'energy',
        previous=roiEditorState.target;

  // Commit only the ROI that was actually being edited.
  if(roiEditorState.active&&roi&&previous!==next)v63StoreROI(previous,roi);
  else if(roiEditorState.active&&roi&&previous===next)v63StoreROI(previous,roi);

  roiEditorState.active=true;
  roiEditorState.target=next;

  let R=v63DefaultROIForTarget(next);
  if(!R){
    // Create only from the requested target's own detector/seed.
    R=next==='channel'?v632ChannelSeed():v632EnergySeed();
  }
  if(!R){
    setStatus(`Manual geometry: ${next} ROI is not available yet. Run Auto ROI first for Energy, or analyze/detect Channel section first.`);
    return false;
  }

  // Do not allow the newly loaded target to equal the opposite target.
  const other=next==='channel'?roiEditorState.energy:roiEditorState.channel;
  if(other&&v632RectNearlySame(R,other)){
    const isolated=next==='channel'?v632ChannelSeed():v632EnergySeed();
    if(isolated&&!v632RectNearlySame(isolated,other))R=isolated;
  }

  v63StoreROI(next,R);
  v632EnsureROIIsolation();
  R=v63DefaultROIForTarget(next);
  roi={...R};
  roiManual=true;
  els.roi.classList.remove('hidden');
  els.roi.classList.add('manual');
  $('editEnergyROI').classList.toggle('active',roiEditorState.target==='energy');
  $('editChannelROI').classList.toggle('active',roiEditorState.target==='channel');
  renderROI();
  v61DrawFullPreviews();
  v63RefreshActiveManualCrop();
  setStatus(`Manual geometry: ${roiEditorState.target==='energy'?'Energy per Band':'Channel'} ROI editing.`);
  return true;
}
function v63CommitActiveROI(){
  if(!roiEditorState.active||!roi)return;
  const ok=v63StoreROI(roiEditorState.target,roi);
  if(!ok){
    // Restore the target-specific authoritative ROI rather than contaminating
    // the opposite ROI with the current rectangle.
    const R=v63DefaultROIForTarget(roiEditorState.target);
    if(R){roi={...R};renderROI()}
    setStatus('ROI isolation guard: Channel ROI and Energy ROI cannot share the same rectangle.');
  }
  v632EnsureROIIsolation();
  v61DrawFullPreviews();
  v63RefreshActiveManualCrop();
}
function v61SetManualROIFromMainROI(){v63CommitActiveROI()}
function v61LoadTargetROI(){v63ActivateROIEditor(manualEditTarget)}

function v61BoxCheckedChannelsInCrop(targetCanvas,crop,channels,detectedBoxes=[]){
  if(!targetCanvas||!crop||!channels?.length)return;
  const q=targetCanvas.getContext('2d');
  q.save();
  q.strokeStyle='#ff3c4b';q.fillStyle='#ff3c4b';
  q.lineWidth=Math.max(2,targetCanvas.width/300);
  q.font=`${Math.max(14,targetCanvas.width/22)}px sans-serif`;

  if(detectedBoxes?.length){
    for(const b of detectedBoxes){
      const x=b.x-crop.x,y=b.y-crop.y;
      q.strokeRect(x,y,b.w,b.h);
      q.fillText(`CH${b.channel}`,x,Math.max(14,y-4));
    }
  }else{
    const rows=[{y:.31,count:9,start:0},{y:.67,count:7,start:9}];
    for(const ch of channels){
      const rr=ch<=8?rows[0]:rows[1],k=ch-rr.start,
            slot=targetCanvas.width/9,
            cx=slot*(k+.42),cy=targetCanvas.height*rr.y,
            sz=Math.max(12,Math.min(targetCanvas.height*.22,slot*.55));
      q.strokeRect(cx-sz*.5,cy-sz*.5,sz,sz);
      q.fillText(`CH${ch}`,cx-sz*.5,Math.max(14,cy-sz*.5-4));
    }
  }
  q.restore();
}

function v6ClampRect(r){
  const x0=EGSCore.clamp(Math.floor(r.x),0,Math.max(0,canvas.width-1)),
        y0=EGSCore.clamp(Math.floor(r.y),0,Math.max(0,canvas.height-1)),
        x1=EGSCore.clamp(Math.ceil(r.x+r.w),x0+1,canvas.width),
        y1=EGSCore.clamp(Math.ceil(r.y+r.h),y0+1,canvas.height);
  return{x:x0,y:y0,w:x1-x0,h:y1-y0};
}

function v6RefineBlackEnergyCrop(found){
  if(!found)return null;
  const P=found.plot||found;
  const sx0=Math.max(0,Math.floor(P.x-P.w*.30)),
        sx1=Math.min(canvas.width,Math.ceil(P.x+P.w*1.08)),
        sy0=Math.max(0,Math.floor(P.y-P.h*.18)),
        sy1=Math.min(canvas.height,Math.ceil(P.y+P.h*1.30)),
        W=Math.max(2,sx1-sx0),H=Math.max(2,sy1-sy0),
        im=ctx.getImageData(sx0,sy0,W,H).data;

  const dark=(x,y)=>{
    const i=(y*W+x)*4,r=im[i],g=im[i+1],b=im[i+2],lum=(r+g+b)/3;
    return lum<118;
  };
  const row=[];
  for(let y=0;y<H;y++){
    let n=0;
    for(let x=0;x<W;x+=2)if(dark(x,y))n++;
    row[y]=n/Math.max(1,Math.ceil(W/2));
  }
  const col=[];
  for(let x=0;x<W;x++){
    let n=0;
    for(let y=0;y<H;y+=2)if(dark(x,y))n++;
    col[x]=n/Math.max(1,Math.ceil(H/2));
  }

  const pcx=Math.round(P.x+P.w*.50)-sx0,
        pcy=Math.round(P.y+P.h*.50)-sy0;

  let l=Math.max(0,pcx),r=Math.min(W-1,pcx),t=Math.max(0,pcy),b=Math.min(H-1,pcy);
  while(l>0 && col[l-1]>.28)l--;
  while(r<W-1 && col[r+1]>.28)r++;
  while(t>0 && row[t-1]>.28)t--;
  while(b<H-1 && row[b+1]>.28)b++;

  // Ensure Y labels/title/X labels remain included even if their glyphs reduce dark ratio.
  const minL=Math.max(0,Math.floor(P.x-P.w*.20)-sx0),
        minT=Math.max(0,Math.floor(P.y-P.h*.10)-sy0),
        minB=Math.min(H-1,Math.ceil(P.y+P.h*1.19)-sy0);
  l=Math.min(l,minL); t=Math.min(t,minT); b=Math.max(b,minB);

  const crop=v6ClampRect({x:sx0+l,y:sy0+t,w:r-l+1,h:b-t+1});
  return{...crop,plot:{...P},confidence:found.confidence||.8,source:'v6-black-boundary'};
}

function v6EstimateAndApplyDeskew(seed){
  // v6.3.4: estimator ONLY. Never rotate automatically.
  // Rotation is applied only by explicit user action:
  // - Manual rotation Apply
  // - Auto tilt correction button
  if(!seed?.plot)return seed;
  try{
    const rot=EGSAnalysisV2.rotationAwareHorizontalGridRows(ctx,canvas,{plot:seed.plot});
    const ang=Number(rot?.angle||0);
    seed.rotationSuggestion={
      angle:Number.isFinite(ang)?ang:0,
      confidence:Number(rot?.confidence||0),
      source:'rotation-suggestion-only-v6.3.4'
    };
  }catch(e){
    console.warn('rotation suggestion failed',e);
  }
  return seed;
}


function v62TextMaskForRect(rect){
  const R=v6ClampRect(rect);
  const im=ctx.getImageData(R.x,R.y,R.w,R.h).data,
        mask=new Uint8Array(R.w*R.h);
  for(let y=0;y<R.h;y++)for(let x=0;x<R.w;x++){
    const i=(y*R.w+x)*4,r=im[i],g=im[i+1],b=im[i+2],
          lum=(r+g+b)/3,
          localContrast=Math.max(r,g,b)-Math.min(r,g,b);
    // UI text is dark gray on light background. Green graph pixels are excluded.
    mask[y*R.w+x]=(lum<150 && !isGreen(r,g,b) && localContrast<100)?1:0;
  }
  return{mask,width:R.w,height:R.h,rect:R};
}

function v62RenderWordTemplate(word,fontSize=24,font='Arial'){
  const pad=8,c=document.createElement('canvas'),q=c.getContext('2d');
  q.font=`${fontSize}px ${font}`;
  const m=q.measureText(word);
  c.width=Math.ceil(m.width)+pad*2;c.height=Math.ceil(fontSize*1.45)+pad*2;
  const qq=c.getContext('2d',{willReadFrequently:true});
  qq.fillStyle='#fff';qq.fillRect(0,0,c.width,c.height);
  qq.fillStyle='#000';qq.font=`${fontSize}px ${font}`;qq.textBaseline='middle';
  qq.fillText(word,pad,c.height/2);
  const im=qq.getImageData(0,0,c.width,c.height).data,
        mask=new Uint8Array(c.width*c.height);
  for(let i=0;i<mask.length;i++)mask[i]=(im[i*4]<150)?1:0;
  return{mask,width:c.width,height:c.height};
}

function v62ScaledMaskSimilarity(obs,tmpl){
  // Resize template to observed patch dimensions by nearest mapping.
  let inter=0,oa=0,ta=0;
  for(let y=0;y<obs.height;y++)for(let x=0;x<obs.width;x++){
    const oi=obs.mask[y*obs.width+x],
          tx=Math.min(tmpl.width-1,Math.floor(x/obs.width*tmpl.width)),
          ty=Math.min(tmpl.height-1,Math.floor(y/obs.height*tmpl.height)),
          ti=tmpl.mask[ty*tmpl.width+tx];
    if(oi)oa++;if(ti)ta++;if(oi&&ti)inter++;
  }
  return inter/Math.max(1,Math.sqrt(oa*ta));
}

function v62FindWord(word,scope){
  const S=v6ClampRect(scope),
        candidates=[],
        fonts=['Arial','Verdana','Tahoma','sans-serif'],
        sizes=[18,22,26,30],
        templates=[];
  for(const f of fonts)for(const sz of sizes)
    templates.push(v62RenderWordTemplate(word,sz,f));

  // Search expected UI text area with coarse-to-fine windows.
  const aspect=word==='Channels'?4.0:3.4;
  for(let h=Math.max(16,Math.floor(S.h*.10));h<=Math.max(20,Math.floor(S.h*.30));h+=4){
    const w=Math.max(45,Math.floor(h*aspect));
    for(let y=S.y;y+h<=S.y+S.h;y+=Math.max(3,Math.floor(h*.20))){
      for(let x=S.x;x+w<=S.x+S.w;x+=Math.max(4,Math.floor(w*.12))){
        const obs=v62TextMaskForRect({x,y,w,h});
        let ink=0;for(const v of obs.mask)ink+=v;
        const dens=ink/Math.max(1,obs.mask.length);
        if(dens<.025||dens>.42)continue;
        let score=0;
        for(const t of templates)score=Math.max(score,v62ScaledMaskSimilarity(obs,t));
        if(score>.22)candidates.push({x,y,w,h,score});
      }
    }
  }
  candidates.sort((A,B)=>B.score-A.score);
  return candidates[0]||null;
}

function v62DetectChannelROI(energy){
  // Search left/below Energy panel where Channels + Select All normally live.
  const scope=v6ClampRect({
    x:Math.max(0,energy.x-energy.w*1.65),
    y:Math.max(0,energy.y+energy.h*.30),
    w:Math.min(canvas.width,energy.w*1.75),
    h:Math.min(canvas.height,energy.h*1.25)
  });
  const channels=v62FindWord('Channels',scope),
        selectAll=v62FindWord('Select All',scope);
  if(!channels||!selectAll)return null;
  if(selectAll.x<=channels.x||selectAll.y<channels.y-channels.h*.4)return null;

  const left=Math.max(0,channels.x-10),
        top=Math.max(0,channels.y+channels.h*.50),
        right=Math.min(canvas.width,selectAll.x+selectAll.w),
        bottom=Math.min(canvas.height,selectAll.y+selectAll.h);
  if(right-left<80||bottom-top<22)return null;
  return{
    x:left,y:top,w:right-left,h:bottom-top,
    channelsAnchor:channels,selectAllAnchor:selectAll,
    source:'Channels-center_to_SelectAll-v6.3.4',
    confidence:Math.min(.99,(channels.score+selectAll.score)/2)
  };
}


function v621CellStats(C,im,rect){
  const x0=Math.max(0,Math.floor(rect.x)),y0=Math.max(0,Math.floor(rect.y)),
        x1=Math.min(C.w,Math.ceil(rect.x+rect.w)),y1=Math.min(C.h,Math.ceil(rect.y+rect.h));
  let dark=0,mid=0,bright=0,n=0,mean=0;
  for(let y=y0;y<y1;y++)for(let x=x0;x<x1;x++){
    const i=(y*C.w+x)*4,r=im[i],g=im[i+1],b=im[i+2],
          lum=(r+g+b)/3;
    mean+=lum;n++;
    if(lum<95)dark++;
    else if(lum<175)mid++;
    else bright++;
  }
  return{
    mean:mean/Math.max(1,n),
    dark:dark/Math.max(1,n),
    mid:mid/Math.max(1,n),
    bright:bright/Math.max(1,n)
  };
}


function v631DetectCheckboxGrid(channelROI){
  const C=v6ClampRect(channelROI),
        im=ctx.getImageData(C.x,C.y,C.w,C.h).data,
        lum=(x,y)=>{
          if(x<0||y<0||x>=C.w||y>=C.h)return 255;
          const i=(Math.floor(y)*C.w+Math.floor(x))*4;
          return (im[i]+im[i+1]+im[i+2])/3;
        };

  // Search square-outline evidence rather than assuming exact checkbox centers.
  const candidates=[];
  const minS=Math.max(5,Math.floor(C.h*.09)),
        maxS=Math.max(minS+1,Math.floor(C.h*.24));

  function edgeScore(x,y,s){
    let borderDark=0,borderN=0,insideDark=0,insideN=0,insideMean=0,outMean=0,outN=0;
    const pad=Math.max(1,Math.round(s*.18));
    for(let yy=y;yy<y+s;yy++)for(let xx=x;xx<x+s;xx++){
      const L=lum(xx,yy),
            border=(xx-x<pad||x+s-1-xx<pad||yy-y<pad||y+s-1-yy<pad);
      if(border){borderN++;if(L<155)borderDark++}
      else{insideN++;insideMean+=L;if(L<118)insideDark++}
    }
    const ring=Math.max(1,Math.round(s*.35));
    for(let yy=y-ring;yy<y+s+ring;yy++)for(let xx=x-ring;xx<x+s+ring;xx++){
      if(xx>=x&&xx<x+s&&yy>=y&&yy<y+s)continue;
      if(xx<0||yy<0||xx>=C.w||yy>=C.h)continue;
      outMean+=lum(xx,yy);outN++;
    }
    insideMean/=Math.max(1,insideN);outMean/=Math.max(1,outN);
    const borderFrac=borderDark/Math.max(1,borderN),
          innerFrac=insideDark/Math.max(1,insideN),
          contrast=Math.abs(outMean-insideMean);
    return{borderFrac,innerFrac,insideMean,outMean,contrast,
           score:borderFrac*1.35+Math.min(.5,contrast/120)};
  }

  // Region excludes far-right Select All button and top label band.
  const xLimit=Math.floor(C.w*.88),
        yStart=Math.floor(C.h*.06),
        yEnd=Math.floor(C.h*.92);

  for(let s=minS;s<=maxS;s+=2){
    const step=Math.max(2,Math.floor(s*.28));
    for(let y=yStart;y+s<yEnd;y+=step){
      for(let x=0;x+s<xLimit;x+=step){
        const q=edgeScore(x,y,s);
        if(q.borderFrac<.20||q.score<.36)continue;
        candidates.push({x,y,w:s,h:s,...q,cx:x+s/2,cy:y+s/2});
      }
    }
  }

  candidates.sort((A,B)=>B.score-A.score);
  const kept=[];
  for(const q of candidates){
    if(kept.some(k=>Math.hypot(k.cx-q.cx,k.cy-q.cy)<Math.max(k.w,q.w)*.72))continue;
    kept.push(q);
    if(kept.length>=30)break;
  }
  if(kept.length<4)return null;

  // Find two dominant Y rows.
  const ys=kept.map(q=>q.cy).sort((x,y)=>x-y);
  let bestSplit=null;
  for(let i=2;i<=ys.length-2;i++){
    const a=ys.slice(0,i),b=ys.slice(i),
          ma=EGSCore.median(a),mb=EGSCore.median(b),
          spread=EGSCore.median(a.map(v=>Math.abs(v-ma)))+
                 EGSCore.median(b.map(v=>Math.abs(v-mb))),
          sep=mb-ma,
          score=sep-Math.max(0,spread*2.5);
    if(!bestSplit||score>bestSplit.score)bestSplit={ma,mb,score};
  }
  if(!bestSplit||bestSplit.mb-bestSplit.ma<C.h*.18)return null;

  const rowTol=Math.max(5,C.h*.12),
        top=kept.filter(q=>Math.abs(q.cy-bestSplit.ma)<=rowTol).sort((A,B)=>A.cx-B.cx),
        bot=kept.filter(q=>Math.abs(q.cy-bestSplit.mb)<=rowTol).sort((A,B)=>A.cx-B.cx);

  // Deduplicate X-near boxes inside each row.
  function dedupe(row,limit){
    const out=[];
    for(const q of row){
      if(out.some(k=>Math.abs(k.cx-q.cx)<Math.max(k.w,q.w)*.75))continue;
      out.push(q);
    }
    return out.slice(0,limit);
  }
  const topBoxes=dedupe(top,9),botBoxes=dedupe(bot,7);
  if(topBoxes.length<6)return null;

  const all=[...topBoxes.map((q,k)=>({...q,channel:k,row:0})),
             ...botBoxes.map((q,k)=>({...q,channel:9+k,row:1}))];

  // Relative classification: disabled boxes are pale/low-contrast.
  // Checked boxes have interior ink clearly above the row's empty-box population.
  const enabledPool=all.filter(q=>q.contrast>=10&&q.insideMean<235),
        innerVals=enabledPool.map(q=>q.innerFrac),
        medInner=innerVals.length?EGSCore.median(innerVals):0,
        madInner=innerVals.length?EGSCore.median(innerVals.map(v=>Math.abs(v-medInner))):0;

  const checked=[],disabled=[],boxes=[];
  for(const q of all){
    const isDisabled=(q.contrast<10&&q.insideMean>150) ||
                     (q.insideMean>205&&q.borderFrac<.34);
    const thresh=Math.max(.075,medInner+Math.max(.025,madInner*1.8));
    const isChecked=!isDisabled &&
                    q.innerFrac>=thresh &&
                    q.borderFrac>=.20;
    if(isDisabled)disabled.push(q.channel);
    if(isChecked){
      checked.push(q.channel);
      boxes.push({
        channel:q.channel,
        x:C.x+q.x,y:C.y+q.y,w:q.w,h:q.h,
        fill:q.innerFrac,disabled:false,source:'detected-square-grid'
      });
    }
  }

  return{
    channels:checked,disabled,boxes,
    allBoxes:all.map(q=>({channel:q.channel,x:C.x+q.x,y:C.y+q.y,w:q.w,h:q.h})),
    source:'detected-checkbox-grid+relative-ink-v6.3.4'
  };
}

function v631FixedLayoutChannelFallback(channelROI){
  // v6.3.4:
  // Channel ROI already starts at the vertical center of the "Channels" label
  // and ends at Select All bottom. Therefore the two checkbox rows occupy
  // stable relative Y bands. No connected-component numbering is used.
  const C=v6ClampRect(channelROI),
        im=ctx.getImageData(C.x,C.y,C.w,C.h).data,
        checked=[],boxes=[],disabled=[];

  // The screenshot UI has CH0..CH8 on first row and CH9..CH15 on second row.
  // The Select All button occupies the far right, so reserve ~12% on the right.
  const usableW=C.w*.88,
        slot=usableW/9,
        rowY=[C.h*.28,C.h*.67],
        boxSize=Math.max(6,Math.min(C.h*.18,slot*.30));

  function analyzeCell(ch,row,k){
    // Checkbox is left of the channel number. Use a fixed relative center
    // inside each 1/9 slot derived from the visible layout.
    const cx=slot*(k+.18),
          cy=rowY[row],
          outer={x:cx-boxSize*.62,y:cy-boxSize*.62,w:boxSize*1.24,h:boxSize*1.24},
          inner={x:cx-boxSize*.30,y:cy-boxSize*.30,w:boxSize*.60,h:boxSize*.60},
          surround={x:cx-boxSize*.90,y:cy-boxSize*.90,w:boxSize*1.80,h:boxSize*1.80},
          os=v621CellStats(C,im,outer),
          ins=v621CellStats(C,im,inner),
          ss=v621CellStats(C,im,surround);

    // Disabled/grey checkbox:
    // low local contrast and mid-gray box/label. It must never be selected.
    const contrast=Math.abs(ss.mean-os.mean)+Math.abs(os.mean-ins.mean),
          isDisabled=(os.mean>125 && os.mean<225 && contrast<38 && ins.dark<.12) ||
                     (ins.mid>.62 && ins.dark<.08);

    // Checked enabled box:
    // check mark adds dark interior pixels compared with empty enabled box.
    // Require both interior dark ink and local contrast.
    const isChecked=!isDisabled &&
                    ins.dark>=.10 &&
                    (ins.dark>=os.dark*.72 || ins.dark-os.dark*.18>=.055) &&
                    contrast>=12;

    const absBox={channel:ch,
      x:C.x+outer.x,y:C.y+outer.y,w:outer.w,h:outer.h,
      fill:ins.dark,mean:ins.mean,disabled:isDisabled};

    if(isDisabled)disabled.push(ch);
    else if(isChecked){checked.push(ch);boxes.push(absBox)}
  }

  for(let k=0;k<9;k++)analyzeCell(k,0,k);
  for(let k=0;k<7;k++)analyzeCell(9+k,1,k);

  return{
    channels:checked,
    boxes,
    disabled,
    source:'known-two-row-layout+enabled-checkmark-v6.3.4'
  };
}

function v621DetectCheckedChannelsFromKnownLayout(channelROI){
  const detected=v631DetectCheckboxGrid(channelROI);
  if(detected)return detected;
  const fallback=v631FixedLayoutChannelFallback(channelROI);
  return{
    ...fallback,
    source:'fixed-layout-fallback-v6.3.4'
  };
}

function v62DetectCheckedChannelsFromROI(channelROI){
  const C=v6ClampRect(channelROI),
        im=ctx.getImageData(C.x,C.y,C.w,C.h).data,
        gray=(x,y)=>{
          if(x<0||y<0||x>=C.w||y>=C.h)return 255;
          const i=(Math.floor(y)*C.w+Math.floor(x))*4;
          return (im[i]+im[i+1]+im[i+2])/3;
        };

  // Locate checkbox boxes as repeated square dark-outline structures.
  const comps=[];
  const visited=new Uint8Array(C.w*C.h);
  const isDark=(x,y)=>gray(x,y)<115;
  for(let y=1;y<C.h-1;y++)for(let x=1;x<C.w-1;x++){
    const id=y*C.w+x;
    if(visited[id]||!isDark(x,y))continue;
    const stack=[[x,y]];visited[id]=1;let minx=x,maxx=x,miny=y,maxy=y,n=0;
    while(stack.length&&n<800){
      const [xx,yy]=stack.pop();n++;
      minx=Math.min(minx,xx);maxx=Math.max(maxx,xx);miny=Math.min(miny,yy);maxy=Math.max(maxy,yy);
      for(const [dx,dy] of [[1,0],[-1,0],[0,1],[0,-1]]){
        const nx=xx+dx,ny=yy+dy;
        if(nx<0||ny<0||nx>=C.w||ny>=C.h)continue;
        const ni=ny*C.w+nx;
        if(!visited[ni]&&isDark(nx,ny)){visited[ni]=1;stack.push([nx,ny])}
      }
    }
    const w=maxx-minx+1,h=maxy-miny+1,ratio=w/Math.max(1,h);
    if(w>=5&&h>=5&&w<=C.h*.42&&h<=C.h*.42&&ratio>.58&&ratio<1.65)
      comps.push({x:minx,y:miny,w,h,n});
  }

  // Deduplicate close square candidates.
  comps.sort((A,B)=>A.y-B.y||A.x-B.x);
  const boxes=[];
  for(const q of comps){
    if(boxes.some(b=>Math.hypot((b.x+b.w/2)-(q.x+q.w/2),(b.y+b.h/2)-(q.y+q.h/2))<Math.max(b.w,q.w)*.75))continue;
    boxes.push(q);
  }

  // Cluster into up to 2 rows and map left-to-right as CH0..8 / CH9..15.
  const ys=boxes.map(b=>b.y+b.h/2).sort((x,y)=>x-y),
        split=ys.length?EGSCore.median(ys):C.h/2,
        top=boxes.filter(b=>b.y+b.h/2<=split).sort((A,B)=>A.x-B.x),
        bot=boxes.filter(b=>b.y+b.h/2>split).sort((A,B)=>A.x-B.x),
        rows=[top.slice(0,9),bot.slice(0,7)];

  const checked=[],checkBoxes=[];
  for(let ri=0;ri<rows.length;ri++){
    rows[ri].forEach((b,k)=>{
      const pad=Math.max(1,Math.floor(Math.min(b.w,b.h)*.22)),
            x0=b.x+pad,y0=b.y+pad,x1=b.x+b.w-pad,y1=b.y+b.h-pad;
      let dark=0,total=0;
      for(let y=y0;y<y1;y++)for(let x=x0;x<x1;x++){if(isDark(x,y))dark++;total++}
      const fill=dark/Math.max(1,total),
            ch=ri===0?k:9+k;
      // check mark adds substantial interior dark ink; empty box has mostly border.
      if(fill>=.13){
        checked.push(ch);
        checkBoxes.push({channel:ch,x:C.x+b.x,y:C.y+b.y,w:b.w,h:b.h,fill});
      }
    });
  }
  return{channels:checked,boxes:checkBoxes,allBoxes:boxes,source:'checkbox-interior-ink-v6.3.4'};
}

function v6ChannelCropForEnergy(energy){
  if(!energy)return null;
  const x0=Math.max(0,energy.x-energy.w*1.36),
        x1=Math.min(canvas.width,energy.x+energy.w*.03),
        y0=Math.max(0,energy.y+energy.h*.45),
        y1=Math.min(canvas.height,energy.y+energy.h*1.38);
  if(x1-x0<50||y1-y0<18)return null;
  return v6ClampRect({x:x0,y:y0,w:x1-x0,h:y1-y0});
}

function v6ChannelSectionPresent(crop){
  if(!crop)return false;
  const C=v6ClampRect(crop),im=ctx.getImageData(C.x,C.y,C.w,C.h).data;
  let dark=0,white=0;
  for(let i=0;i<im.length;i+=16){
    const r=im[i],g=im[i+1],b=im[i+2],lum=(r+g+b)/3;
    if(lum<95)dark++; if(lum>150)white++;
  }
  const n=Math.max(1,Math.floor(im.length/16));
  return dark/n>.035 && white/n>.25;
}

function v6CheckedChannels16(energy){
  const anchored=v62DetectChannelROI(energy);
  if(anchored){
    const det=v621DetectCheckedChannelsFromKnownLayout(anchored);
    return{
      present:true,
      channels:det.channels,
      crop:anchored,
      boxes:det.boxes,
      disabled:det.disabled,
      anchors:{channels:anchored.channelsAnchor,selectAll:anchored.selectAllAnchor},
      source:`${anchored.source}+${det.source}`
    };
  }

  // Fallback: no text anchors -> do not guess all channels from vague dark squares.
  // Return present/unknown and let the manual channel selector handle it.
  const crop=v6ChannelCropForEnergy(energy);
  return{
    present:!!crop,
    channels:[],
    crop,
    boxes:[],
    disabled:[],
    source:'channel-anchor-unresolved-v6.3.4'
  };
}

function v6PreparedFromEnergy(energy){
  if(!energy)return null;
  let P=energy.plot;
  if(!P){
    try{P=EGSAnalysisV2.plotFromGrid(ctx,canvas,energy)?.plot||null}catch(_){}
  }
  if(!P)return null;
  const insets={
    left:(P.x-energy.x)/Math.max(1,energy.w),
    right:((energy.x+energy.w)-(P.x+P.w))/Math.max(1,energy.w),
    top:(P.y-energy.y)/Math.max(1,energy.h),
    bottom:((energy.y+energy.h)-(P.y+P.h))/Math.max(1,energy.h),
    source:'v6-energy-black-boundary'
  };
  return{plot:P,insets};
}


function v63GridFirstRows(plot){
  // Horizontal grid is primary evidence. OCR never creates row geometry.
  const P=v6ClampRect(plot);
  let rot=null;
  try{rot=EGSAnalysisV2.rotationAwareHorizontalGridRows(ctx,canvas,{plot:P})}catch(_){}
  let rows=(rot?.rows||[]).map(q=>({y:q.y,score:q.score||1,source:'rotation-aware-grid'}));

  if(rows.length<2){
    const im=ctx.getImageData(P.x,P.y,P.w,P.h).data,
          scores=[];
    for(let y=0;y<P.h;y++){
      let green=0;
      for(let x=Math.floor(P.w*.05);x<Math.floor(P.w*.98);x++){
        const i=(y*P.w+x)*4;
        if(isGreen(im[i],im[i+1],im[i+2]))green++;
      }
      scores[y]=green/Math.max(1,P.w*.93);
    }
    const raw=[];
    for(let y=1;y<P.h-1;y++)
      if(scores[y]>=.10&&scores[y]>=scores[y-1]&&scores[y]>=scores[y+1])
        raw.push({y:P.y+y,score:scores[y],source:'direct-green-grid'});
    rows=raw;
  }

  rows.sort((A,B)=>A.y-B.y);
  const merged=[];
  for(const q of rows){
    const last=merged.at(-1);
    if(!last||q.y-last.y>Math.max(2,P.h*.020))merged.push({...q});
    else if(q.score>last.score)merged[merged.length-1]={...q};
  }
  if(merged.length<2)return{ok:false,rows:merged,reason:'fewer than two horizontal grid rows'};

  // Recover the fundamental row spacing even when one or more grid rows are weak/missing.
  const candidateSteps=[];
  for(let i=0;i<merged.length;i++)for(let j=i+1;j<merged.length;j++){
    const d=merged[j].y-merged[i].y;
    for(const div of [1,2,3,4]){
      const s=d/div;
      if(s>=P.h*.055&&s<=P.h*.40)candidateSteps.push(s);
    }
  }
  if(!candidateSteps.length)return{ok:false,rows:merged,reason:'no plausible grid spacing'};

  let best=null;
  for(const step of candidateSteps){
    for(const anchor of merged){
      // Assign integer lattice index relative to this observed row.
      const indices=merged.map(q=>Math.round((q.y-anchor.y)/step));
      const residuals=merged.map((q,k)=>Math.abs(q.y-(anchor.y+indices[k]*step))/Math.max(1,step));
      const good=residuals.filter(r=>r<=.22).length,
            med=EGSCore.median(residuals),
            span=Math.max(...indices)-Math.min(...indices),
            score=good*2.5-med*5+Math.min(2,span*.25);
      if(!best||score>best.score)
        best={step,anchorY:anchor.y,indices,residuals,good,score};
    }
  }
  if(!best||best.good<2)return{ok:false,rows:merged,reason:'grid periodicity not coherent'};

  const minIndex=Math.min(...best.indices),
        normalized=merged.map((q,k)=>({
          ...q,index:best.indices[k]-minIndex,
          residual:best.residuals[k]
        })).filter(q=>q.residual<=.30),
        row0=best.anchorY+(minIndex)*best.step;

  return{
    ok:true,
    rows:normalized,
    stepPx:Math.abs(best.step),
    row0,
    rotationDeg:Number(rot?.angle||0),
    rotationConfidence:Number(rot?.confidence||0),
    source:'grid-lattice-primary-v6.3.4'
  };
}


function v631DirectNumericAnchorTemplates(norm){
  if(!norm)return[];
  // Candidate values cover the observed Gain/Noise families, but they are
  // only labels attached to an already detected grid row.
  const values=[
    0,0.001,0.002,0.003,0.004,0.005,
    0.01,0.02,0.03,0.04,0.05,0.1,0.2,0.3,0.4,0.5,
    1,2,3,4,5
  ];
  const texts=new Set();
  for(const v of values){
    if(v===0){texts.add('0');texts.add('0.0');texts.add('0.00000')}
    else if(v<.1){
      texts.add(v.toFixed(2));
      texts.add(v.toFixed(3));
      texts.add(v.toFixed(5));
    }else if(v<1){
      texts.add(v.toFixed(1));
      texts.add(v.toFixed(2));
    }else{
      texts.add(v.toFixed(1));texts.add(String(v));
    }
  }

  const out=[];
  for(const text of texts){
    const value=Number(text);
    for(const font of ['Arial','Verdana','Tahoma','sans-serif']){
      for(const size of [18,20,22,24,26,28]){
        const t=axisTextTemplate(text,font,size,''),
              score=maskSimilarity(norm,t)*.58+
                    projectionSimilarity(norm,t,'row')*.21+
                    projectionSimilarity(norm,t,'col')*.21;
        if(score>=.18)out.push({
          value,text,conf:score,
          family:value>=.5?'Gain':'Noise',
          source:'direct-axis-template-v6.3.4'
        });
      }
    }
  }
  out.sort((A,B)=>B.conf-A.conf);
  const unique=[];
  for(const q of out){
    if(unique.some(u=>Math.abs(u.value-q.value)<Math.max(.0001,Math.abs(q.value)*.03)))continue;
    unique.push(q);
    if(unique.length>=10)break;
  }
  return unique;
}

function v63NumericAnchorHypotheses(energy,plot,lattice){
  // OCR is a SECONDARY numeric anchor only. Each label is tied to a grid row
  // that has already been established independently from the text.
  const stripLeft=Math.max(energy.x,plot.x-plot.w*.45),
        stripRight=Math.max(stripLeft+8,Math.min(plot.x-1,energy.x+energy.w*.42)),
        out=[];

  for(const row of lattice.rows){
    const hh=Math.max(10,lattice.stepPx*.48),
          norm=observedAxisLabelNorm(stripLeft,row.y-hh,stripRight-stripLeft,hh*2+1);
    if(!norm)continue;
    const generic=axisLabelHypotheses(norm,'Any',12)
            .filter(h=>Number.isFinite(h.value)&&h.value>=0&&h.conf>=.055)
            .map(h=>({...h,source:h.source||'generic-axis-hypothesis'})),
          direct=v631DirectNumericAnchorTemplates(norm),
          merged=[...generic,...direct].sort((A,B)=>(B.conf||0)-(A.conf||0)),
          hyps=[];
    for(const q of merged){
      if(hyps.some(u=>Math.abs(u.value-q.value)<Math.max(.0001,Math.abs(q.value)*.025)))continue;
      hyps.push(q);
      if(hyps.length>=12)break;
    }
    if(hyps.length){
      out.push({
        index:row.index,y:row.y,hyps,
        aspect:Number(norm?._aspect||0),
        width:Number(norm?._origW||0),
        height:Number(norm?._origH||0)
      });
    }
  }
  return out;
}

function v63CandidateStepValues(anchorRows){
  const canonical=[2,1,.5,.2,.1,.05,.02,.01,.005,.002,.001,.0005],
        pairRaw=[];

  for(let i=0;i<anchorRows.length;i++)for(let j=i+1;j<anchorRows.length;j++){
    const A=anchorRows[i],B=anchorRows[j],di=B.index-A.index;
    if(di<=0)continue;
    for(const ha of A.hyps.slice(0,8))for(const hb of B.hyps.slice(0,8)){
      const raw=(ha.value-hb.value)/di;
      if(!Number.isFinite(raw)||raw<=0||raw>10)continue;

      // Snap pair-derived interval only when it is reasonably close to a
      // physically/display-plausible grid interval.
      let nearest=canonical[0],err=Infinity;
      for(const c of canonical){
        const e=Math.abs(raw-c)/Math.max(c,1e-9);
        if(e<err){err=e;nearest=c}
      }
      if(err<=.28)pairRaw.push(nearest);
    }
  }

  return canonical.map(value=>({
    value,
    count:1+pairRaw.filter(v=>Math.abs(v-value)<value*.05+1e-8).length,
    pairSupported:pairRaw.some(v=>Math.abs(v-value)<value*.05+1e-8)
  }));
}

function v63ScoreAxisModel(stepValue,lattice,anchorRows){
  // Model: value(index) = topValue - index*stepValue.
  // Every OCR hypothesis votes for topValue; compatible votes cluster.
  const votes=[];
  for(const row of anchorRows){
    for(const h of row.hyps){
      const topValue=h.value+row.index*stepValue;
      if(!Number.isFinite(topValue)||topValue<0||topValue>100)continue;
      votes.push({
        topValue,rowIndex:row.index,y:row.y,value:h.value,
        conf:h.conf,text:h.text,family:h.family
      });
    }
  }
  if(!votes.length)return null;

  let best=null;
  const tol=Math.max(stepValue*.22,stepValue<.1?.0025:.08);
  for(const seed of votes){
    const group=votes.filter(v=>Math.abs(v.topValue-seed.topValue)<=tol);
    // Use at most one best vote per grid row.
    const byRow=new Map();
    for(const v of group){
      const old=byRow.get(v.rowIndex);
      if(!old||v.conf>old.conf)byRow.set(v.rowIndex,v);
    }
    const items=[...byRow.values()],
          supportRows=items.length,
          support=items.reduce((s,v)=>s+(v.conf||0),0),
          top=items.reduce((s,v)=>s+v.topValue*(v.conf||.1),0)/
              Math.max(.0001,items.reduce((s,v)=>s+(v.conf||.1),0)),
          residual=EGSCore.median(items.map(v=>Math.abs(v.topValue-top)/Math.max(stepValue,.0001))),
          score=supportRows*2.8+support*1.6-residual*3.5;

    if(!best||score>best.score)
      best={stepValue,topValue:top,items,supportRows,support,residual,score};
  }
  return best;
}


function v633FitYAxisAffine(items,stepPx,stepValue){
  if(!items?.length)return null;

  // Preferred: weighted direct regression from actual recognized anchor pixels.
  if(items.length>=2){
    let sw=0,sy=0,sv=0;
    for(const q of items){
      const w=Math.max(.05,Number(q.conf||.1));
      sw+=w;sy+=w*q.y;sv+=w*q.value;
    }
    const my=sy/sw,mv=sv/sw;
    let num=0,den=0;
    for(const q of items){
      const w=Math.max(.05,Number(q.conf||.1)),
            dy=q.y-my;
      num+=w*dy*(q.value-mv);
      den+=w*dy*dy;
    }
    if(den>1e-6){
      const slope=num/den,
            intercept=mv-slope*my;
      if(Number.isFinite(slope)&&Number.isFinite(intercept)&&slope<0){
        return{ok:true,slope,intercept,source:'weighted-anchor-regression'};
      }
    }
  }

  // Single-anchor fallback: grid supplies slope, the readable numeric anchor
  // supplies absolute offset. This still does NOT assume bottom=0.
  const q=items[0];
  if(q&&Number.isFinite(q.value)&&Number.isFinite(q.y)&&stepPx>0&&stepValue>0){
    const slope=-stepValue/stepPx,
          intercept=q.value-slope*q.y;
    return{ok:true,slope,intercept,source:'single-anchor+grid-slope'};
  }
  return null;
}

function v633AxisValueAtY(cal,y){
  if(!cal||!Number.isFinite(y))return NaN;
  if(Number.isFinite(cal.valueSlope)&&Number.isFinite(cal.valueIntercept))
    return cal.valueSlope*y+cal.valueIntercept;
  if(Number.isFinite(cal.zeroY)&&Number.isFinite(cal.stepPx)&&Number.isFinite(cal.stepValue))
    return (cal.zeroY-y)/Math.max(1e-9,cal.stepPx)*cal.stepValue;
  return NaN;
}

function v63GridAnchorAxisCalibration(energy,plot){
  const lattice=v63GridFirstRows(plot);
  if(!lattice.ok)return{ok:false,source:'grid-anchor-v6.3.4',reason:lattice.reason,lattice};

  const anchors=v63NumericAnchorHypotheses(energy,plot,lattice),
        steps=v63CandidateStepValues(anchors);
  let best=null,second=null;
  for(const c of steps){
    const model=v63ScoreAxisModel(c.value,lattice,anchors);
    if(!model)continue;

    // Family consistency is derived from numeric interval, not requested mode.
    const family=model.stepValue>=.5?'Gain':'Noise';

    // Weak prior: the anchor magnitudes should be plausible for the chosen interval.
    const medVal=model.items.length
      ?EGSCore.median(model.items.map(v=>Math.abs(v.value)))
      :NaN;
    let plausibility=0;
    if(Number.isFinite(medVal)){
      if(family==='Gain')plausibility=medVal>=.45?.55:-.55;
      else plausibility=medVal<.50?.45:-.60;
    }

    // Reward candidate steps that were directly generated by two numeric anchors.
    const directPairSupport=c.count>1?Math.min(.7,(c.count-1)*.12):0,
          total=model.score+plausibility+directPairSupport,
          entry={...model,family,total,directPairSupport};
    if(!best||total>best.total){second=best;best=entry}
    else if(!second||total>second.total)second=entry;
  }

  if(!best)return{
    ok:false,source:'grid-anchor-v6.3.4',
    reason:'grid found but no numeric anchor hypothesis',lattice,anchorRows:anchors
  };

  // Require either >=2 independently anchored rows, or one usable anchor plus
  // a strong regular grid. This is deliberately not "OCR must fully succeed".
  const oneAnchorAllowed=best.supportRows===1 &&
                         lattice.rows.length>=3 &&
                         best.items[0]?.conf>=.16;
  if(best.supportRows<2&&!oneAnchorAllowed){
    return{
      ok:false,source:'grid-anchor-v6.3.4',
      reason:'numeric anchor evidence insufficient',lattice,anchorRows:anchors,best
    };
  }

  const stepPx=lattice.stepPx,
        topGridY=lattice.row0,
        affine=v633FitYAxisAffine(best.items,stepPx,best.stepValue);
  if(!affine?.ok){
    return{
      ok:false,source:'grid-anchor-v6.3.4',
      reason:'numeric anchors could not define pixel-to-value affine',lattice,anchorRows:anchors,best
    };
  }
  const zeroY=-affine.intercept/affine.slope,
        completed=lattice.rows.map(r=>({
          y:r.y,
          value:affine.slope*r.y+affine.intercept,
          grid:true,
          inferred:!best.items.some(v=>v.rowIndex===r.index)
        })),
        bottomGrid=completed.length?completed.reduce((p,q)=>q.y>p.y?q:p,completed[0]):null,
        confidence=EGSCore.clamp(
          .48+
          Math.min(.28,best.supportRows*.10)+
          Math.min(.12,lattice.rows.length*.025)+
          Math.min(.08,best.support*.08)-
          Math.min(.12,best.residual*.15),
          .42,.98
        );

  return{
    ok:true,
    zeroY,stepPx,stepValue:best.stepValue,
    valueSlope:affine.slope,valueIntercept:affine.intercept,
    affineSource:affine.source,
    bottomGridY:bottomGrid?.y??NaN,
    bottomGridValue:bottomGrid?.value??NaN,
    family:best.family,modeHint:best.family,
    source:'grid-first+numeric-anchor-affine-v6.3.4',
    anchors:best.items.map(v=>({
      y:v.y,value:v.value,conf:v.conf,text:v.text,rowIndex:v.rowIndex
    })),
    completedAnchors:completed,
    gridRows:lattice.rows,
    lattice,
    fitScore:best.total,
    confidence,
    supportRows:best.supportRows,
    singleAnchorFallback:oneAnchorAllowed,
    secondScore:second?.total??null
  };
}

function v6AxisDecision(energy,prep){
  // v6.3.4 canonical Y-axis path:
  // grid geometry first -> partial numeric anchors -> consensus model.
  // Legacy Gain/Noise-specific OCR calibration is intentionally NOT called here.
  const cal=v63GridAnchorAxisCalibration(energy,prep.plot);
  if(!cal.ok){
    return{
      mode:'Unknown',cal:null,gridValueStep:NaN,
      axisFamily:{family:'Unknown',confidence:0,source:cal.source},
      gridAnchor:cal
    };
  }
  const gridValueStep=Math.abs(cal.stepValue),
        mode=gridValueStep>=.5?'Gain':'Noise';
  return{
    mode,cal,gridValueStep,
    axisFamily:{family:mode,confidence:cal.confidence,source:cal.source},
    gridAnchor:cal
  };
}


function v6VerticalGridCols(plot){
  const P=v6ClampRect(plot),im=ctx.getImageData(P.x,P.y,P.w,P.h).data,
        score=[];
  for(let x=0;x<P.w;x++){
    let green=0;
    for(let y=Math.floor(P.h*.05);y<Math.floor(P.h*.92);y++){
      const i=(y*P.w+x)*4;
      if(isGreen(im[i],im[i+1],im[i+2]))green++;
    }
    score[x]=green/Math.max(1,P.h*.87);
  }
  const raw=[];
  for(let x=1;x<P.w-1;x++)
    if(score[x]>=.16&&score[x]>=score[x-1]&&score[x]>=score[x+1])raw.push({x,score:score[x]});
  const groups=[];
  for(const q of raw){
    const g=groups.at(-1);
    if(!g||q.x-g.at(-1).x>Math.max(2,P.w*.012))groups.push([q]);
    else g.push(q);
  }
  return groups.map(g=>g.sort((u,v)=>v.score-u.score)[0].x+P.x).sort((x,y)=>x-y);
}

function v6RecognizeXAxisLabel(cx,step,plot){
  const y0=plot.y+plot.h*.90,
        h=Math.min(canvas.height-y0,Math.max(18,plot.h*.30)),
        w=Math.max(12,step*.86),
        x0=cx-w/2,
        obs=observedAxisLabelNorm(x0,y0,w,h);
  if(!obs)return null;

  const vals=[0,50,100,150,200,250,300,350,400,450,500],
        fonts=['Arial','Verdana','Tahoma','sans-serif'];
  let best=null;
  for(const v of vals){
    for(const font of fonts){
      for(const size of [18,22,26]){
        const t=axisTextTemplate(String(v),font,size,''),
              sc=maskSimilarity(obs,t)*.62+
                 projectionSimilarity(obs,t,'row')*.19+
                 projectionSimilarity(obs,t,'col')*.19;
        if(!best||sc>best.score)best={value:v,score:sc};
      }
    }
  }
  return best&&best.score>=.30?best:null;
}

function v6XAxisCalibration(plot){
  const cols=v6VerticalGridCols(plot);
  if(cols.length<3)return{ok:false,min:0,max:500,source:'fallback-0-500',cols};
  const gaps=[];
  for(let i=1;i<cols.length;i++)gaps.push(cols[i]-cols[i-1]);
  const step=EGSCore.median(gaps),
        labels=[];
  for(const x of cols){
    const hit=v6RecognizeXAxisLabel(x,step,plot);
    if(hit)labels.push({x,value:hit.value,score:hit.score});
  }

  // Fit sample = a*x+b from mutually monotonic recognized labels.
  let bestPair=null;
  for(let i=0;i<labels.length;i++)for(let j=i+1;j<labels.length;j++){
    const A=labels[i],B=labels[j];
    if(B.value<=A.value||B.x<=A.x)continue;
    const a=(B.value-A.value)/(B.x-A.x),
          expected=500/Math.max(1,plot.w);
    if(a<expected*.45||a>expected*1.9)continue;
    const score=A.score+B.score-Math.abs(a-expected)/expected*.15;
    if(!bestPair||score>bestPair.score)bestPair={A,B,a,b:A.value-a*A.x,score};
  }
  if(bestPair){
    return{ok:true,a:bestPair.a,b:bestPair.b,min:0,max:500,
           labels,cols,
           x0:(0-bestPair.b)/bestPair.a,
           x500:(500-bestPair.b)/bestPair.a,
           source:'bottom-label-ocr+vertical-grid'};
  }

  // Structural fallback: use ACTUAL vertical-grid endpoints, not plot bounds.
  // The outer plot rectangle can include Y-label / border margin and caused
  // Low/High lines to shift horizontally.
  if(cols.length>=3){
    const left=cols[0],right=cols[cols.length-1],
          a=500/Math.max(1,right-left),
          b=-a*left;
    return{ok:true,a,b,min:0,max:500,labels,cols,
           x0:left,x500:right,source:'vertical-grid-endpoints-0-500'};
  }
  return{ok:false,min:0,max:500,labels,cols,source:'plot-bounds-last-resort'};
}

function v6SampleX(plot,sample){
  const cal=plot?._xCal;
  if(cal&&Number.isFinite(cal.a)&&Number.isFinite(cal.b)&&Math.abs(cal.a)>1e-12)
    return (sample-cal.b)/cal.a;
  if(cal&&Number.isFinite(cal.x0)&&Number.isFinite(cal.x500))
    return cal.x0+(cal.x500-cal.x0)*(sample/500);
  return plot.x+plot.w*(sample/500);
}


function v631RgbToHue(r,g,b){
  r/=255;g/=255;b/=255;
  const mx=Math.max(r,g,b),mn=Math.min(r,g,b),d=mx-mn;
  if(d===0)return 0;
  let h;
  if(mx===r)h=((g-b)/d)%6;
  else if(mx===g)h=(b-r)/d+2;
  else h=(r-g)/d+4;
  h*=60;
  if(h<0)h+=360;
  return h;
}
function v6SignalPopulation(plot,cal,mode,xSample0,xSample1){
  const x0=Math.max(plot.x,v6SampleX(plot,xSample0)),
        x1=Math.min(plot.x+plot.w,v6SampleX(plot,xSample1));
  if(x1-x0<4)return null;

  const X0=Math.max(0,Math.floor(x0)),X1=Math.min(canvas.width,Math.ceil(x1)),
        Y0=Math.max(0,Math.floor(plot.y)),Y1=Math.min(canvas.height,Math.ceil(plot.y+plot.h)),
        W=X1-X0,H=Y1-Y0;
  if(W<4||H<4)return null;
  const im=ctx.getImageData(X0,Y0,W,H).data;

  // Determine dominant non-green marker hue; white markers are separately retained.
  const bins=new Array(36).fill(0);
  const pix=[];
  for(let y=Math.floor(H*.04);y<Math.ceil(H*.96);y++)for(let x=0;x<W;x++){
    const i=(y*W+x)*4,r=im[i],g=im[i+1],b=im[i+2],
          mx=Math.max(r,g,b),mn=Math.min(r,g,b),sat=(mx-mn)/Math.max(1,mx),lum=(r+g+b)/3;
    const green=isGreen(r,g,b);
    const white=lum>155&&mx-mn<58;
    if(green||lum<70)continue;
    if(sat>.20){
      const h=v631RgbToHue(r,g,b),bi=Math.floor((h%360)/10);
      bins[bi]++;
      pix.push({x:X0+x,y:Y0+y,h,white:false,lum,sat});
    }else if(white){
      pix.push({x:X0+x,y:Y0+y,h:NaN,white:true,lum,sat});
    }
  }
  let bestBin=0;
  for(let i=1;i<36;i++)if(bins[i]>bins[bestBin])bestBin=i;
  const coloredCount=bins.reduce((s,v)=>s+v,0),
        hue=coloredCount>0?bestBin*10+5:NaN,
        hd=(a,b)=>{let d=Math.abs(a-b)%360;return Math.min(d,360-d)};

  const candidates=pix.filter(q=>q.white||(!q.white&&Number.isFinite(hue)&&hd(q.h,hue)<=28));
  if(candidates.length<8)return null;

  // Collapse each X column to a robust marker Y.
  const byX=new Map();
  for(const q of candidates){
    const k=Math.round(q.x);
    if(!byX.has(k))byX.set(k,[]);
    byX.get(k).push(q.y);
  }
  const ys=[],pts=[];
  for(const [x,arr] of byX){
    if(!arr.length)continue;
    // Median suppresses cursor triangles / block edges inside a column.
    const y=EGSCore.median(arr);
    ys.push(y);pts.push({x,y});
  }
  if(ys.length<6)return null;

  const med=EGSCore.median(ys),
        mad=EGSCore.median(ys.map(v=>Math.abs(v-med)))||1,
        keep=pts.filter(q=>Math.abs(q.y-med)<=Math.max(3,mad*3.2));
  if(keep.length<5)return null;

  // Average after spike rejection, as requested.
  const meanY=keep.reduce((s,q)=>s+q.y,0)/keep.length;
  if(!cal)return{meanY,value:NaN,count:keep.length,hue,points:keep,mad};
  const value=v633AxisValueAtY(cal,meanY);
  return{meanY,value,count:keep.length,hue,points:keep,mad};
}

function v6DrawCropPreview(targetId,crop,lines=null,label=''){
  const out=$(targetId); if(!out||!crop)return;
  const R=v6ClampRect(crop),q=out.getContext('2d');
  out.width=R.w;out.height=R.h;
  redrawSource();
  q.drawImage(canvas,R.x,R.y,R.w,R.h,0,0,R.w,R.h);
  if(lines){
    q.save();
    q.lineWidth=Math.max(2,R.w/280);
    q.font=`${Math.max(14,Math.round(R.w/22))}px sans-serif`;
    for(const L of lines){
      q.strokeStyle=L.stroke||'#00d4ff';
      q.fillStyle=L.stroke||'#00d4ff';
      q.beginPath();q.moveTo(L.x0-R.x,L.y-R.y);q.lineTo(L.x1-R.x,L.y-R.y);q.stroke();
      q.fillText(L.text,L.x0-R.x+4,L.y-R.y-5);
    }
    q.restore();
  }
  out.parentElement?.classList.remove('hidden');
  const cap=out.parentElement?.querySelector('.preview-caption');
  if(cap)cap.textContent=label;
}

function v6RenderPreviews(energy,chInfo,lowPop,highPop,mode){
  v61DrawFullPreviews();
  v6LastEnergyCrop=energy;v6LastChannelCrop=chInfo?.crop||null;
  const channelCrop=roiEditorState.channel?{...roiEditorState.channel}:(chInfo?.crop?{...chInfo.crop}:null);
  if(channelCrop){
    v6DrawCropPreview('channelPreview',channelCrop,null,
      `Channel section — ${chInfo?.channels?.length?chInfo.channels.map(c=>'CH'+c).join(', '):'no checked channel resolved'}`);
    v61BoxCheckedChannelsInCrop($('channelPreview'),channelCrop,chInfo?.channels||[],chInfo?.boxes||[]);
  }else{
    $('channelPreviewWrap')?.classList.add('hidden');
  }

  const lines=[];
  if(lowPop&&Number.isFinite(lowPop.meanY))lines.push({
    y:lowPop.meanY,x0:v6SampleX(energy.plot,0),
    x1:v6SampleX(energy.plot,mode==='Gain'?330:260),
    text:`Low ${Number.isFinite(lowPop.value)?(mode==='Noise'?lowPop.value.toFixed(4):lowPop.value.toFixed(2)):'—'}`
  });
  if(highPop&&Number.isFinite(highPop.meanY))lines.push({
    y:highPop.meanY,x0:v6SampleX(energy.plot,mode==='Gain'?340:270),
    x1:v6SampleX(energy.plot,500),
    text:`High ${Number.isFinite(highPop.value)?(mode==='Noise'?highPop.value.toFixed(4):highPop.value.toFixed(2)):'—'}`
  });
  const energyCrop=roiEditorState.energy?{...roiEditorState.energy}:energy;
  v6DrawCropPreview('energyPreview',energyCrop,lines,
    `Energy per Band — ${mode}; rotation corrected ${v6DeskewAngle.toFixed(2)}°`);
}


function v631SetProcessing(percent,stage,detail=''){
  const panel=$('processingPanel');
  if(!panel)return;
  panel.classList.remove('hidden');
  $('processingPercent').textContent=`${Math.max(0,Math.min(100,Math.round(percent)))}%`;
  $('processingBar').style.width=`${Math.max(0,Math.min(100,percent))}%`;
  $('processingStage').textContent=stage||'Processing';
  $('processingDetail').textContent=detail||'';
}
function v631FinishProcessing(stage='Complete',detail=''){
  v631SetProcessing(100,stage,detail);
  setTimeout(()=>$('processingPanel')?.classList.add('hidden'),1400);
}
function v631FailProcessing(detail=''){
  const panel=$('processingPanel');
  if(!panel)return;
  panel.classList.remove('hidden');
  $('processingTitle').textContent='Processing stopped';
  $('processingStage').textContent='Needs attention';
  $('processingDetail').textContent=detail;
  $('processingPercent').textContent='—';
  $('processingBar').style.width='100%';
  setTimeout(()=>{ $('processingTitle').textContent='Processing…'; },50);
}
function v631Yield(){
  return new Promise(resolve=>requestAnimationFrame(()=>setTimeout(resolve,0)));
}
async function v631Stage(percent,stage,detail=''){
  v631SetProcessing(percent,stage,detail);
  await v631Yield();
}

async function analyzeV6(){
  const visibleROILock=roi?{x:roi.x,y:roi.y,w:roi.w,h:roi.h}:null;
  const visibleROILockManual=roiManual;
  if(!sourceReady||!roi)return;
  setStatus('v6 pipeline: rotation → Channel → Energy → axis → Low/High…');
  await v631Stage(3,'Preparing','Locking the active ROI and source image.');
  try{
    redrawSource();
    await v631Stage(10,'ROI / geometry','Using the current Energy ROI without changing it.');

    // Step 1: deskew has normally already run during Auto ROI. If not, estimate
    // from the current plot and keep analysis rotation-aware.
    let baseFound=null;
    if(roiManual){
      const M=roiEditorState.energy?{...roiEditorState.energy}:exactAnalysisROI(roi);
      try{
        const local=EGSAnalysisV2.autoPanelDetect(ctx,canvas,M);
        if(local)baseFound=local;
      }catch(_){}
      if(!baseFound){
        let pg=null;
        try{pg=EGSAnalysisV2.plotFromGrid(ctx,canvas,M)}catch(_){}
        if(pg?.plot)baseFound={...M,plot:pg.plot,confidence:.72,source:'v6-manual-scope'};
      }
    }else{
      baseFound=activeDetectedPanel||detectGraph();
    }
    if(!baseFound)throw Error('Energy per Band candidate could not be localized inside the active ROI.');
    await v631Stage(22,'Energy per Band','Numeric plot geometry localized inside the selected ROI.');

    let energy;
    if(roiEditorState.energy){
      energy={...roiEditorState.energy,source:'manual-energy-authoritative-v6.3.4'};
      // Manual Energy ROI is the exact crop. Localize numeric plot only INSIDE it.
      let pg=null;
      try{pg=EGSAnalysisV2.plotFromGrid(ctx,canvas,energy)}catch(_){}
      if(pg?.plot)energy.plot=pg.plot;
      if(!energy.plot){
        try{
          const local=EGSAnalysisV2.autoPanelDetect(ctx,canvas,energy);
          if(local?.plot)energy.plot=local.plot;
        }catch(_){}
      }
    }else{
      energy=v6RefineBlackEnergyCrop(baseFound)||baseFound;
      energy.plot=baseFound.plot||energy.plot;
      if(!energy.plot){
        const pg=EGSAnalysisV2.plotFromGrid(ctx,canvas,energy);
        if(pg?.plot)energy.plot=pg.plot;
      }
    }
    if(!energy.plot)throw Error('Energy per Band numeric plot could not be localized.');
    await v631Stage(32,'Channel detection','Locating Channel ROI and enabled checked boxes.');

    // v6.3.4 ROI LOCK:
    // Analyze must never move/resize the visible Energy ROI.
    // Internal energy/plot geometry may be refined for numeric analysis only.
    if(!roiManual){
      activeDetectedPanel={...energy,plot:{...energy.plot}};
    }

    // Step 2 Channel section.
    let chInfo;
    if(roiEditorState.channel){
      const det=v621DetectCheckedChannelsFromKnownLayout(roiEditorState.channel);
      chInfo={present:true,channels:det.channels,crop:{...roiEditorState.channel},
              boxes:det.boxes,disabled:det.disabled,source:'manual-channel-authoritative+'+det.source};
    }else{
      chInfo=v6CheckedChannels16(energy);
    }

    await v631Stage(45,'Y-axis grid','Detecting horizontal grid lattice before reading numeric labels.');

    // Step 3 Energy crop / Step 5-6 Y scale & mode.
    const prep=v6PreparedFromEnergy(energy);
    if(!prep)throw Error('Energy plot geometry unavailable.');
    const axis=v6AxisDecision(energy,prep);
    await v631Stage(60,'Y-axis anchors',
      axis.cal
        ? `Grid interval calibrated from ${axis.cal.supportRows||0} numeric anchor row(s).`
        : `Grid/anchor calibration is still incomplete.`);
    if(axis.mode==='Unknown'||!axis.cal){
      v6RenderPreviews(energy,chInfo,null,null,'Unknown');
      const partial={mode:'Unknown',channel:null,confidence:.30,low:NaN,high:NaN,
        message:`Y-axis grid/anchor calibration incomplete: ${axis.gridAnchor?.reason||'unknown'}.`,
        box:{...energy},analysisBox:{...energy},insets:prep.insets,
        diagnostics:{axis_grid_anchor:axis.gridAnchor||null}};
      currentResult=partial;showResult(partial);
      setStatus(`Y軸: gridは主判定、数値はanchorとして解析しましたが未確定 (${axis.gridAnchor?.reason||'unknown'})。`);
      v631FailProcessing(`Y-axis calibration incomplete: ${axis.gridAnchor?.reason||'unknown'}`);
      return;
    }

    // Step 7: read lower numeric labels and vertical-grid lattice.
    await v631Stage(70,'X-axis','Reading Sample scale and vertical grid.');
    const xCal=v6XAxisCalibration(energy.plot);
    energy.plot._xCal={...xCal};
    const mode=axis.gridValueStep>=.5?'Gain':'Noise';

    // Step 8-11 fixed requested ranges + robust spike-rejected mean.
    const lowRange=mode==='Gain'?[0,330]:[0,260],
          highRange=mode==='Gain'?[340,500]:[270,500],
          lowPop=v6SignalPopulation(energy.plot,axis.cal,mode,...lowRange),
          highPop=v6SignalPopulation(energy.plot,axis.cal,mode,...highRange);
    await v631Stage(84,'Low / High markers',
      `Spike-rejected marker populations: Low ${lowPop?.count||0}, High ${highPop?.count||0}.`);

    // Step 4 channel resolution after marker color is known.
    const markerHue=(highPop?.hue??lowPop?.hue),
          channels=chInfo.present?chInfo.channels:[],
          autoDecision=channels.length===1
            ?{channel:channels[0],source:'single checked enabled channel',confidence:1}
            :channels.length>1
              ?channelDecision(channels,{hue:markerHue,score:.8})
              :{channel:null,source:chInfo.present?'no checked enabled channel':'channel section absent',confidence:.5},
          decision=manualFinalChannel==null
            ?autoDecision
            :{channel:manualFinalChannel,source:'manual final channel',confidence:1};

    await v631Stage(93,'Rendering result','Updating Channel crop and Low/High analysis lines.');
    v6RenderPreviews(energy,chInfo,lowPop,highPop,mode);

    if(!lowPop||!highPop||!Number.isFinite(lowPop.value)||!Number.isFinite(highPop.value)){
      const partial={mode,channel:decision.channel,confidence:.55,low:NaN,high:NaN,
        message:`Signal population incomplete; Low ${lowPop?.count||0} samples / High ${highPop?.count||0} samples.`,
        box:{...energy},analysisBox:{...energy},insets:prep.insets};
      currentResult=partial;showResult(partial);
      setStatus('軸は確定。Low/High marker populationの一方を確定できません。');
      v631FailProcessing(`Marker population incomplete: Low ${lowPop?.count||0}, High ${highPop?.count||0}.`);
      return;
    }

    const result={
      mode,channel:decision.channel,channelSource:decision.source,
      confidence:Math.min(.98,Math.max(.62,(axis.axisFamily?.confidence||.6)*.55+.40)),
      low:lowPop.value,high:highPop.value,provisional:false,
      box:{...energy},analysisBox:{...energy},insets:prep.insets,
      axisCal:axis.cal,
      diagnostics:{
        pipeline:'v6.3-grid-anchor+unified-roi-editor',
        manual_roi_target:roiEditorState.active?roiEditorState.target:null,
        rotation_correction_deg:v6DeskewAngle,
        channel_section_present:chInfo.present,
        checked_channels:channels,
        marker_hue:markerHue,
        y_grid_value_step:axis.gridValueStep,
        y_axis_source:axis.cal?.source,
        y_axis_anchor_support:axis.cal?.supportRows,
        y_axis_single_anchor_fallback:!!axis.cal?.singleAnchorFallback,
        y_axis_affine_source:axis.cal?.affineSource,
        y_axis_bottom_grid_y:axis.cal?.bottomGridY,
        y_axis_bottom_grid_value:axis.cal?.bottomGridValue,
        x_axis_x0:xCal?.x0,
        x_axis_x500:xCal?.x500,
        x_scale:{min:0,max:500,source:xCal.source,recognized_labels:xCal.labels||[]},
        low_range:lowRange,high_range:highRange,
        low_samples:lowPop.count,high_samples:highPop.count,
        low_mad_px:lowPop.mad,high_mad_px:highPop.mad
      },
      message:`v6 12-stage pipeline; rotation ${v6DeskewAngle.toFixed(2)}°; `+
        `${chInfo.present?'Channel section detected':'Channel section absent'}; `+
        `Y-grid step ${axis.gridValueStep}; X scale 0-500 (${xCal.source}); `+
        `${mode} ranges Low ${lowRange[0]}-${lowRange[1]}, High ${highRange[0]}-${highRange[1]}; `+
        `spike-rejected mean ${lowPop.count}/${highPop.count} samples`
    };
    currentResult=result;
    showResult(result);
    setStatus('Analysis complete — v6 12-stage pipeline.');
    v631FinishProcessing('Complete',`${mode} analysis complete.`);
  }catch(e){
    console.error('v6 analyze failed',e);
    setStatus(`v6 pipeline — ${e?.name?e.name+': ':''}${e?.message||e}`);
    v631FailProcessing(`${e?.name?e.name+': ':''}${e?.message||e}`);
  }finally{
    if(visibleROILock){
      roi={...visibleROILock};
      roiManual=visibleROILockManual;
      if(roiManual)els.roi.classList.add('manual'); else els.roi.classList.remove('manual');
      renderROI();
    }
  }
}

function detectGraph(){
  const found=stableEnergyPanel();
  if(!found)return null;
  return{
    x:found.x,y:found.y,w:found.w,h:found.h,
    confidence:found.confidence||.80,
    source:found.source||'stable-panel-cache',
    plot:found.plot?{...found.plot}:null,
    darkFrame:found.darkFrame||null,
    diagnostics:{...(found.diagnostics||{}),frameGeneration:analysisFrameGeneration}
  };
}
function canvasDisplayTransform(){
  const cr=canvas.getBoundingClientRect(),
        sr=els.stage.getBoundingClientRect();
  return{
    scaleX:cr.width/Math.max(1,canvas.width),
    scaleY:cr.height/Math.max(1,canvas.height),
    offsetX:cr.left-sr.left,
    offsetY:cr.top-sr.top,
    canvasRect:cr,
    stageRect:sr
  };
}
function renderROI(){
  if(!roi)return;
  const m=canvasDisplayTransform(),sx=m.scaleX,sy=m.scaleY,ox=m.offsetX,oy=m.offsetY;
  Object.assign(els.roi.style,{left:`${ox+roi.x*sx}px`,top:`${oy+roi.y*sy}px`,width:`${roi.w*sx}px`,height:`${roi.h*sy}px`});
  els.roi.classList.remove('hidden');
}
window.addEventListener('resize',renderROI);
let drag=null;
els.roi.addEventListener('pointerdown',e=>{if(!roiManual)return;e.preventDefault();els.roi.setPointerCapture(e.pointerId);drag={x:e.clientX,y:e.clientY,orig:{...roi},handle:e.target?.dataset?.handle||'move'}});
els.roi.addEventListener('pointermove',e=>{if(!drag||!roiManual)return;const m=canvasDisplayTransform(),dx=(e.clientX-drag.x)/Math.max(1e-9,m.scaleX),dy=(e.clientY-drag.y)/Math.max(1e-9,m.scaleY),o=drag.orig,minW=Math.max(70,canvas.width*.10),minH=Math.max(45,canvas.height*.05);if(drag.handle==='move'){roi.x=EGSCore.clamp(o.x+dx,0,canvas.width-o.w);roi.y=EGSCore.clamp(o.y+dy,0,canvas.height-o.h);roi.w=o.w;roi.h=o.h}else{let left=o.x,top=o.y,right=o.x+o.w,bottom=o.y+o.h;if(drag.handle.includes('l'))left=EGSCore.clamp(o.x+dx,0,right-minW);if(drag.handle.includes('r'))right=EGSCore.clamp(o.x+o.w+dx,left+minW,canvas.width);if(drag.handle.includes('t'))top=EGSCore.clamp(o.y+dy,0,bottom-minH);if(drag.handle.includes('b'))bottom=EGSCore.clamp(o.y+o.h+dy,top+minH,canvas.height);roi={x:left,y:top,w:right-left,h:bottom-top}}renderROI();v63CommitActiveROI()});
els.roi.addEventListener('pointerup',()=>{v63CommitActiveROI();drag=null});els.roi.addEventListener('pointercancel',()=>{v63CommitActiveROI();drag=null});
function lineGroups(values,threshold){const idx=[];for(let i=0;i<values.length;i++)if(values[i]>=threshold)idx.push(i);const groups=[];for(const v of idx){if(!groups.length||v-groups.at(-1).at(-1)>2)groups.push([v]);else groups.at(-1).push(v)}return groups.map(g=>g.reduce((a,b)=>a+b,0)/g.length)}
function bestEvenRun(groups,minGap,maxGap){
  if(groups.length<2)return null;let best=null;
  for(let i=0;i<groups.length-1;i++)for(let j=i+1;j<groups.length;j++){
    const gap=groups[j]-groups[i];if(gap<minGap||gap>maxGap)continue;const seq=[groups[i],groups[j]];let last=groups[j];
    for(let k=j+1;k<groups.length;k++){const d=groups[k]-last;if(Math.abs(d-gap)<=Math.max(2,gap*.28)){seq.push(groups[k]);last=groups[k]}}
    if(seq.length<2)continue;const span=seq.at(-1)-seq[0],score=seq.length*3+span/Math.max(1,gap);
    if(!best||score>best.score)best={seq,gap,score}
  }return best
}
function plotInsets(box){
  const x0=Math.max(0,Math.floor(box.x)),y0=Math.max(0,Math.floor(box.y)),w=Math.max(1,Math.min(canvas.width-x0,Math.floor(box.w))),h=Math.max(1,Math.min(canvas.height-y0,Math.floor(box.h))),im=ctx.getImageData(x0,y0,w,h).data,row=new Uint32Array(h),col=new Uint32Array(w);
  for(let y=0;y<h;y++)for(let x=0;x<w;x++){const i=(y*w+x)*4;if(isGreen(im[i],im[i+1],im[i+2])){row[y]++;col[x]++}}
  // Long-line thresholds suppress green title/axis-label text.
  const rows=lineGroups(row,Math.max(7,w*.30)),cols=lineGroups(col,Math.max(7,h*.30));
  const rr=bestEvenRun(rows,Math.max(5,h*.055),h*.38),cc=bestEvenRun(cols,Math.max(6,w*.055),w*.30);
  let ty,by,lx,rx;
  if(rr&&rr.seq.length>=3){ty=rr.seq[0];by=rr.seq.at(-1)}else if(rows.length>=2){ty=rows[0];by=rows.at(-1)}
  if(cc&&cc.seq.length>=3){lx=cc.seq[0];rx=cc.seq.at(-1)}else if(cols.length>=2){lx=cols[0];rx=cols.at(-1)}
  if([ty,by,lx,rx].every(Number.isFinite)&&rx-lx>w*.38&&by-ty>h*.25){
    return{left:EGSCore.clamp(lx/w,.01,.38),right:EGSCore.clamp(1-rx/w,.002,.26),top:EGSCore.clamp(ty/h,.002,.35),bottom:EGSCore.clamp(1-by/h,.01,.48),source:'major-grid',rows,cols};
  }
  // v1.7.3 rescue: perspective/moire can weaken long green grid lines on iPhone.
  // Use a lower threshold only to recover plot geometry; this does not determine Gain/Noise.
  const rrows=lineGroups(row,Math.max(5,w*.14)),rcols=lineGroups(col,Math.max(5,h*.14));
  if(rrows.length>=2&&rcols.length>=2){
    const rty=rrows[0],rby=rrows.at(-1),rlx=rcols[0],rrx=rcols.at(-1);
    if(rrx-rlx>w*.36&&rby-rty>h*.22){
      return{left:EGSCore.clamp(rlx/w,.01,.40),right:EGSCore.clamp(1-rrx/w,.002,.30),top:EGSCore.clamp(rty/h,.002,.38),bottom:EGSCore.clamp(1-rby/h,.005,.50),source:'relaxed-grid',rows:rrows,cols:rcols};
    }
  }
  // Dark-plot fallback: locate the densest contiguous dark rectangle inside the ROI.
  const rscore=new Float32Array(h),cscore=new Float32Array(w);
  for(let y=0;y<h;y++)for(let x=0;x<w;x++){const i=(y*w+x)*4,d=(im[i]+im[i+1]+im[i+2])/3;if(d<105){rscore[y]++;cscore[x]++}}
  const rids=[];for(let y=0;y<h;y++)if(rscore[y]>w*.48)rids.push(y);const cids=[];for(let x=0;x<w;x++)if(cscore[x]>h*.40)cids.push(x);
  if(rids.length&&cids.length){ty=Math.min(...rids);by=Math.max(...rids);lx=Math.min(...cids);rx=Math.max(...cids);if(rx-lx>w*.38&&by-ty>h*.24)return{left:lx/w,right:1-rx/w,top:ty/h,bottom:1-by/h,source:'dark-plot'}}
  // Last-resort ROI geometry: do not stop analysis solely because green grid
  // confirmation failed. Preserve room on the left for Y-axis labels and on the
  // bottom for Sample# labels while using the ROI as the plot envelope.
  return{left:.16,top:.10,right:.025,bottom:.18,source:'roi-estimate',confidence:.28}
}
function checkedChannels(box){
  // Search the checkbox row relative to the graph rather than a fixed 320px offset.
  const d=ctx.getImageData(0,0,canvas.width,canvas.height).data,left=Math.max(0,box.x-box.w*1.22),right=Math.max(left+8,box.x-box.w*.06),top=Math.max(0,box.y+box.h*.52),bottom=Math.min(canvas.height,box.y+box.h*1.35),rw=right-left,rh=bottom-top;if(rw<40||rh<15)return[];
  const out=[],slot=rw/8;for(let ch=0;ch<8;ch++){const sx=Math.floor(left+slot*ch+slot*.16),ex=Math.floor(left+slot*(ch+1)-slot*.16);let best=0;for(let yy=Math.floor(top);yy<bottom;yy+=Math.max(1,Math.floor(rh/18))){let dark=0,total=0;for(let y=yy;y<Math.min(bottom,yy+Math.max(4,rh*.16));y++)for(let x=sx;x<ex;x++){const i=(y*canvas.width+x)*4;if(d[i]<82&&d[i+1]<82&&d[i+2]<82)dark++;total++}best=Math.max(best,dark/Math.max(1,total))}if(best>.16)out.push(ch)}return out
}
function greenRowGroups(box){const x0=Math.max(0,Math.floor(box.x)),y0=Math.max(0,Math.floor(box.y)),w=Math.max(1,Math.min(canvas.width-x0,Math.floor(box.w))),h=Math.max(1,Math.min(canvas.height-y0,Math.floor(box.h))),im=ctx.getImageData(x0,y0,w,h).data,row=new Uint32Array(h);for(let y=0;y<h;y++)for(let x=0;x<w;x++){const i=(y*w+x)*4;if(isGreen(im[i],im[i+1],im[i+2]))row[y]++}const centers=lineGroups(row,Math.max(8,w*.20));return{groups:centers.map(v=>[v]),centers,w,h}}
const axisTemplateCache=new Map();
function axisCandidates(mode='Any'){
  const out=[];
  const add=(value,forms,family)=>out.push({value,forms:[...new Set(forms)],family});
  if(mode==='Gain'||mode==='Any'){
    for(let v=0;v<=4;v++)add(v,[v.toFixed(1)],'Gain');
  }
  if(mode==='Noise'||mode==='Any'){
    for(let i=0;i<=5;i++){
      const v=i/100;
      add(v,[v.toFixed(3),v.toFixed(4),v.toFixed(5)],'Noise');
    }
  }
  return out;
}
function normPoints(points,tw=112,th=28){
  if(!points||points.length<4)return null;
  let minx=Infinity,miny=Infinity,maxx=-Infinity,maxy=-Infinity;
  for(const p of points){minx=Math.min(minx,p[0]);miny=Math.min(miny,p[1]);maxx=Math.max(maxx,p[0]);maxy=Math.max(maxy,p[1])}
  const w=Math.max(1,maxx-minx+1),h=Math.max(1,maxy-miny+1),sc=Math.min((tw-4)/w,(th-4)/h),nw=Math.max(1,Math.round(w*sc)),nh=Math.max(1,Math.round(h*sc));
  const ox=tw-nw-2,oy=Math.floor((th-nh)/2),arr=new Uint8Array(tw*th);
  for(const p of points){
    const xx=ox+Math.min(nw-1,Math.max(0,Math.round((p[0]-minx)*sc))),
          yy=oy+Math.min(nh-1,Math.max(0,Math.round((p[1]-miny)*sc)));
    arr[yy*tw+xx]=1;
  }
  arr._aspect=w/Math.max(1,h);
  arr._density=points.length/Math.max(1,w*h);
  arr._origW=w;arr._origH=h;
  const xp=new Float32Array(16),yp=new Float32Array(8);
  for(const p of points){
    xp[Math.min(15,Math.floor((p[0]-minx)/Math.max(1,w)*16))]++;
    yp[Math.min(7,Math.floor((p[1]-miny)/Math.max(1,h)*8))]++;
  }
  const n=Math.max(1,points.length);
  for(let i=0;i<xp.length;i++)xp[i]/=n;
  for(let i=0;i<yp.length;i++)yp[i]/=n;
  arr._xp=xp;arr._yp=yp;
  return arr;
}
function observedAxisLabelNorm(x0,y0,w,h){
  x0=Math.max(0,Math.floor(x0));y0=Math.max(0,Math.floor(y0));
  w=Math.max(1,Math.min(canvas.width-x0,Math.floor(w)));h=Math.max(1,Math.min(canvas.height-y0,Math.floor(h)));
  if(w<3||h<3)return null;
  const im=ctx.getImageData(x0,y0,w,h).data,pts=[];
  // Keep the part nearest the plot. Use a deliberately permissive green/chroma
  // threshold because iPhone photos soften the tiny 1.0/2.0/3.0 glyph edges.
  const keep=Math.floor(w*.14);
  for(let y=0;y<h;y++)for(let x=keep;x<w;x++){
    const i=(y*w+x)*4,r=im[i],g=im[i+1],b=im[i+2],
          mx=Math.max(r,g,b),mn=Math.min(r,g,b),sat=mx-mn,
          chroma=g-Math.max(r,b),lum=(r+g+b)/3;
    // Axis glyphs are nominally green, but iPhone photos often make their
    // anti-aliased edges yellow/grey/near-white. This crop is already limited
    // to the Y-label strip, so a softened bright-glyph fallback is safe.
    const greenish=g>28 && ((g>r*1.025&&g>b*.99&&chroma>2) || (chroma>7&&lum>24));
    const softBright=lum>72 && sat<58;
    if(greenish||softBright)pts.push([x-keep,y]);
  }
  return normPoints(pts);
}
function axisTextTemplate(text,font,size=24,weight=''){
  const key=text+'|'+font+'|'+size+'|'+weight;
  if(axisTemplateCache.has(key))return axisTemplateCache.get(key);
  const c=document.createElement('canvas');c.width=190;c.height=54;
  const q=c.getContext('2d');q.fillStyle='#000';q.fillRect(0,0,c.width,c.height);
  q.font=`${weight?weight+' ':''}${size}px ${font}`;q.textBaseline='top';q.fillStyle='#fff';q.fillText(text,2,2);
  const im=q.getImageData(0,0,c.width,c.height).data,pts=[];
  for(let y=0;y<c.height;y++)for(let x=0;x<c.width;x++){
    const i=(y*c.width+x)*4;if(im[i]>75)pts.push([x,y]);
  }
  const n=normPoints(pts);axisTemplateCache.set(key,n);return n;
}
function projectionSimilarity(a,b,key){
  const A=a?.[key],B=b?.[key];if(!A||!B||A.length!==B.length)return .5;
  let dot=0,aa=0,bb=0;
  for(let i=0;i<A.length;i++){dot+=A[i]*B[i];aa+=A[i]*A[i];bb+=B[i]*B[i]}
  return aa>0&&bb>0?dot/Math.sqrt(aa*bb):0;
}
function maskSimilarity(a,b,tw=112,th=28){
  if(!a||!b)return 0;let iou=0;
  for(let dy=-3;dy<=3;dy++)for(let dx=-4;dx<=4;dx++){
    let inter=0,union=0;
    for(let y=0;y<th;y++)for(let x=0;x<tw;x++){
      const aa=a[y*tw+x],xx=x-dx,yy=y-dy,bb=(xx>=0&&xx<tw&&yy>=0&&yy<th)?b[yy*tw+xx]:0;
      if(aa&&bb)inter++;if(aa||bb)union++;
    }
    if(union)iou=Math.max(iou,inter/union);
  }
  const arA=Math.max(.05,a._aspect||1),arB=Math.max(.05,b._aspect||1),
        aspect=Math.exp(-Math.abs(Math.log(arA/arB))*1.25),
        dA=a._density||.2,dB=b._density||.2,
        density=Math.max(0,1-Math.abs(dA-dB)/Math.max(.08,(dA+dB)*.8)),
        xp=projectionSimilarity(a,b,'_xp'),yp=projectionSimilarity(a,b,'_yp');
  return .52*iou+.18*aspect+.10*density+.12*xp+.08*yp;
}
function axisLabelHypotheses(norm,mode='Any',limit=6){
  if(!norm)return[];
  const fonts=['Arial','Arial Narrow','Helvetica','Tahoma','Verdana','Courier New','monospace','sans-serif'],
        sizes=[18,20,22,24,26,28],byValue=new Map();
  for(const c of axisCandidates(mode))for(const text of c.forms)for(const font of fonts)for(const size of sizes){
    const score=maskSimilarity(norm,axisTextTemplate(text,font,size));
    const k=c.family+'|'+c.value,prev=byValue.get(k);
    if(!prev||score>prev.conf)byValue.set(k,{value:c.value,conf:score,text,family:c.family});
  }
  const ranked=[...byValue.values()].sort((a,b)=>b.conf-a.conf);
  if(!ranked.length)return[];
  const best=ranked[0].conf;
  return ranked.filter(x=>x.conf>=.14 && x.conf>=best-.075).slice(0,Math.min(limit,4));
}
function recognizeAxisLabel(norm,mode='Any'){
  const h=axisLabelHypotheses(norm,mode,1);return h.length&&h[0].conf>=.12?h[0]:null;
}
function fitAxisLabelSequence(rows,bestBase){
  let best=null;
  const sameFamily=(a,b)=>a.family===b.family;
  for(let i=0;i<rows.length;i++)for(let j=i+1;j<rows.length;j++){
    const Arow=rows[i],Brow=rows[j];
    for(const A of Arow.hyps)for(const B of Brow.hyps){
      if(!sameFamily(A,B)||B.value>=A.value||Brow.y-Arow.y<3)continue;
      const slope=(B.value-A.value)/(Brow.y-Arow.y);
      if(!(slope<0))continue;
      const unit=A.family==='Gain'?1:.01,
            pxPerUnit=Math.abs(unit/slope);
      // A true major-axis numeric series should advance about one displayed
      // unit per major-grid spacing. Broad acceptance allowed 3.0/2.0/1.0
      // glyphs to masquerade as 0.10/0.04/0.02. Keep perspective tolerance,
      // but require the numeric step to agree with the measured grid lattice.
      if(pxPerUnit<bestBase*.62||pxPerUnit>bestBase*1.62)continue;
      const intercept=A.value-slope*Arow.y;
      let support=0,conf=A.conf+B.conf,anchors=[
        {y:Arow.y,value:A.value,conf:A.conf,text:A.text,family:A.family},
        {y:Brow.y,value:B.value,conf:B.conf,text:B.text,family:B.family}
      ];
      for(let k=0;k<rows.length;k++){
        if(k===i||k===j)continue;
        const row=rows[k],expected=slope*row.y+intercept,
              tol=A.family==='Gain'?.34:.0038;
        let hit=null;
        for(const h of row.hyps){
          if(h.family!==A.family)continue;
          const err=Math.abs(h.value-expected);
          if(err<=tol&&(!hit||err<hit.err))hit={...h,err};
        }
        if(hit){support++;conf+=hit.conf;anchors.push({y:row.y,value:hit.value,conf:hit.conf,text:hit.text,family:hit.family})}
      }
      const sortedAnchors=[...anchors].sort((a,b)=>a.y-b.y);
      let gapBad=false;
      for(let z=1;z<sortedAnchors.length;z++){
        const gridGap=Math.abs((sortedAnchors[z].y-sortedAnchors[z-1].y)/bestBase),
              valueGap=Math.abs(sortedAnchors[z].value-sortedAnchors[z-1].value)/unit;
        if(gridGap>2.45||valueGap>2.45){gapBad=true;break}
      }
      if(gapBad)continue;
      const maxVal=Math.max(...sortedAnchors.map(a=>a.value)),
            minVal=Math.min(...sortedAnchors.map(a=>a.value));
      if(A.family==='Gain'&&(minVal<-.01||maxVal>4.01))continue;
      if(A.family==='Noise'&&(minVal<-.0001||maxVal>.0501))continue;
      const meanConf=conf/(2+support),
            directStrong=sortedAnchors.filter(a=>a.conf>=.16).length,
            spacingPenalty=Math.min(1.5,Math.abs(pxPerUnit-bestBase)/Math.max(1,bestBase)),
            score=meanConf+support*.10+Math.min(.14,directStrong*.045)-spacingPenalty*.10;
      if(directStrong<2)continue;
      if(!best||score>best.score)best={score,slope,intercept,family:A.family,anchors:sortedAnchors,pxPerUnit};
    }
  }
  return best;
}

function supportedSingleAxisAnchor(rows,bestBase,modeHint){
  let best=null;
  const families=modeHint==='Any'?['Gain','Noise']:[modeHint];
  for(const family of families){
    const unit=family==='Gain'?1:.01,
          tol=family==='Gain'?.38:.0042;
    for(const row of rows)for(const h of row.hyps){
      if(h.family!==family||h.conf<.13)continue;
      let support=0,score=h.conf,anchors=[{y:row.y,value:h.value,conf:h.conf,text:h.text,family}],
          totalChecked=0;
      for(const other of rows){
        if(other===row)continue;
        const gridSteps=Math.round((other.y-row.y)/bestBase);
        if(gridSteps===0||Math.abs(gridSteps)>5)continue;
        totalChecked++;
        const expected=h.value-gridSteps*unit;
        let hit=null;
        for(const q of other.hyps){
          if(q.family!==family)continue;
          const err=Math.abs(q.value-expected);
          if(err<=tol&&q.conf>=.045&&(!hit||q.conf>hit.conf))hit={...q,err};
        }
        if(hit){
          support++;
          score+=hit.conf*.8;
          anchors.push({y:other.y,value:hit.value,conf:hit.conf,text:hit.text,family});
        }
      }
      // A single OCR glyph is never enough anymore. Require at least one
      // neighboring grid row to weakly corroborate the expected numeric series.
      if(support<1)continue;
      score+=support*.10;
      if(!best||score>best.score)best={score,family,base:h,support,anchors};
    }
  }
  return best;
}
function axisCalibrationBounds(cal,centersAbs){
  if(!cal||!Array.isArray(centersAbs)||!centersAbs.length)return null;
  const values=centersAbs.map(y=>(cal.zeroY-y)/Math.max(1e-9,cal.stepPx)*cal.stepValue);
  return{
    min:Math.min(...values),
    max:Math.max(...values),
    values
  };
}
function yAxisCalibration(box,insets,modeHint='Any'){
  const g=EGSCore.geometry(box,insets),
        gx0=Math.max(0,Math.floor(g.x0)),gx1=Math.min(canvas.width,Math.ceil(g.x1)),
        gy0=Math.max(0,Math.floor(g.y0)),gy1=Math.min(canvas.height,Math.ceil(g.y1)),
        w=Math.max(1,gx1-gx0),h=Math.max(1,gy1-gy0),
        im=ctx.getImageData(gx0,gy0,w,h).data,row=new Uint32Array(h);

  for(let y=0;y<h;y++)for(let x=0;x<w;x++){
    const i=(y*w+x)*4;if(isGreen(im[i],im[i+1],im[i+2]))row[y]++;
  }
  let centers=lineGroups(row,Math.max(6,w*(insets.source==='major-grid'?.20:.11))).filter(v=>v>=1&&v<=h-2);
  if(centers.length<2)return null;

  const merged=[];
  for(const y of centers){
    if(!merged.length||y-merged.at(-1)>Math.max(3,h*.022))merged.push(y);
    else merged[merged.length-1]=(merged.at(-1)+y)/2;
  }
  centers=merged;
  if(centers.length<2)return null;

  const diffs=[];
  for(let i=1;i<centers.length;i++){
    const d=centers[i]-centers[i-1];
    if(d>=Math.max(4,h*.055)&&d<=h*.55)diffs.push(d);
  }
  if(!diffs.length)return null;
  const bases=[];
  for(const d of diffs)for(const k of [1,2,3]){
    const b=d/k;if(b>=h*.055&&b<=h*.48)bases.push(b);
  }
  if(!bases.length)return null;
  let bestBase=null,bestErr=Infinity;
  for(const b of bases){
    const err=EGSCore.median(diffs.map(d=>{const m=Math.max(1,Math.round(d/b));return Math.abs(d-m*b)/b}));
    if(err<bestErr){bestErr=err;bestBase=b}
  }
  if(!Number.isFinite(bestBase)||bestBase<4||bestErr>.48)return null;

  // Read every visible Y label independently of the currently inferred mode.
  // This allows 3.0/2.0/1.0 to correct an erroneous Auto=Noise decision.
  const stripLeft=Math.max(box.x,g.x0-(g.x1-g.x0)*.42),
        stripRight=Math.min(g.x0-1,box.x+box.w*.42),
        rows=[];
  for(const cy of centers){
    const ay=gy0+cy,hh=Math.max(9,bestBase*.48),
          norm=observedAxisLabelNorm(stripLeft,ay-hh,stripRight-stripLeft,hh*2+1),
          hyps=axisLabelHypotheses(norm,modeHint==='Any'?'Any':modeHint,9);
    if(hyps.length)rows.push({
      y:ay,hyps,
      labelAspect:Number.isFinite(norm?._aspect)?norm._aspect:0,
      labelWidth:Number.isFinite(norm?._origW)?norm._origW:0,
      labelHeight:Number.isFinite(norm?._origH)?norm._origH:0
    });
  }

  const seq=fitAxisLabelSequence(rows,bestBase);

  // v1.8.5: grid gives spacing, but the zero row is solved from label/grid
  // ordinal consensus. Never assume the lowest detected major line is zero.
  const unit=modeHint==='Noise'?.01:1,
        centersAbs=centers.map(cy=>gy0+cy).sort((a,b)=>a-b);

  if((modeHint==='Gain'||modeHint==='Noise')&&centersAbs.length>=3){
    const idxs=centersAbs.map((_,i)=>i),
          mi=EGSCore.median(idxs),my=EGSCore.median(centersAbs),
          num=idxs.reduce((a,i,k)=>a+(i-mi)*(centersAbs[k]-my),0),
          den=idxs.reduce((a,i)=>a+(i-mi)*(i-mi),0),
          rowStep=den>0?num/den:bestBase,
          rowY0=my-rowStep*mi,
          gridResiduals=centersAbs.map((y,i)=>Math.abs(y-(rowY0+i*rowStep))/Math.max(1,bestBase)),
          regular=gridResiduals.filter(r=>r<=.24).length;

    if(regular>=Math.max(3,centersAbs.length-1)){
      const votes=[];
      for(const row of rows){
        let nearest=0,bd=Infinity;
        for(let i=0;i<centersAbs.length;i++){
          const d=Math.abs(centersAbs[i]-row.y);
          if(d<bd){bd=d;nearest=i}
        }
        if(bd>Math.abs(rowStep)*.46)continue;
        for(const h of row.hyps){
          if(h.family!==modeHint||h.conf<.14)continue;
          const q=h.value/unit;
          if(!Number.isFinite(q))continue;
          const qRound=Math.round(q);
          if(Math.abs(q-qRound)>.18)continue;
          const offset=nearest+qRound;
          votes.push({offset,rowIndex:nearest,y:row.y,value:h.value,conf:h.conf,text:h.text});
        }
      }

      if(votes.length>=2){
        const buckets=new Map();
        for(const v of votes){
          const b=buckets.get(v.offset)||{score:0,count:0,items:[]};
          b.score+=v.conf*v.conf;
          b.count++;
          b.items.push(v);
          buckets.set(v.offset,b);
        }
        const ranked=[...buckets.entries()].sort((a,b)=>b[1].score-a[1].score);
        const [zeroIndex,bestVote]=ranked[0],
              second=ranked[1]?.[1],
              decisive=bestVote.count>=2 && (!second || bestVote.score>=second.score*1.20);

        if(decisive){
          const zeroY=rowY0+zeroIndex*rowStep,
                anchors=bestVote.items.map(v=>({
                  y:v.y,value:v.value,conf:v.conf,text:v.text,
                  rowIndex:v.rowIndex,zeroIndex
                })),
                cal={
                  zeroY,
                  stepPx:Math.abs(rowStep),
                  stepValue:unit,
                  source:'zero-row-label-grid-consensus',
                  anchors,
                  fitScore:bestVote.score/Math.max(1,bestVote.count),
                  family:modeHint,
                  modeHint,
                  zeroRowIndex:zeroIndex,
                  gridResidual:EGSCore.median(gridResiduals),
                  labelAspect:EGSCore.median(bestVote.items.map(v=>{
                    const rr=rows.find(r=>Math.abs(r.y-v.y)<1.5);
                    return rr?.labelAspect||0;
                  }).filter(v=>v>0)),
                  labelWidths:bestVote.items.map(v=>{
                    const rr=rows.find(r=>Math.abs(r.y-v.y)<1.5);
                    return rr?.labelWidth||0;
                  }).filter(v=>v>0)
                };
          cal.gridBounds=axisCalibrationBounds(cal,centersAbs);
          cal.completedAnchors=completedAxisAnchorSeries(cal);
          return cal;
        }
      }
    }
  }
  return null;
}



function completedAxisAnchorSeries(cal){
  if(!cal?.anchors?.length)return[];
  const unit=cal.stepValue||1,
        a=[...cal.anchors].sort((x,y)=>y.value-x.value),
        out=[...a];
  for(let i=0;i<a.length-1;i++){
    const hi=a[i],lo=a[i+1],
          steps=Math.round((hi.value-lo.value)/unit);
    if(steps>1&&steps<=4){
      for(let k=1;k<steps;k++){
        const value=hi.value-k*unit,
              y=hi.y+(lo.y-hi.y)*(k/steps);
        if(!out.some(q=>Math.abs(q.value-value)<unit*.15))
          out.push({value,y,conf:Math.min(hi.conf||.1,lo.conf||.1)*.75,interpolated:true});
      }
    }
  }
  return out.sort((x,y)=>x.y-y.y);
}

function axisVisualFamilyEvidence(cal){
  if(!cal)return{Gain:0,Noise:0,aspect:0,widthMed:0};
  const aspect=cal.labelAspect||0,
        widths=cal.labelWidths||[],
        widthMed=widths.length?EGSCore.median(widths):0;
  let Gain=0,Noise=0;

  // Noise labels such as 0.04000 are much wider than Gain labels such as 3.0.
  // This direct glyph geometry prevents 0.04000 from being read as 4.0.
  if(aspect>=2.15){Noise+=.62;Gain-=.42}
  else if(aspect>=1.75){Noise+=.34;Gain-=.18}
  else if(aspect>0&&aspect<=1.48){Gain+=.34;Noise-=.16}

  if(widthMed>=24)Noise+=.18;
  else if(widthMed>0&&widthMed<=17)Gain+=.12;
  return{Gain,Noise,aspect,widthMed};
}

function axisHypothesisScore(cal,family,traceFeatures,traceMode){
  if(!cal)return -Infinity;
  const anchors=cal.anchors||[],n=anchors.length,
        meanConf=n?anchors.reduce((a,b)=>a+(b.conf||0),0)/n:0,
        vals=anchors.map(a=>Math.abs(a.value)).filter(Number.isFinite),
        medVal=vals.length?EGSCore.median(vals):0;
  let score=(cal.fitScore||meanConf||0)+Math.min(.30,n*.08)+Math.min(.18,meanConf*.55);

  // Numeric-scale context: Gain labels are typically order-unity (1.0,2.0,3.0);
  // Noise labels are small decimals. This is context, not a hard-coded axis top.
  const visual=axisVisualFamilyEvidence(cal);
  if(family==='Gain'){
    if(medVal>=.65)score+=.28;
    else if(medVal<.22)score-=.34;
    score+=(traceFeatures?.gainScore||0)*.18;
    score+=visual.Gain;
  }else{
    if(vals.length&&Math.max(...vals)<=.20)score+=.18;
    if(medVal>=.65)score-=.42;
    score+=(traceFeatures?.noiseScore||0)*.18;
    score+=visual.Noise;
  }
  if(traceMode===family)score+=.06;
  return score;
}
function visionAxisReasoning(box,insets,requestedMode,trace,modeInference){
  const features=modeInference?.features||normalizedModeFeatures(trace);

  // Manual mode is authoritative. Never allow the opposite OCR family.
  if(requestedMode==='Gain'||requestedMode==='Noise'){
    const cal=yAxisCalibration(box,insets,requestedMode);
    return{
      mode:requestedMode,cal,
      family:requestedMode,
      source:cal?'manual-mode-axis':'manual-mode-axis-unavailable',
      scores:{[requestedMode]:cal?axisHypothesisScore(cal,requestedMode,features,requestedMode):-Infinity},
      decisive:true
    };
  }

  const gainCal=yAxisCalibration(box,insets,'Gain'),
        noiseCal=yAxisCalibration(box,insets,'Noise'),
        traceMode=modeInference?.mode&&modeInference.mode!=='Unknown'?modeInference.mode:null,
        gainScore=axisHypothesisScore(gainCal,'Gain',features,traceMode),
        noiseScore=axisHypothesisScore(noiseCal,'Noise',features,traceMode);

  let family=traceMode||((features.gainScore||0)>=(features.noiseScore||0)?'Gain':'Noise'),
      cal=family==='Gain'?gainCal:noiseCal,
      decisive=false;

  if(Number.isFinite(gainScore)||Number.isFinite(noiseScore)){
    const gv=axisVisualFamilyEvidence(gainCal),
          nv=axisVisualFamilyEvidence(noiseCal),
          noiseVisual=Math.max(gv.Noise,nv.Noise),
          gainVisual=Math.max(gv.Gain,nv.Gain),
          visualDiff=gainVisual-noiseVisual,
          diff=gainScore-noiseScore;

    if(noiseCal&&visualDiff<-.28){family='Noise';cal=noiseCal;decisive=true}
    else if(gainCal&&visualDiff>.28){family='Gain';cal=gainCal;decisive=true}
    else if(diff>.16){family='Gain';cal=gainCal;decisive=true}
    else if(diff<-.16){family='Noise';cal=noiseCal;decisive=true}
    else cal=family==='Gain'?gainCal:noiseCal;
  }
  return{
    mode:family,cal,family,
    source:'vision-axis-reasoning',
    scores:{Gain:gainScore,Noise:noiseScore},
    decisive
  };
}

function calibrateTrack(track,box,insets,mode,calOverride=null){
  const cal=calOverride||yAxisCalibration(box,insets,mode);
  if(!cal)return{track,cal:null,pixels:null};
  const g=EGSCore.geometry(box,insets),h=Math.max(1,g.y1-g.y0),ys=track.ys||[],
        vals=track.vals.map((_,i)=>{
          let py;
          if(Number.isFinite(ys[i]))py=g.y0+(ys[i]/Math.max(1,h-1))*h;
          else py=g.y1-track.vals[i]*h;
          return Math.max(0,(cal.zeroY-py)/Math.max(1e-9,cal.stepPx)*cal.stepValue);
        });
  const out={...track,vals};let pixels=null;
  try{pixels=pixelLevelSummary(out,box,insets,cal)}catch(_){}
  return{track:out,cal,pixels};
}

function validateMeasuredCalibration(mode,cal,pixels,regions=null){
  if(!cal||!pixels||!Number.isFinite(pixels.low)||!Number.isFinite(pixels.high))
    return{ok:false,reason:'missing calibration or measured values'};
  const low=pixels.low,high=pixels.high,b=cal.gridBounds,
        aVals=(cal.anchors||[]).map(a=>a.value);
  if((cal.anchors?.length||0)<2)return{ok:false,reason:`${mode} axis lacks two calibration anchors`};
  if(mode==='Gain'){
    if(aVals.length&&(Math.min(...aVals)<0||Math.max(...aVals)>4))
      return{ok:false,reason:'Gain OCR anchors outside displayed scale'};
    if(high+0.04<low)return{ok:false,reason:`Gain calibration reversed Low/High (${low.toFixed(2)}>${high.toFixed(2)})`};
    if(low<0||high<0||low>3.6||high>3.6)
      return{ok:false,reason:'Gain measured values exceed displayed Energy scale'};
    if(b&&Number.isFinite(b.min)&&Number.isFinite(b.max)){
      const pad=Math.max(.45,cal.stepValue*.55),
            lo=Math.min(b.min,b.max)-pad,hi=Math.max(b.min,b.max)+pad;
      if(low<lo||low>hi||high<lo||high>hi)
        return{ok:false,reason:`Gain values outside visible grid span ${lo.toFixed(2)}..${hi.toFixed(2)}`};
    }
  }else{
    // v6.3.4: Noise grid geometry is authoritative.
    // Trace amplitudes cannot invalidate a coherent Noise axis.
    if(aVals.length&&(Math.min(...aVals)<-.001||Math.max(...aVals)>.0501))
      return{ok:false,reason:'Noise axis anchors outside displayed small-decimal scale'};

    if((cal.source||'').includes('geometry')||
       (cal.source||'').includes('grid')||
       (cal.source||'').includes('yellow-zero')){
      return{ok:true,axisAuthoritative:true};
    }

    if(low<-.003||high<-.003||low>.060||high>.060)
      return{ok:false,reason:'Noise values are implausible for the selected calibration'};
  }
  return{ok:true};
}

function calibratedValueY(box,value,top,insets,cal){
  if(cal)return cal.zeroY-(value/cal.stepValue)*cal.stepPx;
  return EGSCore.valueY(box,value,top,insets);
}

function pixelLevelSummary(track,box,insets,cal){
  const g=EGSCore.geometry(box,insets),srcH=Math.max(1,(track.height||Math.round(g.y1-g.y0))-1),dstH=Math.max(1,g.y1-g.y0),sp=EGSCore.splitPixel(track.width);
  const robustMedianY=a=>{if(a.length<5)return NaN;let v=EGSCore.robust(a,3.0,1.0);if(v.length>=7){const lo=EGSCore.percentile(v,.08),hi=EGSCore.percentile(v,.92);v=v.filter(y=>y>=lo&&y<=hi)}return EGSCore.median(v)};
  const margins=[Math.max(3,track.width*.030),Math.max(2,track.width*.020),Math.max(1,track.width*.010)];
  let chosen=null;
  for(const margin of margins){
    const L=[],R=[];
    for(let i=0;i<track.xs.length;i++){
      if(!Number.isFinite(track.ys?.[i]))continue;
      const py=g.y0+(track.ys[i]/srcH)*dstH;
      if(track.xs[i]<=sp-margin)L.push(py);
      else if(track.xs[i]>=sp+margin)R.push(py);
    }
    if(L.length>=6&&R.length>=6){chosen={margin,L,R};break}
  }
  if(!chosen)throw Error('Noise Low/High trace positions do not contain enough samples around Sample#270');
  const lowY=robustMedianY(chosen.L),highY=robustMedianY(chosen.R);
  if(!Number.isFinite(lowY)||!Number.isFinite(highY))throw Error('Noise Low/High trace positions could not be stabilized');
  const toValue=py=>cal?Math.max(0,(cal.zeroY-py)/Math.max(1e-9,cal.stepPx)*cal.stepValue):NaN;
  return{lowY,highY,low:toValue(lowY),high:toValue(highY),leftN:chosen.L.length,rightN:chosen.R.length,marginPx:chosen.margin,source:'measured-trace-pixel-median'}
}

function gainAutoRegions(track){
  // v6.3.4 authoritative Gain ranges from the requested Sample# definition.
  // Low = 0..330, transition gap = 330..340, High = 340..500.
  const low0=0,low1=330,high0=340,high1=500,
        toX=s=>s/500*Math.max(1,track.width-1),
        L=track.vals.filter((_,i)=>track.xs[i]>=toX(low0)&&track.xs[i]<=toX(low1)),
        H=track.vals.filter((_,i)=>track.xs[i]>=toX(high0)&&track.xs[i]<=toX(high1));
  if(L.length<5||H.length<5)throw Error('Gain fixed Low/High ranges do not contain enough marker samples');
  const clean=a=>{
    const m=EGSCore.median(a),mad=EGSCore.median(a.map(v=>Math.abs(v-m)))||.005,
          k=a.filter(v=>Math.abs(v-m)<=Math.max(.01,mad*3.2));
    return k.length>=5?k:a;
  },Lc=clean(L),Hc=clean(H);
  return{
    low:Lc.reduce((s,v)=>s+v,0)/Lc.length,
    high:Hc.reduce((s,v)=>s+v,0)/Hc.length,
    confidence:.92,
    lowRange:{x0:toX(low0),x1:toX(low1)},
    highRange:{x0:toX(high0),x1:toX(high1)},
    lowMeasureRange:{x0:toX(low0),x1:toX(low1)},
    highMeasureRange:{x0:toX(high0),x1:toX(high1)},
    transition:{x0:toX(330),x1:toX(340),cx:toX(335)},
    diagnostics:{source:'v6-fixed-sample-ranges',low_n:Lc.length,high_n:Hc.length}
  };
}

function gainPixelLevelSummary(track,box,insets,cal,regions){
  const g=EGSCore.geometry(box,insets),srcH=Math.max(1,(track.height||Math.round(g.y1-g.y0))-1),dstH=Math.max(1,g.y1-g.y0),L=[],R=[],
        lm=regions.lowMeasureRange||regions.lowRange,hm=regions.highMeasureRange||regions.highRange;
  for(let i=0;i<track.xs.length;i++){
    if(!Number.isFinite(track.ys?.[i]))continue;
    const x=track.xs[i],py=g.y0+(track.ys[i]/srcH)*dstH;
    if(x>=lm.x0&&x<=lm.x1)L.push(py);
    else if(x>=hm.x0&&x<=hm.x1)R.push(py);
  }
  const robustMedianY=a=>{
    if(a.length<5)return NaN;
    let v=EGSCore.robust(a,3.0,1.0);
    if(v.length>=7){
      const lo=EGSCore.percentile(v,.08),hi=EGSCore.percentile(v,.92);
      v=v.filter(y=>y>=lo&&y<=hi);
    }
    return EGSCore.median(v);
  };
  const lowY=robustMedianY(L),highY=robustMedianY(R),
        toValue=py=>cal?Math.max(0,(cal.zeroY-py)/Math.max(1e-9,cal.stepPx)*cal.stepValue):NaN;
  return{lowY,highY,low:toValue(lowY),high:toValue(highY),leftN:L.length,rightN:R.length,
    source:'measured-trace-pixel-median'};
}

function normalizedModeFeatures(track){
  let gainScore=.15,gain=null;
  try{gain=gainAutoRegions(track);const step=gain.high-gain.low,sep=Math.abs(step),lowPos=EGSCore.clamp((.32-gain.low)/.32,0,1),stepScore=EGSCore.clamp((step-.06)/.28,0,1),stable=EGSCore.clamp(gain.confidence,0,1);gainScore=.35*lowPos+.42*stepScore+.23*stable}catch(_){}
  // Noise remains evaluated as a broad, low-amplitude trace. Its Low/High reporting still uses the Noise split rule.
  const lv=EGSCore.noiseLevels(track.xs,track.vals,1,track.width),low=lv.low,high=lv.high,delta=high-low,absDelta=Math.abs(delta),mean=(low+high)/2;
  const noiseLowBand=EGSCore.clamp((.42-mean)/.42,0,1),noiseFlat=EGSCore.clamp((.18-absDelta)/.18,0,1),noiseNoStep=EGSCore.clamp((.12-delta)/.22,0,1),noiseScore=.42*noiseLowBand+.38*noiseFlat+.20*noiseNoStep;
  return{low,high,delta,gainScore,noiseScore,levelConfidence:lv.confidence,gainRegions:gain}
}
function inferModeFromTrace(track,requested){
  if(requested!=='Auto')return{mode:requested,note:'',confidence:1,features:null};
  const f=normalizedModeFeatures(track),margin=Math.abs(f.gainScore-f.noiseScore),best=Math.max(f.gainScore,f.noiseScore);
  if(best<.50||margin<.08)return{mode:'Unknown',note:`Auto mode uncertain (Gain ${Math.round(f.gainScore*100)}% / Noise ${Math.round(f.noiseScore*100)}%). Select Gain or Noise manually.`,confidence:Math.max(.18,margin),features:f};
  const mode=f.gainScore>f.noiseScore?'Gain':'Noise';return{mode,note:`Auto mode: ${mode} from foreground signal shape (${Math.round(best*100)}%)`,confidence:EGSCore.clamp(.58+.42*margin,0,1),features:f}
}
function modeTop(mode){return mode==='Noise'?.04:mode==='Gain'?3.0:1}
function scaleTrack(track,top){return{...track,vals:track.vals.map(v=>v*top)}}
function rgbToHsv(r,g,b){r/=255;g/=255;b/=255;const mx=Math.max(r,g,b),mn=Math.min(r,g,b),d=mx-mn;let h=0;if(d){if(mx===r)h=((g-b)/d)%6;else if(mx===g)h=(b-r)/d+2;else h=(r-g)/d+4;h=((h*60)%360+360)%360}return{h,s:mx?d/mx:0,v:mx}}
function hueDistance(a,b){const d=Math.abs(a-b)%360;return Math.min(d,360-d)}
function colorSamples(box,insets){const g=EGSCore.geometry(box,insets),x0=Math.max(0,Math.floor(g.x0)),y0=Math.max(0,Math.floor(g.y0)),x1=Math.min(canvas.width-1,Math.floor(g.x1)),y1=Math.min(canvas.height-1,Math.floor(g.y1)),w=x1-x0+1,h=y1-y0+1,img=ctx.getImageData(x0,y0,w,h).data,s=[];for(let y=0;y<h;y+=2)for(let x=0;x<w;x+=2){const i=(y*w+x)*4,r=img[i],gg=img[i+1],b=img[i+2],hsv=rgbToHsv(r,gg,b);if(isGreen(r,gg,b))continue;if(hsv.v>.34&&hsv.s>.22)s.push({h:hsv.h,s:hsv.s,v:hsv.v,r,g:gg,b})}return s}
function clusterTraceColors(box,insets){const pts=colorSamples(box,insets);if(!pts.length)return[];const bins=Array.from({length:24},()=>({n:0,s:0,v:0,rs:0,gs:0,bs:0}));for(const p of pts){const k=Math.floor(((p.h+7.5)%360)/15)%24,b=bins[k];b.n++;b.s+=p.s;b.v+=p.v;b.rs+=p.r;b.gs+=p.g;b.bs+=p.b}let peaks=bins.map((b,k)=>({k,...b})).filter(b=>b.n>=Math.max(8,pts.length*.008)&&b.s/b.n>.27&&b.v/b.n>.38).sort((a,b)=>b.n-a.n);const out=[];for(const p of peaks){const h=(p.k*15+7.5)%360;if(out.some(o=>hueDistance(o.h,h)<24))continue;out.push({h,n:p.n,s:p.s/p.n,v:p.v/p.n,r:p.rs/p.n,g:p.gs/p.n,b:p.bs/p.n});if(out.length>=8)break}return out}
function foregroundTraceForHue(box,top,mode,hue,insets){const g=EGSCore.geometry(box,insets),x0=Math.max(0,Math.floor(g.x0)),y0=Math.max(0,Math.floor(g.y0)),x1=Math.min(canvas.width-1,Math.floor(g.x1)),y1=Math.min(canvas.height-1,Math.floor(g.y1)),w=x1-x0+1,h=y1-y0+1,img=ctx.getImageData(x0,y0,w,h).data,xs=[],vals=[],ysOut=[];let prev=null,miss=0,totalVisible=0,jumps=0;for(let x=0;x<w;x++){const ys=[];for(let y=0;y<h;y++){const i=(y*w+x)*4,r=img[i],gg=img[i+1],b=img[i+2];if(isGreen(r,gg,b))continue;const q=rgbToHsv(r,gg,b);if(q.v>.34&&q.s>.23&&hueDistance(q.h,hue)<=22)ys.push({y,score:q.s*q.v*(1-hueDistance(q.h,hue)/30)});else if(prev!=null&&q.v>.72&&q.s<.22&&Math.abs(y-prev)<Math.max(3,h*.035))ys.push({y,score:.18})}if(!ys.length){miss++;continue}let chosen;if(prev==null||miss>9){ys.sort((a,b)=>b.score-a.score);const bestScore=ys[0].score;const cand=ys.filter(z=>z.score>=bestScore*.75).map(z=>z.y).sort((a,b)=>a-b);chosen=EGSCore.median(cand)}else{let best=null,bestCost=1e9;for(const z of ys){const dist=Math.abs(z.y-prev),cost=dist-Math.min(7,z.score*8);if(cost<bestCost){bestCost=cost;best=z}}chosen=best.y;if(Math.abs(chosen-prev)>h*.12)jumps++}prev=chosen;miss=0;totalVisible++;xs.push(x);ysOut.push(chosen);vals.push((1-chosen/Math.max(1,h-1))*top)}const coverage=totalVisible/Math.max(1,w),continuity=1-EGSCore.clamp(jumps/Math.max(1,totalVisible),0,1),sp=EGSCore.splitPixel(w),ln=xs.filter(x=>x<sp).length,rn=xs.filter(x=>x>=sp).length,leftCoverage=ln/Math.max(1,sp),rightCoverage=rn/Math.max(1,w-sp),balance=Math.sqrt(EGSCore.clamp(leftCoverage,0,1)*EGSCore.clamp(rightCoverage,0,1)),leftVals=vals.filter((_,i)=>xs[i]<sp),rightVals=vals.filter((_,i)=>xs[i]>=sp),lm=EGSCore.median(leftVals),rm=EGSCore.median(rightVals),shape=mode==='Gain'?(EGSCore.clamp((.45-(lm/top))/.45,0,1)*.55+EGSCore.clamp((rm/top)/.18,0,1)*.45):.65;return{hue,xs,vals,ys:ysOut,width:w,height:h,coverage,leftCoverage,rightCoverage,continuity,shape,score:.42*coverage+.22*continuity+.22*balance+.14*shape}}
function chooseForegroundTrace(box,top,mode,insets){const colors=clusterTraceColors(box,insets),tracks=[];for(const c of colors){const t=foregroundTraceForHue(box,1,'Auto',c.h,insets);if(t.vals.length<Math.max(22,t.width*.07))continue;let mf;try{mf=normalizedModeFeatures(t)}catch(_){mf={gainScore:.2,noiseScore:.2}}const plausible=mode==='Gain'?mf.gainScore:mode==='Noise'?mf.noiseScore:Math.max(mf.gainScore,mf.noiseScore);const dominance=EGSCore.clamp(c.n/Math.max(12,t.width*.35),0,1);t.score=.34*t.coverage+.23*t.continuity+.18*Math.sqrt(EGSCore.clamp(t.leftCoverage,0,1)*EGSCore.clamp(t.rightCoverage,0,1))+.15*dominance+.10*plausible;tracks.push({...t,color:c,modeFeatures:mf,dominance})}if(!tracks.length)throw Error('Foreground signal trace could not be isolated');tracks.sort((a,b)=>b.score-a.score);const best=tracks[0];best.alternates=tracks.slice(1,4).map(t=>({hue:Math.round(t.hue),coverage:t.coverage,score:t.score}));return best}
function genericTrace(box,top,mode,insets){const g=EGSCore.geometry(box,insets),x0=Math.max(0,Math.floor(g.x0)),y0=Math.max(0,Math.floor(g.y0)),x1=Math.min(canvas.width-1,Math.floor(g.x1)),y1=Math.min(canvas.height-1,Math.floor(g.y1)),w=x1-x0+1,h=y1-y0+1,img=ctx.getImageData(x0,y0,w,h).data,xs=[],vals=[],ysOut=[];let prev=null,miss=0;for(let x=0;x<w;x++){const yy=[];for(let y=0;y<h;y++){const i=(y*w+x)*4,r=img[i],gg=img[i+1],b=img[i+2],mx=Math.max(r,gg,b),mn=Math.min(r,gg,b),sat=mx-mn,white=(r+gg+b)>385&&mx>138&&sat<72,colored=mx>108&&sat>42;if(!isGreen(r,gg,b)&&(white||colored))yy.push(y)}if(!yy.length){miss++;continue}let py;if(prev==null||miss>6)py=EGSCore.median(yy);else{let best=yy[0],bd=Math.abs(best-prev);for(const y of yy){const d=Math.abs(y-prev);if(d<bd){best=y;bd=d}}py=bd<h*.18?best:EGSCore.median(yy)}prev=py;miss=0;xs.push(x);ysOut.push(py);vals.push((1-py/Math.max(1,h-1))*top)}if(vals.length<Math.max(25,w*.08))throw Error('Not enough signal pixels were found');return{xs,vals,ys:ysOut,width:w,height:h,coverage:vals.length/Math.max(1,w),continuity:.5,score:.5,hue:null}}

// Observed per-channel foreground colors from verification images.
// Only use entries that have actually been observed; unknown/unlearned colors
// must never be guessed. Hue distance is circular.
const CHANNEL_COLOR_MODEL = {
  2:{hue:300,tol:24,label:'purple/magenta'},
  3:{hue:4,tol:22,label:'red'},
  4:{hue:220,tol:24,label:'blue'},
  6:{hue:188,tol:22,label:'cyan'}
};
function hueDistance(a,b){
  if(!Number.isFinite(a)||!Number.isFinite(b))return Infinity;
  const d=Math.abs(a-b)%360;return Math.min(d,360-d);
}
function foregroundChannelFromHue(hue,selected){
  if(!Number.isFinite(hue)||!Array.isArray(selected)||selected.length<2)return null;
  let best=null;
  for(const ch of selected){
    const m=CHANNEL_COLOR_MODEL[ch];
    if(!m)continue;
    const d=hueDistance(hue,m.hue);
    if(d<=m.tol && (!best||d<best.distance))best={channel:ch,distance:d,model:m};
  }
  // Conservative uniqueness rule: if two selected known colors are similarly close,
  // do not invent a channel.
  if(!best)return null;
  let second=Infinity;
  for(const ch of selected){
    if(ch===best.channel||!CHANNEL_COLOR_MODEL[ch])continue;
    second=Math.min(second,hueDistance(hue,CHANNEL_COLOR_MODEL[ch].hue));
  }
  if(Number.isFinite(second)&&second-best.distance<8)return null;
  return best;
}
function channelDecision(channels,track){
  if(channels.length===1)return{channel:channels[0],source:'single checkbox',confidence:1,candidates:[...channels]};
  if(channels.length>1){
    const hit=foregroundChannelFromHue(track?.hue,channels);
    if(hit)return{channel:hit.channel,source:'foreground color matched checked channel',confidence:Math.max(.55,1-hit.distance/Math.max(1,hit.model.tol)),candidates:[...channels],colorDistance:hit.distance};
    return{channel:null,source:'foreground color did not match selected channels',confidence:track?.score||0,candidates:[...channels]};
  }
  return{channel:null,source:'no checked channel',confidence:track?.score||0,candidates:[]};
}

function exactAnalysisROI(box){
  // Convert the visible ROI to one authoritative canvas-pixel rectangle.
  // Every downstream stage receives this same rectangle; no stage is allowed
  // to independently floor/ceil the outer ROI boundary.
  const x0=EGSCore.clamp(Math.floor(box.x),0,Math.max(0,canvas.width-1)),
        y0=EGSCore.clamp(Math.floor(box.y),0,Math.max(0,canvas.height-1)),
        x1=EGSCore.clamp(Math.ceil(box.x+box.w),x0+1,canvas.width),
        y1=EGSCore.clamp(Math.ceil(box.y+box.h),y0+1,canvas.height);
  return{x:x0,y:y0,w:x1-x0,h:y1-y0,source:'exact-visible-roi-pixels'};
}

function analysisCropFingerprint(box){
  // Internal proof of what pixels are actually being analyzed.
  // This does not OCR or modify the image. It records a lightweight checksum
  // and exact bounds so a displayed ROI can be compared to the real crop.
  const b=exactAnalysisROI(box),
        im=ctx.getImageData(b.x,b.y,b.w,b.h).data,
        sx=Math.max(1,Math.floor(b.w/19)),
        sy=Math.max(1,Math.floor(b.h/13));
  let hash=2166136261>>>0,count=0;
  for(let y=0;y<b.h;y+=sy){
    for(let x=0;x<b.w;x+=sx){
      const i=(y*b.w+x)*4;
      hash^=im[i];hash=Math.imul(hash,16777619)>>>0;
      hash^=im[i+1];hash=Math.imul(hash,16777619)>>>0;
      hash^=im[i+2];hash=Math.imul(hash,16777619)>>>0;
      count++;
    }
  }
  return{...b,hash:hash.toString(16).padStart(8,'0'),samples:count};
}

function overlay(result){
  redrawSource();const b=result.analysisBox||result.box,g=EGSCore.geometry(b,result.insets),split=EGSCore.splitX(b,result.insets),tw=Math.max(1,g.x1-g.x0);
  // Red = full Energy-per-Band analysis panel. Cyan = inner numeric grid only.
  ctx.lineWidth=Math.max(2,canvas.width/500);ctx.strokeStyle='#ff3c4b';ctx.strokeRect(b.x,b.y,b.w,b.h);
  const dbgPlot=result?.diagnostics?.v2_plot;
  if(dbgPlot){ctx.save();ctx.lineWidth=Math.max(1.5,canvas.width/700);ctx.strokeStyle='#00d4ff';ctx.setLineDash([5,4]);ctx.strokeRect(dbgPlot.x,dbgPlot.y,dbgPlot.w,dbgPlot.h);ctx.restore();}
  if(result.mode==='Gain'&&result.gainRegions){const xr=x=>g.x0+(x/Math.max(1,result.trace.width-1))*tw,a=xr(result.gainRegions.lowRange.x0),c=xr(result.gainRegions.lowRange.x1),d=xr(result.gainRegions.highRange.x0),e=xr(result.gainRegions.highRange.x1);ctx.strokeStyle='#ffd23f';ctx.setLineDash([8,7]);ctx.beginPath();ctx.moveTo(c,g.y0);ctx.lineTo(c,g.y1);ctx.moveTo(d,g.y0);ctx.lineTo(d,g.y1);ctx.stroke();ctx.setLineDash([]);result._gainDraw={a,c,d,e}}else{ctx.strokeStyle='#ffd23f';ctx.setLineDash([8,7]);ctx.beginPath();ctx.moveTo(split,g.y0);ctx.lineTo(split,g.y1);ctx.stroke();ctx.setLineDash([]);}
  // Show the actually tracked foreground trace, so the user can verify which line was measured.
  if(result.trace&&result.trace.ys&&result.trace.ys.length){const tw=Math.max(1,g.x1-g.x0),th=Math.max(1,g.y1-g.y0),srcH=Math.max(1,(result.trace.height||Math.round(th))-1);ctx.fillStyle='rgba(255,255,255,.78)';const step=Math.max(1,Math.floor(result.trace.xs.length/90));for(let i=0;i<result.trace.xs.length;i+=step){const x=g.x0+(result.trace.xs[i]/Math.max(1,result.trace.width-1))*tw,y=g.y0+(result.trace.ys[i]/srcH)*th;ctx.fillRect(x-1,y-1,2,2)}}

  // Core v2.0.3: visualize the exact Noise grid/value path.
  const nd=result?.diagnostics||{},na=nd.v2_noise_axis,nv=nd.v2_noise_values,np=nd.v2_plot;
  if(na?.ok&&np){
    ctx.save();ctx.font=`${Math.max(10,canvas.width/80)}px sans-serif`;
    for(const a of na.anchors||[]){
      ctx.setLineDash([6,5]);ctx.lineWidth=Math.max(1.5,canvas.width/700);
      ctx.strokeStyle='#00d4ff';ctx.beginPath();ctx.moveTo(np.x,a.y);ctx.lineTo(np.x+np.w,a.y);ctx.stroke();
      ctx.setLineDash([]);ctx.fillStyle='#00d4ff';
      ctx.fillText(a.value.toFixed(2)+(a.inferred?'*':''),np.x+4,Math.max(12,a.y-3));
    }
    if(nv?.ok){
      ctx.lineWidth=Math.max(2,canvas.width/600);ctx.setLineDash([]);
      ctx.strokeStyle='#ffffff';ctx.beginPath();ctx.moveTo(np.x,nv.lowY);ctx.lineTo(nv.splitX,nv.lowY);ctx.stroke();
      ctx.strokeStyle='#ff9f0a';ctx.beginPath();ctx.moveTo(nv.splitX,nv.highY);ctx.lineTo(np.x+np.w,nv.highY);ctx.stroke();
      ctx.setLineDash([5,4]);ctx.strokeStyle='#ffd60a';ctx.beginPath();ctx.moveTo(nv.splitX,np.y);ctx.lineTo(nv.splitX,np.y+np.h);ctx.stroke();
    }
    ctx.restore();
  }

  const ly=result.pixelLevels&&Number.isFinite(result.pixelLevels.lowY)?result.pixelLevels.lowY:null,
        hy=result.pixelLevels&&Number.isFinite(result.pixelLevels.highY)?result.pixelLevels.highY:null;
  if(ly==null||hy==null)return;
  ctx.strokeStyle='#00bff3';ctx.beginPath();if(result.mode==='Gain'&&result._gainDraw){ctx.moveTo(result._gainDraw.a,ly);ctx.lineTo(result._gainDraw.c,ly)}else{ctx.moveTo(g.x0,ly);ctx.lineTo(split,ly)}ctx.stroke();ctx.strokeStyle='#ff7f27';ctx.beginPath();if(result.mode==='Gain'&&result._gainDraw){ctx.moveTo(result._gainDraw.d,hy);ctx.lineTo(result._gainDraw.e,hy)}else{ctx.moveTo(split,hy);ctx.lineTo(g.x1,hy)}ctx.stroke();
}
function analyze(){if(!sourceReady||!roi)return;
  currentResult=null;
  els.result.classList.add('hidden');
  let fatalStage='analyze-entry';
  setStatus('Analyzing…');
  try{
  fatalStage='restore-stable-imagedata';
  redrawSource();
  fatalStage='exact-analysis-roi';
  // Freeze the red visible ROI into exact canvas pixels before doing anything.
  // From this point on, visible ROI == analyzed crop.
  const analysisROI=exactAnalysisROI(roi),
        cropMeta=analysisCropFingerprint(analysisROI);
  roi={...analysisROI};
  renderROI();
  redrawSource();

  // Stage 1 — Channel checkbox interpretation is independent from plot certainty
  // and must always run first.
  const channels=checkedChannels(analysisROI);

  // Stage 2 — v6.3.4 shared structural detector:
  // Auto uses multi-hypothesis structural detection. Manual uses the same detector
  // strictly inside the red ROI. Auto and Manual therefore share plot logic,
  // while Manual remains a hard boundary.
  let snappedPanel=null, v2=null,analysisStage='stage2-start';

  if(roiManual){
    // v6.3.4 MANUAL ROI AUTHORITATIVE:
    // Red ROI is the hard analysis boundary. Never call stable/global panel
    // discovery and never replace this result with canonical/global geometry.
    analysisStage='manual-authoritative-scoped';
    try{
      fatalStage='manual-authoritative-scoped';
      // v6.3.4: Manual path starts with the exact red-ROI scoped detector.
      // Do not run the generic auto-style prepare first.
      v2=EGSAnalysisV2.prepareManualROI(ctx,canvas,analysisROI);
    }catch(e){
      console.warn('manual authoritative scoped prepare failed',e);
      v2=null;
    }

    if(!v2){
      analysisStage='manual-generic-last-fallback';
      try{
        fatalStage='manual-generic-last-fallback';
        v2=EGSAnalysisV2.prepare(ctx,canvas,analysisROI);
      }catch(e){
        console.warn('manual generic last fallback failed',e);
        v2=null;
      }
    }

    // Hard containment contract: numeric plot/context may not escape red ROI.
    if(v2){
      const A=analysisROI,
            inside=(B)=>B && B.x>=A.x-1 && B.y>=A.y-1 &&
              B.x+B.w<=A.x+A.w+1 && B.y+B.h<=A.y+A.h+1;
      if(!inside(v2.plot)){
        console.warn('manual plot escaped ROI; forcing direct manual fallback',v2.plot,A);
        try{v2=EGSAnalysisV2.prepareManualROI(ctx,canvas,analysisROI)}catch(_){v2=null}
      }
      if(v2){
        v2.context={...analysisROI};
        v2.snappedPanel=null;
        v2.manualAuthoritative=true;
        v2.version='manual-authoritative-v6.3.4';
      }
    }
  }else{
    analysisStage='auto-known-plot';
    if(activeDetectedPanel?.plot){
      try{
        fatalStage='auto-known-plot';
        v2=EGSAnalysisV2.prepareKnownPanel(ctx,canvas,analysisROI,activeDetectedPanel.plot,{
          gridRowsAbs:activeDetectedPanel.gridRowsAbs||[],
          gridColsAbs:activeDetectedPanel.gridColsAbs||[],
          source:activeDetectedPanel.source||'active-auto-detector',
          confidence:activeDetectedPanel.confidence||.85,
          diagnostics:activeDetectedPanel.diagnostics||null,
          manual:false
        });
      }catch(e){v2=null}
    }
    if(!v2){
      analysisStage='auto-prepare-fallback';
      try{
        fatalStage='auto-prepare-fallback';
        v2=EGSAnalysisV2.prepare(ctx,canvas,analysisROI);
      }catch(e){
        v2=null;
      }
    }
  }

  if(!v2 && !roiManual){
    analysisStage='auto-stable-recovery';
    const recovered=stableEnergyPanel();
    if(recovered){
      activeDetectedPanel={...recovered,plot:recovered.plot?{...recovered.plot}:null};
      roi={x:recovered.x,y:recovered.y,w:recovered.w,h:recovered.h};
      renderROI();
      const recoveredROI=exactAnalysisROI(roi);
      try{
        v2=recovered.plot?EGSAnalysisV2.prepareKnownPanel(ctx,canvas,recoveredROI,recovered.plot,{
          gridRowsAbs:recovered.gridRowsAbs||[],gridColsAbs:recovered.gridColsAbs||[],
          source:recovered.source||'auto-recovery-known-plot',
          confidence:recovered.confidence||.80,diagnostics:recovered.diagnostics||null
        }):EGSAnalysisV2.prepare(ctx,canvas,recoveredROI);
      }catch(_){
        v2=null;
      }
    }
  }

  if(!roiManual&&!activeDetectedPanel&&canonicalMode&&canonicalRegistration?.ok&&v2){
    const cp=canonicalRegistration.energyPlot,
          ep=canonicalRegistration.energyPanel;
    v2.plot={x:cp.x,y:cp.y,w:cp.w,h:cp.h};
    v2.context={x:ep.x,y:ep.y,w:ep.w,h:ep.h};
    v2.insets={
      left:cp.x-ep.x,
      right:(ep.x+ep.w)-(cp.x+cp.w),
      top:cp.y-ep.y,
      bottom:(ep.y+ep.h)-(cp.y+cp.h),
      source:'canonical-fixed-v6.3.4'
    };
    v2.snappedPanel={x:ep.x,y:ep.y,w:ep.w,h:ep.h,overlap:1};
    v2.version='canonical-deterministic-v6.3.4';
  } else if(v2&&roiManual&&!v2.snappedPanel){
    v2.version='manual-hint-localized-v6.3.4';
  }
  if(!v2){
    const partial={mode:els.mode.value==='Auto'?'Unknown':els.mode.value,provisional:true,
      channels,channel:channels.length===1?channels[0]:null,
      channelSource:channels.length===1?'single checked channel':'plot not localized',
      low:NaN,high:NaN,confidence:.15,box:{...analysisROI},analysisBox:{...analysisROI},
      top:1,insets:{left:0,top:0,right:0,bottom:0,source:'v2-no-plot'},
      axisCal:null,pixelLevels:null,gainRegions:null,trace:null,
      diagnostics:{analysis_crop:cropMeta,analysis_core:'v3.0.1-shared-auto-roi'},
      message:roiManual?`Manual ROI analysis could not initialize at ${analysisStage}. Numeric result withheld.`:'Auto ROI path: shared Energy per Band detector could not localize the plot. Numeric result withheld.'};
    currentResult=partial;overlay(partial);showResult(partial);
    setStatus('Energy per Band plotを確定できませんでした。数値のみ保留しました。');
    return;
  }
  const analysisBox=v2.context,insets=v2.insets;
  cropMeta.numeric_panel={x:analysisBox.x,y:analysisBox.y,w:analysisBox.w,h:analysisBox.h};
  cropMeta.numeric_plot={x:v2.plot.x,y:v2.plot.y,w:v2.plot.w,h:v2.plot.h};
  cropMeta.input_path=sourceGuideCropped?'camera-crop-unified':'library-unified';
  cropMeta.frame_generation=analysisFrameGeneration;
  cropMeta.analysis_base=`${canvas.width}x${canvas.height}`;
  if(v2.snappedPanel){
    cropMeta.analysis_policy='ROI hint -> cached stable Energy panel';
    cropMeta.snapped_panel={...v2.snappedPanel};
  }else{
    cropMeta.analysis_policy=roiManual?'manual ROI fallback':'auto localized panel';
  }

  fatalStage='foreground-trace';
  let normTrack,fgUsed=false,trackError=null;
  try{
    normTrack=chooseForegroundTrace(analysisBox,1,els.mode.value==='Auto'?'Auto':els.mode.value,insets);
    fgUsed=true;
  }catch(e){
    trackError=e;
    // Multiple checked channels no longer stop analysis. Try a generic signal
    // trace and keep Channel=Unknown if foreground color cannot be resolved.
    normTrack=genericTrace(analysisBox,1,'Auto',insets);
  }

  // Channel result is available as soon as foreground hue exists.
  let earlyDecision=channelDecision(channels,normTrack);

  fatalStage='mode-inference';
  let mi=inferModeFromTrace(normTrack,els.mode.value),provisional=false;
  if(els.mode.value==='Auto'&&v2.axisFamily?.family&&v2.axisFamily.confidence>=.58){
    mi={...mi,mode:v2.axisFamily.family,
        confidence:Math.max(mi.confidence||0,v2.axisFamily.confidence),
        note:`Auto mode from Core v2 Y-axis: ${v2.axisFamily.family} (${Math.round(v2.axisFamily.confidence*100)}%)`,
        axisFamilyAuthoritative:true};
  }
  if(mi.mode==='Unknown'){
    if(els.mode.value!=='Auto')throw Error('Mode could not be determined.');
    const f=mi.features||normalizedModeFeatures(normTrack);
    const pick=(f.gainScore||0)>=(f.noiseScore||0)?'Gain':'Noise';
    mi={...mi,mode:pick,confidence:Math.max(f.gainScore||0,f.noiseScore||0),note:`Provisional Auto ${pick}: confirm mode before SPEC`,features:f};
    provisional=true;
  }

  // Vision-style context reasoning: manual mode is authoritative; Auto compares
  // separate Gain/Noise axis hypotheses with trace shape and grid-step consistency.
  if(mi.mode==='Noise' && !v2.noiseAxis?.ok){
    v2.noiseAxis=EGSAnalysisV2.noiseAxisSeries(ctx,canvas,v2);
  }
  if(mi.mode==='Noise'){
    if(!v2.noiseTrace?.ok)v2.noiseTrace=EGSAnalysisV2.directNoiseTrace(ctx,canvas,v2);
    if(v2.noiseAxis?.ok&&v2.noiseTrace?.ok)
      v2.noiseValues=EGSAnalysisV2.directNoiseValues(v2,v2.noiseTrace);
  }

  let axisReason=visionAxisReasoning(analysisBox,insets,(els.mode.value==='Auto'&&mi.axisFamilyAuthoritative)?mi.mode:els.mode.value,normTrack,mi),
      axisProbe=axisReason.cal;
  // v6.3.4 mode authority: numeric difference between adjacent Y major-grid labels.
  // >= 0.5 => Gain, < 0.5 => Noise.
  if(els.mode.value==='Auto'&&axisReason?.cal?.stepValue){
    const d=Math.abs(axisReason.cal.stepValue);
    mi={...mi,mode:d>=.5?'Gain':'Noise',
        confidence:Math.max(mi.confidence||0,.90),
        note:`v6 mode from Y-grid numeric interval ${d}`};
  }
  const robustMode=EGSRobustV3.resolveMode(els.mode.value,v2,mi.mode,axisReason);
  if(els.mode.value==='Auto'&&(robustMode.value==='Gain'||robustMode.value==='Noise')){
    mi={...mi,mode:robustMode.value,confidence:Math.max(mi.confidence||0,robustMode.score||0),
        note:`Robust Core v3 mode consensus: ${robustMode.value} (${Math.round((robustMode.score||0)*100)}%)`};
  }
  if(els.mode.value==='Auto' && !mi.axisFamilyAuthoritative && axisReason.mode && axisReason.mode!==mi.mode){
    mi={...mi,mode:axisReason.mode,
        confidence:Math.max(mi.confidence||0,axisReason.decisive?.80:.58),
        note:`Auto mode ${axisReason.decisive?'corrected':'kept'} as ${axisReason.mode} by vision-style axis reasoning`};
    provisional=!axisReason.decisive;
  }else if(els.mode.value!=='Auto'){
    mi={...mi,mode:els.mode.value,confidence:1,note:`Manual ${els.mode.value} authoritative`};
    provisional=false;
  }

  // Re-rank the foreground trace after the final mode selection. Failure is non-fatal.
  if(fgUsed||channels.length>1){
    try{
      normTrack=chooseForegroundTrace(analysisBox,1,mi.mode,insets);
      fgUsed=true;
      earlyDecision=channelDecision(channels,normTrack);
    }catch(_){}
  }

  const top=modeTop(mi.mode),scaled=scaleTrack(normTrack,top),
        calibrated=calibrateTrack(scaled,analysisBox,insets,mi.mode,axisProbe),
        tr=calibrated.track,
        decision=channelDecision(channels,tr),
        robustChannel=EGSRobustV3.resolveChannel(channels,decision?.channel),
        digits=mi.mode==='Noise'?4:2,msg=[];
  let axisCal=calibrated.cal;
  if(mi.mode==='Noise'&&v2.noiseAxis?.ok){
    axisCal={
      zeroY:v2.noiseAxis.zeroY,
      stepPx:v2.noiseAxis.stepPx,
      stepValue:v2.noiseAxis.stepValue,
      source:v2.noiseAxis.source,
      anchors:v2.noiseAxis.anchors,
      fitScore:v2.noiseAxis.confidence,
      family:'Noise',
      modeHint:'Noise',
      gridBounds:{min:0,max:.05}
    };
  }

  // Y-axis numeric calibration remains required for numeric/SPEC output, but
  // channel/mode/trace analysis has already completed and is never lost.
  if(!axisCal){
    const partial={
      mode:mi.mode,provisional:true,channels,channel:(robustChannel?.value==='Unknown'?null:robustChannel?.value),
      channelSource:robustChannel?.source||decision.source,low:NaN,high:NaN,
      confidence:EGSCore.clamp((tr.score||.3)*.55,0,1),box:{...analysisROI},analysisBox:{...analysisBox},top,insets,
      axisCal:null,pixelLevels:null,gainRegions:null,
      trace:{xs:[...tr.xs],ys:[...tr.ys||[]],width:tr.width,height:tr.height},
      diagnostics:{mode_features:mi.features,foreground_hue:tr.hue,foreground_coverage:tr.coverage,foreground_continuity:tr.continuity,analysis_crop:cropMeta,analysis_core:'v2',v2_plot:v2.plot,v2_axis_family:v2.axisFamily,v2_noise_axis:v2.noiseAxis,v2_noise_trace:v2.noiseTrace,v2_noise_values:v2.noiseValues},
      message:`Plot geometry: ${insets.source}; Channel: ${decision.channel!=null?'CH'+decision.channel:'Unknown'} (${decision.source}); Y-axis grid lattice could not be reconstructed. Numeric Low/High withheld.`
    };
    currentResult=partial;overlay(partial);showResult(partial);
    setStatus('Trace/Channel解析は完了。水平グリッド幾何からY軸を確定できないためLow/High数値のみ保留。');
    return;
  }

  const robustNoiseNumeric=mi.mode==='Noise'?EGSRobustV3.resolveNoiseNumeric(v2):null;
  let gainRegions=null,lv,pixelLevels=calibrated.pixels;
  if(mi.mode==='Noise'&&robustNoiseNumeric?.value){
    pixelLevels={...robustNoiseNumeric.value,source:'robust-core-v3-noise-consensus'};
  }
  if(mi.mode==='Noise'&&v2.noiseValues?.ok){
    pixelLevels={
      low:v2.noiseValues.low,
      high:v2.noiseValues.high,
      lowY:v2.noiseValues.lowY,
      highY:v2.noiseValues.highY,
      source:v2.noiseValues.source||'axis-authoritative-noise-v407',
      rejectedCount:v2.noiseValues.rejectedCount||0,
      visibleMin:v2.noiseValues.visibleMin,
      visibleMax:v2.noiseValues.visibleMax
    };
  }else if(mi.mode==='Noise'&&v2.noiseAxis?.ok&&tr?.points?.length){
    const g=EGSCore.geometry(analysisBox,insets),
          xSplit=g.x0+(g.x1-g.x0)*(EGSCore.SAMPLE_SPLIT/EGSCore.SAMPLE_AXIS_MAX),
          lowVals=[],highVals=[];
    const nAnch=(v2.noiseAxis.anchors||[]).map(a=>a.value).filter(Number.isFinite),
          nMin=nAnch.length?Math.min(...nAnch):0,
          nMax=nAnch.length?Math.max(...nAnch):.04,
          nPad=Math.max(.0012,(v2.noiseAxis.stepValue||.01)*.16);
    for(const pt of tr.points){
      if(!Number.isFinite(pt.x)||!Number.isFinite(pt.y))continue;
      const v=EGSAnalysisV2.pixelYToValue(pt.y,v2.noiseAxis);
      if(!Number.isFinite(v)||v<nMin-nPad||v>nMax+nPad)continue;
      const vv=Math.max(nMin,Math.min(nMax,v));
      if(pt.x<xSplit)lowVals.push(vv); else highVals.push(vv);
    }
    if(lowVals.length>=5&&highVals.length>=5){
      pixelLevels={low:EGSCore.median(lowVals),high:EGSCore.median(highVals),
                   source:'v2-noise-major-grid-series-fallback'};
    }
  }
  if(mi.mode==='Gain'){
    gainRegions=gainAutoRegions(tr);
    lv={low:gainRegions.low,high:gainRegions.high,confidence:gainRegions.confidence,diagnostics:gainRegions.diagnostics};
    pixelLevels=gainPixelLevelSummary(tr,analysisBox,insets,axisCal,gainRegions);
  }else{
    // Noise: calibrated direct pixels are authoritative. The legacy sparse trace
    // splitter is fallback only, so a valid manual ROI is not rejected afterwards.
    if(pixelLevels && Number.isFinite(pixelLevels.low) && Number.isFinite(pixelLevels.high)){
      lv={low:pixelLevels.low,high:pixelLevels.high,confidence:.96,
          diagnostics:{source:pixelLevels.source||'direct-noise-authoritative'}};
      msg.push(`Noise ranges: Sample#0-${EGSCore.SAMPLE_SPLIT} / ${EGSCore.SAMPLE_SPLIT}-${EGSCore.SAMPLE_AXIS_MAX}; grid-only Y-axis + dominant signal population`);
    }else{
      lv=EGSCore.noiseLevels(tr.xs,tr.vals,top,tr.width);
      msg.push(`Noise ranges: Sample#0-${EGSCore.SAMPLE_SPLIT} / ${EGSCore.SAMPLE_SPLIT}-${EGSCore.SAMPLE_AXIS_MAX}; legacy trace fallback`);
    }
  }

  if(mi.note)msg.push(mi.note);
  msg.push(`Robust Core v3 + Analysis Providers: ${v2.plot.source}; Y-axis ${v2.axisFamily?.family||'Unknown'} ${Math.round((v2.axisFamily?.confidence||0)*100)}% (${v2.axisFamily?.reason||'n/a'})`); if(v2.noiseAxis?.ok)msg.push(`Noise grid series: ${v2.noiseAxis.anchors.map(a=>a.value.toFixed(2)+'@'+Math.round(a.y)+(a.inferred?'[infer]':'')).join(', ')}`);
  if(v2.noiseValues?.ok){
    msg.push(`Direct Noise values: Low ${v2.noiseValues.low.toFixed(4)} / High ${v2.noiseValues.high.toFixed(4)} (${v2.noiseValues.lowCount}/${v2.noiseValues.highCount} samples)`);
    msg.push(`Signal populations: Low coverage ${Math.round((v2.noiseValues.lowModel?.coverage||0)*100)}% / High coverage ${Math.round((v2.noiseValues.highModel?.coverage||0)*100)}%; High selection ${v2.noiseTrace?.highSelection||'n/a'}; hue ${Math.round(v2.noiseValues.signalHue||0)}°; Y-axis source ${v2.noiseAxis?.source||'unknown'}`);
  if(v2.noiseAxis?.lattice)msg.push(`Rotation compensation: ${Number(v2.noiseAxis.lattice.rotationDeg||0).toFixed(2)}° / ${Math.round((v2.noiseAxis.lattice.rotationConfidence||0)*100)}%`);
  } msg.push(`Plot geometry: ${insets.source}`);
  msg.push(`Axis reasoning: Gain ${Number.isFinite(axisReason?.scores?.Gain)?axisReason.scores.Gain.toFixed(2):'—'} / Noise ${Number.isFinite(axisReason?.scores?.Noise)?axisReason.scores.Noise.toFixed(2):'—'}; selected ${mi.mode}${els.mode.value==='Auto'?'':' (manual)'}`);
  msg.push(`Y calibration: ${axisCal.source}; family ${axisCal.family||mi.mode}; anchors ${axisCal.anchors?.map(a=>a.value+'@'+Math.round(a.y)+'('+Math.round((a.conf||0)*100)+'%)').join(', ')||'none'}`);

  if(channels.length===1){
    msg.push(`Single checked channel CH${channels[0]} prioritized`);
  }else if(channels.length>1){
    msg.push(`Checked candidates: ${channels.map(c=>'CH'+c).join(', ')}`);
    if(decision.channel!=null)msg.push(`Foreground color matched CH${decision.channel}`);
    else msg.push('Foreground color did not match a selected known channel; Channel=Unknown');
  }else{
    msg.push('No checked channel resolved; Channel=Unknown');
  }
  if(trackError)msg.push('Foreground-specific tracking failed once; generic trace fallback used');
  if(fgUsed&&Number.isFinite(tr.hue))msg.push(`Foreground hue ${Math.round(tr.hue)}°, visibility ${Math.round(tr.coverage*100)}%`);

  const modeConfidence=els.mode.value==='Auto'?mi.confidence:1,
        axisAnchorFactor=Math.min(1,.55+.17*(axisCal?.anchors?.length||0)+.20*Math.min(1,axisCal?.fitScore||0)),
        confidence=EGSCore.clamp(lv.confidence*(fgUsed?(.72+.28*tr.score):.72)*(.72+.28*modeConfidence)*axisAnchorFactor,0,1);

  if(!pixelLevels||!Number.isFinite(pixelLevels.low)||!Number.isFinite(pixelLevels.high)){
    throw Error('Trace pixel levels could not be calibrated. No numeric result was produced.');
  }

  const calCheck=validateMeasuredCalibration(mi.mode,axisCal,pixelLevels,gainRegions);
  if(!calCheck.ok){
    const partial={
      mode:mi.mode,provisional:true,channels,channel:(robustChannel?.value==='Unknown'?null:robustChannel?.value),
      channelSource:robustChannel?.source||decision.source,low:NaN,high:NaN,
      confidence:EGSCore.clamp(confidence*.55,0,1),box:{...analysisROI},analysisBox:{...analysisBox},top,insets,
      axisCal:null,pixelLevels:null,gainRegions,
      trace:{xs:[...tr.xs],ys:[...tr.ys||[]],width:tr.width,height:tr.height},
      diagnostics:{...lv.diagnostics,mode_features:mi.features,foreground_hue:tr.hue,foreground_coverage:tr.coverage,foreground_continuity:tr.continuity,analysis_crop:cropMeta,analysis_core:'v2',v2_plot:v2.plot,v2_axis_family:v2.axisFamily,v2_noise_axis:v2.noiseAxis,v2_noise_trace:v2.noiseTrace,v2_noise_values:v2.noiseValues},
      message:`Trace/Channel/Mode retained; numeric calibration rejected: ${calCheck.reason}; Axis candidate ${axisCal.source}; anchors ${axisCal.anchors?.map(a=>a.value+'@'+Math.round(a.y)+'('+Math.round((a.conf||0)*100)+'%)').join(', ')||'none'}`
    };
    currentResult=partial;overlay(partial);showResult(partial);
    setStatus('Trace/Channel解析は完了。Y軸校正候補が波形と矛盾したためLow/High数値のみ保留。');
    return;
  }

  msg.push(`Visible ROI: x=${cropMeta.x}, y=${cropMeta.y}, w=${cropMeta.w}, h=${cropMeta.h}, crop#${cropMeta.hash}`);
  if(!roiManual&&v2.snappedPanel)msg.push(`Auto panel snap: x=${Math.round(v2.snappedPanel.x)}, y=${Math.round(v2.snappedPanel.y)}, w=${Math.round(v2.snappedPanel.w)}, h=${Math.round(v2.snappedPanel.h)}, overlap=${Math.round(v2.snappedPanel.overlap*100)}%`);
  if(roiManual){
    msg.push(`Manual ROI authoritative: numeric analysis is confined to the red ROI; global/canonical snap disabled`);
  }else{
    msg.push(`Auto ROI: numeric plot localized automatically`);
  }
  const lowValue=pixelLevels.low,highValue=pixelLevels.high;
  if(mi.mode==='Gain'&&gainRegions)msg.push(`Gain ranges auto-detected: Low ${Math.round(gainRegions.lowRange.x0)}-${Math.round(gainRegions.lowRange.x1)}, High ${Math.round(gainRegions.highRange.x0)}-${Math.round(gainRegions.highRange.x1)}`);

  currentResult={
    mode:mi.mode,provisional,channels,channel:decision.channel,channelSource:decision.source,
    low:+lowValue.toFixed(digits),high:+highValue.toFixed(digits),confidence,
    box:{...analysisROI},analysisBox:{...analysisBox},top,insets,axisCal,pixelLevels,gainRegions,
    trace:{xs:[...tr.xs],ys:[...tr.ys||[]],width:tr.width,height:tr.height},
    diagnostics:{...lv.diagnostics,mode_features:mi.features,foreground_hue:tr.hue,foreground_coverage:tr.coverage,foreground_continuity:tr.continuity,analysis_crop:cropMeta,analysis_core:'v2',v2_plot:v2.plot,v2_axis_family:v2.axisFamily,v2_noise_axis:v2.noiseAxis,v2_noise_trace:v2.noiseTrace,v2_noise_values:v2.noiseValues},
    message:msg.join('; ')
  };
  overlay(currentResult);showResult(currentResult);setStatus('Analysis complete.');
}catch(e){
  try{redrawSource()}catch(_){}
  try{renderROI()}catch(_){}
  currentResult=null;
  els.result.classList.add('hidden');
  const name=e?.name?`${e.name}: `:'';
  const code=(typeof e?.code!=='undefined'&&e.code!==0)?` [code ${e.code}]`:'';
  setStatus(`Stage ${fatalStage} — ${name}${e?.message||String(e)}${code}`);
  console.error('Analyze failed at',fatalStage,e);
}}
function showResult(r){els.result.classList.remove('hidden');$('modeOut').textContent=r.mode;$('channelOut').textContent=r.channel!=null?`CH${r.channel}`:'Unknown';$('confidenceOut').textContent=`${Math.round(r.confidence*100)}%`;if(r.mode==='Unknown'||!Number.isFinite(r.low)||!Number.isFinite(r.high)){$('lowOut').textContent='—';$('highOut').textContent='—';const sp=$('specOut');sp.textContent='—';sp.className='';$('messageOut').textContent=r.message||'Select Gain or Noise manually.';return}$('lowOut').textContent=r.mode==='Noise'?r.low.toFixed(4):r.low.toFixed(2);$('highOut').textContent=r.mode==='Noise'?r.high.toFixed(4):r.high.toFixed(2);const sp=$('specOut');if(r.provisional){sp.textContent='—';sp.className='';$('messageOut').textContent=(r.message?r.message+'; ':'')+'Auto mode is provisional. Select Gain or Noise to enable SPEC.';return}const ok=EGSCore.spec(r.mode,r.low,r.high);sp.textContent=ok?'IN':'OUT';sp.className=ok?'spec-in':'spec-out';$('messageOut').textContent=r.message||'—'}
if('serviceWorker' in navigator){
  window.addEventListener('load',async()=>{
    try{
      const reg=await navigator.serviceWorker.register('./sw.js',{scope:'./'});
      const ready=await navigator.serviceWorker.ready;
      console.info('Energy Graph Scan offline scope:', ready.scope);
      // Ask the browser to check for an updated offline bundle whenever the app opens online.
      if(navigator.onLine)reg.update().catch(()=>{});
    }catch(e){console.warn('Offline service worker unavailable',e)}
  });
}
window.addEventListener('online',()=>setStatus(sourceReady?'Online — analysis ready':'Online — app ready'));
window.addEventListener('offline',()=>setStatus(sourceReady?'Offline — local analysis ready':'Offline — app ready'));
