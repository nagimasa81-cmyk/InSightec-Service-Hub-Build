Option Explicit

'===============================================================================
' ReadPSClog_LogMergeReady_FIXED.bas
'
' Purpose:
'   Parse psc.log files encoded in UTF-8.
'   This version supports both formats below:
'     1) PscStates :: function_name : key = value
'     2) MRMAIL send/get/reply opcode=... seq=... status=... and other non-"::" rows
'
' Output:
'   Sheet 1: PSC_Log      - one row per log line with fixed columns and Param1..ParamN
'   Sheet 2: PSC_Params   - one row per extracted parameter, easier for LogMerge integration
'
' LogMerge integration entry point:
'   ImportPSCLogToWorkbook filePath, targetWorkbook
'   or
'   ImportPSCLogToSheets filePath, wsLog, wsParams
'===============================================================================

Private Const PSC_LOG_SHEET As String = "PSC_Log"
Private Const PSC_PARAM_SHEET As String = "PSC_Params"

Public Sub ParsePSCLog_Standalone_LogMergeReady()
    Dim filePath As String
    Dim wb As Workbook
    Dim defaultName As String
    Dim savePath As Variant
    Dim rowCount As Long

    With Application.FileDialog(msoFileDialogFilePicker)
        .Title = "Please select psc.log"
        .Filters.Clear
        .Filters.Add "Log Files", "*.log;*.txt"
        .AllowMultiSelect = False
        If .Show <> -1 Then Exit Sub
        filePath = .SelectedItems(1)
    End With

    Application.ScreenUpdating = False
    Application.EnableEvents = False

    Set wb = Workbooks.Add
    rowCount = ImportPSCLogToWorkbook(filePath, wb)

    defaultName = FileBaseName(filePath) & "_Parsed_" & Format(Now, "yyyymmdd_HHMMSS") & ".xlsx"
    savePath = Application.GetSaveAsFilename(defaultName, "Excel Files (*.xlsx), *.xlsx")

    If VarType(savePath) <> vbBoolean Then
        Application.DisplayAlerts = False
        wb.SaveAs CStr(savePath), xlOpenXMLWorkbook
        Application.DisplayAlerts = True
    End If

    Application.EnableEvents = True
    Application.ScreenUpdating = True

    MsgBox "PSC log parsing completed." & vbCrLf & _
           "Parsed log rows: " & rowCount, vbInformation
End Sub

Public Function ImportPSCLogToWorkbook(ByVal filePath As String, ByVal targetWorkbook As Workbook) As Long
    Dim wsLog As Worksheet
    Dim wsParams As Worksheet

    Set wsLog = GetOrCreateSheet(targetWorkbook, PSC_LOG_SHEET)
    Set wsParams = GetOrCreateSheet(targetWorkbook, PSC_PARAM_SHEET)

    wsLog.Cells.Clear
    wsParams.Cells.Clear

    WritePSCLogHeaders wsLog
    WritePSCParamHeaders wsParams

    ImportPSCLogToWorkbook = ImportPSCLogToSheets(filePath, wsLog, wsParams, 2, 2)
End Function

