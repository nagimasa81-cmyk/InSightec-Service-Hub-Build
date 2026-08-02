Option Explicit

'============================================================
' Unified Tracker SNR Batch Report - VERSION 2.8 SIGNAL NOISE FIX
'============================================================
' Entry point:
'   Run_TrackerSNR_V2  (recommended)
'   CreateTrackerSNRBatchReport_Final
'
' Main features:
'   - Multiple log file selection OR folder selection.
'   - Creates one NEW output workbook.
'   - Dashboard + Summary + combined data sheet.
'   - Dashboard is shown by default.
'   - One-file and multi-file workflows use the same UI.
'   - File selector, metric selector, block selector.
'   - Tracker based graph only. By Scan mode is intentionally removed.
'   - Scan numbers are NOT trusted from the log.
'   - Scan is always Scan0..Scan3 repeated for each tracker.
'   - Block means one Scan0..Scan3 cycle for a tracker set.
'   - Matrix displays only the selected block: T0..T5 x Scan0..Scan3.
'   - Matrix has no Max / Average columns.
'   - SNR spec coloring: >=100 blue, <100 red.
'   - Signal and Noise selectors are shown only for files that have Signal/Noise data.
'   - Zero data rows are not imported:
'       * Tracker No 0 is valid.
'       * SNR must be > 0.
'       * For Signal/Noise rows: Signal > 0 and Noise > 0 are also required.
'   - No completion message. Folder mode imports only date-name target logs like 2025_Jan_22_22_05_31.Log.
'   - Existing output file: asks whether to recreate or do nothing.
'   - File list is sorted newest first. Dashboard defaults to the newest valid file.
'============================================================

Private Const SHEET_DASH As String = "Dashboard"
Private Const SHEET_SUMMARY As String = "Summary"
Private Const SHEET_DATA As String = "Tracker_SNR"
Private Const SHEET_LIST As String = "_Lists"

Private Const CHART_NAME As String = "chtTrackerMetric"
Private Const SPEC_SNR As Double = 100#

Private Const CELL_FILE_INDEX As String = "Z1"
Private Const CELL_METRIC_INDEX As String = "Z2"
Private Const CELL_BLOCK_INDEX As String = "Z3"
Private Const CELL_FILE_COUNT As String = "Z4"
Private Const CELL_BLOCK_COUNT As String = "Z5"
Private Const CELL_TRACKER_COUNT As String = "Z6"
Private Const CELL_HAS_SIGNAL As String = "Z7"
Private Const CELL_ACTUAL_FILE_ID As String = "Z8"

Private gInternalUpdate As Boolean

'============================================================
' Entry point
'============================================================
Public Sub Run_TrackerSNR_V2()
    CreateTrackerSNRBatchReport_Final
End Sub

Public Sub CreateTrackerSNRBatchReport_Final()
    Dim files As Collection
    Dim firstFolder As String
    Dim outPath As String
    Dim wbOut As Workbook
    Dim wsData As Worksheet
    Dim wsSummary As Worksheet
    Dim wsDash As Worksheet
    Dim wsList As Worksheet
    Dim totalRows As Long
    Dim i As Long
    Dim filePath As String
    Dim nextRow As Long
    Dim fileRows As Long
    Dim trackerCount As Long
    Dim blockCount As Long
    Dim hasSignalNoise As Boolean
    Dim saveOk As Boolean

    On Error GoTo ErrHandler

    Set files = PickTrackerLogFiles()
    If files Is Nothing Then Exit Sub
    If files.Count = 0 Then Exit Sub

    firstFolder = Left$(CStr(files(1)), InStrRev(CStr(files(1)), Application.PathSeparator))
    If files.Count = 1 Then
        outPath = firstFolder & "Tracker SNR_" & SafeFileName(FileBaseName(CStr(files(1)))) & ".xlsx"
    Else
        outPath = firstFolder & "Tracker SNR_Batch_" & Format(Now, "yyyymmdd_hhnnss") & ".xlsx"
    End If

    If WorkbookIsOpen(outPath) Then
        MsgBox "The output file is already open. Please close it and run again." & vbCrLf & outPath, vbExclamation, "Tracker SNR"
        Exit Sub
    End If

    If Dir(outPath) <> "" Then
        If MsgBox("Output file already exists." & vbCrLf & vbCrLf & outPath & vbCrLf & vbCrLf & _
                  "Recreate it?", vbQuestion + vbYesNo, "Tracker SNR") = vbNo Then
            Exit Sub
        End If
        On Error Resume Next
        Kill outPath
        On Error GoTo ErrHandler
        If Dir(outPath) <> "" Then
            MsgBox "The existing output file could not be deleted. Please close it or check permissions.", vbExclamation, "Tracker SNR"
            Exit Sub
        End If
    End If

    Application.ScreenUpdating = False
    Application.DisplayAlerts = False
    Application.EnableEvents = False
    Application.StatusBar = "Creating Tracker SNR report..."

    Set wbOut = Workbooks.Add(xlWBATWorksheet)
    Set wsData = wbOut.Worksheets(1)
    wsData.Name = SHEET_DATA
    WriteDataHeader wsData
    nextRow = 2

    Set wsSummary = wbOut.Worksheets.Add(After:=wsData)
    wsSummary.Name = SHEET_SUMMARY
    WriteSummaryHeader wsSummary

    For i = 1 To files.Count
        filePath = CStr(files(i))
        Application.StatusBar = "Processing " & i & " / " & files.Count & " : " & FileNameOnly(filePath)

        fileRows = ImportOneTrackerFile(filePath, i, wsData, nextRow, trackerCount, hasSignalNoise)
        If fileRows > 0 Then
            blockCount = AssignScanAndBlockForFile(wsData, i, trackerCount)
            WriteSummaryRow wsSummary, i, filePath, fileRows, trackerCount, hasSignalNoise, blockCount
            nextRow = nextRow + fileRows
            totalRows = totalRows + fileRows
        Else
            ' No valid target rows in this file. Do not add it to the Dashboard file list.
        End If
    Next i

    If totalRows = 0 Then
        wbOut.Close SaveChanges:=False
        Application.StatusBar = False
        Application.DisplayAlerts = True
        Application.ScreenUpdating = True
        Application.EnableEvents = True
        MsgBox "No valid Tracker SNR data was found." & vbCrLf & _
               "Rows with SNR <= 0 are ignored. Rows with Signal/Noise data also require Signal > 0 and Noise > 0.", _
               vbExclamation, "Tracker SNR"
        Exit Sub
    End If

    UpdateSummarySNRStats wsSummary, wsData

    wsData.Range("A1:M" & nextRow - 1).AutoFilter
    wsData.Columns("A:M").AutoFit
    wsSummary.Columns("A:I").AutoFit

    Set wsDash = wbOut.Worksheets.Add(Before:=wbOut.Worksheets(1))
    wsDash.Name = SHEET_DASH
    Set wsList = wbOut.Worksheets.Add(After:=wbOut.Worksheets(wbOut.Worksheets.Count))
    wsList.Name = SHEET_LIST
    wsList.Visible = xlSheetVeryHidden

    BuildDashboard wbOut, wsDash, wsList, wsSummary
    RefreshTrackerSNRBatchDashboard

    wsDash.Activate
    wsDash.Range("A1").Select

    saveOk = SaveReportWorkbook(wbOut, outPath)

    Application.StatusBar = False
    Application.DisplayAlerts = True
    Application.ScreenUpdating = True
    Application.EnableEvents = True

    If Not saveOk Then
        MsgBox "The report was created, but SaveAs failed." & vbCrLf & _
               "Please save the workbook manually.", vbExclamation, "Tracker SNR"
    End If
    Exit Sub

