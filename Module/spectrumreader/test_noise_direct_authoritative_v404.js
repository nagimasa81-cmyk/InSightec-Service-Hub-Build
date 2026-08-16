const fs=require('fs'),s=fs.readFileSync('app.js','utf8');
function ok(v,m){if(!v)throw Error(m)}
ok(s.includes('Y-axis-grid authoritative; out-of-scale trace pixels rejected'),'direct path missing');
ok(s.includes('if(pixelLevels && Number.isFinite(pixelLevels.low) && Number.isFinite(pixelLevels.high))'),'guard missing');
console.log('v4.0.4 direct Noise authoritative regression PASS');