Public Function ImportPSCLogToSheets(ByVal filePath As String, _
                                     ByVal wsLog As Worksheet, _
                                     ByVal wsParams As Worksheet, _
                                     Optional ByVal startLogRow As Long = 2, _
                                     Optional ByVal startParamRow As Long = 2) As Long
    Dim fileContent As String
    Dim lines() As String
    Dim lineText As Variant
    Dim logRow As Long
    Dim paramRow As Long
    Dim parsedCount As Long
    Dim currentLogDate As String
    Dim maxParamCount As Long

    Dim sourceFile As String
    Dim rawLine As String
    Dim logTime As String
    Dim fullDateTime As String
    Dim processName As String
    Dim moduleName As String
    Dim functionName As String
    Dim messageText As String
    Dim rawParams As String
    Dim paramNames As Collection
    Dim paramValues As Collection
    Dim paramCount As Long
    Dim i As Long

    sourceFile = FileNameOnly(filePath)
    fileContent = ReadTextFileUTF8(filePath)
    fileContent = Replace(fileContent, vbCrLf, vbLf)
    fileContent = Replace(fileContent, vbCr, vbLf)
    lines = Split(fileContent, vbLf)

    logRow = startLogRow
    paramRow = startParamRow
    currentLogDate = ""
    maxParamCount = 0

    For Each lineText In lines
        rawLine = Trim(CStr(lineText))
        If Len(rawLine) = 0 Then GoTo ContinueLine

        If IsPSCDateHeader(rawLine) Then
            currentLogDate = NormalizePSCDateHeader(rawLine)
            GoTo ContinueLine
        End If

        Set paramNames = New Collection
        Set paramValues = New Collection
        logTime = ""
        fullDateTime = ""
        processName = ""
        moduleName = ""
        functionName = ""
        messageText = ""
        rawParams = ""

        If ParsePSCLogLine(rawLine, currentLogDate, logTime, fullDateTime, processName, _
                           moduleName, functionName, messageText, rawParams, paramNames, paramValues) Then
            paramCount = paramNames.Count
            If paramCount > maxParamCount Then maxParamCount = paramCount

            wsLog.Cells(logRow, 1).Value = sourceFile
            wsLog.Cells(logRow, 2).Value = currentLogDate
            wsLog.Cells(logRow, 3).Value = logTime
            wsLog.Cells(logRow, 4).Value = fullDateTime
            wsLog.Cells(logRow, 5).Value = processName
            wsLog.Cells(logRow, 6).Value = moduleName
            wsLog.Cells(logRow, 7).Value = functionName
            wsLog.Cells(logRow, 8).Value = messageText
            wsLog.Cells(logRow, 9).Value = rawParams
            wsLog.Cells(logRow, 10).Value = paramCount
            wsLog.Cells(logRow, 11).Value = rawLine

            For i = 1 To paramCount
                wsLog.Cells(logRow, 11 + i).Value = CStr(paramNames(i)) & "=" & CStr(paramValues(i))

                wsParams.Cells(paramRow, 1).Value = sourceFile
                wsParams.Cells(paramRow, 2).Value = currentLogDate
                wsParams.Cells(paramRow, 3).Value = logTime
                wsParams.Cells(paramRow, 4).Value = fullDateTime
                wsParams.Cells(paramRow, 5).Value = processName
                wsParams.Cells(paramRow, 6).Value = moduleName
                wsParams.Cells(paramRow, 7).Value = functionName
                wsParams.Cells(paramRow, 8).Value = CStr(paramNames(i))
                wsParams.Cells(paramRow, 9).Value = CStr(paramValues(i))
                wsParams.Cells(paramRow, 10).Value = messageText
                wsParams.Cells(paramRow, 11).Value = rawLine
                paramRow = paramRow + 1
            Next i

            logRow = logRow + 1
            parsedCount = parsedCount + 1
        End If

ContinueLine:
    Next lineText

    AddDynamicParamHeaders wsLog, maxParamCount
    FormatPSCSheets wsLog, wsParams

    ImportPSCLogToSheets = parsedCount
End Function