ErrHandler:
    Application.StatusBar = False
    Application.DisplayAlerts = True
    Application.ScreenUpdating = True
    Application.EnableEvents = True
    MsgBox "Error: " & Err.Description, vbCritical, "Tracker SNR"
End Sub

'============================================================
' File picker
'============================================================
Private Function PickTrackerLogFiles() As Collection
    Dim modeAnswer As VbMsgBoxResult
    Dim result As Collection

    modeAnswer = MsgBox( _
        "Select import source." & vbCrLf & vbCrLf & _
        "Yes    = Select a folder and import all target log files in it" & vbCrLf & _
        "No     = Select one or more files" & vbCrLf & _
        "Cancel = Exit", _
        vbQuestion + vbYesNoCancel, _
        "Tracker SNR - Select Source")

    Select Case modeAnswer
        Case vbYes
            Set result = PickTrackerLogFolderFiles()
        Case vbNo
            Set result = PickTrackerLogFilePickerFiles()
        Case Else
            Set PickTrackerLogFiles = Nothing
            Exit Function
    End Select

    If result Is Nothing Then
        Set PickTrackerLogFiles = Nothing
    ElseIf result.Count = 0 Then
        MsgBox "No target log files were found." & vbCrLf & _
               "Folder mode target name: yyyy_Mmm_dd_hh_mm_ss.Log", _
               vbExclamation, "Tracker SNR"
        Set PickTrackerLogFiles = Nothing
    Else
        Set PickTrackerLogFiles = result
    End If
End Function

Private Function PickTrackerLogFilePickerFiles() As Collection
    Dim fd As FileDialog
    Dim result As New Collection
    Dim item As Variant

    Set fd = Application.FileDialog(msoFileDialogFilePicker)
    With fd
        .Title = "Select Tracker SNR log files"
        .AllowMultiSelect = True
        .Filters.Clear
        .Filters.Add "Target Log Files", "*.log;*.Log;*.txt"
        .Filters.Add "All Files", "*.*"
        If .Show <> -1 Then
            Set PickTrackerLogFilePickerFiles = Nothing
            Exit Function
        End If
        For Each item In .SelectedItems
            If IsTargetLogFile(CStr(item)) Then result.Add CStr(item)
        Next item
    End With

    Set PickTrackerLogFilePickerFiles = SortPathCollection(result)
End Function

Private Function PickTrackerLogFolderFiles() As Collection
    Dim fd As FileDialog
    Dim folderPath As String
    Dim result As Collection

    Set fd = Application.FileDialog(msoFileDialogFolderPicker)
    With fd
        .Title = "Select a folder that contains Tracker SNR log files"
        .AllowMultiSelect = False
        If .Show <> -1 Then
            Set PickTrackerLogFolderFiles = Nothing
            Exit Function
        End If
        folderPath = CStr(.SelectedItems(1))
    End With

    Set result = CollectTargetLogFilesFromFolder(folderPath)
    Set PickTrackerLogFolderFiles = result
End Function

Private Function CollectTargetLogFilesFromFolder(ByVal folderPath As String) As Collection
    Dim result As New Collection
    Dim f As String
    Dim fullPath As String

    If Len(folderPath) = 0 Then
        Set CollectTargetLogFilesFromFolder = result
        Exit Function
    End If

    If Right$(folderPath, 1) <> Application.PathSeparator Then
        folderPath = folderPath & Application.PathSeparator
    End If

    f = Dir(folderPath & "*.*")
    Do While Len(f) > 0
        fullPath = folderPath & f
        If IsTargetFolderLogFile(fullPath) Then result.Add fullPath
        f = Dir()
    Loop

    Set CollectTargetLogFilesFromFolder = SortPathCollection(result)
End Function


Private Function IsTargetFolderLogFile(ByVal fullPath As String) As Boolean
    Dim fileName As String
    Dim v As Variant

    If Not IsTargetLogFile(fullPath) Then Exit Function

    fileName = FileNameOnly(fullPath)
    ' Folder mode target format:
    '   2025_Jan_22_22_05_31.Log
    '   2025_Sep_11_20_34_19.Log
    v = ExtractTextByRegex(fileName, "^([0-9]{4}_[A-Za-z]{3}_[0-9]{1,2}_[0-9]{1,2}_[0-9]{1,2}_[0-9]{1,2})\.(log|txt)$")
    IsTargetFolderLogFile = Not IsEmpty(v)
End Function

Private Function IsTargetLogFile(ByVal fullPath As String) As Boolean
    Dim ext As String
    Dim p As Long

    p = InStrRev(fullPath, ".")
    If p = 0 Then Exit Function

    ext = LCase$(Mid$(fullPath, p + 1))
    Select Case ext
        Case "log", "txt"
            IsTargetLogFile = True
    End Select
End Function

Private Function SortPathCollection(ByVal source As Collection) As Collection
    Dim result As New Collection
    Dim arr() As String
    Dim keys() As Double
    Dim i As Long
    Dim j As Long
    Dim tmp As String
    Dim tmpKey As Double

    If source Is Nothing Then
        Set SortPathCollection = result
        Exit Function
    End If

    If source.Count = 0 Then
        Set SortPathCollection = result
        Exit Function
    End If

    ReDim arr(1 To source.Count)
    ReDim keys(1 To source.Count)
    For i = 1 To source.Count
        arr(i) = CStr(source(i))
        keys(i) = FileSortKey(arr(i))
    Next i

    'Newest first.  The date embedded in names such as
    '2025_Jan_22_22_05_31.Log is used first; file modified time is the fallback.
    For i = LBound(arr) To UBound(arr) - 1
        For j = i + 1 To UBound(arr)
            If keys(i) < keys(j) Or _
               (keys(i) = keys(j) And StrComp(arr(i), arr(j), vbTextCompare) < 0) Then
                tmp = arr(i)
                arr(i) = arr(j)
                arr(j) = tmp
                tmpKey = keys(i)
                keys(i) = keys(j)
                keys(j) = tmpKey
            End If
        Next j
    Next i

    For i = LBound(arr) To UBound(arr)
        result.Add arr(i)
    Next i

    Set SortPathCollection = result
End Function

Private Function FileSortKey(ByVal fullPath As String) As Double
    Dim stamp As Variant
    Dim dt As Date

    stamp = ExtractTextByRegex(FileNameOnly(fullPath), "([0-9]{4}_[A-Za-z]{3}_[0-9]{1,2}_[0-9]{1,2}_[0-9]{1,2}_[0-9]{1,2})")
    If Not IsEmpty(stamp) Then
        If TryDateFromLogStamp(CStr(stamp), dt) Then
            FileSortKey = CDbl(dt)
            Exit Function
        End If
    End If

    On Error Resume Next
    dt = FileDateTime(fullPath)
    If Err.Number = 0 Then
        FileSortKey = CDbl(dt)
    Else
        FileSortKey = 0#
    End If
    Err.Clear
    On Error GoTo 0
End Function

Private Function TryDateFromLogStamp(ByVal stamp As String, ByRef dt As Date) As Boolean
    Dim p() As String
    Dim y As Long
    Dim m As Long
    Dim d As Long
    Dim hh As Long
    Dim nn As Long
    Dim ss As Long

    On Error GoTo Failed
    p = Split(stamp, "_")
    If UBound(p) < 5 Then GoTo Failed

    y = CLng(p(0))
    m = MonthNumberFromText(p(1))
    d = CLng(p(2))
    hh = CLng(p(3))
    nn = CLng(p(4))
    ss = CLng(p(5))
    If m < 1 Then GoTo Failed

    dt = DateSerial(y, m, d) + TimeSerial(hh, nn, ss)
    TryDateFromLogStamp = True
    Exit Function

