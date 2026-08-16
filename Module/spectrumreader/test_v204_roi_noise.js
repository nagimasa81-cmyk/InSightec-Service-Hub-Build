
const fs=require('fs');
const c=fs.readFileSync('analysis_core_v2.js','utf8');
const a=fs.readFileSync('app.js','utf8');
function ok(x,m){if(!x)throw new Error(m)}
ok(c.includes("gridRowsAbs"),"localized structural rows not retained");
ok(c.includes("plot-localization-lattice"),"Noise axis does not reuse localization lattice");
ok(c.includes("plot.w*.40"),"full panel left context not expanded");
ok(c.includes("plot.h*.36"),"full panel bottom context not expanded");
ok(c.includes("value:.04")&&c.includes("value:.01"),"Noise fixed grid anchors missing");
ok(a.includes("v2.0.4-structural-noise-grid-mapping"),"v2.0.4 numeric path missing");
ok(a.includes("Cyan = inner numeric grid only"),"panel/grid overlay separation missing");
console.log("v2.0.4 ROI + structural Noise regression PASS");
