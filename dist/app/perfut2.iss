; Inno Setup Script para instalar Perfut Flask

#define MyAppName "Perfut"
#define MyAppVersion "1.0"
#define MyAppPublisher "Felipe Conceição"
#define MyAppExeName "start_app.bat"

[Setup]
AppId={{B74A44E7-3C77-4F9D-BF4E-1234567890AB}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DisableProgramGroupPage=yes
OutputDir=.
OutputBaseFilename=Perfut_Installer
Compression=lzma
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "portuguese"; MessagesFile: "compiler:Languages\Portuguese.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Copia toda a pasta perfut_flask_sqlite
Source: "C:\Users\felipe.conceicao\Downloads\perfut_flask_sqlite\*"; DestDir: "{app}\perfut_flask_sqlite"; Flags: recursesubdirs ignoreversion

[Icons]
; Atalho no menu iniciar
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\perfut_flask_sqlite\{#MyAppExeName}"
; Atalho na área de trabalho
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\perfut_flask_sqlite\{#MyAppExeName}"; Tasks: desktopicon

[Run]
; Executa o bat no final da instalação
Filename: "{app}\perfut_flask_sqlite\{#MyAppExeName}"; Description: "Abrir {#MyAppName}"; Flags: nowait postinstall skipifsilent