Failed:
    TryDateFromLogStamp = False
End Function

Private Function MonthNumberFromText(ByVal monthText As String) As Long
    Select Case LCase$(Left$(Trim$(monthText), 3))
        Case "jan": MonthNumberFromText = 1
        Case "feb": MonthNumberFromText = 2
        Case "mar": MonthNumberFromText = 3
        Case "apr": MonthNumberFromText = 4
        Case "may": MonthNumberFromText = 5
        Case "jun": MonthNumberFromText = 6
        Case "jul": MonthNumberFromText = 7
        Case "aug": MonthNumberFromText = 8
        Case "sep": MonthNumberFromText = 9
        Case "oct": MonthNumberFromText = 10
        Case "nov": MonthNumberFromText = 11
        Case "dec": MonthNumberFromText = 12
        Case Else: MonthNumberFromText = 0
    End Select
End Function

'============================================================
' Data import
'============================================================
Private Sub WriteDataHeader(ByVal ws As Worksheet)
    ws.Range("A1:M1").Value = Array("File Index", "File Name", "Time", "Tracker No", "Scan No", "Block No", _
                                    "Signal", "Noise", "SNR", "Peak Loc", "Peak COM", "Peak Center", "Source Type")
    ws.Rows(1).Font.Bold = True
End Sub

Private Function ImportOneTrackerFile(ByVal filePath As String, ByVal fileIndex As Long, ByVal ws As Worksheet, _
                                      ByVal startRow As Long, ByRef trackerCount As Long, _
                                      ByRef hasSignalNoise As Boolean) As Long
    Dim ff As Integer
    Dim lineText As String
    Dim t As String
    Dim rowOut As Long
    Dim trackerDict As Object
    Dim trackerNo As Variant
    Dim signalVal As Variant
    Dim noiseVal As Variant
    Dim snrVal As Variant
    Dim peakLoc As Variant
    Dim peakCom As Variant
    Dim peakCenter As Variant

    On Error GoTo FileReadFailed

    Set trackerDict = CreateObject("Scripting.Dictionary")
    hasSignalNoise = False
    rowOut = startRow

    ff = FreeFile
    Open filePath For Input As #ff

    Do Until EOF(ff)
        Line Input #ff, lineText
        lineText = Trim$(lineText)
        If Len(lineText) = 0 Then GoTo ContinueLoop

        t = ExtractTimeText(lineText)

        'Signal/Noise rows also contain the words "peak" and "SNR".
        'Therefore they must be evaluated before PEAK rows, otherwise Signal and Noise stay blank.
        If IsSignalNoiseDataLine(lineText) Then
            trackerNo = ExtractTrackerNumber(lineText)
            signalVal = ExtractNamedNumber(lineText, "signal")
            noiseVal = ExtractNamedNumber(lineText, "noise")
            snrVal = ExtractLastNamedNumber(lineText, "snr")

            If IsValidTrackerNumber(trackerNo) And IsPositiveNumber(signalVal) And _
               IsPositiveNumber(noiseVal) And IsPositiveNumber(snrVal) Then
                hasSignalNoise = True
                WriteDataRow ws, rowOut, fileIndex, FileNameOnly(filePath), t, CLng(trackerNo), _
                             CDbl(signalVal), CDbl(noiseVal), CDbl(snrVal), Empty, Empty, Empty, "SIGNAL"
                AddTracker trackerDict, CLng(trackerNo)
                rowOut = rowOut + 1
            End If

        ElseIf IsPeakSNRDataLine(lineText) Then
            trackerNo = ExtractTrackerNumber(lineText)
            snrVal = ExtractLastNamedNumber(lineText, "snr")

            If IsValidTrackerNumber(trackerNo) And IsPositiveNumber(snrVal) Then
                peakLoc = ExtractFirstOf(lineText, Array("peakLocation", "peakLoc"))
                peakCom = ExtractFirstOf(lineText, Array("peakCOM", "peakCom"))
                peakCenter = ExtractFirstOf(lineText, Array("peakCenterNoWeight", "peakCenter"))

                WriteDataRow ws, rowOut, fileIndex, FileNameOnly(filePath), t, CLng(trackerNo), _
                             Empty, Empty, CDbl(snrVal), peakLoc, peakCom, peakCenter, "PEAK"
                AddTracker trackerDict, CLng(trackerNo)
                rowOut = rowOut + 1
            End If
        End If

ContinueLoop:
    Loop
    Close #ff

    trackerCount = DetectTrackerCount(trackerDict)
    ImportOneTrackerFile = rowOut - startRow
    Exit Function

FileReadFailed:
    On Error Resume Next
    Close #ff
    trackerCount = 0
    hasSignalNoise = False
    ImportOneTrackerFile = 0
End Function

Private Sub WriteDataRow(ByVal ws As Worksheet, ByVal rowNo As Long, ByVal fileIndex As Long, _
                         ByVal fileName As String, ByVal timeText As String, ByVal trackerNo As Long, _
                         ByVal signalVal As Variant, ByVal noiseVal As Variant, ByVal snrVal As Double, _
                         ByVal peakLoc As Variant, ByVal peakCom As Variant, ByVal peakCenter As Variant, _
                         ByVal sourceType As String)
    ws.Cells(rowNo, 1).Value = fileIndex
    ws.Cells(rowNo, 2).Value = fileName
    ws.Cells(rowNo, 3).Value = timeText
    ws.Cells(rowNo, 4).Value = trackerNo
    ws.Cells(rowNo, 7).Value = signalVal
    ws.Cells(rowNo, 8).Value = noiseVal
    ws.Cells(rowNo, 9).Value = snrVal
    ws.Cells(rowNo, 10).Value = peakLoc
    ws.Cells(rowNo, 11).Value = peakCom
    ws.Cells(rowNo, 12).Value = peakCenter
    ws.Cells(rowNo, 13).Value = sourceType
End Sub

Private Function AssignScanAndBlockForFile(ByVal ws As Worksheet, ByVal fileIndex As Long, ByVal trackerCount As Long) As Long
    Dim lastRow As Long
    Dim r As Long
    Dim sourceType As String
    Dim trackerNo As Long
    Dim key As String
    Dim occurrenceCounter As Object
    Dim occurrenceNo As Long
    Dim scanNo As Long
    Dim blockNo As Long
    Dim maxBlock As Long

    Set occurrenceCounter = CreateObject("Scripting.Dictionary")
    lastRow = ws.Cells(ws.Rows.Count, "A").End(xlUp).Row
    If trackerCount <= 0 Then trackerCount = 4
    maxBlock = 1

    ' Important rule:
    ' Do not use scan numbers from the log. Treat Scan0..Scan3 as a repeated cycle.
    ' Count occurrences independently for each tracker and source type.
    ' This prevents Signal/Noise rows from being forced into Scan0 when PEAK rows contain scan text.
    For r = 2 To lastRow
        If CLng(Val(ws.Cells(r, 1).Value)) = fileIndex Then
            trackerNo = CLng(ws.Cells(r, 4).Value)
            sourceType = CStr(ws.Cells(r, 13).Value)
            key = sourceType & "|" & CStr(trackerNo)
            If Not occurrenceCounter.Exists(key) Then occurrenceCounter.Add key, 0

            occurrenceCounter(key) = CLng(occurrenceCounter(key)) + 1
            occurrenceNo = CLng(occurrenceCounter(key))

            scanNo = (occurrenceNo - 1) Mod 4
            blockNo = ((occurrenceNo - 1) \ 4) + 1

            ws.Cells(r, 5).Value = scanNo
            ws.Cells(r, 6).Value = blockNo
            If blockNo > maxBlock Then maxBlock = blockNo
        End If
    Next r

    AssignScanAndBlockForFile = maxBlock
