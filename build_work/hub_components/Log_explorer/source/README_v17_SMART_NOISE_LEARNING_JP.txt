LogMergeTool NoExcel v17 - Smart Noise Learning

追加機能:
- Smart Noise Learning / Filter をメイン画面に追加
- Merge処理で承認済みNoise Ruleを適用可能
- Learning Modeでは候補をNoiseDB.sqliteに保存するだけで、自動削除しません
- 最終判断はオペレーターがManage Noise RulesまたはViewerから実施
- Dual Log Viewerで左右どちらの行も「Mark as Noise」「Not Noise」可能
- ルールは後からEnable/Disable/Delete可能
- 保存先: %LOCALAPPDATA%\LogMergeTool_NoExcel\NoiseDB.sqlite

操作:
1. Enable in Merge
   承認済みNoise RuleをMerge処理に使います。
2. Exclude approved noise from output
   ONの場合、承認済みNoiseに一致したログをxlsx/csvに保存しません。
   OFFの場合は学習・Viewer中心で、出力除外はしません。
3. Learning Mode: suggest only
   ノイズ候補をDBに保存しますが、自動除外はしません。
4. Manage Noise Rules
   ルールの追加、無効化、有効化、削除が可能です。

Viewer:
- Apply Noise Filter: 承認済みNoiseをViewer上で非表示
- Mark Left as Noise / Mark Right as Noise: 選択行からOperator承認ルールを作成
- Mark Selected Not Noise: 選択行をNot Noiseサンプルとして保存

注意:
- AI/学習候補は自動削除しません。
- 保存除外は必ず承認済みルールかつExclude approved noise from outputがONの時だけです。
