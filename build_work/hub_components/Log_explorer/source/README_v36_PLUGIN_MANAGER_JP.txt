LogMergeTool v36 Plugin Manager / Update File Type

追加内容
- Update File Type ボタンを追加
- File Type Plugin ZIP をインストール可能
- plugins フォルダへ展開してホットリロード
- インストール済みPluginをEnable/Disable/Remove可能
- Pluginとして追加したログタイプはLog Types欄に自動でチェックボックス表示
- チェックONにするとMerge対象として扱う
- PluginBuilder.py / Build_PluginBuilder_EXE.bat を同梱

Plugin ZIPの最低構成
- manifest.json 必須
- parser.json 推奨
- README.txt 任意
- sample/ 任意

manifest.json例
{
  "id": "newlog",
  "display_name": "New Log",
  "version": "1.0.0",
  "mode": ["merge", "import"],
  "patterns": ["newlog*.log", "*.newlog"],
  "enabled": true,
  "plugin_api": "2.0"
}

使い方
1. LogMergeToolを起動
2. Update File Typeをクリック
3. xxx.plugin.zipを選択
4. Install完了後、Log Types欄にPluginチェックボックスが追加される
5. 必要なPluginをチェックしてRun Log Merge

Plugin Builder
- PluginBuilder.pyを直接実行、またはBuild_PluginBuilder_EXE.batでEXE化
- Sample Logを読み込み、PreviewでTimestamp候補を確認
- Build Plugin ZIPでUpdate File Type用ZIPを作成

注意
- v36のPlugin Parserは安全性重視のJSON定義型です。
- 複雑な専用Parser.py実行は未有効化。任意コード実行を避けるためです。
- 追加Pluginは基本のTimestamp抽出エンジンを使って読み込みます。