Private Function ParsePSCLogLine(ByVal rawLine As String, _
                                 ByVal currentLogDate As String, _
                                 ByRef logTime As String, _
                                 ByRef fullDateTime As String, _
                                 ByRef processName As String, _
                                 ByRef moduleName As String, _
                                 ByRef functionName As String, _
                                 ByRef messageText As String, _
                                 ByRef rawParams As String, _
                                 ByRef paramNames As Collection, _
                                 ByRef paramValues As Collection) As Boolean
    Dim firstSpace As Long
    Dim rest As String
    Dim closeBracket As Long
    Dim beforeDcolon As String
    Dim afterDcolon As String
    Dim colonPos As Long
    Dim moduleCandidate As String
    Dim temp As String

    firstSpace = InStr(1, rawLine, " ")
    If firstSpace <= 0 Then Exit Function

    logTime = Left$(rawLine, firstSpace - 1)
    If Not IsPSCTimeToken(logTime) Then Exit Function

    rest = Trim$(Mid$(rawLine, firstSpace + 1))

    If Left$(rest, 1) = "[" Then
        closeBracket = InStr(1, rest, "]")
        If closeBracket > 0 Then
            processName = Mid$(rest, 2, closeBracket - 2)
            rest = Trim$(Mid$(rest, closeBracket + 1))
        End If
    End If

    If Len(currentLogDate) > 0 Then
        fullDateTime = currentLogDate & " " & logTime
    Else
        fullDateTime = logTime
    End If

    messageText = rest

    If InStr(1, rest, "::", vbTextCompare) > 0 Then
        beforeDcolon = Trim$(Left$(rest, InStr(1, rest, "::", vbTextCompare) - 1))
        afterDcolon = Trim$(Mid$(rest, InStr(1, rest, "::", vbTextCompare) + 2))

        moduleName = beforeDcolon
        colonPos = InStr(1, afterDcolon, ":")
        If colonPos > 0 Then
            functionName = Trim$(Left$(afterDcolon, colonPos - 1))
            rawParams = Trim$(Mid$(afterDcolon, colonPos + 1))
        Else
            functionName = FirstToken(afterDcolon)
            rawParams = Trim$(Mid$(afterDcolon, Len(functionName) + 1))
        End If
    Else
        colonPos = InStr(1, rest, ":")
        If colonPos > 0 Then
            moduleCandidate = Trim$(Left$(rest, colonPos - 1))
            If Len(moduleCandidate) > 0 Then moduleName = moduleCandidate
            temp = Trim$(Mid$(rest, colonPos + 1))
            functionName = FirstToken(temp)
            rawParams = temp
        Else
            moduleName = FirstToken(rest)
            functionName = SecondToken(rest)
            rawParams = rest
        End If
    End If

    ExtractKeyValueParameters rest, paramNames, paramValues

    ParsePSCLogLine = True
End Function

Private Sub ExtractKeyValueParameters(ByVal textValue As String, _
                                      ByRef paramNames As Collection, _
                                      ByRef paramValues As Collection)
    Dim re As Object
    Dim matches As Object
    Dim m As Object
    Dim nameValue As String
    Dim valueText As String

    Set re = CreateObject("VBScript.RegExp")
    With re
        .Global = True
        .IgnoreCase = False
        .Pattern = "([A-Za-z_][A-Za-z0-9_\[\]\.]*)(\s*=\s*)(""[^""]*""|'[^']*'|[^\s;]*)"
    End With

    If re.Test(textValue) Then
        Set matches = re.Execute(textValue)
        For Each m In matches
            nameValue = CStr(m.SubMatches(0))
            valueText = CStr(m.SubMatches(2))
            valueText = TrimTrailingPunctuation(valueText)
            paramNames.Add nameValue
            paramValues.Add valueText
        Next m
    End If
End Sub

Private Function TrimTrailingPunctuation(ByVal valueText As String) As String
    valueText = Trim$(valueText)
    Do While Len(valueText) > 1 And Right$(valueText, 1) = "."
        If IsNumeric(Left$(valueText, Len(valueText) - 1)) Then
            valueText = Left$(valueText, Len(valueText) - 1)
        Else
            Exit Do
        End If
    Loop
    TrimTrailingPunctuation = valueText
End Function

Private Function IsPSCTimeToken(ByVal token As String) As Boolean
    Dim re As Object
    Set re = CreateObject("VBScript.RegExp")
    re.Pattern = "^\d{2}:\d{2}:\d{2}(\.\d+)?$"
    IsPSCTimeToken = re.Test(token)
End Function

Private Function IsPSCDateHeader(ByVal lineText As String) As Boolean
    Dim re As Object
    Set re = CreateObject("VBScript.RegExp")
    re.IgnoreCase = True
    re.Pattern = "^(Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2}\s+\d{4}$"
    IsPSCDateHeader = re.Test(lineText)
End Function

Private Function NormalizePSCDateHeader(ByVal lineText As String) As String
    On Error GoTo Fallback
    NormalizePSCDateHeader = Format$(CDate(Mid$(lineText, 5)), "yyyy-mm-dd")
    Exit Function
Fallback:
    NormalizePSCDateHeader = lineText
End Function

Private Function FirstToken(ByVal textValue As String) As String
    Dim parts() As String
    textValue = Trim$(textValue)
    If Len(textValue) = 0 Then Exit Function
    parts = Split(textValue, " ")
    FirstToken = Trim$(parts(0))
End Function

Private Function SecondToken(ByVal textValue As String) As String
    Dim parts() As String
    textValue = Trim$(textValue)
    If Len(textValue) = 0 Then Exit Function
    parts = Split(textValue, " ")
    If UBound(parts) >= 1 Then SecondToken = Trim$(parts(1))
End Function

Private Function ReadTextFileUTF8(ByVal filePath As String) As String
    Dim stream As Object
    Set stream = CreateObject("ADODB.Stream")
    With stream
        .Type = 2
        .Charset = "utf-8"
        .Open
        .LoadFromFile filePath
        ReadTextFileUTF8 = .ReadText
        .Close
    End With
End Function

Private Sub WritePSCLogHeaders(ByVal ws As Worksheet)
    ws.Cells(1, 1).Value = "SourceFile"
    ws.Cells(1, 2).Value = "LogDate"
    ws.Cells(1, 3).Value = "Time"
    ws.Cells(1, 4).Value = "DateTime"
    ws.Cells(1, 5).Value = "Process"
    ws.Cells(1, 6).Value = "Module"
    ws.Cells(1, 7).Value = "Function"
    ws.Cells(1, 8).Value = "Message"
    ws.Cells(1, 9).Value = "ParameterText"
    ws.Cells(1, 10).Value = "ParamCount"
    ws.Cells(1, 11).Value = "RawLine"
End Sub

Private Sub WritePSCParamHeaders(ByVal ws As Worksheet)
    ws.Cells(1, 1).Value = "SourceFile"
    ws.Cells(1, 2).Value = "LogDate"
    ws.Cells(1, 3).Value = "Time"
    ws.Cells(1, 4).Value = "DateTime"
    ws.Cells(1, 5).Value = "Process"
    ws.Cells(1, 6).Value = "Module"
    ws.Cells(1, 7).Value = "Function"
    ws.Cells(1, 8).Value = "ParameterName"
    ws.Cells(1, 9).Value = "ParameterValue"
    ws.Cells(1, 10).Value = "Message"
    ws.Cells(1, 11).Value = "RawLine"
End Sub

Private Sub AddDynamicParamHeaders(ByVal ws As Worksheet, ByVal maxParamCount As Long)
    Dim i As Long
    For i = 1 To maxParamCount
        ws.Cells(1, 11 + i).Value = "Param" & CStr(i)
    Next i
End Sub

Private Sub FormatPSCSheets(ByVal wsLog As Worksheet, ByVal wsParams As Worksheet)
    With wsLog
        .Rows(1).Font.Bold = True
        .Rows(1).AutoFilter
        .Columns.AutoFit
        .Columns("H:H").ColumnWidth = 60
        .Columns("K:K").ColumnWidth = 80
    End With

    With wsParams
        .Rows(1).Font.Bold = True
        .Rows(1).AutoFilter
        .Columns.AutoFit
        .Columns("J:J").ColumnWidth = 60
        .Columns("K:K").ColumnWidth = 80
    End With
End Sub

Private Function GetOrCreateSheet(ByVal wb As Workbook, ByVal sheetName As String) As Worksheet
    On Error Resume Next
    Set GetOrCreateSheet = wb.Worksheets(sheetName)
    On Error GoTo 0

    If GetOrCreateSheet Is Nothing Then
        Set GetOrCreateSheet = wb.Worksheets.Add(After:=wb.Worksheets(wb.Worksheets.Count))
        GetOrCreateSheet.Name = sheetName
    End If
End Function

Private Function FileNameOnly(ByVal filePath As String) As String
    FileNameOnly = Mid$(filePath, InStrRev(filePath, "\") + 1)
End Function

Private Function FileBaseName(ByVal filePath As String) As String
    Dim nameOnly As String
    nameOnly = FileNameOnly(filePath)
    If InStrRev(nameOnly, ".") > 0 Then
        FileBaseName = Left$(nameOnly, InStrRev(nameOnly, ".") - 1)
    Else
        FileBaseName = nameOnly
    End If
End Function
