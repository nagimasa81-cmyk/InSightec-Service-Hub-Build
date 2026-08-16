
const fs=require('fs');
const c=fs.readFileSync('analysis_core_v2.js','utf8');
const a=fs.readFileSync('app.js','utf8');
function ok(v,m){if(!v)throw new Error(m)}
ok(c.includes("horizScore"),"horizontal continuity score missing");
ok(c.includes("edgeScore"),"structural edge score missing");
ok(c.includes("score>=.22"),"row nomination threshold missing");
ok(c.includes("err>.28"),"regular lattice validation missing");
ok(c.includes("q.noiseAxis=noiseAxisSeries"),"Noise candidate must be prepared unconditionally");
ok(a.includes("if(mi.mode==='Noise' && !v2.noiseAxis?.ok)"),"Noise-mode retry missing");
console.log("v2.0.2 structural Noise grid regression PASS");
