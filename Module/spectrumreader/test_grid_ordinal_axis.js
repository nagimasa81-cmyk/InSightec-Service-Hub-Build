
const fs=require('fs');
const s=fs.readFileSync('app.js','utf8');
function ok(v,m){if(!v)throw new Error(m)}
ok(!s.includes("bottom=centersAbs.at(-1)"),"bottom-grid=zero assumption still active");
ok(s.includes("zero-row-label-grid-consensus"),"zero-row label/grid consensus missing");
console.log("Grid ordinal zero-origin regression PASS");
