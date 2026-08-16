const fs=require('fs');
const c=fs.readFileSync('analysis_core_v2.js','utf8');
function ok(v,m){if(!v)throw Error(m)}
ok(c.includes('lattice*5.2+darkScore*2.0+signalScore*1.35'), 'structural score weights missing');
ok(c.includes('titleScore*.55'), 'title-band support missing');
ok(c.includes('lineRegularity(q.gridRowsAbs)'), 'row regularity missing');
ok(c.includes('lineRegularity(q.gridColsAbs)'), 'column regularity missing');
ok(c.includes('margin<.35'), 'ambiguity confidence penalty missing');
console.log('v5.1.0 candidate scoring regression PASS');
