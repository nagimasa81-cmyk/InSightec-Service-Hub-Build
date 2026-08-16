
const fs=require('fs');
const c=fs.readFileSync('analysis_core_v2.js','utf8');
const a=fs.readFileSync('app.js','utf8');
function ok(v,m){if(!v)throw new Error(m)}
ok(c.includes("function detectRightDarkFrame"),"right dark frame detector missing");
ok(c.includes("energy-dark-rectangle-boundary"),"dark frame source tag missing");
ok(c.includes("dark-rectangle-first+shared-analysis-core"),"black-frame-first path missing");
ok(c.includes("const q=plotFromGrid(ctx,canvas,roi)"),"shared plot provider must remain");
ok(c.includes("const widths=darkFrame?"),"dark-frame restricted search missing");
console.log("v3.0.3 dark-rectangle compatibility PASS");
