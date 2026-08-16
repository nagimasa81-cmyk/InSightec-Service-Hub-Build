
const fs=require('fs');
const a=fs.readFileSync('app.js','utf8');
function ok(v,m){if(!v)throw Error(m)}

ok(a.includes('function v632EnergySeed('),'Energy seed function missing');
ok(a.includes('function v632ChannelSeed('),'Channel seed function missing');
ok(a.includes('function v632RectNearlySame('),'ROI alias detector missing');
ok(a.includes('function v632EnsureROIIsolation('),'ROI isolation guard missing');

const def=a.slice(a.indexOf('function v63DefaultROIForTarget('),a.indexOf('function v63RefreshActiveManualCrop'));
ok(!def.includes('(roi?{...roi}:null)'), 'generic current ROI fallback still exists');
ok(def.includes("target==='channel'?v632ChannelSeed():v632EnergySeed()"),
   'target-specific seed routing missing');

const auto=a.slice(a.indexOf("$('autoDetectBtn').onclick"),a.indexOf("$('manualBtn').onclick"));
ok(auto.includes('roiEditorState.energy={...roi}'),'Auto ROI does not initialize Energy state');
ok(!auto.includes('roiEditorState.channel={...roi}'),'Auto ROI contaminates Channel state');

const preview=a.slice(a.indexOf('function v6RenderPreviews('),a.indexOf('function v631SetProcessing'));
ok(preview.includes('roiEditorState.channel?{...roiEditorState.channel}'),
   'Channel preview does not use isolated state');
ok(preview.includes('roiEditorState.energy?{...roiEditorState.energy}'),
   'Energy preview does not use isolated state');

ok(a.includes("ROI isolation guard: Channel ROI and Energy ROI cannot share the same rectangle."),
   'alias guard status missing');

console.log('v6.3.4 ROI isolation regression PASS');
