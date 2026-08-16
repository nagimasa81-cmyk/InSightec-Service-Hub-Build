((root,factory)=>{const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;root.EGSCore=api;})(typeof window!=='undefined'?window:globalThis,()=>{
  const SAMPLE_SPLIT=270,SAMPLE_AXIS_MAX=500;
  const clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
  const mean=a=>a.length?a.reduce((s,v)=>s+v,0)/a.length:NaN;
  const median=a=>{const b=[...a].filter(Number.isFinite).sort((x,y)=>x-y),n=b.length;if(!n)return NaN;return n%2?b[(n-1)/2]:(b[n/2-1]+b[n/2])/2};
  const percentile=(a,q)=>{const b=[...a].filter(Number.isFinite).sort((x,y)=>x-y);if(!b.length)return NaN;const p=clamp(q,0,1)*(b.length-1),i=Math.floor(p),j=Math.ceil(p);return b[i]+(b[j]-b[i])*(p-i)};
  function robust(values,z=3.5,floor=.0003){const a=values.filter(Number.isFinite);if(!a.length)return[];const med=median(a),mad=median(a.map(v=>Math.abs(v-med)));if(!Number.isFinite(mad)||mad<1e-9){const tol=Math.max(floor,Math.abs(med)*.18);return a.filter(v=>Math.abs(v-med)<=tol)}const sigma=1.4826*mad;return a.filter(v=>Math.abs(v-med)/sigma<=z)}
  function stableLevel(values,top){let a=robust(values,3.2,Math.max(.00015,top*.006));if(a.length>=5){const lo=percentile(a,.10),hi=percentile(a,.90);a=a.filter(v=>v>=lo&&v<=hi)}return {mean:mean(a),median:median(a),n:a.length,spread:Math.max(0,percentile(a,.84)-percentile(a,.16))}}
  function splitPixel(width){return Math.max(0,(width-1)*SAMPLE_SPLIT/SAMPLE_AXIS_MAX)}
  function horizontalLevels(xs,vals,top,width){
    const split=splitPixel(width),margin=Math.max(2,width*.016),left=[],right=[];
    for(let i=0;i<xs.length;i++){if(xs[i]<=split-margin)left.push(vals[i]);else if(xs[i]>=split+margin)right.push(vals[i])}
    if(left.length<5||right.length<5)throw Error('Low/High regions do not contain enough signal samples');
    const L=stableLevel(left,top),R=stableLevel(right,top);
    if(L.n<4||R.n<4||!Number.isFinite(L.mean)||!Number.isFinite(R.mean))throw Error('Signal samples were removed as outliers');
    const sep=Math.abs(R.median-L.median),noise=Math.max(.00001,(L.spread+R.spread)/2,top*.008),
          coverage=clamp(Math.min(L.n,R.n)/Math.max(12,width*.10),0,1),
          separation=clamp(sep/(noise*3),0,1),
          confidence=clamp(.55*coverage+.45*separation,0,1);
    return{low:L.mean,high:R.mean,confidence,diagnostics:{left_n:L.n,right_n:R.n,left_spread:L.spread,right_spread:R.spread,separation:sep}};
  }

  // Noise Low/High are defined by Sample# position, not by amplitude separation.
  // This is intentionally different from Gain: Noise Low and High may be nearly
  // identical and that must NOT reduce confidence or cause a classification failure.
  function noiseLevels(xs,vals,top,width){
    const split=splitPixel(width);
    const attempts=[
      Math.max(3,width*.030),   // keep well away from the 270 transition neighborhood
      Math.max(2,width*.020),
      Math.max(1,width*.010)
    ];
    let chosen=null;
    for(const margin of attempts){
      const left=[],right=[],leftX=[],rightX=[];
      for(let i=0;i<xs.length;i++){
        if(!Number.isFinite(xs[i])||!Number.isFinite(vals[i]))continue;
        if(xs[i]<=split-margin){left.push(vals[i]);leftX.push(xs[i])}
        else if(xs[i]>=split+margin){right.push(vals[i]);rightX.push(xs[i])}
      }
      if(left.length>=6&&right.length>=6){chosen={margin,left,right,leftX,rightX};break}
    }
    if(!chosen)throw Error('Noise Low/High regions do not contain enough signal samples on both sides of Sample#270');

    const L=stableLevel(chosen.left,top),R=stableLevel(chosen.right,top);
    if(L.n<5||R.n<5||!Number.isFinite(L.mean)||!Number.isFinite(R.mean))
      throw Error('Noise Low/High samples could not be stabilized');

    // Confidence is based on coverage + within-region stability only.
    // Separation is diagnostic information, never a requirement for Noise.
    const expectedLeft=Math.max(8,width*(SAMPLE_SPLIT/SAMPLE_AXIS_MAX)*.12),
          expectedRight=Math.max(8,width*((SAMPLE_AXIS_MAX-SAMPLE_SPLIT)/SAMPLE_AXIS_MAX)*.12),
          coverage=clamp(Math.min(L.n/expectedLeft,R.n/expectedRight),0,1),
          spreadScale=Math.max(.00025,top*.055),
          stableL=1-clamp(L.spread/spreadScale,0,1),
          stableR=1-clamp(R.spread/spreadScale,0,1),
          stability=(stableL+stableR)/2,
          confidence=clamp(.68*coverage+.32*stability,0,1),
          sep=Math.abs(R.median-L.median);

    return{
      low:L.mean,high:R.mean,confidence,
      splitSample:SAMPLE_SPLIT,splitX:split,marginPx:chosen.margin,
      lowRange:{x0:0,x1:Math.max(0,split-chosen.margin)},
      highRange:{x0:Math.min(width-1,split+chosen.margin),x1:Math.max(0,width-1)},
      diagnostics:{
        left_n:L.n,right_n:R.n,left_spread:L.spread,right_spread:R.spread,
        separation:sep,coverage,stability,
        separation_required:false
      }
    };
  }
  function geometry(box,insets){
    const d={left:.145,top:.08,right:.013,bottom:.27},raw={...d,...(insets||{})};
    // v5.1.3 defensive normalization:
    // current contract is fractional insets, but tolerate legacy pixel insets.
    const frac=(v,dim,def)=>{
      if(!Number.isFinite(v))return def;
      let q=Math.abs(v)>1.25?v/Math.max(1,dim):v;
      return clamp(q,0,.92);
    };
    let left=frac(raw.left,box.w,d.left),right=frac(raw.right,box.w,d.right),
        top=frac(raw.top,box.h,d.top),bottom=frac(raw.bottom,box.h,d.bottom);
    // Guarantee a non-degenerate plot even with malformed metadata.
    if(left+right>.94){const k=.94/(left+right);left*=k;right*=k}
    if(top+bottom>.94){const k=.94/(top+bottom);top*=k;bottom*=k}
    return{x0:box.x+box.w*left,y0:box.y+box.h*top,
           x1:box.x+box.w*(1-right),y1:box.y+box.h*(1-bottom)}
  }
  function splitX(box,insets){const g=geometry(box,insets);return g.x0+(g.x1-g.x0)*SAMPLE_SPLIT/SAMPLE_AXIS_MAX}
  function valueY(box,v,top,insets){const g=geometry(box,insets);return g.y1-clamp(v/Math.max(top,1e-12),0,1)*(g.y1-g.y0)}
  function spec(mode,low,high){if(mode==='Noise')return low>=0&&low<=.015&&high>=.001&&high<=.02;if(mode==='Gain')return high>=1&&high<=1.5;return false}
  return{SAMPLE_SPLIT,SAMPLE_AXIS_MAX,clamp,mean,median,percentile,robust,stableLevel,splitPixel,horizontalLevels,noiseLevels,geometry,splitX,valueY,spec};
});
