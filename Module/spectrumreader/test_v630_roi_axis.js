
const fs=require('fs');
const a=fs.readFileSync('app.js','utf8');
function ok(v,m){if(!v)throw Error(m)}

ok(a.includes('let roiEditorState='),'unified editor state missing');
ok(a.includes('function v63ActivateROIEditor('),'unified ROI activation missing');
ok(a.includes('function v63CommitActiveROI('),'unified ROI commit missing');
ok(a.includes("v63ActivateROIEditor('energy')"),'Energy ROI button bypasses editor');
ok(a.includes("v63ActivateROIEditor('channel')"),'Channel ROI button bypasses editor');
ok(a.includes('v63CommitActiveROI()});'),'drag does not commit ROI');
ok(a.includes("pointerup',()=>{v63CommitActiveROI()"),'pointerup does not commit ROI');
ok(a.includes('function v63RefreshActiveManualCrop('),'live crop refresh missing');

ok(a.includes('function v63GridFirstRows('),'grid-first stage missing');
ok(a.includes('function v63NumericAnchorHypotheses('),'numeric anchor stage missing');
ok(a.includes('function v63GridAnchorAxisCalibration('),'grid-anchor calibration missing');
ok(a.includes("source:'grid-first+numeric-anchor-affine-v6.3.3'"),'canonical source missing');
const s=a.slice(a.indexOf('function v6AxisDecision('),a.indexOf('function v6VerticalGridCols'));
ok(s.includes('v63GridAnchorAxisCalibration'),'canonical decision not using grid-anchor');
ok(!s.includes('yAxisCalibration('),'legacy OCR mode calibration still canonical');
ok(s.includes("gridValueStep>=.5?'Gain':'Noise'"),'mode threshold missing');
ok(
  a.includes('const zeroY=-affine.intercept/affine.slope'),
  'zero not affine/grid-anchor-derived'
);

console.log('v6.3.3 ROI editor + grid-anchor Y-axis PASS');
