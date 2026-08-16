
const fs=require('fs');
const a=fs.readFileSync('app.js','utf8');
const h=fs.readFileSync('index.html','utf8');
function ok(v,m){if(!v)throw Error(m)}
ok(a.includes('function v631RgbToHue('),'rgbToHue local helper missing');
ok(!/\brgbToHue\(/.test(a.replace(/v631RgbToHue\(/g,'')),'undefined rgbToHue call remains');
ok(a.includes('function v631DetectCheckboxGrid('),'checkbox grid detector missing');
ok(a.includes("source:'detected-checkbox-grid+relative-ink-v6.3.3'"),'relative checkbox source missing');
ok(a.includes('v631FixedLayoutChannelFallback'),'fixed layout fallback missing');
ok(a.includes('function v631DirectNumericAnchorTemplates('),'direct numeric anchor templates missing');
ok(a.includes('async function analyzeV6('),'Analyze is not async for progress rendering');
ok(a.includes('async function v631Stage('),'progress stage helper missing');
ok(h.includes('id="processingPanel"')&&h.includes('id="processingBar"'),'processing UI missing');
ok(a.includes("'Y-axis grid'")&&a.includes("'Low / High markers'"),'processing stages incomplete');
console.log('v6.3.3 progress/recognition regression PASS');
