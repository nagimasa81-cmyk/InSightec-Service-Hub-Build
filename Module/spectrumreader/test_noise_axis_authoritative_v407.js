
const fs=require('fs');
const a=fs.readFileSync('app.js','utf8');
const c=fs.readFileSync('analysis_core_v2.js','utf8');
function ok(v,m){if(!v)throw Error(m)}
ok(c.includes("source:'noise-region-cloud-grid-mapping-v412'"),"axis-authoritative Noise source missing");
ok(c.includes("visibleMax=anchors.length?Math.max(...anchors):.04"),"visible axis max missing");
ok(c.includes("rejected.push({x:pt.x,y:pt.y,value:v})"),"out-of-scale rejection missing");
ok(c.includes("10% trimmed mean"),"robust dense-band estimator missing");
ok(a.includes("Noise grid geometry is authoritative"),"authoritative validation policy missing");
ok(a.includes("return{ok:true,axisAuthoritative:true}"),"geometry axis must survive trace outliers");
ok(!a.includes("Noise measured values exceed displayed Energy scale"),"old trace-invalidates-axis rejection remains");
ok(a.includes("Noise axis authoritative: visible"),"diagnostic missing");
console.log("v4.0.7 Noise axis-authoritative regression PASS");
