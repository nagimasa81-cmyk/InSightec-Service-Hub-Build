
globalThis.window=globalThis;
require('./core.js');
const C=globalThis.EGSCore;

function assertNear(a,b,t,msg){if(Math.abs(a-b)>t)throw new Error(`${msg}: ${a} vs ${b}`)}
function run(){
  const width=501, xs=[], vals=[];
  // Low and High deliberately almost identical: visual separation is hard.
  for(let x=0;x<width;x++){
    if(x>262&&x<278) continue; // missing/transition neighborhood
    const base=x<270?0.0062:0.0064;
    const wobble=((x%11)-5)*0.000025;
    xs.push(x); vals.push(base+wobble);
  }
  const r=C.noiseLevels(xs,vals,0.04,width);
  assertNear(r.low,0.0062,0.00035,'noise low');
  assertNear(r.high,0.0064,0.00035,'noise high');
  if(r.confidence<0.55)throw new Error(`noise confidence too low: ${r.confidence}`);
  if(r.diagnostics.separation_required!==false)throw new Error('separation must not be required');

  // Equal levels are also valid and must still calculate.
  const vals2=xs.map((x,i)=>0.0070+(((i%7)-3)*0.00002));
  const r2=C.noiseLevels(xs,vals2,0.04,width);
  assertNear(r2.low,0.0070,0.0003,'equal noise low');
  assertNear(r2.high,0.0070,0.0003,'equal noise high');
  if(r2.confidence<0.55)throw new Error(`equal-level noise confidence too low: ${r2.confidence}`);
  console.log('Noise positional Low/High regression PASS');
}
run();
