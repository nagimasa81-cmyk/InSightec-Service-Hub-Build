
const fs=require('fs');
const a=fs.readFileSync('app.js','utf8');
function ok(v,m){if(!v)throw new Error(m)}
ok(a.includes("canonicalMode&&canonicalRegistration?.ok&&v2&&!roiManual"),
   "canonical plot must be auto-only");
ok(a.includes("manual-roi-authoritative-v4.0.3"),
   "manual ROI diagnostic tag missing");
ok(!a.includes("canonicalMode&&canonicalRegistration?.ok&&v2){"),
   "legacy unconditional canonical override remains");
console.log("v4.0.1 manual ROI authoritative regression PASS");
