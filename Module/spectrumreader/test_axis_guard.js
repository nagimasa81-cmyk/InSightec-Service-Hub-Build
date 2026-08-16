
const fs=require('fs');
const s=fs.readFileSync('app.js','utf8');
function ok(cond,msg){if(!cond)throw new Error(msg)}
ok(s.includes("axisLabelHypotheses(norm,modeHint==='Any'?'Any':modeHint,9)"),"modeHint not enforced");
ok(s.includes("supportedSingleAxisAnchor"),"neighbor-supported single anchor missing");
ok(s.includes("Gain calibration reversed Low/High"),"Gain reverse guard missing");
ok(s.includes("values outside visible grid span"),"visible-grid span guard missing");
ok(!s.includes("source:'one-axis-label+grid-spacing'"),"unsafe old one-anchor fallback still present");
console.log("Axis contradiction guard regression PASS");
