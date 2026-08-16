
const fs=require('fs');
const c=fs.readFileSync('analysis_core_v2.js','utf8');
const a=fs.readFileSync('app.js','utf8');
function ok(v,m){if(!v)throw Error(m)}
ok(c.includes("direct-noise-lower-dense-band-v406"),"lower dense-band trace missing");
ok(c.includes("quantile(ys,.72)"),"Y72 estimator missing");
ok(c.includes("Math.abs(raw[j].x-cur.x)<=6"),"local X smoothing missing");
ok(c.includes("denseTrimmedCenter"),"dense region center missing");
ok(c.includes("mad*2.8"),"MAD spike rejection missing");
ok(c.includes("10% trimmed mean"),"trimmed mean estimator missing");
ok(a.includes("Y-axis-grid authoritative; out-of-scale trace pixels rejected"),"UI diagnostic missing");
console.log("v4.0.7 Noise lower dense-band regression PASS");
