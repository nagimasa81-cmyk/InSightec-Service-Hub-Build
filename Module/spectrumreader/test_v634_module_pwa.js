const fs=require('fs');
const path=require('path');
function ok(v,m){if(!v)throw Error(m)}
const h=fs.readFileSync('index.html','utf8');
const sw=fs.readFileSync('sw.js','utf8');
const m=JSON.parse(fs.readFileSync('manifest.webmanifest','utf8'));
const a=fs.readFileSync('app.js','utf8');

ok(m.start_url==='./','manifest start_url is not module-relative');
ok(m.scope==='./','manifest scope is not module-relative');
ok(h.includes('href="./manifest.webmanifest"'),'manifest link not relative');
for(const f of ['core.js','analysis_core_v2.js','robust_core_v3.js','canonical_registration_v4.js','app.js'])
  ok(h.includes(`src="./${f}?v=6.3.4"`),`${f} is not module-relative`);
for(const f of ['analysis_core_v2.js','robust_core_v3.js','canonical_registration_v4.js'])
  ok(sw.includes(`'./${f}?v=6.3.4'`),`${f} not precached`);
ok(sw.includes("url.pathname.startsWith(scope.pathname)"),'SW scope path isolation missing');
ok(a.includes("register('./sw.js',{scope:'./'})"),'SW registration not relative');
console.log('v6.3.4 Module/spectrumreader PWA contract PASS');
