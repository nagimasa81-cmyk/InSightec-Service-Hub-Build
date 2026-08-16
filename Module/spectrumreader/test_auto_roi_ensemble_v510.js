const fs=require('fs');
const c=fs.readFileSync('analysis_core_v2.js','utf8');
function ok(v,m){if(!v)throw Error(m)}
ok(c.includes('function energyCandidateEvidence'), 'candidate evidence missing');
ok(c.includes('function detectEnergyPanelInScope'), 'scoped ensemble missing');
ok(c.includes("source='multi-hypothesis-energy-panel-v510'"), 'auto ensemble source missing');
ok(c.includes("'auto-ensemble-v510'"), 'confirmed plot panel source missing');
ok(c.includes('panelFromConfirmedPlot(ctx,canvas,best.q,best.ev'), 'final ROI not derived from confirmed plot');
ok(!/const c=best\.q\.context;[\s\S]{0,250}return\{\s*x:c\.x/.test(c), 'legacy search-window ROI return remains');
ok(c.includes("source:'manual-scoped-same-detector-as-auto'"), 'manual shared detector missing');
ok(c.includes("source:'manual-emergency-relative-only'"), 'manual fallback not clearly emergency');
console.log('v5.1.0 Auto ROI ensemble regression PASS');
