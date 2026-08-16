
function choose(lowCenter, step, cands){
  let high=[...cands].sort((a,b)=>b.baseScore-a.baseScore)[0];
  const distinct=cands.filter(c=>{
    const rise=(lowCenter-c.center)/step;
    const supportOK=c.coverage>=.20||c.density>=.18;
    const enoughPixels=c.n>=8;
    return rise>=.28&&supportOK&&enoughPixels;
  }).map(c=>{
    const rise=(lowCenter-c.center)/step;
    const verticalCloud=Math.min(1.5,c.spread84/step);
    return {...c,riseFromLowSteps:rise,
      selectScore:c.baseScore+Math.min(2.4,rise*1.6)+verticalCloud*.45};
  }).sort((a,b)=>b.selectScore-a.selectScore);
  if(distinct.length){
    const d=distinct[0];
    if(d.coverage>=.24||d.density>=.24||d.selectScore>=high.baseScore+.55)high=d;
  }
  return high;
}
function ok(v,m){if(!v)throw Error(m)}

// Continuing Low-level line has huge coverage, but elevated cloud is real High.
let h=choose(200,34,[
  {name:'continued-low',center:200,coverage:.98,density:.43,n:100,spread84:2,baseScore:4.7},
  {name:'high-cloud',center:166,coverage:.55,density:.36,n:60,spread84:16,baseScore:3.4}
]);
ok(h.name==='high-cloud','elevated High cloud should override continuing Low line');

// No elevated cloud: retain same-level signal.
h=choose(200,34,[
  {name:'same-level',center:198,coverage:.92,density:.55,n:100,spread84:3,baseScore:4.8},
  {name:'spike',center:160,coverage:.04,density:.03,n:4,spread84:20,baseScore:.7}
]);
ok(h.name==='same-level','sparse spike must not override same-level signal');

console.log('v5.1.3 high selection math PASS');
