
((root,factory)=>{
  const api=factory();
  if(typeof module==='object'&&module.exports)module.exports=api;
  root.EGSAnalysisV2=api;
})(typeof window!=='undefined'?window:globalThis,()=>{

  const clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
  const median=a=>{
    const b=[...a].filter(Number.isFinite).sort((x,y)=>x-y),n=b.length;
    if(!n)return NaN;
    return n%2?b[(n-1)/2]:(b[n/2-1]+b[n/2])/2;
  };

  function greenish(r,g,b){
    const mx=Math.max(r,g,b),mn=Math.min(r,g,b),sat=mx-mn,lum=(r+g+b)/3;
    return g>34&&(
      (g>r*1.045&&g>b*.96&&g-Math.max(r,b)>3)||
      (lum>42&&sat>20&&g>=mx-3)
    );
  }
  const dark=(r,g,b)=>(r+g+b)/3<112;

  function groups(scores,threshold,maxGap=2){
    const ids=[],out=[];
    for(let i=0;i<scores.length;i++)if(scores[i]>=threshold)ids.push(i);
    for(const v of ids){
      if(!out.length||v-out.at(-1).at(-1)>maxGap)out.push([v]);
      else out.at(-1).push(v);
    }
    return out.map(g=>g.reduce((a,b)=>a+b,0)/g.length);
  }

  function regularRun(values,minGap,maxGap){
    if(values.length<3)return null;
    let best=null;
    for(let i=0;i<values.length-2;i++)for(let j=i+1;j<values.length-1;j++){
      const gap=values[j]-values[i];
      if(gap<minGap||gap>maxGap)continue;
      const seq=[values[i],values[j]];
      let last=values[j],err=0;
      for(let k=j+1;k<values.length;k++){
        const d=values[k]-last;
        if(Math.abs(d-gap)<=Math.max(2,gap*.28)){
          seq.push(values[k]);err+=Math.abs(d-gap)/Math.max(1,gap);last=values[k];
        }
      }
      if(seq.length<3)continue;
      const score=seq.length*4+(seq.at(-1)-seq[0])/Math.max(1,gap)-err;
      if(!best||score>best.score)best={seq,gap,score};
    }
    return best;
  }

  function plotFromGrid(ctx,canvas,roi){
    const x0=Math.max(0,Math.floor(roi.x)),
          y0=Math.max(0,Math.floor(roi.y)),
          w=Math.max(2,Math.min(canvas.width-x0,Math.ceil(roi.w))),
          h=Math.max(2,Math.min(canvas.height-y0,Math.ceil(roi.h))),
          im=ctx.getImageData(x0,y0,w,h).data,
          row=new Uint32Array(h),col=new Uint32Array(w),
          darkRow=new Uint32Array(h),darkCol=new Uint32Array(w);

    for(let y=0;y<h;y++)for(let x=0;x<w;x++){
      const i=(y*w+x)*4,r=im[i],g=im[i+1],b=im[i+2];
      if(greenish(r,g,b)){row[y]++;col[x]++}
      if(dark(r,g,b)){darkRow[y]++;darkCol[x]++}
    }

    const rows=groups(row,Math.max(6,w*.20)),
          cols=groups(col,Math.max(6,h*.19)),
          rr=regularRun(rows,Math.max(5,h*.045),h*.30),
          cc=regularRun(cols,Math.max(6,w*.045),w*.25);

    let top,bottom,left,right,source='';
    if(rr&&cc){
      top=rr.seq[0];bottom=rr.seq.at(-1);
      left=cc.seq[0];right=cc.seq.at(-1);
      source='grid-lattice';
    }else{
      const rids=[],cids=[];
      for(let y=0;y<Math.floor(h*.78);y++)if(darkRow[y]>w*.28)rids.push(y);
      for(let x=Math.floor(w*.34);x<w;x++)if(darkCol[x]>h*.16)cids.push(x);
      if(rids.length&&cids.length){
        top=Math.min(...rids);bottom=Math.max(...rids);
        left=Math.min(...cids);right=Math.max(...cids);
        source='dark-rectangle';
      }
    }
    if(![top,bottom,left,right].every(Number.isFinite))return null;
    if(right-left<w*.26||bottom-top<h*.16)return null;

    const near=(arr,target,rad)=>{
      let best=target,score=-1;
      const a=Math.max(0,Math.floor(target-rad)),b=Math.min(arr.length-1,Math.ceil(target+rad));
      for(let i=a;i<=b;i++)if(arr[i]>score){best=i;score=arr[i]}
      return best;
    };
    top=near(row,top,Math.max(3,h*.035));
    bottom=near(row,bottom,Math.max(3,h*.035));
    left=near(col,left,Math.max(3,w*.035));
    right=near(col,right,Math.max(3,w*.035));

    const plot={x:x0+left,y:y0+top,w:right-left,h:bottom-top,
                x0:x0+left,y0:y0+top,x1:x0+right,y1:y0+bottom,source};
    const aspect=plot.w/Math.max(1,plot.h);
    if(aspect<1.25||aspect>4.5)return null;

    // v2.0.4: the grid lattice is NOT the whole Energy-per-Band panel.
    // Keep plot for numeric geometry, but expand context to include Y labels/title/X labels.
    const lp=Math.max(28,plot.w*.40),rp=Math.max(10,plot.w*.10),
          tp=Math.max(10,plot.h*.18),bp=Math.max(18,plot.h*.36),
          cx0=clamp(plot.x-lp,0,canvas.width-2),
          cy0=clamp(plot.y-tp,0,canvas.height-2),
          cx1=clamp(plot.x+plot.w+rp,cx0+2,canvas.width),
          cy1=clamp(plot.y+plot.h+bp,cy0+2,canvas.height),
          context={x:cx0,y:cy0,w:cx1-cx0,h:cy1-cy0},
          insets={
            left:(plot.x-context.x)/context.w,
            top:(plot.y-context.y)/context.h,
            right:(context.x+context.w-(plot.x+plot.w))/context.w,
            bottom:(context.y+context.h-(plot.y+plot.h))/context.h,
            source:'v2-normalized-plot-context'
          };
    return{plot,context,insets,rows,cols,
      gridRowsAbs:rr?.seq?.map(y=>y0+y)||[],
      gridColsAbs:cc?.seq?.map(x=>x0+x)||[],
      gridStepY:rr?.gap||NaN,gridStepX:cc?.gap||NaN};
  }

  function axisStripFamily(ctx,canvas,q){
    if(!q)return{family:null,confidence:0,reason:'no plot'};
    const p=q.plot,
          step=Number.isFinite(q.gridStepY)?q.gridStepY:Math.max(8,p.h/4),
          sx0=Math.max(0,Math.floor(p.x-p.w*.27)),
          sx1=Math.max(sx0+4,Math.floor(p.x-p.w*.015)),
          sw=sx1-sx0,
          count=Math.max(3,Math.min(7,Math.round(p.h/step)+1)),
          aspects=[],widths=[];

    for(let k=0;k<count;k++){
      const cy=p.y+k*(p.h/Math.max(1,count-1)),
            y0=Math.max(0,Math.floor(cy-step*.34)),
            y1=Math.min(canvas.height,Math.ceil(cy+step*.34)),
            h=Math.max(1,y1-y0),
            im=ctx.getImageData(sx0,y0,sw,h).data;
      let minx=Infinity,miny=Infinity,maxx=-Infinity,maxy=-Infinity,n=0;
      for(let y=0;y<h;y++)for(let x=0;x<sw;x++){
        const i=(y*sw+x)*4,r=im[i],g=im[i+1],b=im[i+2],
              mx=Math.max(r,g,b),mn=Math.min(r,g,b),sat=mx-mn,lum=(r+g+b)/3,
              glyph=greenish(r,g,b)||(lum>80&&sat<62);
        if(glyph){minx=Math.min(minx,x);maxx=Math.max(maxx,x);miny=Math.min(miny,y);maxy=Math.max(maxy,y);n++}
      }
      if(n<5||!Number.isFinite(minx))continue;
      const ww=maxx-minx+1,hh=maxy-miny+1;
      if(ww>=3&&hh>=3){aspects.push(ww/hh);widths.push(ww)}
    }
    if(aspects.length<2)return{family:null,confidence:0,reason:'insufficient Y-axis glyph rows',aspects,widths};

    const a=median(aspects),wm=median(widths);
    if(a>=2.0||wm>=24)
      return{family:'Noise',confidence:clamp(.60+(a-2)*.18+(wm-24)*.012,.55,.96),
             reason:'long decimal Y-axis glyphs',aspect:a,width:wm,rows:aspects.length};
    if(a>0&&a<=1.55&&wm<=20)
      return{family:'Gain',confidence:clamp(.58+(1.55-a)*.22+(20-wm)*.010,.54,.94),
             reason:'short Gain Y-axis glyphs',aspect:a,width:wm,rows:aspects.length};
    return{family:null,confidence:.35,reason:'axis glyph geometry ambiguous',aspect:a,width:wm,rows:aspects.length};
  }



  function sampleHorizontalGridRows(ctx,canvas,prepared){
    const p=prepared.plot,
          x0=Math.max(0,Math.floor(p.x)),
          y0=Math.max(0,Math.floor(p.y)),
          w=Math.max(2,Math.floor(p.w)),
          h=Math.max(2,Math.floor(p.h)),
          im=ctx.getImageData(x0,y0,w,h).data,
          greenScore=new Float32Array(h),
          horizScore=new Float32Array(h),
          edgeScore=new Float32Array(h);

    // Evaluate only the middle 82% of the plot width so Y labels, title text,
    // mouse tooltip and right-edge clutter cannot dominate the row score.
    const xa=Math.floor(w*.08), xb=Math.max(xa+2,Math.floor(w*.90));

    for(let y=0;y<h;y++){
      let green=0,run=0,maxRun=0,lumSum=0,edge=0;
      let prevLum=null;
      for(let x=xa;x<xb;x++){
        const i=(y*w+x)*4,r=im[i],g=im[i+1],b=im[i+2],
              lum=(r+g+b)/3,
              gr=greenish(r,g,b),
              lineLike=gr || (g>32 && g>=r*.93 && g>=b*.90 && lum<145);
        if(gr)green++;
        if(lineLike){run++;if(run>maxRun)maxRun=run}else run=0;
        lumSum+=lum;
        if(prevLum!==null)edge+=Math.abs(lum-prevLum);
        prevLum=lum;
      }
      greenScore[y]=green/Math.max(1,xb-xa);
      horizScore[y]=maxRun/Math.max(1,xb-xa);
      edgeScore[y]=edge/Math.max(1,xb-xa-1);
    }

    // A major horizontal grid row is often dim/green and horizontally
    // continuous. Camera moire can weaken the green component, so continuity
    // alone is allowed to nominate a row.
    const raw=[];
    for(let y=1;y<h-1;y++){
      const score=
        greenScore[y]*1.25 +
        horizScore[y]*1.65 +
        Math.min(.30,edgeScore[y]/90*.30);

      const local=score>=(
        greenScore[y-1]*1.25+horizScore[y-1]*1.65+Math.min(.30,edgeScore[y-1]/90*.30)
      ) && score>=(
        greenScore[y+1]*1.25+horizScore[y+1]*1.65+Math.min(.30,edgeScore[y+1]/90*.30)
      );

      if(local && score>=.22) raw.push({y,score});
    }

    // Merge nearby peaks into a single row.
    const merged=[];
    for(const q of raw){
      const last=merged.at(-1);
      if(!last || q.y-last.y>Math.max(2,h*.018)){
        merged.push({...q});
      }else if(q.score>last.score){
        merged[merged.length-1]={...q};
      }
    }

    // Search all candidate subsets for the most regular 4-6 row lattice.
    let best=null;
    for(let i=0;i<merged.length;i++){
      for(let j=i+3;j<Math.min(merged.length,i+8);j++){
        const seq=merged.slice(i,j+1),
              gaps=[];
        for(let k=1;k<seq.length;k++)gaps.push(seq[k].y-seq[k-1].y);
        const med=median(gaps);
        if(!(med>=h*.10 && med<=h*.34))continue;
        const err=median(gaps.map(g=>Math.abs(g-med)/Math.max(1,med)));
        if(err>.28)continue;
        const strength=median(seq.map(q=>q.score));
        const score=seq.length*3 + strength*4 - err*7;
        if(!best||score>best.score)best={seq,step:med,err,score};
      }
    }

    if(best){
      return best.seq.map(q=>y0+q.y);
    }

    // Fallback: use green projection groups with a much lower threshold.
    const fallbackScores=new Uint32Array(h);
    for(let y=0;y<h;y++)
      fallbackScores[y]=Math.round(greenScore[y]*(xb-xa));
    return groups(fallbackScores,Math.max(4,(xb-xa)*.07),3)
      .map(v=>y0+v).sort((a,b)=>a-b);
  }



  function permissiveNoiseGridRows(ctx,canvas,prepared){
    // Broad green/dark-green row projection. Unlike the old detector this does not
    // require a single uninterrupted line, because the yellow trace and camera moire
    // break horizontal grid lines into fragments.
    const p=prepared.plot,x0=Math.max(0,Math.floor(p.x)),y0=Math.max(0,Math.floor(p.y)),
          w=Math.max(2,Math.floor(p.w)),h=Math.max(2,Math.floor(p.h)),
          im=ctx.getImageData(x0,y0,w,h).data,xa=Math.floor(w*.08),xb=Math.floor(w*.94),
          scores=[];
    for(let y=0;y<h;y++){
      let n=0;
      for(let x=xa;x<xb;x++){
        const i=(y*w+x)*4,r=im[i],g=im[i+1],b=im[i+2],mx=Math.max(r,g,b),mn=Math.min(r,g,b);
        // green grid: permit desaturated/blurred camera pixels
        if(g>=r*.88&&g>=b*.90&&g>28&&mx-mn>5&&mx<205)n++;
      }
      scores.push(n/Math.max(1,xb-xa));
    }
    const peaks=[];
    for(let y=2;y<h-2;y++){
      if(scores[y]>=.055&&scores[y]>=scores[y-1]&&scores[y]>=scores[y+1])
        peaks.push({y:y0+y,score:scores[y]});
    }
    const out=[];
    for(const q of peaks){
      const last=out.at(-1);
      if(!last||q.y-last.y>Math.max(3,h*.025))out.push(q);
      else if(q.score>last.score)out[out.length-1]=q;
    }
    return out;
  }





  function rotationAwareHorizontalGridRows(ctx,canvas,prepared){
    // v6.0.0: detect horizontal major-grid rows while compensating small in-plane rotation.
    // We do NOT rotate the display or mutate source pixels. Instead, each candidate
    // horizontal line is sampled along a slope and converted back to a deskewed center-Y.
    const p=prepared.plot,
          x0=Math.max(0,Math.floor(p.x)),y0=Math.max(0,Math.floor(p.y)),
          w=Math.max(8,Math.min(canvas.width-x0,Math.floor(p.w))),
          h=Math.max(8,Math.min(canvas.height-y0,Math.floor(p.h)));

    if(w<12||h<12)return{angle:0,confidence:0,rows:[]};

    const im=ctx.getImageData(x0,y0,w,h).data,
          xa=Math.floor(w*.08),xb=Math.max(xa+4,Math.floor(w*.94)),
          cx=(xa+xb)/2;

    function evidence(x,y){
      if(x<0||y<0||x>=w||y>=h)return 0;
      const i=(Math.round(y)*w+Math.round(x))*4,
            r=im[i],g=im[i+1],b=im[i+2],
            lum=(r+g+b)/3,
            green=(g>34&&g>r*1.06&&g>b*1.02&&(g-Math.max(r,b))>2&&lum<185),
            gray=(lum<125&&Math.max(r,g,b)-Math.min(r,g,b)<44);
      return green?1.0:(gray?.22:0);
    }

    // Angle search: choose angle maximizing long-line continuity over several rows.
    let bestAngle=0,bestScore=-1,second=-1;
    for(let deg=-8;deg<=8.0001;deg+=.25){
      const slope=Math.tan(deg*Math.PI/180);
      let score=0,validRows=0;
      const yStep=Math.max(2,Math.floor(h/36));
      for(let yc=Math.floor(h*.08);yc<Math.floor(h*.94);yc+=yStep){
        let hits=0,run=0,maxRun=0,n=0;
        for(let x=xa;x<xb;x++){
          const y=yc+slope*(x-cx),
                ev=evidence(x,y);
          n++;
          if(ev>=.8){hits+=ev;run++;if(run>maxRun)maxRun=run}
          else if(ev>0){hits+=ev;run=0}
          else run=0;
        }
        const frac=hits/Math.max(1,n),
              cont=maxRun/Math.max(1,n);
        if(frac>.07||cont>.16){
          score+=frac*.9+cont*1.8;
          validRows++;
        }
      }
      score+=validRows*.035;
      if(score>bestScore){
        second=bestScore;bestScore=score;bestAngle=deg;
      }else if(score>second)second=score;
    }

    // With chosen angle, build a deskewed row-score profile.
    const slope=Math.tan(bestAngle*Math.PI/180),raw=[];
    for(let yc=1;yc<h-1;yc++){
      let hits=0,n=0,run=0,maxRun=0;
      for(let x=xa;x<xb;x++){
        const y=yc+slope*(x-cx),
              ev=evidence(x,y);
        n++;
        if(ev>=.8){hits+=ev;run++;if(run>maxRun)maxRun=run}
        else if(ev>0){hits+=ev;run=0}
        else run=0;
      }
      const frac=hits/Math.max(1,n),
            cont=maxRun/Math.max(1,n),
            score=frac*1.15+cont*1.75;
      if(score>=.20)raw.push({y:y0+yc,score,frac,cont});
    }

    const merged=[];
    for(const q of raw){
      const last=merged.at(-1);
      if(!last||q.y-last.y>Math.max(2,h*.018))merged.push({...q});
      else if(q.score>last.score)merged[merged.length-1]={...q};
    }

    const margin=bestScore-Math.max(0,second),
          confidence=Math.max(0,Math.min(.99,.50+margin*.55+Math.min(.25,bestScore*.02)));
    return{
      angle:bestAngle,
      confidence,
      rows:merged.sort((a,b)=>a.y-b.y),
      score:bestScore,
      source:'rotation-aware-grid-v6.0.0'
    };
  }

  function strongHorizontalMajorGridRows(ctx,canvas,prepared){
    // v5.0.3: major grid must have distributed horizontal support.
    const p=prepared.plot,
          x0=Math.max(0,Math.floor(p.x)),y0=Math.max(0,Math.floor(p.y)),
          w=Math.max(2,Math.floor(p.w)),h=Math.max(2,Math.floor(p.h)),
          im=ctx.getImageData(x0,y0,w,h).data,
          xa=Math.floor(w*.10),xb=Math.floor(w*.94),
          bins=8,bw=Math.max(3,Math.floor((xb-xa)/bins)),cand=[];
    for(let y=1;y<h-1;y++){
      let supported=0,totalGreen=0,total=0;
      for(let b=0;b<bins;b++){
        const aa=xa+b*bw,z=(b===bins-1?xb:Math.min(xb,aa+bw));
        let gn=0,n=0;
        for(let x=aa;x<z;x++){
          const i=(y*w+x)*4,r=im[i],g=im[i+1],bb=im[i+2],lum=(r+g+bb)/3,
                trueGrid=(g>34&&g>r*1.10&&g>bb*1.04&&(g-Math.max(r,bb))>4&&lum<175);
          if(trueGrid)gn++;n++;
        }
        totalGreen+=gn;total+=n;
        if(gn/Math.max(1,n)>=.12)supported++;
      }
      const frac=totalGreen/Math.max(1,total),support=supported/bins;
      if(support>=.62&&frac>=.10)cand.push({y:y0+y,support,frac,score:support*2+frac});
    }
    const groups=[];
    for(const q of cand){
      const last=groups.at(-1);
      if(!last||q.y-last.items.at(-1).y>Math.max(2,h*.018))groups.push({items:[q]});
      else last.items.push(q);
    }
    return groups.map(g=>{g.items.sort((a,b)=>b.score-a.score);return g.items[0]})
      .sort((a,b)=>a.y-b.y);
  }


  function consensusNoiseGridLattice(ctx,canvas,prepared){
    const p=prepared.plot,
          rot=rotationAwareHorizontalGridRows(ctx,canvas,prepared),
          strong=strongHorizontalMajorGridRows(ctx,canvas,prepared),
          sampled=sampleHorizontalGridRows(ctx,canvas,prepared),
          structural=(prepared.gridRowsAbs||[]).filter(Number.isFinite),
          all=[...rot.rows.map(q=>({y:q.y,w:3.6,src:'rot-aware'})),
               ...strong.map(q=>({y:q.y,w:3.0,src:'strong'})),
               ...sampled.map(y=>({y,w:1.8,src:'sampled'})),
               ...structural.map(y=>({y,w:2.2,src:'structural'}))]
            .filter(q=>q.y>=p.y-p.h*.08&&q.y<=p.y+p.h*1.08)
            .sort((a,b)=>a.y-b.y);

    const merged=[];
    for(const q of all){
      const last=merged.at(-1);
      if(last&&Math.abs(q.y-last.y)<=Math.max(2,p.h*.020)){
        const tw=last.w+q.w;
        last.y=(last.y*last.w+q.y*q.w)/tw;
        last.w=tw;
        last.src+='+'+q.src;
      }else merged.push({...q});
    }

    const steps=[];
    if(Number.isFinite(prepared.gridStepY))steps.push(prepared.gridStepY);
    for(let i=0;i<merged.length;i++)for(let j=i+1;j<merged.length;j++){
      const d=merged[j].y-merged[i].y;
      for(const div of [1,2,3,4]){
        const st=d/div;
        if(st>=p.h*.10&&st<=p.h*.30)steps.push(st);
      }
    }
    for(const ratio of [.62,.68,.74,.80,.86,.92])steps.push(p.h*ratio/4);
    if(!steps.length)return{ok:false,reason:'no grid step candidates',rows:merged};

    steps.sort((a,b)=>a-b);
    const uniq=[];
    for(const st of steps){
      if(!uniq.length||Math.abs(st-uniq.at(-1))>Math.max(1,p.h*.012))uniq.push(st);
    }

    let best=null;
    for(const step of uniq){
      const phases=[p.y];
      for(const q of merged)for(let k=0;k<5;k++)phases.push(q.y-k*step);

      for(const top of phases){
        if(top<p.y-p.h*.10||top>p.y+p.h*.28)continue;
        const zero=top+4*step, span=(4*step)/Math.max(1,p.h);
        if(span<.52||span>1.02)continue;

        let support=0,matched=0;
        const residuals=[];
        for(let k=0;k<5;k++){
          const target=top+k*step;
          let nearest=null,dist=Infinity;
          for(const q of merged){
            const d=Math.abs(q.y-target);
            if(d<dist){dist=d;nearest=q}
          }
          const tol=Math.max(2.5,step*.20);
          if(nearest&&dist<=tol){
            matched++;
            support+=nearest.w*(1-dist/tol);
            residuals.push(dist/Math.max(1,step));
          }
        }
        if(matched<2)continue;

        const resid=residuals.length?median(residuals):1,
              topPenalty=Math.abs(top-p.y)/Math.max(1,p.h),
              zeroPenalty=Math.max(0,(zero-(p.y+p.h))/Math.max(1,p.h)),
              stepPrior=Number.isFinite(prepared.gridStepY)
                ?Math.abs(step-prepared.gridStepY)/Math.max(1,prepared.gridStepY):0,
              score=support+matched*2.8-resid*8-topPenalty*2.5-zeroPenalty*1.5-stepPrior*2.0;

        if(!best||score>best.score)
          best={top,zero,step,matched,support,resid,span,score,rows:merged};
      }
    }

    if(!best)return{ok:false,reason:'no coherent periodic major-grid lattice',rows:merged};

    return{
      ok:true,source:'periodic-grid-consensus-rotaware-v6.0.0',
      gridTop:best.top,zeroY:best.zero,stepPx:best.step,
      matchedRows:best.matched,support:best.support,residual:best.resid,
      spanRatio:best.span,score:best.score,rows:best.rows,
      rotationDeg:rot.angle,rotationConfidence:rot.confidence,
      rotationRows:rot.rows
    };
  }

  function noiseAxisSeries(ctx,canvas,prepared){
    const lat=consensusNoiseGridLattice(ctx,canvas,prepared);
    if(!lat.ok){
      return{
        ok:false,
        reason:`Noise Y-axis grid lattice unavailable: ${lat.reason||'unknown'}`,
        source:'periodic-grid-consensus-rotaware-v6.0.0',
        lattice:lat
      };
    }

    const anchors=[
      {y:lat.gridTop,value:.04,geometry:true},
      {y:lat.gridTop+lat.stepPx,value:.03,geometry:true},
      {y:lat.gridTop+lat.stepPx*2,value:.02,geometry:true},
      {y:lat.gridTop+lat.stepPx*3,value:.01,geometry:true},
      {y:lat.gridTop+lat.stepPx*4,value:0,geometry:true}
    ];
    for(const a of anchors){
      a.observed=(lat.rows||[]).some(q=>Math.abs(q.y-a.y)<=Math.max(2.5,lat.stepPx*.20));
    }

    const observed=anchors.filter(a=>a.observed).length,
          confidence=clamp(.68+observed*.055+Math.min(.12,(lat.support||0)*.006)-(lat.residual||0)*.18,.62,.98);

    return{
      ok:true,family:'Noise',
      source:'periodic-grid-consensus-rotaware-v6.0.0',
      anchors,stepPx:lat.stepPx,stepValue:.01,zeroY:lat.zeroY,confidence,
      lattice:lat,
      geometry:{
        rowCount:observed,reconstructedRows:5-observed,
        gridTop:lat.gridTop,gridZero:lat.zeroY,stepPx:lat.stepPx,
        residual:lat.residual,spanRatio:lat.spanRatio,
        rotationDeg:lat.rotationDeg,rotationConfidence:lat.rotationConfidence
      }
    };
  }

  function pixelYToValue(y,cal){
    if(!cal?.ok)return NaN;
    return (cal.zeroY-y)/Math.max(1e-9,cal.stepPx)*cal.stepValue;
  }


  function rgbToHue(r,g,b){
    const mx=Math.max(r,g,b),mn=Math.min(r,g,b),d=mx-mn;
    if(d===0)return 0;
    let h;
    if(mx===r)h=((g-b)/d)%6;
    else if(mx===g)h=(b-r)/d+2;
    else h=(r-g)/d+4;
    h*=60;if(h<0)h+=360;
    return h;
  }

  function noiseForegroundMask(r,g,b){
    const mx=Math.max(r,g,b),mn=Math.min(r,g,b),
          sat=(mx-mn)/Math.max(1,mx),lum=(r+g+b)/3,h=rgbToHue(r,g,b);
    return lum>=72&&sat>=.28&&h>=35&&h<=105&&mx>=95;
  }

  function directNoiseTrace(ctx,canvas,prepared){
    // v6.0.0 REGIONAL POPULATION model.
    // Y-axis calibration is independent. Here we only identify the actual
    // foreground signal populations in Sample 0-270 and 270-500.
    //
    // Important Noise behavior:
    // - A long horizontal Low signal is a real measured signal, never "zero".
    // - In High, a continuing Low-level line may coexist with a true elevated
    //   signal cloud. Coverage alone must NOT make the continuing line win.
    const p=prepared.plot,cal=prepared.noiseAxis,
          x0=Math.max(0,Math.floor(p.x)),y0=Math.max(0,Math.floor(p.y)),
          x1=Math.min(canvas.width,Math.ceil(p.x+p.w)),
          y1=Math.min(canvas.height,Math.ceil(p.y+p.h)),
          w=Math.max(1,x1-x0),h=Math.max(1,y1-y0);

    if(w<3||h<3)
      return{ok:false,reason:`invalid plot raster ${w}x${h}`,points:[]};

    const im=ctx.getImageData(x0,y0,w,h).data,
          lowEndXAbs=p.x+p.w*(260/500),
          highStartXAbs=p.x+p.w*(270/500),
          stepPx=Number.isFinite(cal?.stepPx)?cal.stepPx:Math.max(8,p.h*.18);

    function satHue(r,g,b){
      const mx=Math.max(r,g,b),mn=Math.min(r,g,b),
            sat=(mx-mn)/Math.max(1,mx),lum=(r+g+b)/3;
      return{mx,mn,sat,lum,h:rgbToHue(r,g,b)};
    }
    function hueDist(a,b){
      let d=Math.abs(a-b)%360;return Math.min(d,360-d);
    }

    // Dominant foreground hue from saturated pixels.
    const hueBins=new Array(36).fill(0),hueCols=Array.from({length:36},()=>new Set());
    const sx0=Math.floor(w*.06),sx1=Math.max(sx0+1,Math.floor(w*.99)),
          sy0=Math.floor(h*.06),sy1=Math.max(sy0+1,Math.floor(h*.97));
    for(let yy=sy0;yy<sy1;yy++){
      for(let xx=sx0;xx<sx1;xx++){
        const i=(yy*w+xx)*4,q=satHue(im[i],im[i+1],im[i+2]);
        if(q.mx<118||q.sat<.30||q.lum<58)continue;
        const bin=Math.floor((q.h%360)/10);
        hueBins[bin]+=1;hueCols[bin].add(xx);
      }
    }
    let hueBin=0,hueScore=-1;
    for(let b=0;b<36;b++){
      const score=hueCols[b].size*2.1+hueBins[b]*.075;
      if(score>hueScore){hueScore=score;hueBin=b}
    }
    const signalHue=hueBin*10+5;

    function isSignalPixel(r,g,b){
      const q=satHue(r,g,b);
      return q.mx>=105&&q.sat>=.27&&q.lum>=52&&hueDist(q.h,signalHue)<=30;
    }

    function populationCandidates(rx0,rx1,label){
      const pts=[],
            xmin=Math.max(x0,Math.ceil(rx0)),
            xmax=Math.min(x0+w,Math.floor(rx1));
      if(xmax-xmin<3)return{label,ok:false,reason:'region too narrow',points:[],candidates:[]};

      for(let x=xmin;x<xmax;x++){
        const xx=x-x0;
        for(let y=Math.max(y0,Math.floor(p.y+p.h*.035));
                y<Math.min(y0+h,Math.ceil(p.y+p.h*.975));y++){
          const yy=y-y0,i=(yy*w+xx)*4;
          if(isSignalPixel(im[i],im[i+1],im[i+2]))pts.push({x,y});
        }
      }
      if(!pts.length)
        return{label,ok:false,reason:'no signal-colored pixels',points:[],candidates:[]};

      // Smooth Y histogram and identify separated populations.
      const hist=new Array(h).fill(0);
      for(const q of pts){
        const yy=Math.max(0,Math.min(h-1,Math.round(q.y-y0)));
        hist[yy]++;
      }
      const smooth=hist.map((_,i)=>{
        let v=0;
        for(let k=-3;k<=3;k++){
          if(i+k<0||i+k>=h)continue;
          const wt=(k===0?4:Math.abs(k)===1?3:Math.abs(k)===2?2:1);
          v+=hist[i+k]*wt;
        }
        return v;
      });

      const peakYs=[],minPeak=Math.max(3,pts.length*.0018);
      for(let i=2;i<h-2;i++){
        if(smooth[i]<minPeak||smooth[i]<smooth[i-1]||smooth[i]<smooth[i+1])continue;
        if(!peakYs.length||i-peakYs.at(-1)>Math.max(3,stepPx*.16)){
          peakYs.push(i);
        }else if(smooth[i]>smooth[peakYs.at(-1)]){
          peakYs[peakYs.length-1]=i;
        }
      }
      if(!peakYs.length)peakYs.push(Math.round(median(pts.map(q=>q.y-y0))));

      const candidates=[];
      for(const py of peakYs){
        // Narrow enough not to merge a Low line with an elevated High cloud.
        const bandHalf=Math.max(3,stepPx*.27),
              members=pts.filter(q=>Math.abs((q.y-y0)-py)<=bandHalf);
        if(members.length<4)continue;

        const xset=new Set(members.map(q=>Math.round(q.x))),
              coverage=xset.size/Math.max(1,xmax-xmin),
              center=median(members.map(q=>q.y)),
              mad=median(members.map(q=>Math.abs(q.y-center)))||1,
              spread84=EGSCore.percentile(members.map(q=>q.y),.84)-EGSCore.percentile(members.map(q=>q.y),.16),
              compact=1/(1+mad/Math.max(1,stepPx)),
              density=members.length/Math.max(1,pts.length),
              // compact horizontal lines and dispersed clouds can both be real.
              baseScore=coverage*3.5+density*2.0+compact*.8;

        const byX=new Map();
        for(const q of members){
          const k=Math.round(q.x);
          if(!byX.has(k))byX.set(k,[]);
          byX.get(k).push(q.y);
        }
        const points=[];
        for(const [x,ys] of byX.entries())
          points.push({x,y:median(ys),source:'regional-population'});
        points.sort((a,b)=>a.x-b.x);

        candidates.push({
          label,points,members,coverage,center,mad,spread84,
          compactness:compact,density,baseScore,
          rawSignalPixels:pts.length,signalHue
        });
      }

      candidates.sort((a,b)=>b.baseScore-a.baseScore);
      return{label,ok:candidates.length>0,reason:candidates.length?'':'no coherent signal population',
             candidates,rawPoints:pts};
    }

    const lowRegion=populationCandidates(p.x,lowEndXAbs,'Low'),
          highRegion=populationCandidates(highStartXAbs,p.x+p.w,'High');

    if(!lowRegion.ok||!highRegion.ok)
      return{ok:false,reason:`signal population unavailable: Low=${lowRegion.ok} High=${highRegion.ok}`,
             points:[],lowRegion,highRegion,signalHue,lowEndX:lowEndXAbs,highStartX:highStartXAbs};

    // Low: most supported real population. No zero/baseline semantics.
    const lowModel=lowRegion.candidates[0];

    // High: first score candidates normally, then look for a genuine population
    // distinctly ABOVE the Low level. In image coordinates, "above" = smaller Y.
    //
    // This solves the common screenshot pattern where:
    //   - a thin Low-level line continues through High with ~100% X coverage
    //   - the actual High measurement is a dense elevated cloud.
    let highModel=highRegion.candidates[0];
    const distinct=highRegion.candidates
      .filter(c=>{
        const rise=(lowModel.center-c.center)/Math.max(1,stepPx);
        const supportOK=c.coverage>=.20 || c.density>=.18;
        const enoughPixels=c.points.length>=Math.max(8,(p.w*(230/500))*.06);
        return rise>=.28 && supportOK && enoughPixels;
      })
      .map(c=>{
        const rise=(lowModel.center-c.center)/Math.max(1,stepPx),
              verticalCloud=Math.min(1.5,c.spread84/Math.max(1,stepPx));
        // Distinct elevated support outranks the continuing Low line.
        const selectScore=c.baseScore + Math.min(2.4,rise*1.6) + verticalCloud*.45;
        return{...c,riseFromLowSteps:rise,selectScore};
      })
      .sort((a,b)=>b.selectScore-a.selectScore);

    if(distinct.length){
      const d=distinct[0];
      // Require reasonable evidence before overriding the normal dominant population.
      if(d.coverage>=.24 || d.density>=.24 || d.selectScore>=highModel.baseScore+.55)
        highModel=d;
    }

    // Short local median smoothing on selected populations.
    function smoothPoints(points){
      const out=[];
      for(let i=0;i<points.length;i++){
        const q=points[i],near=[];
        for(let j=Math.max(0,i-4);j<=Math.min(points.length-1,i+4);j++){
          if(Math.abs(points[j].x-q.x)<=5)near.push(points[j].y);
        }
        out.push({...q,y:median(near.length?near:[q.y])});
      }
      return out;
    }

    lowModel.points=smoothPoints(lowModel.points);
    highModel.points=smoothPoints(highModel.points);

    const points=[...lowModel.points,...highModel.points];

    return{
      ok:true,source:'regional-signal-population-v6.0.0',
      points,splitX:highStartXAbs,lowEndX:lowEndXAbs,highStartX:highStartXAbs,signalHue,
      lowModel,highModel,
      lowCandidates:lowRegion.candidates.map(c=>({
        center:c.center,coverage:c.coverage,density:c.density,spread84:c.spread84,score:c.baseScore
      })),
      highCandidates:highRegion.candidates.map(c=>({
        center:c.center,coverage:c.coverage,density:c.density,spread84:c.spread84,score:c.baseScore,
        riseFromLowSteps:(lowModel.center-c.center)/Math.max(1,stepPx)
      })),
      highSelection:highModel.riseFromLowSteps>=.28?'distinct-elevated-population':'dominant-population',
      coverage:points.length/Math.max(1,w)
    };
  }
  function robustMedian(vals){
    const a=vals.filter(Number.isFinite);
    if(!a.length)return NaN;
    const m=median(a),mad=median(a.map(v=>Math.abs(v-m)))||1e-9,
          keep=a.filter(v=>Math.abs(v-m)<=Math.max(mad*3.5,.0015));
    return median(keep.length?keep:a);
  }

  function directNoiseValues(prepared,trace){
    const cal=prepared.noiseAxis;
    if(!cal?.ok||!trace?.ok)return{ok:false,reason:'Noise axis or signal population unavailable'};

    const p=prepared.plot,
          lowEndX=Number.isFinite(trace.lowEndX)?trace.lowEndX:(p.x+p.w*(260/500)),
          highStartX=Number.isFinite(trace.highStartX)?trace.highStartX:(p.x+p.w*(270/500)),
          anchors=(cal.anchors||[]).map(a=>a.value).filter(Number.isFinite),
          visibleMax=anchors.length?Math.max(...anchors):.04,
          visibleMin=anchors.length?Math.min(...anchors):0,
          low=[],high=[];

    for(const pt of trace.points){
      const v=pixelYToValue(pt.y,cal);
      if(!Number.isFinite(v))continue;
      if(v<visibleMin-.003||v>visibleMax+.003)continue;
      const vv=Math.max(visibleMin,Math.min(visibleMax,v));
      if(pt.x<=lowEndX)low.push(vv);else if(pt.x>=highStartX)high.push(vv);
    }

    if(low.length<5||high.length<5)
      return{ok:false,reason:`insufficient mapped signal population samples (${low.length}/${high.length})`,
             lowCount:low.length,highCount:high.length,lowEndX,highStartX,visibleMin,visibleMax};

    function robustPopulationValue(vals){
      let a=vals.filter(Number.isFinite).sort((x,y)=>x-y);
      if(!a.length)return NaN;
      const med=median(a),
            mad=median(a.map(v=>Math.abs(v-med)))||.00020,
            keep=a.filter(v=>Math.abs(v-med)<=Math.max(.0008,mad*3.2));
      if(keep.length>=Math.max(5,a.length*.45))a=keep;
      return median(a);
    }

    const lowValue=robustPopulationValue(low),
          highValue=robustPopulationValue(high);
    if(!Number.isFinite(lowValue)||!Number.isFinite(highValue))
      return{ok:false,reason:'signal population center unavailable',
             lowCount:low.length,highCount:high.length,lowEndX,highStartX,visibleMin,visibleMax};

    return{
      ok:true,source:'grid-axis-plus-regional-population-v6.0.0',
      low:lowValue,high:highValue,lowCount:low.length,highCount:high.length,lowEndX,highStartX,
      lowY:cal.zeroY-(lowValue/cal.stepValue)*cal.stepPx,
      highY:cal.zeroY-(highValue/cal.stepValue)*cal.stepPx,
      visibleMin,visibleMax,
      estimator:'grid-only Y-axis + independent Low/High regional populations + robust median',
      lowModel:trace.lowModel,highModel:trace.highModel,signalHue:trace.signalHue
    };
  }



  function detectRightDarkFrame(ctx,canvas){
    // v3.0.3: detect a DARK RECTANGLE, not a connected black blob.
    // The Energy-per-Band panel may be fragmented by grid lines, labels and trace,
    // so connected-components are intrinsically unstable.
    const W=canvas.width,H=canvas.height,
          im=ctx.getImageData(0,0,W,H).data,
          gray=(x,y)=>{
            x=Math.max(0,Math.min(W-1,x|0)); y=Math.max(0,Math.min(H-1,y|0));
            const i=(y*W+x)*4; return (im[i]+im[i+1]+im[i+2])/3;
          },
          dark=(x,y)=>gray(x,y)<112;

    function interiorStats(x,y,w,h){
      const sx=Math.max(2,Math.round(w/64)), sy=Math.max(2,Math.round(h/38));
      let n=0,d=0,green=0,color=0;
      for(let yy=y+sy;yy<y+h-sy;yy+=sy){
        for(let xx=x+sx;xx<x+w-sx;xx+=sx){
          const i=((yy|0)*W+(xx|0))*4,r=im[i],g=im[i+1],b=im[i+2],
                lum=(r+g+b)/3,mx=Math.max(r,g,b),mn=Math.min(r,g,b),
                sat=(mx-mn)/Math.max(1,mx);
          if(lum<118)d++;
          if(g>45&&g>r*1.08&&g>b*.92)green++;
          if(mx>130&&sat>.25)color++;
          n++;
        }
      }
      return {darkRatio:d/Math.max(1,n),greenRatio:green/Math.max(1,n),
              colorRatio:color/Math.max(1,n),n};
    }

    function edgeDarkRatio(x,y,w,h){
      const step=Math.max(2,Math.round(Math.min(w,h)/42));
      let top=0,bot=0,left=0,right=0,nt=0,nb=0,nl=0,nr=0;
      for(let xx=x;xx<=x+w;xx+=step){
        if(dark(xx,y)){top++} nt++;
        if(dark(xx,y+h)){bot++} nb++;
      }
      for(let yy=y;yy<=y+h;yy+=step){
        if(dark(x,yy)){left++} nl++;
        if(dark(x+w,yy)){right++} nr++;
      }
      return {top:top/nt,bottom:bot/nb,left:left/nl,right:right/nr};
    }

    const cands=[];
    // Search plausible panel rectangles directly. The photo is roughly aligned by the user,
    // but the detector does not require exact upper-right placement.
    for(let wf=.26;wf<=.52;wf+=.035){
      const w=Math.round(W*wf);
      for(let aspect=1.55;aspect<=3.25;aspect+=.22){
        const h=Math.round(w/aspect);
        if(h<H*.10||h>H*.34)continue;
        const sx=Math.max(10,Math.round(w*.055)),
              sy=Math.max(8,Math.round(h*.075));
        for(let y=Math.round(H*.12);y+h<Math.round(H*.70);y+=sy){
          for(let x=Math.round(W*.36);x+w<W;x+=sx){
            const st=interiorStats(x,y,w,h);
            if(st.darkRatio<.50)continue;

            const e=edgeDarkRatio(x,y,w,h);
            // The true panel rectangle must have a dark interior and persistent dark border
            // on most sides; grid/trace may interrupt an edge, so don't require perfection.
            const edgeMean=(e.top+e.bottom+e.left+e.right)/4;
            if(edgeMean<.42)continue;

            const ar=w/h,
                  aspectScore=Math.exp(-Math.pow((ar-2.15)/.85,2)),
                  rightness=(x+w*.5)/W,
                  sizeScore=Math.min(1,(w*h)/(W*H*.085)),
                  score=
                    st.darkRatio*4.1+
                    edgeMean*2.2+
                    Math.min(.8,st.greenRatio*13)+
                    Math.min(.65,st.colorRatio*7)+
                    aspectScore*.9+
                    rightness*.45+
                    sizeScore*.45;

            cands.push({x,y,w,h,score,stats:st,edges:e,aspect:ar});
          }
        }
      }
    }

    if(!cands.length)return null;
    cands.sort((a,b)=>b.score-a.score);

    // Refine each side independently by looking for the strongest transition
    // from pale UI -> dark plot near the coarse rectangle.
    const b={...cands[0]};
    function verticalDarkness(xx,y0,y1){
      let n=0,d=0,step=Math.max(2,Math.round((y1-y0)/55));
      for(let y=y0;y<=y1;y+=step){if(dark(xx,y))d++;n++}
      return d/Math.max(1,n);
    }
    function horizontalDarkness(yy,x0,x1){
      let n=0,d=0,step=Math.max(2,Math.round((x1-x0)/70));
      for(let x=x0;x<=x1;x+=step){if(dark(x,yy))d++;n++}
      return d/Math.max(1,n);
    }

    let bestL={x:b.x,s:-1}, bestR={x:b.x+b.w,s:-1},
        bestT={y:b.y,s:-1}, bestB={y:b.y+b.h,s:-1};

    const dx=Math.max(8,Math.round(b.w*.12)),
          dy=Math.max(6,Math.round(b.h*.16));
    for(let x=Math.max(0,b.x-dx);x<=Math.min(W-1,b.x+dx);x++){
      const inside=verticalDarkness(x+3,b.y,b.y+b.h),
            outside=verticalDarkness(x-4,b.y,b.y+b.h),
            sc=inside-outside;
      if(sc>bestL.s)bestL={x,s:sc};
    }
    for(let x=Math.max(1,b.x+b.w-dx);x<=Math.min(W-2,b.x+b.w+dx);x++){
      const inside=verticalDarkness(x-3,b.y,b.y+b.h),
            outside=verticalDarkness(x+4,b.y,b.y+b.h),
            sc=inside-outside;
      if(sc>bestR.s)bestR={x,s:sc};
    }
    for(let y=Math.max(0,b.y-dy);y<=Math.min(H-1,b.y+dy);y++){
      const inside=horizontalDarkness(y+3,b.x,b.x+b.w),
            outside=horizontalDarkness(y-4,b.x,b.x+b.w),
            sc=inside-outside;
      if(sc>bestT.s)bestT={y,s:sc};
    }
    for(let y=Math.max(1,b.y+b.h-dy);y<=Math.min(H-2,b.y+b.h+dy);y++){
      const inside=horizontalDarkness(y-3,b.x,b.x+b.w),
            outside=horizontalDarkness(y+4,b.x,b.x+b.w),
            sc=inside-outside;
      if(sc>bestB.s)bestB={y,s:sc};
    }

    let x=Math.max(0,bestL.x), y=Math.max(0,bestT.y),
        x2=Math.min(W,bestR.x), y2=Math.min(H,bestB.y);
    if(x2-x<W*.16||y2-y<H*.08){x=b.x;y=b.y;x2=b.x+b.w;y2=b.y+b.h}

    return{
      x,y,w:x2-x,h:y2-y,
      source:'energy-dark-rectangle-boundary',
      confidence:clamp(.58+b.score/10,.58,.98),
      diagnostics:{
        coarse:b,
        refined:{left:bestL,right:bestR,top:bestT,bottom:bestB},
        method:'dark-rectangle-interior+four-edge-transition'
      }
    };
  }


  function localPanelBoundaryFromPlot(ctx,canvas,plot){
    const W=canvas.width,H=canvas.height,
          im=ctx.getImageData(0,0,W,H).data,
          lum=(x,y)=>{
            x=Math.max(0,Math.min(W-1,x|0));y=Math.max(0,Math.min(H-1,y|0));
            const i=(y*W+x)*4;return (im[i]+im[i+1]+im[i+2])/3;
          },
          dark=(x,y)=>lum(x,y)<125;

    function vRatio(x,y0,y1){
      let n=0,d=0,st=Math.max(2,Math.round((y1-y0)/60));
      for(let y=y0;y<=y1;y+=st){if(dark(x,y))d++;n++}
      return d/Math.max(1,n);
    }
    function hRatio(y,x0,x1){
      let n=0,d=0,st=Math.max(2,Math.round((x1-x0)/80));
      for(let x=x0;x<=x1;x+=st){if(dark(x,y))d++;n++}
      return d/Math.max(1,n);
    }

    const px=plot.x,py=plot.y,pw=plot.w,ph=plot.h,
          y0=Math.max(0,py-ph*.06),y1=Math.min(H-1,py+ph*1.08),
          x0=Math.max(0,px-pw*.04),x1=Math.min(W-1,px+pw*1.04);

    // Starting from an already-confirmed grid plot, search only locally for the
    // pale-UI -> dark-panel transition. This is far more stable than finding a
    // black rectangle from the entire photograph.
    function bestLeft(){
      let best={v:px-pw*.30,s:-1};
      const lo=Math.max(1,Math.round(px-pw*.48)),hi=Math.max(lo,Math.round(px-pw*.04));
      for(let x=lo;x<=hi;x++){
        const inside=vRatio(x+4,y0,y1),outside=vRatio(x-5,y0,y1),
              sc=inside-outside;
        if(sc>best.s)best={v:x,s:sc};
      }
      return best;
    }
    function bestRight(){
      let best={v:px+pw*.10,s:-1};
      const lo=Math.min(W-2,Math.round(px+pw*1.01)),
            hi=Math.min(W-2,Math.round(px+pw*1.28));
      for(let x=lo;x<=hi;x++){
        const inside=vRatio(x-4,y0,y1),outside=vRatio(x+5,y0,y1),
              sc=inside-outside;
        if(sc>best.s)best={v:x,s:sc};
      }
      return best;
    }
    function bestTop(){
      let best={v:py-ph*.10,s:-1};
      const lo=Math.max(1,Math.round(py-ph*.30)),hi=Math.max(lo,Math.round(py-ph*.01));
      for(let y=lo;y<=hi;y++){
        const inside=hRatio(y+4,x0,x1),outside=hRatio(y-5,x0,x1),
              sc=inside-outside;
        if(sc>best.s)best={v:y,s:sc};
      }
      return best;
    }
    function bestBottom(){
      let best={v:py+ph*.18,s:-1};
      const lo=Math.min(H-2,Math.round(py+ph*1.01)),
            hi=Math.min(H-2,Math.round(py+ph*1.46));
      for(let y=lo;y<=hi;y++){
        const inside=hRatio(y-4,x0,x1),outside=hRatio(y+5,x0,x1),
              sc=inside-outside;
        if(sc>best.s)best={v:y,s:sc};
      }
      return best;
    }

    const L=bestLeft(),R=bestRight(),T=bestTop(),B=bestBottom(),
          weak=[L,R,T,B].filter(o=>o.s<.16).length;

    // If a side transition is weak, use a conservative geometry expansion from
    // the confirmed grid instead of inventing a remote edge.
    const left =L.s>=.16?L.v:px-pw*.30,
          right=R.s>=.16?R.v:px+pw*1.10,
          top  =T.s>=.16?T.v:py-ph*.12,
          bottom=B.s>=.16?B.v:py+ph*1.28,
          x=Math.max(0,left),y=Math.max(0,top),
          x2=Math.min(W,right),y2=Math.min(H,bottom);

    return{
      x,y,w:Math.max(2,x2-x),h:Math.max(2,y2-y),
      source:'guide-grid-local-panel-boundary',
      confidence:clamp(.94-weak*.08,.62,.94),
      diagnostics:{L,R,T,B,weakSides:weak}
    };
  }

  function guideAlignedPanelDetect(ctx,canvas){
    const W=canvas.width,H=canvas.height,cands=[];

    // The camera image has ALREADY been cropped to the shooting guide.
    // Search only the expected upper-right application area for a regular grid.
    // No global dark-component or global black-rectangle detector is used here.
    const seeds=[
      {x:.42,y:.10,w:.57,h:.43},
      {x:.46,y:.12,w:.53,h:.40},
      {x:.50,y:.14,w:.49,h:.37},
      {x:.40,y:.15,w:.59,h:.36},
      {x:.44,y:.18,w:.55,h:.34},
      {x:.48,y:.20,w:.51,h:.32}
    ];

    for(const ss of seeds){
      const roi={
        x:Math.round(W*ss.x),y:Math.round(H*ss.y),
        w:Math.round(W*ss.w),h:Math.round(H*ss.h)
      };
      if(roi.x+roi.w>W)roi.w=W-roi.x;
      if(roi.y+roi.h>H)roi.h=H-roi.y;
      const q=plotFromGrid(ctx,canvas,roi);
      if(!q)continue;
      const p=q.plot,
            rows=(q.gridRowsAbs||[]).length,
            cols=(q.gridColsAbs||[]).length,
            aspect=p.w/Math.max(1,p.h),
            right=(p.x+p.w*.5)/W,
            upper=1-(p.y+p.h*.5)/H,
            rowScore=Math.min(1,rows/5),
            colScore=Math.min(1,cols/6),
            aspectScore=Math.exp(-Math.pow((aspect-2.15)/.85,2)),
            score=rowScore*4+colScore*4+aspectScore*2+right*.7+upper*.3;
      cands.push({q,score,rows,cols,aspect});
    }

    if(!cands.length)return null;
    cands.sort((a,b)=>b.score-a.score);
    const best=cands[0];
    if(best.rows<3||best.cols<3)return null;

    const panel=localPanelBoundaryFromPlot(ctx,canvas,best.q.plot);
    return{
      ...panel,
      plot:{...best.q.plot},
      gridRowsAbs:[...(best.q.gridRowsAbs||[])],
      gridColsAbs:[...(best.q.gridColsAbs||[])],
      confidence:clamp((panel.confidence*.65)+Math.min(1,best.score/10)*.35,.60,.98),
      source:'guide-first-grid-then-local-panel',
      diagnostics:{
        candidateScore:best.score,rows:best.rows,cols:best.cols,
        plotAspect:best.aspect,panel:panel.diagnostics
      }
    };
  }

  function lineRegularity(lines){
    const a=(lines||[]).filter(Number.isFinite).sort((x,y)=>x-y);
    if(a.length<3)return{score:0,count:a.length,cv:9,step:NaN};
    const gaps=[];for(let i=1;i<a.length;i++)if(a[i]-a[i-1]>2)gaps.push(a[i]-a[i-1]);
    if(gaps.length<2)return{score:0,count:a.length,cv:9,step:NaN};
    const step=median(gaps),mad=median(gaps.map(g=>Math.abs(g-step))),cv=mad/Math.max(1,step);
    return{score:clamp(1-cv/.34,0,1),count:a.length,cv,step};
  }

  function energyCandidateEvidence(ctx,canvas,q,scope=null){
    if(!q?.plot)return null;
    const W=canvas.width,H=canvas.height,p=q.plot,
          x0=Math.max(0,Math.floor(p.x)),y0=Math.max(0,Math.floor(p.y)),
          w=Math.max(2,Math.min(W-x0,Math.floor(p.w))),h=Math.max(2,Math.min(H-y0,Math.floor(p.h)));
    if(w<24||h<16)return null;
    const im=ctx.getImageData(x0,y0,w,h).data,
          rs=lineRegularity(q.gridRowsAbs),cs=lineRegularity(q.gridColsAbs);
    let n=0,dark=0,sat=0,green=0,topGreen=0,topN=0;
    const sx=Math.max(1,Math.floor(w/70)),sy=Math.max(1,Math.floor(h/45));
    for(let y=0;y<h;y+=sy){
      for(let x=0;x<w;x+=sx){
        const i=(y*w+x)*4,r=im[i],g=im[i+1],b=im[i+2],mx=Math.max(r,g,b),mn=Math.min(r,g,b),lum=(r+g+b)/3,
              chrom=mx-mn;
        if(lum<122)dark++;
        if(mx>115&&chrom>42)sat++;
        if(g>48&&g>r*1.04&&g>b*.94)green++;
        if(y<h*.24&&x>w*.48){topN++;if(g>55&&g>r*1.04&&g>b*.94)topGreen++}
        n++;
      }
    }
    const darkRatio=dark/Math.max(1,n),satRatio=sat/Math.max(1,n),greenRatio=green/Math.max(1,n),
          titleGreen=topGreen/Math.max(1,topN),aspect=w/Math.max(1,h),
          aspectScore=Math.exp(-Math.pow((aspect-2.15)/1.05,2)),
          rows=Math.min(1,(q.gridRowsAbs||[]).length/5),cols=Math.min(1,(q.gridColsAbs||[]).length/7),
          lattice=(rs.score+cs.score+rows+cols)/4,
          right=(p.x+p.w*.5)/Math.max(1,W), upper=1-(p.y+p.h*.5)/Math.max(1,H),
          scopeFit=scope?((p.x>=scope.x-2&&p.y>=scope.y-2&&p.x+p.w<=scope.x+scope.w+2&&p.y+p.h<=scope.y+scope.h+2)?1:0):1,
          signalScore=clamp(satRatio/.18,0,1),darkScore=clamp((darkRatio-.35)/.45,0,1),
          titleScore=clamp(titleGreen/.10,0,1),
          score=lattice*5.2+darkScore*2.0+signalScore*1.35+aspectScore*1.15+titleScore*.55+right*.35+upper*.15+scopeFit*.3;
    return{score,lattice,darkRatio,satRatio,greenRatio,titleGreen,aspect,aspectScore,rs,cs,scopeFit};
  }

  function panelFromConfirmedPlot(ctx,canvas,q,evidence,source){
    const panel=localPanelBoundaryFromPlot(ctx,canvas,q.plot),W=canvas.width,H=canvas.height;
    let x=panel.x,y=panel.y,w=panel.w,h=panel.h;
    // Hard sanity around the confirmed grid plot. Never let a weak side transition
    // create a huge remote Auto ROI.
    const p=q.plot,
          minX=Math.max(0,p.x-p.w*.42),maxX=Math.min(W,p.x+p.w*1.22),
          minY=Math.max(0,p.y-p.h*.34),maxY=Math.min(H,p.y+p.h*1.52);
    x=clamp(x,minX,p.x);y=clamp(y,minY,p.y);
    const x2=clamp(x+w,p.x+p.w,maxX),y2=clamp(y+h,p.y+p.h,maxY);
    w=Math.max(2,x2-x);h=Math.max(2,y2-y);
    return{
      x,y,w,h,plot:{...p},gridRowsAbs:[...(q.gridRowsAbs||[])],gridColsAbs:[...(q.gridColsAbs||[])],
      confidence:clamp(.56+(evidence?.score||0)/13,.56,.99),source,
      diagnostics:{evidence,panel:panel.diagnostics,confirmedPlot:{...p}}
    };
  }

  function detectEnergyPanelInScope(ctx,canvas,scope,options={}){
    const W=canvas.width,H=canvas.height,
          S={x:clamp(scope.x,0,W-2),y:clamp(scope.y,0,H-2),w:clamp(scope.w,2,W-scope.x),h:clamp(scope.h,2,H-scope.y)},
          candidates=[];
    function addQ(q,seedSource){
      if(!q?.plot)return;
      const ev=energyCandidateEvidence(ctx,canvas,q,S);if(!ev)return;
      if((q.gridRowsAbs||[]).length<3||(q.gridColsAbs||[]).length<3)return;
      if(ev.lattice<.36||ev.darkRatio<.34)return;
      candidates.push({q,ev,seedSource});
    }

    // 1) Entire scope itself: strongest path for a well-positioned manual ROI.
    try{addQ(plotFromGrid(ctx,canvas,S),'scope-full')}catch(_){}

    // 2) Structured seeds inside the scope. These cover loose manual boxes and Auto search.
    const seeds=[
      [.00,.00,1.00,1.00],[.08,.04,.92,.88],[.16,.05,.84,.82],[.24,.06,.76,.76],
      [.30,.08,.70,.70],[.38,.08,.62,.66],[.44,.10,.56,.62],[.48,.12,.52,.58],
      [.18,.14,.82,.70],[.28,.18,.72,.64],[.36,.20,.64,.58]
    ];
    for(const [fx,fy,fw,fh] of seeds){
      const r={x:S.x+S.w*fx,y:S.y+S.h*fy,w:S.w*fw,h:S.h*fh};
      if(r.w<45||r.h<28)continue;
      try{addQ(plotFromGrid(ctx,canvas,r),'seed')}catch(_){}
    }

    // 3) Coarse multi-scale scan, deliberately sparse to keep iPhone responsive.
    const widths=options.manual?[.54,.68,.82,.96]:[.34,.48,.64,.82,.96],
          aspects=[1.65,2.05,2.45,2.95];
    for(const wf of widths){
      const rw=S.w*wf;
      for(const asp of aspects){
        const rh=rw/asp;if(rh<S.h*.16||rh>S.h*.90)continue;
        const nx=3,ny=3;
        for(let iy=0;iy<ny;iy++)for(let ix=0;ix<nx;ix++){
          const maxDx=Math.max(0,S.w-rw),maxDy=Math.max(0,S.h-rh),
                r={x:S.x+(nx===1?0:maxDx*ix/(nx-1)),y:S.y+(ny===1?0:maxDy*iy/(ny-1)),w:rw,h:rh};
          try{addQ(plotFromGrid(ctx,canvas,r),'multiscale')}catch(_){}
        }
      }
    }

    if(!candidates.length)return null;
    candidates.sort((a,b)=>b.ev.score-a.ev.score);
    // Deduplicate by plot IoU.
    const kept=[];
    for(const c of candidates){
      const A=c.q.plot;let dup=false;
      for(const k of kept){
        const B=k.q.plot,ix=Math.max(0,Math.min(A.x+A.w,B.x+B.w)-Math.max(A.x,B.x)),
              iy=Math.max(0,Math.min(A.y+A.h,B.y+B.h)-Math.max(A.y,B.y)),inter=ix*iy,
              union=A.w*A.h+B.w*B.h-inter;
        if(union>0&&inter/union>.72){dup=true;break}
      }
      if(!dup)kept.push(c);if(kept.length>=7)break;
    }
    const best=kept[0],second=kept[1],margin=second?best.ev.score-second.ev.score:best.ev.score,
          out=panelFromConfirmedPlot(ctx,canvas,best.q,best.ev,options.manual?'manual-scope-ensemble-v510':'auto-ensemble-v510');
    out.diagnostics={...(out.diagnostics||{}),candidateCount:candidates.length,keptCount:kept.length,
      bestScore:best.ev.score,secondScore:second?.ev.score??null,margin,seedSource:best.seedSource,
      topCandidates:kept.slice(0,5).map(c=>({score:c.ev.score,plot:{...c.q.plot},seedSource:c.seedSource,lattice:c.ev.lattice,dark:c.ev.darkRatio,signal:c.ev.satRatio}))};
    // Confidence penalty when two geometrically different candidates are nearly tied.
    if(second&&margin<.35)out.confidence=Math.min(out.confidence,.74);
    return out;
  }

  function autoPanelDetect(ctx,canvas){
    const W=canvas.width,H=canvas.height,proposals=[];
    function add(panel,sourceBoost=0){
      if(!panel?.plot)return;
      const q={plot:panel.plot,gridRowsAbs:panel.gridRowsAbs||[],gridColsAbs:panel.gridColsAbs||[]},
            ev=energyCandidateEvidence(ctx,canvas,q,null);
      if(!ev)return;
      proposals.push({panel,score:ev.score+sourceBoost,evidence:ev});
    }

    // Guide-aligned detector is very strong for normal iPhone capture composition.
    try{add(guideAlignedPanelDetect(ctx,canvas),.45)}catch(_){}

    // Dark-frame is only a search hint, never the final ROI.
    let darkFrame=null;
    try{darkFrame=detectRightDarkFrame(ctx,canvas)}catch(_){}
    if(darkFrame){
      const ex={x:Math.max(0,darkFrame.x-darkFrame.w*.36),y:Math.max(0,darkFrame.y-darkFrame.h*.34),
                w:Math.min(W,darkFrame.w*1.55),h:Math.min(H,darkFrame.h*1.65)};
      ex.w=Math.min(W-ex.x,ex.w);ex.h=Math.min(H-ex.y,ex.h);
      try{add(detectEnergyPanelInScope(ctx,canvas,ex,{manual:false}),.30)}catch(_){}
    }

    // Broad right-side scope supports off-center/rotated captures.
    const scopes=[
      {x:W*.20,y:H*.02,w:W*.80,h:H*.74},
      {x:W*.08,y:H*.03,w:W*.92,h:H*.80}
    ];
    for(const sc of scopes){
      const S={x:Math.round(sc.x),y:Math.round(sc.y),w:Math.round(sc.w),h:Math.round(sc.h)};
      try{add(detectEnergyPanelInScope(ctx,canvas,S,{manual:false}),0)}catch(_){}
    }

    if(!proposals.length)return null;
    proposals.sort((a,b)=>b.score-a.score);
    const best=proposals[0],second=proposals[1],margin=second?best.score-second.score:best.score,
          out={...best.panel};
    out.source='multi-hypothesis-energy-panel-v510';
    out.confidence=clamp((out.confidence||.7)+(margin>.5?.08:margin<.18?-.10:0),.55,.99);
    out.diagnostics={...(out.diagnostics||{}),autoEnsemble:true,proposalCount:proposals.length,
      bestCombinedScore:best.score,secondCombinedScore:second?.score??null,margin,
      proposals:proposals.slice(0,6).map(p=>({score:p.score,source:p.panel.source,plot:p.panel.plot,confidence:p.panel.confidence}))};
    return out;
  }


  function prepareKnownPanel(ctx,canvas,panel,knownPlot,meta={}){
    // v5.1.1: When Auto/Manual detector already found the numeric plot,
    // do NOT localize it again. Reuse the exact detector geometry and only
    // perform axis + signal analysis on that geometry.
    if(!panel||!knownPlot)return null;
    const R={
      x:clamp(panel.x,0,canvas.width-2),
      y:clamp(panel.y,0,canvas.height-2),
      w:clamp(panel.w,2,canvas.width-panel.x),
      h:clamp(panel.h,2,canvas.height-panel.y)
    };
    const P={
      x:clamp(knownPlot.x,R.x,R.x+R.w-2),
      y:clamp(knownPlot.y,R.y,R.y+R.h-2),
      w:Math.max(2,Math.min(knownPlot.w,R.x+R.w-knownPlot.x)),
      h:Math.max(2,Math.min(knownPlot.h,R.y+R.h-knownPlot.y))
    };
    if(P.x+P.w>R.x+R.w+1||P.y+P.h>R.y+R.h+1)return null;

    const q={
      version:'known-plot-v6.0.0',
      context:{...R},
      plot:{...P},
      insets:{
        // v6.0.0: EGSCore.geometry() expects FRACTIONS, not pixels.
        // This was the root cause of Safari InvalidStateError in foreground-trace:
        // e.g. 30px left inset was interpreted as 30x the panel width.
        left:(P.x-R.x)/Math.max(1,R.w),
        right:((R.x+R.w)-(P.x+P.w))/Math.max(1,R.w),
        top:(P.y-R.y)/Math.max(1,R.h),
        bottom:((R.y+R.h)-(P.y+P.h))/Math.max(1,R.h),
        source:'known-detector-geometry-normalized-v6.0.0'
      },
      gridRowsAbs:[...(meta.gridRowsAbs||[])],
      gridColsAbs:[...(meta.gridColsAbs||[])],
      axisFamily:null,noiseAxis:null,noiseTrace:null,noiseValues:null,
      source:meta.source||'known-detector-geometry',
      confidence:meta.confidence||.85,
      detectorDiagnostics:meta.diagnostics||null,
      manual:!!meta.manual
    };

    // If the detector did not provide explicit grid rows, derive them only
    // inside the already-fixed plot/panel. Plot localization itself is frozen.
    if(!q.gridRowsAbs.length||!q.gridColsAbs.length){
      try{
        const g=plotFromGrid(ctx,canvas,R);
        if(g){
          // Accept grid rows/cols only when its plot overlaps the known plot.
          const ix=Math.max(0,Math.min(P.x+P.w,g.plot.x+g.plot.w)-Math.max(P.x,g.plot.x)),
                iy=Math.max(0,Math.min(P.y+P.h,g.plot.y+g.plot.h)-Math.max(P.y,g.plot.y)),
                overlap=(ix*iy)/Math.max(1,Math.min(P.w*P.h,g.plot.w*g.plot.h));
          if(overlap>=.45){
            q.gridRowsAbs=[...(g.gridRowsAbs||[])];
            q.gridColsAbs=[...(g.gridColsAbs||[])];
            q.gridStepY=g.gridStepY;
            q.gridStepX=g.gridStepX;
          }
        }
      }catch(_){}
    }

    try{q.axisFamily=axisStripFamily(ctx,canvas,q)}catch(_){}
    try{q.noiseAxis=noiseAxisSeries(ctx,canvas,q)}catch(_){}
    try{q.noiseTrace=directNoiseTrace(ctx,canvas,q)}catch(_){}
    if(q.noiseAxis?.ok&&q.noiseTrace?.ok){
      try{q.noiseValues=directNoiseValues(q,q.noiseTrace)}catch(_){}
    }
    return q;
  }

  function prepareManualROI(ctx,canvas,roi){
    const R={
      x:clamp(roi.x,0,canvas.width-2),y:clamp(roi.y,0,canvas.height-2),
      w:clamp(roi.w,2,canvas.width-roi.x),h:clamp(roi.h,2,canvas.height-roi.y)
    };

    // Use exactly the same structural detector as Auto, but hard-clipped to the red ROI.
    // This is the preferred manual path. It does not use fixed percentages.
    let found=null;
    try{found=detectEnergyPanelInScope(ctx,canvas,R,{manual:true})}catch(_){}
    if(found?.plot){
      const A=R,P=found.plot,inside=P.x>=A.x-1&&P.y>=A.y-1&&P.x+P.w<=A.x+A.w+1&&P.y+P.h<=A.y+A.h+1;
      if(inside){
        const q=prepareKnownPanel(ctx,canvas,R,P,{
          gridRowsAbs:found.gridRowsAbs||[],gridColsAbs:found.gridColsAbs||[],
          source:'manual-scoped-same-detector-as-auto-v6.0.0',
          confidence:found.confidence||.80,diagnostics:found.diagnostics,manual:true
        });
        if(q)return q;
      }
    }

    // Tight-manual fallback: search only inside the exact red ROI for grid geometry.
    let local=null;
    try{local=plotFromGrid(ctx,canvas,R)}catch(_){}
    if(local?.plot){
      const P=local.plot,
            inside=P.x>=R.x-1&&P.y>=R.y-1&&P.x+P.w<=R.x+R.w+1&&P.y+P.h<=R.y+R.h+1;
      if(inside){
        const q=prepareKnownPanel(ctx,canvas,R,P,{
          gridRowsAbs:local.gridRowsAbs||[],gridColsAbs:local.gridColsAbs||[],
          source:'manual-tight-grid-v6.0.0',confidence:.78,manual:true
        });
        if(q)return q;
      }
    }

    // Final emergency fallback only.
    const plot={x:R.x+R.w*.07,y:R.y+R.h*.06,w:R.w*.91,h:R.h*.78},
          q={version:'manual-emergency-relative-v6.0.0',context:{...R},plot,
             insets:{left:plot.x-R.x,right:(R.x+R.w)-(plot.x+plot.w),top:plot.y-R.y,bottom:(R.y+R.h)-(plot.y+plot.h),source:'manual-emergency-relative-v6.0.0'},
             gridRowsAbs:[],gridColsAbs:[],axisFamily:null,noiseAxis:null,noiseTrace:null,noiseValues:null,
             source:'manual-emergency-relative-only-v5.1.2',confidence:.32,manual:true};
    try{q.noiseAxis=noiseAxisSeries(ctx,canvas,q)}catch(_){}
    try{q.noiseTrace=directNoiseTrace(ctx,canvas,q)}catch(_){}
    if(q.noiseAxis?.ok&&q.noiseTrace?.ok)try{q.noiseValues=directNoiseValues(q,q.noiseTrace)}catch(_){}
    return q;
  }

  function prepare(ctx,canvas,roi){
    const q=plotFromGrid(ctx,canvas,roi);
    if(!q)return null;
    q.axisFamily=axisStripFamily(ctx,canvas,q);
    q.noiseAxis=noiseAxisSeries(ctx,canvas,q);
    q.noiseTrace=directNoiseTrace(ctx,canvas,q);
    q.noiseValues=(q.noiseAxis?.ok&&q.noiseTrace?.ok)?directNoiseValues(q,q.noiseTrace):null;
    q.version='analysis-core-v6.0.0';
    return q;
  }
  return{prepare,prepareKnownPanel,prepareManualROI,plotFromGrid,localPanelBoundaryFromPlot,guideAlignedPanelDetect,detectRightDarkFrame,detectEnergyPanelInScope,autoPanelDetect,axisStripFamily,rotationAwareHorizontalGridRows,consensusNoiseGridLattice,noiseAxisSeries,pixelYToValue,directNoiseTrace,directNoiseValues};
});
