LogMergeTool NoExcel v41 Workflow + Viewer Update

主な変更:
- STARTはImport/Viewer読み込み専用に変更
- MERGEを別ボタンとして追加
- Review/PSCは通常のLog Typeとして選択可能。ただしMERGE時はSearch統合対象にせず、Viewer/Import用として扱う
- Plugin Builder/manifestでは supports_merge / supports_import の考え方を採用する準備を追加
- Log ViewerのView modeドロップダウンを廃止し、Show 1/2/3/4チェックで表示ペインを制御
- Viewer初期化順序をガードし、main_splitter未生成エラーを回避
- Viewerは取り込み済みログタイプのみをドロップダウンに表示
- Viewer読込/処理中のProgressを新デザインに統一
- Viewer下部詳細ウインドウを非表示化
- Timestamp列を短め固定、Message列優先表示
- Review/WaterSystemは専用の既定列表示へ変更
- Viewer Time Rangeは行ダブルクリックでStart/Endに採用し、表示中ペインへ自動反映

使い方:
1. Source folderを選択
2. STARTを押すとSmart Discovery後、選択ログをLog Viewerへ読み込みます
3. MERGEを押すとMerge可能ログのみ統合出力します。PSC/ReviewはMerge出力には入りません
4. ViewerではShow 1/2/3/4で表示ペイン数を切替します
