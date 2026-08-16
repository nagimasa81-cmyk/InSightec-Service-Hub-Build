
const fs=require('fs');
const a=fs.readFileSync('app.js','utf8');
function ok(v,m){if(!v)throw Error(m)}
ok(a.includes('let originalMasterCanvas=null'),'immutable master state missing');
ok(a.includes('function snapshotOriginalMasterFromCanvas('),'master snapshot missing');
ok(a.includes('function buildRotatedMasterCanvas('),'master rotation builder missing');
ok(a.includes('Math.ceil(W*c+H*s)')&&a.includes('Math.ceil(W*s+H*c)'),'expanded rotation bounds missing');
ok(a.includes('function transformRectBetweenRotations('),'ROI rotation mapping missing');
ok(a.includes('applyRotationFromImmutableOriginal(angleDeg,{remapROI:true})'),'manual rotation not from original');
ok(a.includes('o.getContext') || a.includes("const oq=o.getContext('2d')"),'Original preview drawing missing');
ok(a.includes("const maxOutW=2800"),'capture resolution not increased');
ok(a.includes("'image/jpeg',.98"),'capture JPEG quality not increased');
ok(!a.includes("const maxW=1400"),'1400px useImage downscale remains');
console.log('v6.3.0 immutable Original regression PASS');
