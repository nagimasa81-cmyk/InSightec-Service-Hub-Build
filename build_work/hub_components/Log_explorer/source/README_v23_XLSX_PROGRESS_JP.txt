LogMergeTool v23 - XLSX Progress Improvement

変更点:
- xlsx作成時にSearch/Errors/Type/Merged_1などの行書き込み進捗をポップアップへ反映。
- openpyxlの最終保存/圧縮処理は内部進捗を取得できないため、その段階では「Finalizing workbook...」として表示。
- 大量行出力時に0%のまま止まって見える問題を改善。
- v22のImport/Explorer/Noise機能は継続。

注意:
- 最終的な wb.save() のZIP圧縮中だけは正確な%取得不可です。
  そのため、行書き込みを95%程度まで進め、最後は保存処理中であることを明示します。
