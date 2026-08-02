Log Merge Tool v21 Explorer Fixes

主な変更:
1. Merge時のIllegalCharacterError対策
   - Excelが保存できない制御文字をxlsx出力前に除去します。
   - ログ本文は可能な限り保持し、Excel禁止文字のみ削除します。

2. Log Explorer改善
   - 左右それぞれにSearch欄を追加。
   - Message列はタイムスタンプを除いた本文を表示。
   - 左右それぞれでLoad可能。
   - Load Bothで左右をまとめて読み込み可能。
   - 左右別Reloadボタンは削除。

3. Noise Rule適用タイミング
   - 追加直後に即適用。
   - Apply Rules Nowボタンを押した時だけ適用。
   を選択可能にしました。

4. Review表示
   - review.out / review.out.ar は、抽出パラメータをExplorer上の列として表示します。
   - 通常ログは従来どおりMessage中心の表示です。

注意:
- Excel Tableは使用せず通常AutoFilterのみ使用します。
- C2固定/フィルター/本文Timestampルールは継続しています。
