Log Merge Tool v32 - Viewer Time Range + Resizable Splitter

変更内容:
1. Log Viewerに表示用の開始/終了日時フィルターを追加
   - Enable Viewer Time Range
   - Start / End に 2026/07/04 13:07:58.6 の形式で入力
   - Apply to Left / Apply to Right / Apply to Both で左右別または両方へ適用
   - Clear Time Range で全件表示へ戻す
   - Set Start from Selected / Set End from Selected で選択行のTimestampを入力欄へコピー

2. 日付時間フィルターはMerge出力には影響しない
   - Explorer内の表示と検索対象だけを絞り込む
   - Searchはフィルター後の表示行に対して動作

3. 左右ペインの中央境界をドラッグ可能に改善
   - 中央の境界線をマウスで左右にドラッグすると、左/右ログの表示幅が変わる
   - Message列は自動で広く/狭くなる
   - Timestamp列は左端の基準列として固定幅表示

4. マウスオーバー説明追加
   - Time Range関連ボタン
   - 中央スプリッター

注意:
- 日時入力例: 2026/07/04 13:07:58.6
- 日付だけの場合、Startは00:00:00.0、Endは23:59:59.999999として扱う
