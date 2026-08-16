
const fs=require('fs');
const c=fs.readFileSync('analysis_core_v2.js','utf8');
function ok(v,m){if(!v)throw Error(m)}
ok(c.includes("source:'strong-major-grid-only-v503'"),"grid-only axis missing");
ok(!c.includes("detectNoiseZeroBaseline"),"signal-derived zero detector remains");
ok(!c.includes("inferNoiseAxisFromZeroAndRows"),"signal-derived zero inference remains");
ok(!c.includes("yellow-zero-plus-grid-consensus"),"legacy yellow-zero source remains");
ok(c.includes("source:'signal-population-v500'"),"signal population extractor missing");
ok(c.includes("coverage*5.0+density*2.2+compact*1.4"),"population scoring missing");
ok(c.includes("source:'grid-axis-plus-signal-population-v500'"),"final mapping missing");
ok(c.includes("return median(a);"),"robust median final value missing");
ok(!c.includes("useCloud="),"old baseline/cloud selector remains");
console.log("v5.0.0 signal geometry regression PASS");
