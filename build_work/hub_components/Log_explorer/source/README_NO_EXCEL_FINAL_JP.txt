[Superseded by README_v7_ULTIMATE_JP.txt]

Log Merge Tool - No Excel / No COM FINAL v2 StartupFix

Main build BAT:
  Build_EXE_Windows11_Python313_Nuitka_NO_EXCEL_FINAL.bat

Build output:
  dist\LogMergeTool_NoExcel.exe

変更点:
- onefile構成に変更しました。Mainは dist\LogMergeTool_NoExcel.exe だけです。
- EXEダブルクリックで何も出ない場合でも起動エラーを保存します。
  %LOCALAPPDATA%\LogMergeTool_NoExcel\startup_error.log
- 診断用に Run_Source_Debug.bat と Build_DEBUG_Console_EXE.bat を追加しました。

重要:
- Excel/VBA/COMは使用しません。
- Pythonでログを解析し、openpyxlでxlsxを生成します。
- 日付範囲指定、再帰検索、CSA Error List検出、Site/Serial選択に対応しています。

確認手順:
1. Run_Source_Debug.bat でソース状態の画面起動を確認。
2. Build_EXE_Windows11_Python313_Nuitka_NO_EXCEL_FINAL.bat でビルド。
3. dist\LogMergeTool_NoExcel.exe をダブルクリック。
4. 起動しない場合は startup_error.log を確認。


[v11 update]
Search output uses a single explicit Timestamp column. Date and Time columns are removed. Search sheet freeze panes remain C2 and AutoFilter is ON.

[v12 update]
Searchはxlsxシートとして出力し、Timestampを yyyy/mm/dd hh:mm:ss.0 表示、C2固定、フィルターONにします。Date列とTime列は作りません。
