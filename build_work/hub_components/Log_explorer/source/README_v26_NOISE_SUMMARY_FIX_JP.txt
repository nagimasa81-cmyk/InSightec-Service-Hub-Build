LogMergeTool No Excel v26 - Noise / Summary xlsx Fix

修正内容:
- CSV + Summary xlsx モードで NameError: write_sheet_rows is not defined が出る問題を修正。
- Summary xlsx 側の書き込みヘルパーを統一し、Output Files / Type Summary / Error Sample / CSA Error / Lists を安全に出力。
- Excel Table XML は作成せず、通常AutoFilterだけを使用。
- v25のNoise Rule適用ロジックは維持。

Noise Rule適用の注意:
- Learning Modeは候補保存のみで、出力除外はしません。
- 出力から除外するには Apply approved Noise Rules in Merge output をONにしてください。
- 既存ルールは Manage Noise Rules で Enabled になっている必要があります。
