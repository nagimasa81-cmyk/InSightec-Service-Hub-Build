LogMergeTool No Excel v25 - Noise Filter Fix

修正内容:
- 「Apply approved Noise Rules in Merge output」をONにすると、承認済み/有効なNoise Ruleに一致する行をMerge出力から除外します。
- 以前の版では「Enable in Merge」と「Exclude approved noise from output」の両方が必要で、期待通りに除外されないケースがありました。
- Learning Modeは候補保存のみで、勝手に除外しません。
- Mergeログに「Noise Filter: excluded ... rows」と表示します。
- 一致が0件の場合も「enabled, but no rows matched...」と表示します。

使い方:
1. Manage Noise RulesでルールがStatus=Enabled / Approvedになっていることを確認。
2. メイン画面で「Apply approved Noise Rules in Merge output」をON。
3. Run Log Merge。
4. 出力から対象ログが除外されます。

注意:
- Explorer側の表示だけ除外したい場合はExplorer内の「Apply Noise Filter」をONにしてLoad Bothしてください。
