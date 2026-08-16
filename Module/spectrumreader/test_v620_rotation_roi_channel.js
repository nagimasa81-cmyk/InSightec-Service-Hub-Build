
const fs=require('fs');
const a=fs.readFileSync('app.js','utf8');
const h=fs.readFileSync('index.html','utf8');
function ok(v,m){if(!v)throw Error(m)}

ok(h.includes('id="autoTiltBtn"'),'Auto tilt button missing');
ok(a.includes('estimator ONLY. Never rotate automatically'),'auto rotation policy missing');
ok(a.includes("visibleROILock=roi?{x:roi.x,y:roi.y,w:roi.w,h:roi.h}:null"),'ROI lock missing');
ok(a.includes('Analyze must never move/resize the visible Energy ROI'),'Analyze ROI lock policy missing');
ok(a.includes("v62FindWord('Channels'"),'Channels text anchor missing');
ok(a.includes("v62FindWord('Select All'"),'Select All text anchor missing');
ok(a.includes('channels.x-10'),'Channels left-10 rule missing');
ok(a.includes('channels.y+channels.h*.50'),'Channels center top rule missing');
ok(a.includes('selectAll.x+selectAll.w'),'Select All right edge rule missing');
ok(a.includes('selectAll.y+selectAll.h'),'Select All bottom edge rule missing');
ok(a.includes('if(fill>=.13)'),'checked-box interior ink criterion missing');
ok(a.includes("source:'checkbox-interior-ink-v6.3.0'"),'checkbox detector source missing');
console.log('v6.3.0 rotation/ROI/channel regression PASS');
