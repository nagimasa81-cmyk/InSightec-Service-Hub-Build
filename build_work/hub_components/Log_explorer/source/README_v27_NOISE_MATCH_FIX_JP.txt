LogMergeTool v27 Noise Match Fix

修正内容:
- Noise Ruleの一致判定を正規化して、スペース/タブ/制御文字/表示本文とRawの差で外れないように修正。
- ExplorerとMerge出力の両方で同じNoiseEngineを使用。
- Hit Countを実際に一致した時に更新。
- ルール追加時はオペレーターが入力した文字列をそのまま保存し、再圧縮しない。
- Apply Rules Nowで左右ペインを再読込し、現在の承認済みルールを適用。
