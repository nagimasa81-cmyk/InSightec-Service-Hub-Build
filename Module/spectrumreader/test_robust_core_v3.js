
const R=require('./robust_core_v3.js');
function ok(v,m){if(!v)throw new Error(m)}
let m=R.resolveMode('Auto',{axisFamily:{family:'Noise',confidence:.85}},'Gain',null);
ok(m.value==='Noise','strong axis-family should beat weak trace morphology');
let c=R.resolveChannel([1,2,3],2);
ok(c.value===2,'matched foreground must resolve among checked channels');
c=R.resolveChannel([1,2,3],7);
ok(c.value==='Unknown','mismatched foreground must stay Unknown');
let n=R.resolveNoiseNumeric({noiseAxis:{ok:true,confidence:.9},noiseValues:{ok:true,low:.006,high:.014,lowCount:40,highCount:50}});
ok(n.value&&Math.abs(n.value.low-.006)<1e-9,'Noise numeric consensus failed');
console.log('Robust Core v3 iPhone policy PASS');
