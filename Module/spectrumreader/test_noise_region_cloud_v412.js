
const fs=require('fs');
const c=fs.readFileSync('analysis_core_v2.js','utf8');
function ok(v,m){if(!v)throw Error(m)}
ok(c.includes("source:'direct-noise-region-cloud-v412'"),"region cloud trace source missing");
ok(c.includes("elevatedColumnFraction>=.16"),"cloud X-support criterion missing");
ok(c.includes("allElev.length>=Math.max(18,allBase.length*.10)"),"cloud density criterion missing");
ok(c.includes("source:'noise-region-cloud-grid-mapping-v412'"),"region mapping source missing");
ok(c.includes("if(useCloud&&c.elev.length)"),"cloud must override baseline when present");
ok(c.includes("if(!Number.isFinite(y)&&c.base.length)"),"baseline fallback missing");
ok(c.includes("v=Math.max(visibleMin,Math.min(visibleMax,v))"),"outside values should clamp, not delete cloud");
console.log("v4.1.2 Noise region-cloud regression PASS");
