; Voice Input 安装程序
#define MyAppName "Voice Input"
#define MyAppVersion "1.1.0"
#define MyAppExeName "VoiceInput.exe"

[Setup]
AppId={{B3E7F2A1-8D4C-4E9F-9A6D-2F5C8E7B1A3D}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2/ultra64
SolidCompression=yes
OutputDir=.\installer
OutputBaseFilename=VoiceInput_Setup_v{#MyAppVersion}
PrivilegesRequired=admin
MinVersion=10.0
DisableProgramGroupPage=yes
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=no
SetupIconFile=

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create desktop shortcut"; GroupDescription: "Shortcuts:"

[Files]
Source: "dist\VoiceInput.exe"; DestDir: "{app}"; Flags: ignoreversion
; SenseVoice 模型 (int8 量化, ~229 MB)
Source: "models\sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17\*"; DestDir: "{app}\models\sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17"; Flags: ignoreversion recursesubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Start Voice Input"; Flags: postinstall nowait skipifsilent shellexec
