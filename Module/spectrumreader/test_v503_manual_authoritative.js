
const fs=require('fs'),a=fs.readFileSync('app.js','utf8'),c=fs.readFileSync('analysis_core_v2.js','utf8');
function ok(v,m){if(!v)throw Error(m)}
const m=a.indexOf('if(roiManual){',a.indexOf('let snappedPanel=null, v2=null'));
const e=a.indexOf("}else{\n    analysisStage='auto-prepare';",m);
const b=a.slice(m,e);
ok(!b.includes('stableEnergyPanel()'),'manual branch still calls global stable panel');
ok(b.includes('manualAuthoritative=true'),'manual authority flag missing');
ok(a.includes('if(!roiManual&&canonicalMode&&canonicalRegistration?.ok&&v2){'),'canonical override must be auto-only');
ok(c.includes('function strongHorizontalMajorGridRows'),'strong major grid detector missing');
ok(c.includes('support>=.62&&frac>=.10'),'distributed support rule missing');
ok(c.includes('step>=p.h*.13'),'compressed Y-grid rejection missing');
ok(c.includes('spanRatio<.58||spanRatio>.96'),'axis span validation missing');
console.log('v5.0.3 manual authoritative + strong Y-grid PASS');
