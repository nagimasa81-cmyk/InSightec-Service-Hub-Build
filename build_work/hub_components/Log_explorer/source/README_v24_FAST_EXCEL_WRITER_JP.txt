LogMergeTool NoExcel v24 Fast Excel Writer

目的:
大量ログ出力時のxlsx書き込み時間を短縮するための高速化版です。

追加/変更:
- Fast xlsx mode
  - 大量データ時は重い重複シートや装飾を減らします。
- CSV + Summary xlsx for large data
  - 100,000行以上では全件データをCSVに出力し、xlsxはSummary中心にします。
  - 最速が必要な場合はこの設定をONにしてください。
- Skip Merged_1 duplicate
  - Searchと同じ内容をMerged_1へ重複出力しないことで保存時間を短縮します。
- Timestamp as text for speed
  - Timestampを `2026/07/04 13:07:58.6` の文字列として出力します。
  - Excel日時型より高速です。
- No styles for large xlsx
  - 50,000行以上では罫線/折返しなどの重い書式を省略します。

推奨設定:
- 10万行以上: CSV + Summary xlsx ON
- Excelファイルだけ必要: Fast xlsx mode ON、Skip Merged_1 ON、No styles ON
- Excel上で日時計算をしたい場合のみ Timestamp as text をOFF

注意:
- CSV出力ではC2固定やExcelフィルターは使えません。
- xlsxのSearchシートでは従来通りフィルター/C2固定を維持します。
