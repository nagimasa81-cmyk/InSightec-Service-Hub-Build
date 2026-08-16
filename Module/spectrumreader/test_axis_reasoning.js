
// Static regression checks for policy invariants. DOM/image runtime tests remain in-app.
const fs=require('fs');
const s=fs.readFileSync('app.js','utf8');
function req(x,msg){if(!s.includes(x))throw new Error(msg)}
req("if(requestedMode==='Gain'||requestedMode==='Noise')","manual authoritative branch missing");
req("const cal=yAxisCalibration(box,insets,requestedMode)","manual family-specific calibration missing");
if(s.includes("let axisProbe=yAxisCalibration(roi,insets,'Any')"))throw new Error("legacy Any axis probe still active");
if(s.includes("const cal=calOverride||yAxisCalibration(box,insets,'Any')"))throw new Error("calibrateTrack Any fallback still active");
console.log('iPhone vision-axis policy regression PASS');
