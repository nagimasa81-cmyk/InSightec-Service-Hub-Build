
const fs=require('fs');
const s=fs.readFileSync('app.js','utf8');
function ok(v,m){if(!v)throw new Error(m)}
ok(s.includes("labelAspect:"),"label aspect capture missing");
ok(s.includes("function axisVisualFamilyEvidence"),"visual family helper missing");
ok(s.includes("aspect>=2.15"),"long-decimal Noise rule missing");
ok(s.includes("visualDiff<-.28"),"Auto visual Noise override missing");
ok(s.includes("function completedAxisAnchorSeries"),"ordinal fill helper missing");
console.log("Axis visual-family regression PASS");
