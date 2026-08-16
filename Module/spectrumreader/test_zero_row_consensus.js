
const fs=require('fs');
const s=fs.readFileSync('app.js','utf8');
function ok(v,m){if(!v)throw new Error(m)}
ok(s.includes("source:'zero-row-label-grid-consensus'"),"zero-row consensus calibration missing");
ok(s.includes("const offset=nearest+qRound"),"zero-row offset equation missing");
ok(s.includes("bestVote.count>=2"),"two-label consensus requirement missing");
ok(!s.includes("bottom=centersAbs.at(-1)"),"bottom-grid=zero assumption still present");
console.log("Zero-row consensus regression PASS");