End Function

Private Function DetectTrackerCount(ByVal trackerDict As Object) As Long
    Dim maxTracker As Long
    Dim k As Variant

    maxTracker = -1
    For Each k In trackerDict.Keys
        If CLng(k) > maxTracker Then maxTracker = CLng(k)
    Next k

    If maxTracker >= 5 Then
        DetectTrackerCount = 6
    ElseIf maxTracker >= 3 Then
        DetectTrackerCount = 4
    ElseIf trackerDict.Count > 0 Then
        DetectTrackerCount = trackerDict.Count
    Else
        DetectTrackerCount = 4
    End If
End Function

Private Sub AddTracker(ByVal dict As Object, ByVal trackerNo As Long)
    If Not dict.Exists(CStr(trackerNo)) Then dict.Add CStr(trackerNo), True
End Sub

'============================================================
' Summary
'============================================================
Private Sub WriteSummaryHeader(ByVal ws As Worksheet)
    ws.Range("A1:I1").Value = Array("File Index", "File Name", "Full Path", "Rows", "Trackers", _
                                    "Signal/Noise", "Blocks", "Max SNR", "Min SNR")
    ws.Rows(1).Font.Bold = True
End Sub

Private Sub WriteSummaryRow(ByVal ws As Worksheet, ByVal fileIndex As Long, ByVal filePath As String, _
                            ByVal rowCount As Long, ByVal trackerCount As Long, ByVal hasSignalNoise As Boolean, _
                            ByVal blockCount As Long)
    Dim r As Long
    r = ws.Cells(ws.Rows.Count, "A").End(xlUp).Row + 1
    ws.Cells(r, 1).Value = fileIndex
    ws.Cells(r, 2).Value = FileNameOnly(filePath)
    ws.Cells(r, 3).Value = filePath
    ws.Cells(r, 4).Value = rowCount
    ws.Cells(r, 5).Value = trackerCount
    ws.Cells(r, 6).Value = IIf(hasSignalNoise, "Detected", "Not detected")
    ws.Cells(r, 7).Value = blockCount
End Sub

Private Sub UpdateSummarySNRStats(ByVal wsSummary As Worksheet, ByVal wsData As Worksheet)
    Dim lastSummaryRow As Long
    Dim lastDataRow As Long
    Dim sr As Long, dr As Long
    Dim fileIndex As Long
    Dim snrVal As Variant
    Dim maxVal As Double, minVal As Double
    Dim firstVal As Boolean

    lastSummaryRow = wsSummary.Cells(wsSummary.Rows.Count, "A").End(xlUp).Row
    lastDataRow = wsData.Cells(wsData.Rows.Count, "A").End(xlUp).Row

    For sr = 2 To lastSummaryRow
        fileIndex = CLng(wsSummary.Cells(sr, 1).Value)
        firstVal = True
        For dr = 2 To lastDataRow
            If CLng(wsData.Cells(dr, 1).Value) = fileIndex Then
                snrVal = wsData.Cells(dr, 9).Value
                If IsNumeric(snrVal) And CDbl(snrVal) > 0 Then
                    If firstVal Then
                        maxVal = CDbl(snrVal)
                        minVal = CDbl(snrVal)
                        firstVal = False
                    Else
                        If CDbl(snrVal) > maxVal Then maxVal = CDbl(snrVal)
                        If CDbl(snrVal) < minVal Then minVal = CDbl(snrVal)
                    End If
                End If
            End If
        Next dr
        If Not firstVal Then
            wsSummary.Cells(sr, 8).Value = Round(maxVal, 1)
            wsSummary.Cells(sr, 9).Value = Round(minVal, 1)
        End If
    Next sr
End Sub

'============================================================
' Dashboard build
'============================================================
Private Sub BuildDashboard(ByVal wb As Workbook, ByVal wsDash As Worksheet, ByVal wsList As Worksheet, ByVal wsSummary As Worksheet)
    Dim fileCount As Long
    Dim i As Long
    Dim dd As DropDown
    Dim cb As CheckBox
    Dim btn As Button

    gInternalUpdate = True

    wsDash.Cells.Clear
    wsDash.Activate
    ActiveWindow.DisplayGridlines = False

    wsDash.Range("A1").Value = "Tracker SNR Report"
    wsDash.Range("A1").Font.Bold = True
    wsDash.Range("A1").Font.Size = 16

    wsDash.Columns("A:A").ColumnWidth = 12
    wsDash.Columns("B:B").ColumnWidth = 13
    wsDash.Columns("C:C").ColumnWidth = 11
    wsDash.Columns("D:D").ColumnWidth = 8
    wsDash.Columns("E:J").ColumnWidth = 10
    wsDash.Rows("1:14").RowHeight = 19

    fileCount = wsSummary.Cells(wsSummary.Rows.Count, "A").End(xlUp).Row - 1
    wsDash.Range(CELL_FILE_COUNT).Value = fileCount
    wsDash.Range(CELL_FILE_INDEX).Value = 1
    wsDash.Range(CELL_METRIC_INDEX).Value = 1
    wsDash.Range(CELL_BLOCK_INDEX).Value = 1
    wsDash.Columns("Z:Z").Hidden = True

    BuildStaticLists wsList, wsSummary

    wsDash.Range("A3").Value = "File"
    wsDash.Range("A4").Value = "Graph data"
    wsDash.Range("A5").Value = "Block"
    wsDash.Range("A7").Value = "Trackers"

    Set dd = wsDash.DropDowns.Add(wsDash.Range("B3").Left, wsDash.Range("B3").Top, 160, 20)
    dd.Name = "ddFile"
    dd.ListFillRange = "'" & SHEET_LIST & "'!$A$1:$A$" & fileCount
    dd.LinkedCell = wsDash.Range(CELL_FILE_INDEX).Address
    dd.OnAction = MacroRef("RefreshTrackerSNRBatchDashboard")
    dd.Value = 1

    Set dd = wsDash.DropDowns.Add(wsDash.Range("B4").Left, wsDash.Range("B4").Top, 100, 20)
    dd.Name = "ddMetric"
    dd.ListFillRange = "'" & SHEET_LIST & "'!$B$1:$B$3"
    dd.LinkedCell = wsDash.Range(CELL_METRIC_INDEX).Address
    dd.OnAction = MacroRef("RefreshTrackerSNRBatchDashboard")
    dd.Value = 1

    Set dd = wsDash.DropDowns.Add(wsDash.Range("B5").Left, wsDash.Range("B5").Top, 100, 20)
    dd.Name = "ddBlock"
    dd.ListFillRange = "'" & SHEET_LIST & "'!$C$1:$C$1"
    dd.LinkedCell = wsDash.Range(CELL_BLOCK_INDEX).Address
    dd.OnAction = MacroRef("RefreshTrackerSNRBatchDashboard")
    dd.Value = 1

    Set btn = wsDash.Buttons.Add(wsDash.Range("B7").Left, wsDash.Range("B7").Top, 96, 24)
    btn.Name = "btnAllOn"
    btn.Caption = "All ON"
    btn.OnAction = MacroRef("TrackerSNRBatch_AllOn")

    Set btn = wsDash.Buttons.Add(wsDash.Range("C7").Left, wsDash.Range("C7").Top, 96, 24)
    btn.Name = "btnAllOff"
    btn.Caption = "All OFF"
    btn.OnAction = MacroRef("TrackerSNRBatch_AllOff")

    For i = 0 To 5
        wsDash.Cells(9 + i, 1).Value = "T" & i
        Set cb = wsDash.CheckBoxes.Add(wsDash.Range("B" & (9 + i)).Left, wsDash.Range("B" & (9 + i)).Top + 1, 70, 16)
        cb.Name = "chkTracker_" & i
        cb.Caption = "Show"
        cb.Value = xlOn
        cb.OnAction = MacroRef("TrackerSNRBatch_TrackerChanged")
    Next i

    wsDash.Range("E2").Value = "Source"
    wsDash.Range("E3").Value = "Trackers"
    wsDash.Range("E4").Value = "Signal/Noise"
    wsDash.Range("E5").Value = "Blocks"
    wsDash.Range("E6").Value = "Matrix spec"
    wsDash.Range("E2:E6").Font.Bold = True

    wsDash.Range("E8").Value = "Selected Block SNR Matrix"
    wsDash.Range("E8").Font.Bold = True

    wsDash.ChartObjects.Add Left:=wsDash.Range("A16").Left, Top:=wsDash.Range("A16").Top, Width:=820, Height:=300
    wsDash.ChartObjects(1).Name = CHART_NAME

    wsDash.Range("A1:J36").Font.Name = "Calibri"
    wsDash.Range("A1:J36").Font.Size = 9

    gInternalUpdate = False
