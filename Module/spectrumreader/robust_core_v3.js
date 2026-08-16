
((root,factory)=>{
  const api=factory();
  if(typeof module==='object'&&module.exports)module.exports=api;
  root.EGSRobustV3=api;
})(typeof window!=='undefined'?window:globalThis,()=>{

  const clamp=(v,a=0,b=1)=>Math.max(a,Math.min(b,v));
  const finite=v=>Number.isFinite(v);
  function H(kind,value,score,source,evidence={}){
    return {kind,value,score:clamp(score),source,evidence};
  }
  function rank(list){
    return [...(list||[])].filter(x=>x&&finite(x.score)).sort((a,b)=>b.score-a.score);
  }
  function select(list,{margin=.10,min=.45,allowUnknown=true}={}){
    const r=rank(list);
    if(!r.length)return {value:allowUnknown?'Unknown':null,score:0,source:'no-hypothesis',ranked:[]};
    const a=r[0],b=r[1];
    if(a.score<min)return {value:allowUnknown?'Unknown':null,score:a.score,source:'below-minimum',ranked:r};
    if(b && a.value!==b.value && a.score-b.score<margin)
      return {value:allowUnknown?'Unknown':null,score:a.score,source:'ambiguous-margin',ranked:r};
    return {...a,ranked:r};
  }

  function modeHypotheses(requested,v2,traceMode,axisReason){
    if(requested==='Gain'||requested==='Noise')return [H('mode',requested,1,'manual')];
    const out=[];
    if(v2?.axisFamily?.family)
      out.push(H('mode',v2.axisFamily.family,.55+.40*(v2.axisFamily.confidence||0),'axis-family',v2.axisFamily));
    if(traceMode==='Gain'||traceMode==='Noise')
      out.push(H('mode',traceMode,.52,'trace-morphology'));
    if(axisReason?.mode)
      out.push(H('mode',axisReason.mode,.50+.35*(axisReason.confidence||0),'axis-reasoning',axisReason));
    return out;
  }

  function resolveMode(requested,v2,traceMode,axisReason){
    return select(modeHypotheses(requested,v2,traceMode,axisReason),{margin:.12,min:.48});
  }

  function resolveChannel(checked,colorMatched){
    if(Array.isArray(checked)&&checked.length===1)
      return H('channel',checked[0],1,'single-checked');
    if(Array.isArray(checked)&&checked.length>1){
      if(colorMatched!==null&&colorMatched!==undefined&&checked.includes(colorMatched))
        return H('channel',colorMatched,.92,'foreground-color-matched');
      return H('channel','Unknown',.60,'multiple-checked-no-color-match',{checked,colorMatched});
    }
    return H('channel','Unknown',.50,'no-checked-channel');
  }

  function resolveNoiseNumeric(v2){
    const cand=[];
    if(v2?.noiseValues?.ok){
      const n=v2.noiseValues,axis=v2.noiseAxis||{};
      let score=.62;
      score+=.18*(axis.confidence||0);
      score+=.10*Math.min(1,(n.lowCount||0)/25);
      score+=.10*Math.min(1,(n.highCount||0)/25);
      const sane=finite(n.low)&&finite(n.high)&&n.low>=-.003&&n.high>=-.003&&n.low<=.06&&n.high<=.06;
      if(sane)cand.push(H('numeric',{low:n.low,high:n.high,lowY:n.lowY,highY:n.highY,splitX:n.splitX},score,'direct-noise-grid',n));
    }
    return select(cand,{margin:.08,min:.55,allowUnknown:false});
  }

  function audit({mode,channel,numeric,v2}){
    const issues=[];
    if(!v2?.plot)issues.push('plot-unresolved');
    if(mode?.value==='Unknown')issues.push('mode-ambiguous');
    if(channel?.value==='Unknown')issues.push('channel-unknown');
    if(mode?.value==='Noise'&&!v2?.noiseAxis?.ok)issues.push('noise-axis-unresolved');
    if(!numeric?.value)issues.push('numeric-withheld');
    return {ok:issues.filter(x=>x!=='channel-unknown').length===0,issues};
  }

  return{H,rank,select,modeHypotheses,resolveMode,resolveChannel,resolveNoiseNumeric,audit};
});
