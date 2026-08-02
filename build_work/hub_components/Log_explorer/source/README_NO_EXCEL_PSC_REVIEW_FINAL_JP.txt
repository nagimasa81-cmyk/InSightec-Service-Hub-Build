[Superseded by README_v7_ULTIMATE_JP.txt]

Log Merge Tool No Excel - PSC / review.out 統合最終版
=====================================================

目的
----
Windows 11 / Python 3.13 / 最新PySide6 / 最新Nuitka 前提で、Excelマクロ/VBA/COMを一切使わずにEXE化する構成です。

今回の追加内容
--------------
1. psc.log を通常ログ種別と同じように選択式で Merge 対象に追加
   - GUI の Log Types に「PSC」を追加
   - Run Log Merge 実行時に PSC_Log / PSC_Params シートも出力
   - 日付範囲指定にも対応

2. psc.log の Import Only に対応
   - 「Import PSC Only」ボタンで単体psc.logをxlsx化
   - 出力シート: PSC_Log / PSC_Params

3. review.out の Import Only に対応
   - 「Import review.out Only」ボタンで単体review.out/review.*をxlsx化
   - 出力シート: ScanSummary
   - reviewoutはMerge対象には入れず、Import Only専用

4. Excel / VBA / COM 非依存
   - Microsoft Excelを起動しません
   - マクロを実行しません
   - 出力xlsxはPython側で作成します

ビルド方法
----------
1. このフォルダをWindows 11 PCに展開
2. Python 3.13 をインストール
3. Build_EXE_Windows11_Python313_Nuitka_NO_EXCEL_FINAL.bat をダブルクリック
4. 完了後、以下がMain EXEです

   dist\LogMergeTool_NoExcel.exe

起動しない場合
--------------
診断用に以下を確認してください。

%LOCALAPPDATA%\LogMergeTool_NoExcel\startup_error.log

補足
----
この版はExcelマクロではなくPython実装です。
既存VBAの主要ロジックをPython側へ移植していますが、実運用ログで列名や抽出結果に差分が出た場合は、サンプルログと出力結果を元に parser 部分を調整してください。

Double-check note v2.1.1:
- Source compile check passed.
- PSC import parser was checked with both PscStates :: function : key=value and MRMAIL-style non-:: lines.
- review.out parser was checked with multi-key lines separated by two spaces.
- app_dir was corrected for Nuitka onefile bundled data files.
- Import-only operations now show an error if no valid PSC/review.out rows are detected.

v2.1.2 update:
- Scan 100%後にxlsx作成中のステータスログを表示するよう修正。
- 大量行で固まって見える原因になっていた全セルAutoFit走査を高速化。
- 50,000行を超える巨大シートではExcel Tableオブジェクトを省略し、AutoFilter/FreezePanesは維持。
