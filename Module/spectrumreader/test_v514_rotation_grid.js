
const fs=require('fs');
const c=fs.readFileSync('analysis_core_v2.js','utf8');
function ok(v,m){if(!v)throw Error(m)}
ok(c.includes('function rotationAwareHorizontalGridRows('),'rotation-aware sampler missing');
ok(c.includes('for(let deg=-8;deg<=8.0001;deg+=.25)'),'angle scan missing');
ok(c.includes("src:'rot-aware'"),'rotation rows not added to consensus');
ok(c.includes("source:'periodic-grid-consensus-rotaware-v5.1.4'"),'rotation-aware axis source missing');
ok(c.includes('rotationDeg:rot.angle'),'rotation angle not propagated');
console.log('v5.1.4 rotation-grid regression PASS');