End Sub

Private Sub BuildStaticLists(ByVal wsList As Worksheet, ByVal wsSummary As Worksheet)
    Dim lastRow As Long
    Dim r As Long

    wsList.Cells.Clear
    lastRow = wsSummary.Cells(wsSummary.Rows.Count, "A").End(xlUp).Row

    For r = 2 To lastRow
        wsList.Cells(r - 1, 1).Value = wsSummary.Cells(r, 2).Value
    Next r

    wsList.Range("B1").Value = "SNR"
    wsList.Range("B2").Value = "Signal"
    wsList.Range("B3").Value = "Noise"
    wsList.Range("C1").Value = "Block 1"
End Sub

Private Sub UpdateDynamicDashboardLists(ByVal wb As Workbook, ByVal wsDash As Worksheet)
    Dim wsList As Worksheet
    Dim wsSummary As Worksheet
    Dim fileIndex As Long
    Dim blockCount As Long
    Dim hasSignal As Boolean
    Dim i As Long
    Dim metricMax As Long

    Set wsList = wb.Worksheets(SHEET_LIST)
    Set wsSummary = wb.Worksheets(SHEET_SUMMARY)

    fileIndex = SelectedFileIndex(wsDash)
    wsDash.Range(CELL_ACTUAL_FILE_ID).Value = SummaryLong(wsSummary, fileIndex, 1)
    blockCount = SummaryLong(wsSummary, fileIndex, 7)
    hasSignal = SummaryHasSignal(wsSummary, fileIndex)
    If blockCount < 1 Then blockCount = 1

    wsList.Columns("C").ClearContents
    For i = 1 To blockCount
        wsList.Cells(i, 3).Value = "Block " & i
    Next i

    wsDash.Range(CELL_BLOCK_COUNT).Value = blockCount
    wsDash.Range(CELL_TRACKER_COUNT).Value = SummaryLong(wsSummary, fileIndex, 5)
    wsDash.Range(CELL_HAS_SIGNAL).Value = IIf(hasSignal, 1, 0)

    On Error Resume Next
    wsDash.DropDowns("ddBlock").ListFillRange = "'" & SHEET_LIST & "'!$C$1:$C$" & blockCount
    wsDash.DropDowns("ddMetric").ListFillRange = "'" & SHEET_LIST & "'!$B$1:$B$" & IIf(hasSignal, 3, 1)
    On Error GoTo 0

    If CLng(Val(wsDash.Range(CELL_BLOCK_INDEX).Value)) < 1 Or _
       CLng(Val(wsDash.Range(CELL_BLOCK_INDEX).Value)) > blockCount Then
        wsDash.Range(CELL_BLOCK_INDEX).Value = 1
        On Error Resume Next
        wsDash.DropDowns("ddBlock").Value = 1
        On Error GoTo 0
    End If

    metricMax = IIf(hasSignal, 3, 1)
    If CLng(Val(wsDash.Range(CELL_METRIC_INDEX).Value)) < 1 Or _
       CLng(Val(wsDash.Range(CELL_METRIC_INDEX).Value)) > metricMax Then
        wsDash.Range(CELL_METRIC_INDEX).Value = 1
        On Error Resume Next
        wsDash.DropDowns("ddMetric").Value = 1
        On Error GoTo 0
    End If
End Sub

'============================================================
' Dashboard refresh and buttons
'============================================================
Public Sub RefreshTrackerSNRBatchDashboard()
    Dim wb As Workbook
    Dim wsDash As Worksheet
    Dim wsData As Worksheet
    Dim wsSummary As Worksheet

    If gInternalUpdate Then Exit Sub

    On Error GoTo SafeExit
    Set wb = ActiveWorkbook
    Set wsDash = wb.Worksheets(SHEET_DASH)
    Set wsData = wb.Worksheets(SHEET_DATA)
    Set wsSummary = wb.Worksheets(SHEET_SUMMARY)

    Application.ScreenUpdating = False
    gInternalUpdate = True
    UpdateDynamicDashboardLists wb, wsDash
    UpdateDashboardInfo wsDash, wsSummary
    UpdateTrackerCheckVisibility wsDash
    ResetTrackerCheckboxActions wsDash
    gInternalUpdate = False

    DrawSelectedBlockMatrix wsDash, wsData
    DrawTrackerChart wsDash, wsData

SafeExit:
    gInternalUpdate = False
    Application.ScreenUpdating = True
End Sub

Public Sub TrackerSNRBatch_AllOn()
    SetAllVisibleTrackers True
End Sub

Public Sub TrackerSNRBatch_AllOff()
    SetAllVisibleTrackers False
End Sub

Public Sub TrackerSNRBatch_TrackerChanged()
    'Called by each tracker checkbox.
    'Keep this macro separate from the generic refresh so the chart also refreshes
    'correctly after All OFF has cleared every tracker.
    gInternalUpdate = False
    RefreshTrackerSNRBatchDashboard
End Sub

Private Sub SetAllVisibleTrackers(ByVal turnOn As Boolean)
    Dim ws As Worksheet
    Dim cb As CheckBox

    Set ws = ActiveWorkbook.Worksheets(SHEET_DASH)
    gInternalUpdate = True
    For Each cb In ws.CheckBoxes
        If Left$(cb.Name, 11) = "chkTracker_" Then
            If cb.Visible Then cb.Value = IIf(turnOn, xlOn, xlOff)
        End If
    Next cb
    gInternalUpdate = False

    ResetTrackerCheckboxActions ws
    RefreshTrackerSNRBatchDashboard
End Sub

Private Sub UpdateDashboardInfo(ByVal wsDash As Worksheet, ByVal wsSummary As Worksheet)
    Dim fileIndex As Long
    fileIndex = SelectedFileIndex(wsDash)

    wsDash.Range("F2").Value = SummaryText(wsSummary, fileIndex, 2)
    wsDash.Range("F3").Value = SummaryLong(wsSummary, fileIndex, 5)
    wsDash.Range("F4").Value = SummaryText(wsSummary, fileIndex, 6)
    wsDash.Range("F5").Value = SummaryLong(wsSummary, fileIndex, 7)
    wsDash.Range("F6").Value = "Blue: >=100, Red: <100"
End Sub

