
const fs=require('fs');
const c=fs.readFileSync('analysis_core_v2.js','utf8');
const a=fs.readFileSync('app.js','utf8');
function ok(v,m){if(!v)throw Error(m)}
ok(c.includes('function consensusNoiseGridLattice('),'lattice helper missing');
ok(c.includes('if(matched<2)continue'),'two observed rows not allowed');
ok(c.includes("source:'periodic-grid-consensus-v5.1.3'"),'new axis source missing');
ok(c.includes("source:'signal-population-v500'"),'signal population path lost');
ok(c.includes("source:'manual-tight-grid-v5.1.3'"),'manual tight ROI path missing');
ok(c.includes("gridTop+lat.stepPx*4,value:0"),'grid-derived zero missing');
ok(!c.includes("strong-major-grid-only-v503"),'strict old axis still active');
ok(a.includes('v5.1.3'),'app version missing');
console.log('v5.1.3 current contract PASS');
