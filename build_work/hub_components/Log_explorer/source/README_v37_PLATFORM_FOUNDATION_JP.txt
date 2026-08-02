LogMergeTool NoExcel v37 Platform Foundation

主な修正/追加:
1. Update File Typeボタンのエラー修正
   - PluginManagerDialog未定義エラーを修正しました。

2. Plugin Manager完成度向上
   - Install / Update Plugin ZIP
   - Validate Selected
   - Enable / Disable
   - Remove
   - Reload
   - インストール後、Log Typesに自動反映

3. Tool本体ZIPアップデートの土台追加
   - Update Toolボタン追加
   - Core Update ZIPを選択
   - manifest.jsonを検証
   - LOCALAPPDATA配下に安全に展開/ステージング
   - apply_update.batを生成

注意:
- 起動中のEXEは直接自己上書きできないため、v37では安全な「ステージング方式」です。
- 実際の置換は、LogMergeToolを閉じてから staged folder の apply_update.bat を確認して実行してください。
- 今後の版では専用Updater.exeで自動置換/Rollbackまで拡張できます。

Plugin ZIPの最低構成:
- manifest.json 必須

manifest例:
{
  "id": "newlog",
  "display_name": "New Log",
  "version": "1.0.0",
  "mode": ["merge", "import", "viewer"],
  "patterns": ["newlog*.log"]
}

Core Update ZIPの最低構成:
- manifest.json 必須

manifest例:
{
  "package_type": "core_update",
  "app_id": "log_merge_tool_noexcel",
  "version": "2.37.1",
  "min_supported_version": "2.37.0"
}