Private Sub ResetTrackerCheckboxActions(ByVal wsDash As Worksheet)
    Dim cb As CheckBox
    On Error Resume Next
    For Each cb In wsDash.CheckBoxes
        If Left$(cb.Name, 11) = "chkTracker_" Then
            cb.OnAction = MacroRef("TrackerSNRBatch_TrackerChanged")
            cb.Enabled = True
        End If
    Next cb
    On Error GoTo 0
End Sub

Private Sub UpdateTrackerCheckVisibility(ByVal wsDash As Worksheet)
    Dim trackerCount As Long
    Dim i As Long
    Dim cb As CheckBox

    trackerCount = CLng(Val(wsDash.Range(CELL_TRACKER_COUNT).Value))
    If trackerCount < 1 Then trackerCount = 4

    For i = 0 To 5
        wsDash.Cells(9 + i, 1).Value = ""
        On Error Resume Next
        Set cb = wsDash.CheckBoxes("chkTracker_" & i)
        On Error GoTo 0
        If Not cb Is Nothing Then
            If i < trackerCount Then
                wsDash.Cells(9 + i, 1).Value = "T" & i
                cb.Visible = True
            Else
                cb.Visible = False
            End If
        End If
        Set cb = Nothing
    Next i
End Sub

'============================================================
' Matrix
'============================================================
Private Sub DrawSelectedBlockMatrix(ByVal wsDash As Worksheet, ByVal wsData As Worksheet)
    Dim fileIndex As Long
    Dim blockNo As Long
    Dim trackerCount As Long
    Dim t As Long, s As Long
    Dim v As Variant
    Dim startCell As Range
    Dim matrixRange As Range

    fileIndex = SelectedActualFileId(wsDash)
    blockNo = SelectedBlockNo(wsDash)
    trackerCount = CLng(Val(wsDash.Range(CELL_TRACKER_COUNT).Value))
    If trackerCount < 1 Then trackerCount = 4

    Set startCell = wsDash.Range("E9")
    wsDash.Range("E9:J15").Clear

    startCell.Value = "Tracker / Scan"
    For s = 0 To 3
        startCell.Offset(0, 1 + s).Value = "Scan" & s
    Next s

    For t = 0 To trackerCount - 1
        startCell.Offset(1 + t, 0).Value = "T" & t
        For s = 0 To 3
            v = GetBlockValue(wsData, fileIndex, blockNo, t, s, "SNR")
            If Not IsError(v) Then
                startCell.Offset(1 + t, 1 + s).Value = Round(CDbl(v), 1)
                ColorSpecCell startCell.Offset(1 + t, 1 + s), CDbl(v)
            End If
        Next s
    Next t

    Set matrixRange = wsDash.Range(startCell, startCell.Offset(trackerCount, 4))
    With matrixRange
        .Borders.LineStyle = xlContinuous
        .HorizontalAlignment = xlCenter
        .VerticalAlignment = xlCenter
        .Font.Size = 9
    End With
    wsDash.Range(startCell, startCell.Offset(0, 4)).Font.Bold = True
    wsDash.Range(startCell, startCell.Offset(0, 4)).Interior.Color = RGB(235, 242, 250)
    wsDash.Range(startCell.Offset(1, 0), startCell.Offset(trackerCount, 0)).Font.Bold = True
End Sub

Private Sub ColorSpecCell(ByVal c As Range, ByVal valueNum As Double)
    If valueNum >= SPEC_SNR Then
        c.Font.Color = RGB(0, 70, 180)
    Else
        c.Font.Color = RGB(190, 0, 0)
    End If
End Sub

'============================================================
' Chart
'============================================================
Private Sub DrawTrackerChart(ByVal wsDash As Worksheet, ByVal wsData As Worksheet)
    Dim chartObj As ChartObject
    Dim ch As Chart
    Dim metricName As String
    Dim fileIndex As Long
    Dim blockNo As Long
    Dim trackerCount As Long
    Dim t As Long
    Dim s As Long
    Dim xVals(1 To 4) As String
    Dim yVals(1 To 4) As Variant
    Dim v As Variant
    Dim selectedAny As Boolean
    Dim firstVal As Boolean
    Dim minV As Double
    Dim maxV As Double

    metricName = SelectedMetric(wsDash)
    fileIndex = SelectedActualFileId(wsDash)
    blockNo = SelectedBlockNo(wsDash)
    trackerCount = CLng(Val(wsDash.Range(CELL_TRACKER_COUNT).Value))
    If trackerCount < 1 Then trackerCount = 4

    Set chartObj = wsDash.ChartObjects(CHART_NAME)
    chartObj.Visible = True
    Set ch = chartObj.Chart

    Do While ch.SeriesCollection.Count > 0
        ch.SeriesCollection(1).Delete
    Loop

    ch.ChartType = xlLineMarkers
    ch.HasTitle = True
    ch.ChartTitle.Text = metricName & " by Tracker - Block " & blockNo
    ch.HasLegend = True
    ch.Legend.Position = xlLegendPositionBottom

    For s = 1 To 4
        xVals(s) = "Scan" & (s - 1)
    Next s

    firstVal = True
    selectedAny = False

    For t = 0 To trackerCount - 1
        If IsTrackerChecked(wsDash, t) Then
            selectedAny = True
            For s = 0 To 3
                v = GetBlockValue(wsData, fileIndex, blockNo, t, s, metricName)
                If IsError(v) Then
                    yVals(s + 1) = CVErr(xlErrNA)
                Else
                    yVals(s + 1) = CDbl(v)
                    If firstVal Then
                        minV = CDbl(v)
                        maxV = CDbl(v)
                        firstVal = False
                    Else
                        If CDbl(v) < minV Then minV = CDbl(v)
                        If CDbl(v) > maxV Then maxV = CDbl(v)
                    End If
                End If
            Next s

            With ch.SeriesCollection.NewSeries
                .Name = "T" & t
                .XValues = xVals
                .Values = yVals
                .MarkerStyle = xlMarkerStyleCircle
                .MarkerSize = 5
            End With
        End If
    Next t

    If Not selectedAny Or firstVal Then
        ch.HasTitle = True
        If Not selectedAny Then
            ch.ChartTitle.Text = "No tracker selected"
        Else
            ch.ChartTitle.Text = "No data for selected block"
        End If
        ch.HasLegend = False
        AddBlankSeries ch
    Else
        ScaleValueAxis ch, minV, maxV
    End If

    On Error Resume Next
    ch.Axes(xlCategory).HasTitle = True
    ch.Axes(xlCategory).AxisTitle.Text = "Scan"
    ch.Axes(xlValue).HasTitle = True
    ch.Axes(xlValue).AxisTitle.Text = metricName
    On Error GoTo 0
End Sub

Private Sub AddBlankSeries(ByVal ch As Chart)
    Dim xVals(1 To 4) As String
    Dim yVals(1 To 4) As Variant
    Dim i As Long

    For i = 1 To 4
        xVals(i) = "Scan" & (i - 1)
        yVals(i) = CVErr(xlErrNA)
    Next i

    With ch.SeriesCollection.NewSeries
        .Name = ""
        .XValues = xVals
        .Values = yVals
    End With
End Sub

Private Sub ScaleValueAxis(ByVal ch As Chart, ByVal minV As Double, ByVal maxV As Double)
    Dim span As Double
    Dim pad As Double

    span = maxV - minV
    If span = 0 Then span = Abs(maxV) * 0.1
    If span = 0 Then span = 1
    pad = span * 0.12

    With ch.Axes(xlValue)
        .MinimumScaleIsAuto = False
        .MaximumScaleIsAuto = False
        .MinimumScale = WorksheetFunction.Max(0, minV - pad)
        .MaximumScale = maxV + pad
    End With
