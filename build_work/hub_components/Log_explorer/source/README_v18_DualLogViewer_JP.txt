Log Merge Tool v18 - Dual Log Viewer / Log Explorer

使い方:
1. Source Folderにログフォルダを指定します。
2. 必要ならStart/End Dateを指定します。Viewerでも本文Timestamp基準でフィルターされます。
3. Open Dual Log Viewer / Log Explorerを押します。
4. Left / Rightで表示したいログ種別を選びます。
   - Merged: メインMerge対象を時系列統合して表示
   - WS / CGA / CSA / MRSERVER / GESYS / LAIS / PSC / Review: 種別単独で表示
   - Custom File: 任意ファイルを直接選択して表示
5. Load Left / Load Right / Load Bothを押して読み込みます。
6. 左右どちらかの行をクリックすると、そのTimestampに一番近い反対側の行へジャンプします。
7. Jump toleranceで±秒の目安を変更できます。範囲外の場合はstatusに表示されます。
8. Apply Noise FilterをONにすると承認済みNoise Ruleを非表示にします。
9. Mark Left/Right as Noiseで選択行からNoise Ruleを作れます。
10. Export Selected Pairで左右の選択行をCSV出力できます。

軽量化方針:
- QTableView + QAbstractTableModelで表示します。
- ExcelセルのようなWidgetを大量生成しません。
- データは表示に必要な列だけに整形して表示します。

注意:
- Viewerは現在のSource Folderと日付条件を使用します。
- Reviewはreview.out / review.out.ar / review.out.*を対象にします。
- Mergedはメイン画面で選択されているログタイプを統合表示します。
