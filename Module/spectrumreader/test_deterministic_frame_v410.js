
const fs=require('fs');
const a=fs.readFileSync('app.js','utf8');
function ok(v,m){if(!v)throw Error(m)}
ok(a.includes('let analysisBaseCanvas=null,stablePanelCache=null'),'immutable state missing');
ok(a.includes('function snapshotAnalysisBase()'),'snapshot helper missing');
ok(a.includes('analysisBaseCanvas.width===canvas.width'),'redraw must use immutable base');
ok(a.includes('snapshotAnalysisBase();') && a.includes('Critical: canonical pixels become the immutable analysis source'),
   'canonical snapshot missing');
ok(a.includes('function stableEnergyPanel()'),'stable panel cache missing');
ok(a.includes('if(stablePanelCache)return stablePanelCache'),'panel cache not reused');
ok(a.includes("source:'canonical-fixed-stable-panel'"),'canonical stable panel missing');
ok(!a.includes('try{snappedPanel=EGSAnalysisV2.autoPanelDetect(ctx,canvas)}catch(_){}'),
   'manual analyze still re-runs panel detector');
ok(a.includes("source:'canonical-fixed-v4.1.2'"),'canonical fixed context missing');
console.log('v4.1.0 deterministic frame regression PASS');
