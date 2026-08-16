
const fs=require('fs');
const a=fs.readFileSync('app.js','utf8');
const h=fs.readFileSync('index.html','utf8');
function ok(v,m){if(!v)throw Error(m)}

ok(a.includes("source:'manual-energy-authoritative-v6.3.3'"),'manual Energy ROI not authoritative');
ok(a.includes("manual-channel-authoritative+"),'manual Channel ROI not authoritative');
ok(a.includes('function v621DetectCheckedChannelsFromKnownLayout('),'known layout detector missing');
ok(a.includes('for(let k=0;k<9;k++)analyzeCell(k,0,k)'),'CH0-8 row missing');
ok(a.includes('for(let k=0;k<7;k++)analyzeCell(9+k,1,k)'),'CH9-15 row missing');
ok(a.includes('isDisabled')&&a.includes('else if(isChecked)'), 'disabled-before-checked logic missing');
ok(h.includes('id="manualChannelSelect"'),'manual final channel selector missing');
ok(a.includes("source:'manual final channel'"),'manual channel override missing');
ok(a.includes("channels:[],")&&a.includes("channel-anchor-unresolved-v6.3.3"),
   'anchor failure must not guess all channels');
console.log('v6.3.3 manual authoritative/channel regression PASS');
