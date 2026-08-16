const fs=require('fs');
const core=require('./core.js');
const app=fs.readFileSync('./app.js','utf8');
const ac=fs.readFileSync('./analysis_core_v2.js','utf8');
let results=[];
function test(name,fn){try{const detail=fn();results.push({name,ok:true,detail});}catch(e){results.push({name,ok:false,detail:e.message});}}
function assert(v,m){if(!v)throw Error(m)}

// 1-8 lifecycle / Safari / ROI architecture
test('01 JS source uses ImageData snapshot',()=>{assert(app.includes('analysisBaseImageData=ctx.getImageData(0,0,canvas.width,canvas.height)'), 'missing ImageData snapshot');return 'PASS'});
test('02 Analyze restore uses putImageData',()=>{assert(app.includes('ctx.putImageData(analysisBaseImageData,0,0)'), 'missing putImageData restore');return 'PASS'});
test('03 No HTMLImage fallback in redrawSource',()=>{const p=app.indexOf('function redrawSource()');const q=app.indexOf('function withCleanAnalysisPixels',p);const b=app.slice(p,q);assert(!b.includes('drawImage('),'drawImage remains in redrawSource');return 'PASS'});
test('04 File URL revoked after useImage',()=>{assert(app.includes("useImage(img);\n    setTimeout(()=>URL.revokeObjectURL(url),0)"),'revoke order wrong');return 'PASS'});
test('05 Camera URL revoked after useImage',()=>{assert(app.includes("useImage(img,{guideCropped});\n    setTimeout(()=>URL.revokeObjectURL(url),0)"),'camera revoke order wrong');return 'PASS'});
test('06 Manual path has local prepare before stable snap',()=>{const m=app.indexOf('if(roiManual){');const p=app.indexOf('EGSAnalysisV2.prepare(ctx,canvas,analysisROI)',m);const s=app.indexOf('snappedPanel=stableEnergyPanel()',m);assert(p>m&&s>p,'manual order wrong');return 'PASS'});
test('07 Manual fallback exists',()=>{assert(app.includes('EGSAnalysisV2.prepareManualROI(ctx,canvas,analysisROI)'),'manual fallback missing');return 'PASS'});
test('08 Stable panel failure is non-fatal',()=>{assert(app.includes("stableEnergyPanel non-fatal failure"),'stable panel catch missing');return 'PASS'});

// 9-12 geometry contracts
test('09 Sample split is exactly 270/500',()=>{assert(core.SAMPLE_SPLIT===270&&core.SAMPLE_AXIS_MAX===500,'split constants wrong');return core.splitPixel(501)});
test('10 Noise equal Low/High is allowed',()=>{const xs=[],vals=[];for(let x=0;x<500;x+=2){xs.push(x);vals.push(.008+(x%7-3)*.00003)}const r=core.noiseLevels(xs,vals,.04,500);assert(Math.abs(r.low-r.high)<.001,'equal regions destabilized');return r});
test('11 Noise Low/High different levels',()=>{const xs=[],vals=[];for(let x=0;x<500;x++){xs.push(x);vals.push(x<270?.006:.016)}const r=core.noiseLevels(xs,vals,.04,500);assert(Math.abs(r.low-.006)<.0005&&Math.abs(r.high-.016)<.0005,'wrong levels');return r});
test('12 Noise not forced to zero',()=>{const xs=[],vals=[];for(let x=0;x<500;x++){xs.push(x);vals.push(x<270?.0045:.013)}const r=core.noiseLevels(xs,vals,.04,500);assert(r.low>.0035,'Low collapsed to zero');return r});

// 13-17 robustness to noise/outliers/density/width
test('13 Sparse upward spikes rejected',()=>{const xs=[],vals=[];for(let x=0;x<500;x++){xs.push(x);let v=x<270?.005:.014;if(x%41===0)v=.038;vals.push(v)}const r=core.noiseLevels(xs,vals,.04,500);assert(r.low<.007&&r.high<.017,'spikes biased result');return r});
test('14 Downward outliers rejected',()=>{const xs=[],vals=[];for(let x=0;x<500;x++){xs.push(x);let v=x<270?.007:.015;if(x%37===0)v=.0002;vals.push(v)}const r=core.noiseLevels(xs,vals,.04,500);assert(r.low>.0055&&r.high>.013,'down outliers biased result');return r});
test('15 Different width 300 px',()=>{const xs=[],vals=[];for(let x=0;x<300;x++){xs.push(x);vals.push(x<core.splitPixel(300)?.006:.014)}const r=core.noiseLevels(xs,vals,.04,300);assert(Math.abs(r.low-.006)<.0005&&Math.abs(r.high-.014)<.0005,'width-dependent result');return r});
test('16 Different width 900 px',()=>{const xs=[],vals=[];for(let x=0;x<900;x+=2){xs.push(x);vals.push(x<core.splitPixel(900)?.0065:.0155)}const r=core.noiseLevels(xs,vals,.04,900);assert(Math.abs(r.low-.0065)<.0006&&Math.abs(r.high-.0155)<.0006,'wide width result wrong');return r});
test('17 Uneven sampling density Low/High',()=>{const xs=[],vals=[];for(let x=0;x<270;x+=4){xs.push(x);vals.push(.006)}for(let x=275;x<500;x++){xs.push(x);vals.push(.015)}const r=core.noiseLevels(xs,vals,.04,500);assert(Math.abs(r.low-.006)<.0005&&Math.abs(r.high-.015)<.0005,'density bias');return r});

// 18-20 v5 semantic guards
test('18 Signal cannot define zero in v5',()=>{assert(!ac.includes('detectNoiseZeroBaseline'),'legacy signal zero detector remains');assert(!ac.includes('inferNoiseAxisFromZeroAndRows'),'legacy zero inference remains');return 'PASS'});
test('19 Grid-only Noise axis is present',()=>{assert(ac.includes("source:'grid-only-no-signal-axis-v500'"),'grid-only axis missing');return 'PASS'});
test('20 Dominant signal population path is present',()=>{assert(ac.includes("source:'signal-population-v500'")&&ac.includes("source:'grid-axis-plus-signal-population-v500'"),'population path missing');return 'PASS'});

for(const [i,r] of results.entries()) console.log(`${r.ok?'PASS':'FAIL'} ${r.name} :: ${typeof r.detail==='string'?r.detail:JSON.stringify(r.detail)}`);
console.log(`SUMMARY ${results.filter(x=>x.ok).length}/${results.length} PASS`);
if(results.some(x=>!x.ok))process.exit(1);
