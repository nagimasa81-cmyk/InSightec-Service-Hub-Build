
const fs=require('fs');
const a=fs.readFileSync('app.js','utf8');
function ok(v,m){if(!v)throw Error(m)}

ok(a.includes('function v633FitYAxisAffine('),'Y affine fit missing');
ok(a.includes('function v633AxisValueAtY('),'Y value evaluator missing');
ok(a.includes("source:'weighted-anchor-regression'"),'weighted anchor regression missing');
ok(a.includes("source:'single-anchor+grid-slope'"),'single anchor fallback missing');
ok(!a.includes('Math.max(0,(cal.zeroY-meanY)'), 'bottom-zero clamp remains');
ok(a.includes('bottomGridValue'),'bottom grid value diagnostic missing');

const xs=a.slice(a.indexOf('function v6XAxisCalibration('),a.indexOf('function v631RgbToHue('));
ok(xs.includes("source:'vertical-grid-endpoints-0-500'"),'grid endpoint X fallback missing');
ok(xs.includes('return (sample-cal.b)/cal.a'),'calibrated sample->X inverse missing');

const an=a.slice(a.indexOf('async function analyzeV6('));
ok(an.includes('energy.plot._xCal={...xCal}'),'X calibration not attached before extraction');
ok(a.includes('v6SampleX(energy.plot,0)'),'Low line not using calibrated X');
ok(a.includes("v6SampleX(energy.plot,mode==='Gain'?340:270)"),'High line not using calibrated X');

console.log('v6.3.4 Y-bottom + X-line alignment PASS');
