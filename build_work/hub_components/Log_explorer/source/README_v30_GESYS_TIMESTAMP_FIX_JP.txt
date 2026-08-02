# v30 GESYS Timestamp Fix

## 修正内容

- GESYSログはファイル名日付ではなく、セクション内の日時行を優先してTimestampを作成します。
- 対象形式例:
  1780144501    0    1    Sat May 30 12:35:01 2026    0
- 上記の行で取得したTimestampを、そのセクション内の後続行へ継承します。
- GESYSの「Release」「build」「message body内の日付」はTimestampとして扱いません。
- 日付フィルターは各行/各セクションのTimestamp基準です。

## 添付データ確認

4010-2026-05-08-20-10-31.zip内のgesys_MR750W2.logでは、セクションTimestampが多数あり、2026/05/08までのログが含まれることを確認しました。