End Sub

Private Function GetBlockValue(ByVal wsData As Worksheet, ByVal fileIndex As Long, ByVal blockNo As Long, _
                               ByVal trackerNo As Long, ByVal scanNo As Long, ByVal metricName As String) As Variant
    Dim colNo As Long
    Dim v As Variant

    Select Case UCase$(metricName)
        Case "SIGNAL"
            colNo = 7
            GetBlockValue = FindBlockValueBySource(wsData, fileIndex, blockNo, trackerNo, scanNo, colNo, "SIGNAL")
        Case "NOISE"
            colNo = 8
            GetBlockValue = FindBlockValueBySource(wsData, fileIndex, blockNo, trackerNo, scanNo, colNo, "SIGNAL")
        Case Else
            colNo = 9
            'For SNR, use Signal source first when it exists, but fall back to PEAK.
            'This prevents Tracker 0 from disappearing when one source has missing rows.
            v = FindBlockValueBySource(wsData, fileIndex, blockNo, trackerNo, scanNo, colNo, "SIGNAL")
            If IsError(v) Then v = FindBlockValueBySource(wsData, fileIndex, blockNo, trackerNo, scanNo, colNo, "PEAK")
            GetBlockValue = v
    End Select
End Function

Private Function FindBlockValueBySource(ByVal wsData As Worksheet, ByVal fileIndex As Long, ByVal blockNo As Long, _
                                        ByVal trackerNo As Long, ByVal scanNo As Long, ByVal colNo As Long, _
                                        ByVal sourceType As String) As Variant
    Dim lastRow As Long
    Dim r As Long
    Dim v As Variant

    lastRow = wsData.Cells(wsData.Rows.Count, "A").End(xlUp).Row
    For r = 2 To lastRow
        If CLng(Val(wsData.Cells(r, 1).Value)) = fileIndex And _
           CLng(Val(wsData.Cells(r, 6).Value)) = blockNo And _
           CLng(Val(wsData.Cells(r, 4).Value)) = trackerNo And _
           CLng(Val(wsData.Cells(r, 5).Value)) = scanNo And _
           StrComp(CStr(wsData.Cells(r, 13).Value), sourceType, vbTextCompare) = 0 Then
            v = wsData.Cells(r, colNo).Value
            If IsNumeric(v) And CDbl(v) > 0 Then
                FindBlockValueBySource = CDbl(v)
                Exit Function
            End If
        End If
    Next r

    FindBlockValueBySource = CVErr(xlErrNA)
End Function

Private Function FileHasSignalData(ByVal wsData As Worksheet, ByVal fileIndex As Long) As Boolean
    Dim lastRow As Long
    Dim r As Long
    lastRow = wsData.Cells(wsData.Rows.Count, "A").End(xlUp).Row
    For r = 2 To lastRow
        If CLng(Val(wsData.Cells(r, 1).Value)) = fileIndex Then
            If StrComp(CStr(wsData.Cells(r, 13).Value), "SIGNAL", vbTextCompare) = 0 Then
                FileHasSignalData = True
                Exit Function
            End If
        End If
    Next r
End Function

'============================================================
' Selection helpers
'============================================================
Private Function SelectedFileIndex(ByVal wsDash As Worksheet) As Long
    Dim v As Long
    v = CLng(Val(wsDash.Range(CELL_FILE_INDEX).Value))
    If v < 1 Then v = 1
    If v > CLng(Val(wsDash.Range(CELL_FILE_COUNT).Value)) Then v = CLng(Val(wsDash.Range(CELL_FILE_COUNT).Value))
    SelectedFileIndex = v
End Function

Private Function SelectedActualFileId(ByVal wsDash As Worksheet) As Long
    Dim v As Long
    v = CLng(Val(wsDash.Range(CELL_ACTUAL_FILE_ID).Value))
    If v < 1 Then v = SelectedFileIndex(wsDash)
    SelectedActualFileId = v
End Function

Private Function SelectedMetric(ByVal wsDash As Worksheet) As String
    Select Case CLng(Val(wsDash.Range(CELL_METRIC_INDEX).Value))
        Case 2: SelectedMetric = "Signal"
        Case 3: SelectedMetric = "Noise"
        Case Else: SelectedMetric = "SNR"
    End Select
End Function

Private Function SelectedBlockNo(ByVal wsDash As Worksheet) As Long
    Dim v As Long
    Dim maxBlock As Long
    v = CLng(Val(wsDash.Range(CELL_BLOCK_INDEX).Value))
    maxBlock = CLng(Val(wsDash.Range(CELL_BLOCK_COUNT).Value))
    If maxBlock < 1 Then maxBlock = 1
    If v < 1 Then v = 1
    If v > maxBlock Then v = maxBlock
    SelectedBlockNo = v
End Function

Private Function IsTrackerChecked(ByVal wsDash As Worksheet, ByVal trackerNo As Long) As Boolean
    On Error GoTo NotFound
    IsTrackerChecked = (wsDash.CheckBoxes("chkTracker_" & trackerNo).Value = xlOn)
    Exit Function
NotFound:
    IsTrackerChecked = False
End Function

Private Function SummaryText(ByVal wsSummary As Worksheet, ByVal fileIndex As Long, ByVal colNo As Long) As String
    Dim r As Long
    r = fileIndex + 1
    SummaryText = CStr(wsSummary.Cells(r, colNo).Value)
End Function

Private Function SummaryLong(ByVal wsSummary As Worksheet, ByVal fileIndex As Long, ByVal colNo As Long) As Long
    Dim r As Long
    r = fileIndex + 1
    SummaryLong = CLng(Val(wsSummary.Cells(r, colNo).Value))
End Function

Private Function SummaryHasSignal(ByVal wsSummary As Worksheet, ByVal fileIndex As Long) As Boolean
    SummaryHasSignal = (StrComp(SummaryText(wsSummary, fileIndex, 6), "Detected", vbTextCompare) = 0)
End Function

'============================================================
' Parsing helpers
'============================================================
Private Function IsPeakSNRDataLine(ByVal s As String) As Boolean
    ' Accept both the original exact header and slightly different PEAK log wording.
    ' Exclude Signal/Noise result rows such as:
    '   SNR: tracker 0 peak signal: ... noise: ... SNR: ...
    ' Those rows are handled by IsSignalNoiseDataLine.
    If InStr(1, s, "signal", vbTextCompare) > 0 And InStr(1, s, "noise", vbTextCompare) > 0 Then Exit Function

    If InStr(1, s, "TRACKER PEAK LOG", vbTextCompare) > 0 Then
        If Not IsEmpty(ExtractLastNamedNumber(s, "snr")) Then IsPeakSNRDataLine = True
        Exit Function
    End If

    If InStr(1, s, "peak", vbTextCompare) = 0 Then Exit Function
    If InStr(1, s, "snr", vbTextCompare) = 0 Then Exit Function
    If IsEmpty(ExtractTrackerNumber(s)) Then Exit Function
    If IsEmpty(ExtractLastNamedNumber(s, "snr")) Then Exit Function
    IsPeakSNRDataLine = True
End Function

