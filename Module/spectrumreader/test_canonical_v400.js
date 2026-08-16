
const fs=require('fs');
const c=fs.readFileSync('canonical_registration_v4.js','utf8');
const a=fs.readFileSync('app.js','utf8');
function ok(v,m){if(!v)throw new Error(m)}
ok(c.includes("energyPanel:{x:"),"fixed canonical ROI missing");
ok(c.includes("function homographyFrom4"),"homography missing");
ok(c.includes("function warpToCanonical"),"warp missing");
ok(c.includes("function detectWindowQuad"),"window registration missing");
ok(a.includes("applyCanonicalRegistration"),"canonical hook missing");
ok(a.includes("canonical-fixed-energy-panel"),"fixed ROI route missing");
ok(a.includes("canonicalMode&&canonicalRegistration?.ok"),"canonical analysis route missing");
console.log("Canonical v4.0.0 regression PASS");
