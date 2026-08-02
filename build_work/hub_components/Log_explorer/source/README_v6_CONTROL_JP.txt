[Superseded by README_v7_ULTIMATE_JP.txt]

Log Merge Tool - No Excel / v6 Turbo Control

変更点:
1. Log Types の表示を「PSC」に変更しました。
   - 画面上の「PSC psc.log」は廃止。
   - Merge対象としての動作は従来通り PSC ログを対象にします。

2. 進捗表示を強化しました。
   - Progress bar に % を表示。
   - スキャン/解析中はファイル数ベースで進捗表示。
   - Turbo CSV 出力中は行数ベースで進捗表示。

3. Pause / Cancel ボタンを追加しました。
   - Pause: 処理を一時停止します。
   - Resume: 一時停止した処理を再開します。
   - Cancel: 処理を中断します。

注意:
- Cancel は現在処理中のファイルまたはCSV書き込みチャンクが完了したタイミングで停止します。
- 非Turboの巨大xlsx書き込み中はExcelファイル保存処理の都合で即時停止できない場合があります。
- 大量ログでは v6 Turbo CSV をONにして使用することを推奨します。
