LogMergeTool NoExcel v16 Dual Log Viewer
========================================

追加機能:
- Open Dual Log Viewer ボタンを追加。
- 左右それぞれに任意ログを選択可能。
  - Merged
  - WS
  - CGA
  - CSA
  - MRSERVER
  - GESYS
  - LAIS
  - PSC
  - Review
  - Custom File
- Mergeしないファイルも左右に読み込み可能。
- 左右どちらかの行をクリックすると、Timestampが一番近い反対側の行へジャンプ。
- ±秒の許容範囲を設定可能。
- 下部に選択行のRaw詳細を表示。
- 選択した左右ペアをCSV出力可能。

軽量化方針:
- QTableView + QAbstractTableModelを使用。
- セルごとのWidgetを作成しない。
- 左右は必要なデータだけ手動Load。
- Custom Fileは単体ファイルだけ読み込むため軽量確認に使用可能。
- 日付範囲がONの場合、Viewerでも行Timestamp基準で絞り込み。

注意:
- 非常に大きいログをMergedで読み込む場合は時間がかかります。
  まずWSやMRSERVERなど単体種別で確認することを推奨します。
- Reviewはreview.out / review.out.ar / review.out.* が対象です。
- PSCはpsc.log系が対象です。
