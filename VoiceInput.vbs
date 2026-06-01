On Error Resume Next
Dim shell, fso, logFile, cmd
Set fso = CreateObject("Scripting.FileSystemObject")
Set logFile = fso.CreateTextFile(fso.GetParentFolderName(WScript.ScriptFullName) & "\debug.log", True)
logFile.WriteLine Now & " — Starting VoiceInput"

' 检查是否已有实例
Dim objWMIService, colProcesses, isRunning
isRunning = False
Set objWMIService = GetObject("winmgmts:\\.\root\cimv2")
Set colProcesses = objWMIService.ExecQuery("SELECT * FROM Win32_Process WHERE Name='pythonw.exe' AND CommandLine LIKE '%main.py%'")
If colProcesses.Count > 0 Then
    isRunning = True
    logFile.WriteLine Now & " — Instance already running, skipping"
End If

If Err.Number <> 0 Then
    logFile.WriteLine Now & " — WMI Error: " & Err.Description
    Err.Clear
End If

If Not isRunning Then
    Set shell = CreateObject("WScript.Shell")
    Dim appDir
    appDir = fso.GetParentFolderName(WScript.ScriptFullName)
    shell.CurrentDirectory = appDir
    logFile.WriteLine Now & " — WorkingDir: " & appDir
    
    ' 从注册表找 pythonw 路径
    Dim pythonwPath
    pythonwPath = ""
    On Error Resume Next
    pythonwPath = shell.RegRead("HKLM\SOFTWARE\Python\PythonCore\3.12\InstallPath\ExecutablePath")
    If pythonwPath = "" Then
        pythonwPath = shell.RegRead("HKCU\SOFTWARE\Python\PythonCore\3.12\InstallPath\ExecutablePath")
    End If
    If pythonwPath = "" Then
        ' 默认路径
        pythonwPath = "C:\Users\fei\AppData\Local\Programs\Python\Python312\pythonw.exe"
    Else
        pythonwPath = Replace(pythonwPath, "python.exe", "pythonw.exe")
    End If
    On Error Goto 0
    
    cmd = pythonwPath & " -u main.py"
    shell.Run cmd, 0, False
    logFile.WriteLine Now & " — Launched: " & cmd
End If

logFile.WriteLine Now & " — VBS finished"
logFile.Close
