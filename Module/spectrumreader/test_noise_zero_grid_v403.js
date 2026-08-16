
const fs=require('fs'),c=fs.readFileSync('analysis_core_v2.js','utf8');
function ok(v,m){if(!v)throw new Error(m)}
ok(c.includes('detectNoiseZeroBaseline'),'zero baseline detector missing');
ok(c.includes('permissiveNoiseGridRows'),'permissive rows missing');
ok(c.includes('yellow-zero-plus-grid-consensus'),'consensus source missing');
ok(c.includes('inferNoiseAxisFromZeroAndRows'),'fallback missing');
console.log('v4.0.3 zero-baseline/grid consensus regression PASS');
