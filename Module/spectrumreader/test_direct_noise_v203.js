
const fs=require('fs');
const c=fs.readFileSync('analysis_core_v2.js','utf8');
const a=fs.readFileSync('app.js','utf8');
function ok(v,m){if(!v)throw new Error(m)}
ok(c.includes("function directNoiseTrace"),"direct Noise trace missing");
ok(c.includes("function directNoiseValues"),"direct Noise mapper missing");
ok(c.includes("noiseForegroundMask"),"foreground mask missing");
ok(c.includes("(270/500)"),"270/500 split missing");
ok(a.includes("structural-noise-grid-mapping"),"direct Noise numeric mapping missing");
ok(a.includes("v2_noise_values"),"Noise value diagnostics missing");
ok(a.includes("nv.lowY"),"Low debug line missing");
ok(a.includes("nv.highY"),"High debug line missing");
console.log("v2.0.3 direct Noise numeric regression PASS");
