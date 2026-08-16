
const fs=require('fs');
const a=fs.readFileSync('app.js','utf8');
const c=fs.readFileSync('analysis_core_v2.js','utf8');
const h=fs.readFileSync('index.html','utf8');
function ok(v,m){if(!v)throw Error(m)}

ok(a.includes('function v6EstimateAndApplyDeskew('),'deskew stage missing');
ok(a.includes('function v6CheckedChannels16('),'channel stage missing');
ok(a.includes('function v6RefineBlackEnergyCrop('),'Energy black crop stage missing');
ok(a.includes('function v6AxisDecision('),'Y-axis/mode stage missing');
ok(a.includes("gridValueStep>=.5?'Gain':'Noise'"),'0.5 mode threshold missing');
ok(a.includes('function v6XAxisCalibration('),'X-axis calibration stage missing');
ok(a.includes("mode==='Gain'?[0,330]:[0,260]"),'Low range contract missing');
ok(a.includes("mode==='Gain'?[340,500]:[270,500]"),'High range contract missing');
ok(a.includes('mad*3.2'),'spike rejection missing');
ok(a.includes('reduce((s,q)=>s+q.y,0)/keep.length'),'post-rejection mean missing');
ok(a.includes("v6DrawCropPreview('energyPreview'"),'annotated Energy preview missing');
ok(h.includes('id="channelPreview"')&&h.includes('id="energyPreview"'),'preview UI missing');
ok(!c.match(/[^A-Za-z0-9_.]percentile\(/),'undefined percentile call remains');
ok(
  a.includes("$('analyzeBtn').onclick=async()=>") && a.includes("try{await analyzeV6()}"),
  'Analyze button not routed to async v6 pipeline'
);

console.log('v6.3.4 12-stage pipeline contract PASS');
