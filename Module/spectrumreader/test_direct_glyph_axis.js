
const fs=require('fs');
const s=fs.readFileSync('app.js','utf8');
function ok(v,m){if(!v)throw new Error(m)}
ok(s.includes("for(let v=0;v<=4;v++)add(v,[v.toFixed(1)],'Gain');"),"Gain candidates not constrained");
ok(s.includes("for(let i=0;i<=5;i++)"),"Noise candidates not constrained");
ok(s.includes("arr._aspect"),"glyph aspect metadata missing");
ok(s.includes("projectionSimilarity"),"projection similarity missing");
ok(s.includes("directStrong<2"),"two-direct-anchor requirement missing");
ok(!s.includes("source:'one-axis-label+neighbor-series'"),"one-anchor calibration still active");
console.log("Direct-glyph axis regression PASS");
