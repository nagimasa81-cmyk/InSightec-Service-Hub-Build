LogMergeTool v41.1 Stabilization

主な修正:
- Log Viewer初回起動時の main_splitter 系エラー対策を強化
- START後 / MERGE後のViewer表示前に進捗ポップアップを表示
- Viewerを画面内に収まるサイズで中央表示
- 読み込んだログタイプのみLog Viewerのドロップダウンへ表示
- ViewerのProgress Popupを新デザインへ統一
- View modeドロップダウンを非表示化し、Showチェックのみで表示ペインを制御
- 下部詳細ウインドウを非表示
- Timestamp列をコンパクト固定、Message優先表示を継続

使い方:
1. Build_EXE_Windows11_Python313_Nuitka_NO_EXCEL_FINAL.bat を実行
2. dist内のEXEを起動
3. STARTでImport/Viewer読み込み、MERGEでマージ出力
