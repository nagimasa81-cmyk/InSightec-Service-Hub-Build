
const fs=require('fs'),a=fs.readFileSync('app.js','utf8');
function ok(v,m){if(!v)throw Error(m)}
ok(a.includes("useImage(img,{guideCropped});\n    setTimeout(()=>URL.revokeObjectURL(url),0)"),'captured URL revoked before pixel copy');
ok(a.includes("useImage(img);\n    setTimeout(()=>URL.revokeObjectURL(url),0)"),'file URL revoked before pixel copy');
ok(a.includes('sourceImage=analysisBaseCanvas;\n  sourceReady=true;'),'stable Canvas not promoted after load');
ok(a.includes("throw new Error('Stable analysis pixel buffer unavailable')"),'redraw still silently falls back');
ok(!a.includes("}else if(sourceImage){\n    ctx.drawImage(sourceImage"),'HTMLImageElement fallback still present');
ok(a.includes('if(!sourceReady)return;'),'UI guards still depend on image object state');
console.log('v5.0.1 Safari stable-pixel lifecycle PASS');
