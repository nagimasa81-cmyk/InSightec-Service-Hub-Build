Log Merge Tool v9 BuildFix

この版は、Nuitkaビルド時に numpy.linalg._umath_linalg など不要な外部パッケージが巻き込まれて Scons failed になる問題を避けるため、ローカルの .venv_build を作ってクリーン環境でビルドします。

使い方:
1. ZIPを日本語や記号を含まない短いパスに展開します。例: C:\LogMergeBuild\v9
2. Build_EXE_Windows11_Python313_Nuitka_NO_EXCEL_FINAL.bat を実行します。
3. 完成EXEは dist\LogMergeTool_NoExcel.exe です。

前回のように module.numpy.linalg._umath_linalg / Scons failed が出る場合:
- .venv_build フォルダを削除
- dist/build も削除
- BATを再実行

機能内容:
- WSは行頭時刻を本文タイムスタンプとして使用
- 他ログも本文中の日付/時刻を優先
- 日付範囲指定は本文タイムスタンプ基準
- PSC Merge/Import対応
- Reviewは review.out / review.out.ar / review.out.* のImport Only
- Pause/Resume/Cancel対応
