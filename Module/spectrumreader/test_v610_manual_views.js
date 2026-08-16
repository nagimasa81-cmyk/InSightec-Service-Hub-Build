
const fs=require('fs');
const a=fs.readFileSync('app.js','utf8');
const h=fs.readFileSync('index.html','utf8');
function ok(v,m){if(!v)throw Error(m)}
ok(h.indexOf('id="originalPreview"') < h.indexOf('id="rotatedPreview"'),'Original must precede rotated');
ok(h.indexOf('id="rotatedPreview"') < h.indexOf('id="channelPreview"'),'Rotated must precede Channel crop');
ok(h.indexOf('id="channelPreview"') < h.indexOf('id="energyPreview"'),'Channel must precede Energy crop');
ok(h.includes('id="rotationRange"')&&h.includes('id="rotationNumber"'),'manual rotation controls missing');
ok(h.includes('id="editEnergyROI"')&&h.includes('id="editChannelROI"'),'independent ROI controls missing');
ok(a.includes('manualChannelROI')&&a.includes('manualEnergyROI'),'manual ROI state missing');
ok(a.includes('function v61UseRotatedWorkingFrame('),'manual rotation working frame missing');
ok(a.includes('function v61BoxCheckedChannelsInCrop('),'red channel boxes missing');
ok(a.includes('Low ${Number.isFinite(lowPop.value)'), 'Low line label missing');
ok(a.includes('High ${Number.isFinite(highPop.value)'), 'High line label missing');
console.log('v6.3.0 manual views regression PASS');