Private Function IsSignalNoiseDataLine(ByVal s As String) As Boolean
    ' Support multiple variants seen in logs:
    '   SNR: tracker 0 signal: ... noise: ... snr: ...
    '   SNR noise of tracker signal ...
    '   SNR noise of traders signal ...
    If InStr(1, s, "signal", vbTextCompare) = 0 Then Exit Function
    If InStr(1, s, "noise", vbTextCompare) = 0 Then Exit Function
    If InStr(1, s, "snr", vbTextCompare) = 0 Then Exit Function

    If InStr(1, s, "tracker", vbTextCompare) = 0 And _
       InStr(1, s, "track", vbTextCompare) = 0 And _
       InStr(1, s, "trader", vbTextCompare) = 0 Then Exit Function

    If IsEmpty(ExtractTrackerNumber(s)) Then Exit Function
    If IsEmpty(ExtractNamedNumber(s, "signal")) Then Exit Function
    If IsEmpty(ExtractNamedNumber(s, "noise")) Then Exit Function
    If IsEmpty(ExtractNamedNumber(s, "snr")) Then Exit Function
    IsSignalNoiseDataLine = True
End Function

Private Function ExtractTimeText(ByVal s As String) As String
    Dim v As Variant
    v = ExtractTextByRegex(s, "(^|\s)([0-9]{1,2}:[0-9]{2}:[0-9]{2}[:.][0-9]{1,3})")
    If IsEmpty(v) Then
        ExtractTimeText = ""
    Else
        ExtractTimeText = Replace(CStr(v), ".", ":")
    End If
End Function

Private Function ExtractTrackerNumber(ByVal s As String) As Variant
    Dim v As Variant

    v = ExtractNumberByRegex(s, "\btracker\s*#?\s*[:=]?\s*([0-9]+)")
    If IsEmpty(v) Then v = ExtractNumberByRegex(s, "\btrack\s*#?\s*[:=]?\s*([0-9]+)")
    If IsEmpty(v) Then v = ExtractNumberByRegex(s, "\btrader[s]?\s*#?\s*[:=]?\s*([0-9]+)")
    If IsEmpty(v) Then v = ExtractNumberByRegex(s, "\btracker\D{0,20}([0-9]+)")
    If IsEmpty(v) Then v = ExtractNumberByRegex(s, "\btrack\D{0,20}([0-9]+)")
    If IsEmpty(v) Then v = ExtractNumberByRegex(s, "\btrader[s]?\D{0,20}([0-9]+)")

    ExtractTrackerNumber = v
End Function

Private Function ExtractNamedNumber(ByVal s As String, ByVal nameText As String) As Variant
    Dim v As Variant

    'Use strict label extraction only.  A previous flexible pattern could read the
    'tracker number after the first "SNR:" as the SNR value, so valid Signal/Noise
    'rows were discarded as SNR = 0.
    v = ExtractNumberByRegex(s, "\b" & EscapeRegex(nameText) & "\b\s*[:=]?\s*(-?[0-9]+(?:\.[0-9]+)?)")
    ExtractNamedNumber = v
End Function

Private Function ExtractLastNamedNumber(ByVal s As String, ByVal nameText As String) As Variant
    'For SNR rows the line can start with "SNR:" and later contain the real "SNR: 680.20".
    'This function returns the last numeric value with the requested label.
    Dim re As Object
    Dim matches As Object
    Dim m As Object
    Set re = CreateObject("VBScript.RegExp")
    re.Pattern = "\b" & EscapeRegex(nameText) & "\b\s*[:=]?\s*(-?[0-9]+(?:\.[0-9]+)?)"
    re.IgnoreCase = True
    re.Global = True

    If re.Test(s) Then
        Set matches = re.Execute(s)
        Set m = matches(matches.Count - 1)
        ExtractLastNamedNumber = CDbl(m.SubMatches(m.SubMatches.Count - 1))
    Else
        ExtractLastNamedNumber = Empty
    End If
End Function

Private Function ExtractFirstOf(ByVal s As String, ByVal names As Variant) As Variant
    Dim i As Long
    Dim v As Variant
    For i = LBound(names) To UBound(names)
        v = ExtractNamedNumber(s, CStr(names(i)))
        If Not IsEmpty(v) Then
            ExtractFirstOf = v
            Exit Function
        End If
    Next i
    ExtractFirstOf = Empty
End Function

Private Function ExtractNumberByRegex(ByVal s As String, ByVal pattern As String) As Variant
    Dim re As Object
    Dim m As Object
    Set re = CreateObject("VBScript.RegExp")
    re.Pattern = pattern
    re.IgnoreCase = True
    re.Global = False
    If re.Test(s) Then
        Set m = re.Execute(s)(0)
        ExtractNumberByRegex = CDbl(m.SubMatches(m.SubMatches.Count - 1))
    Else
        ExtractNumberByRegex = Empty
    End If
End Function

Private Function ExtractTextByRegex(ByVal s As String, ByVal pattern As String) As Variant
    Dim re As Object
    Dim m As Object
    Set re = CreateObject("VBScript.RegExp")
    re.Pattern = pattern
    re.IgnoreCase = True
    re.Global = False
    If re.Test(s) Then
        Set m = re.Execute(s)(0)
        ExtractTextByRegex = m.SubMatches(m.SubMatches.Count - 1)
    Else
        ExtractTextByRegex = Empty
    End If
End Function

Private Function EscapeRegex(ByVal s As String) As String
    Dim chars As Variant
    Dim i As Long
    chars = Array("\", ".", "+", "*", "?", "[", "^", "]", "$", "(", ")", "{", "}", "=", "!", "<", ">", "|", ":", "-")
    EscapeRegex = s
    For i = LBound(chars) To UBound(chars)
        EscapeRegex = Replace(EscapeRegex, chars(i), "\" & chars(i))
    Next i
End Function

Private Function IsValidTrackerNumber(ByVal v As Variant) As Boolean
    If IsEmpty(v) Then Exit Function
    If Not IsNumeric(v) Then Exit Function
    IsValidTrackerNumber = (CLng(v) >= 0)
End Function

Private Function IsPositiveNumber(ByVal v As Variant) As Boolean
    If IsEmpty(v) Then Exit Function
    If Not IsNumeric(v) Then Exit Function
    IsPositiveNumber = (CDbl(v) > 0)
End Function

'============================================================
' Workbook / file helpers
'============================================================
Private Function SaveReportWorkbook(ByVal wb As Workbook, ByVal outPath As String) As Boolean
    On Error GoTo SaveFailed
    wb.SaveAs Filename:=outPath, FileFormat:=xlOpenXMLWorkbook, CreateBackup:=False
    SaveReportWorkbook = True
    Exit Function
SaveFailed:
    SaveReportWorkbook = False
End Function

Private Function WorkbookIsOpen(ByVal fullPath As String) As Boolean
    Dim wb As Workbook
    For Each wb In Application.Workbooks
        If StrComp(wb.FullName, fullPath, vbTextCompare) = 0 Then
            WorkbookIsOpen = True
            Exit Function
        End If
    Next wb
End Function

Private Function MacroRef(ByVal macroName As String) As String
    MacroRef = "'" & ThisWorkbook.Name & "'!" & macroName
End Function

Private Function FileNameOnly(ByVal fullPath As String) As String
    Dim p As Long
    p = InStrRev(fullPath, Application.PathSeparator)
    If p > 0 Then
        FileNameOnly = Mid$(fullPath, p + 1)
    Else
        FileNameOnly = fullPath
    End If
End Function

Private Function FileBaseName(ByVal fullPath As String) As String
    Dim s As String
    Dim p As Long
    s = FileNameOnly(fullPath)
    p = InStrRev(s, ".")
    If p > 0 Then s = Left$(s, p - 1)
    FileBaseName = s
End Function

Private Function SafeFileName(ByVal s As String) As String
    Dim badChars As Variant
    Dim i As Long
    badChars = Array("\", "/", ":", "*", "?", """", "<", ">", "|")
    SafeFileName = s
    For i = LBound(badChars) To UBound(badChars)
        SafeFileName = Replace(SafeFileName, badChars(i), "_")
    Next i
End Function
