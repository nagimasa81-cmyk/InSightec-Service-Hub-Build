const fs=require('fs');
const a=fs.readFileSync('app.js','utf8');
function ok(v,m){if(!v)throw Error(m)}
ok(a.includes('let analysisBaseCanvas=null,analysisBaseImageData=null'),'ImageData state missing');
ok(a.includes('analysisBaseImageData=ctx.getImageData(0,0,canvas.width,canvas.height)'),'ImageData snapshot missing');
ok(a.includes('ctx.putImageData(analysisBaseImageData,0,0)'),'ImageData restore missing');
ok(!a.includes('ctx.drawImage(analysisBaseCanvas,0,0,analysisBaseCanvas.width,analysisBaseCanvas.height'),'Canvas restore drawImage remains');
ok(a.includes('Stage ${fatalStage}'),'fatal stage UI missing');
console.log('v5.0.2 Safari ImageData regression PASS');