; Script Inno Setup para instalar Perfut (Flask/SQLite)

#define MyAppName "Perfut"
#define MyAppVersion "1.5"
#define MyAppPublisher "Meu Nome/Empresa"
#define MyAppURL "https://www.example.com/"
#define MyAppExeName "perfut.exe"   ; o executável final que você gerou no dist
#define MyAppFolder "perfut_flask_sqlite"

[Setup]
; Identificação do app
AppId={{853B377C-D52B-4A70-81CA-C5AC30E86A04}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DisableProgramGroupPage=yes
OutputBaseFilename=PerfutSetup
Compression=lzma
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "portuguese"; MessagesFile: "compiler:Languages\Portuguese.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Copia toda a pasta perfut_flask_sqlite, mas ignora arquivos .iss
Source: "C:\Users\felipe.conceicao\Downloads\perfut_flask_sqlite\*"; DestDir: "{app}\{#MyAppFolder}"; \
    Flags: recursesubdirs ignoreversion; Excludes: "*.iss"

[Icons]
; Atalho no menu iniciar
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppFolder}\dist\{#MyAppExeName}"
; Atalho opcional na área de trabalho
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppFolder}\dist\{#MyAppExeName}"; Tasks: desktopicon

[Run]
; Executa após a instalação
Filename: "{app}\{#MyAppFolder}\dist\{#MyAppExeName}"; \
    Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent
