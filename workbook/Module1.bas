Attribute VB_Name = "Module1"
Option Explicit

' Corrected Evaluate for "Usefulness of process workbook.xlsm".
' The 2017 macro read rows 1-10, scored column G twice, and never read
' column O ("Yes"). This replacement reads one "A" on each written
' question (rows 5-13, columns G-O) and uses the same verdicts as
' uselessness/evaluate.py. Import it over Module1, or paste the body
' into that module, then click the existing Evaluate button.

Public Sub Evaluate()
    Dim questionnaire As Worksheet
    Dim resultSheet As Worksheet
    Dim scores(1 To 9) As Integer
    Dim question As Integer
    Dim column As Integer
    Dim marks As Integer
    Dim total As Integer
    Dim score As Integer
    Dim result As String

    Set questionnaire = ThisWorkbook.Sheets(2)
    Set resultSheet = ThisWorkbook.Sheets(3)
    total = 0

    For question = 1 To 9
        marks = 0
        score = 0
        For column = 7 To 15
            If UCase$(Trim$(CStr(questionnaire.Cells(question + 4, column).Value))) = "A" Then
                marks = marks + 1
                score = column - 7
            End If
        Next column
        If marks <> 1 Then
            resultSheet.Range("I7").Value = _
                "Question " & question & " needs a single A between No and Yes."
            Exit Sub
        End If
        scores(question) = score
        total = total + score
    Next question

    If total > 30 Then
        result = "The Process can not be eliminated"
    Else
        result = "The Process can be eliminated!"
        If scores(1) > 5 Then
            result = result & " With consideration for impact on end user if step is removed"
        End If
        If scores(2) > 5 Then
            result = result & " With consideration for impact on other parties if step is removed"
        End If
        If scores(3) > 5 Then
            result = result & " With consideration for impact on problem that the step solved"
        End If
        If scores(4) < 5 Then
            result = result & " With consideration for removing redundant tasks"
        End If
        If scores(5) < 5 Then
            result = result & " With consideration for automation of the step"
        End If
        If scores(6) < 5 Then
            result = result & " With consideration for breaking this step down to further steps"
        End If
        If scores(7) > 5 Then
            result = result & " With consideration for Regulatory requirements"
        End If
        If scores(8) > 5 Then
            result = result & " With consideration for the effort involved in replacing this task"
        End If
        If scores(9) > 5 Then
            result = result & " With consideration for impact documentation, support and maintenance activity following removal."
        End If
    End If

    resultSheet.Range("I7").Value = result
End Sub
