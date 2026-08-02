# v33 Smart File Discovery

追加内容:
- Run Log Merge実行前に指定フォルダをスキャン
- 指定フォルダ直下/指定フォルダ以下すべて（Recursive設定）を対象
- 検出できたログタイプだけをチェックボックス表示
- 日時範囲を入力して対象ファイルを絞り込み
- フィルター後の対象ファイル一覧を再表示
- 最終確認としてファイル単位でON/OFF可能
- Start with Checked Filesで選択ファイルのみMerge開始

重要:
- 日時範囲判定はファイル作成日/更新日ではなく、各ログ本文から生成したTimestampを使用します。
- REVIEWは検出表示されますが、Merge対象ではなくImport Onlyです。
- Timestampが抽出できないファイルは、誤除外を避けるため日時フィルター後も表示し、オペレーター判断でON/OFFできます。

操作:
1. Source Folderを選択
2. RecursiveのON/OFFを指定
3. Run Log Mergeを押す
4. Smart File Discovery画面でLog Typeを選択
5. 必要に応じてStart/Endを入力しApply
6. Files after Filterで最終対象ファイルを確認
7. 不要ファイルをOFFにしてStart with Checked Files
