LogMergeTool v41.2 Clean Integrated

目的:
- v41/v41.1で後付けになっていたUI/Viewerパッチを、起動前に確実に適用する構成へ修正。
- 以前のUIに先祖返りして見える問題を低減。

主な修正:
- main()呼び出しをファイル末尾へ移動し、全override適用後に起動するよう変更
- START = Import / Viewer読み込み、MERGE = Merge出力の役割を再整理
- Import PSC / Import Review / Import Selectedの旧ボタンは非表示維持
- Updateは1ボタン化を維持し、ZIP種別を自動判定する説明へ統一
- PSC / Reviewは通常Log Typeとして選択可能、MERGE時は統合対象外
- ViewerのView Mode UIを非表示、Showチェック方式へ統一
- LOAD LOGS表記へ整理
- Viewer下部詳細ウインドウ非表示
- Viewer初期化後に読み込み済みLogだけドロップダウンへ反映
- Merge完了後のViewer準備中Progress表示を安定化
- Python文法チェックOK

評価ポイント:
1. 起動時に旧UIへ戻っていないか
2. STARTとMERGEの役割が分かれているか
3. Viewer初回起動でmain_splitter系エラーが出ないか
4. 未読み込みLogがViewerドロップダウンに出ないか
5. LOAD LOGS / Showチェック方式になっているか
