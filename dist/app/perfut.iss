; Inno Setup Script para instalar o Perfut

#define MyAppName "Perfut"
#define MyAppVersion "1.5"
#define MyAppPublisher "Felipe Conceição"
#define MyAppURL "https://www.example.com/"
#define MyAppExeName "app.exe"

[Setup]
; Identificação única do instalador (gerar novo GUID se necessário)
AppId={{853B377C-D52B-4A70-81CA-C5AC30E86A04}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
UninstallDisplayIcon={app}\{#MyAppExeName}
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
DisableProgramGroupPage=yes
OutputBaseFilename=PerfutSetup
Compression=lzma
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "portuguese"; MessagesFile: "compiler:Languages\Portuguese.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; \
    GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Inclui o executável principal
Source: "C:\Users\felipe.conceicao\Downloads\perfut_flask_sqlite\dist\app\app.exe"; \
    DestDir: "{app}"; Flags: ignoreversion

; Caso tenha banco de dados ou outros arquivos necessários, adicione aqui
; Exemplo:
; Source: "C:\Users\felipe.conceicao\Downloads\perfut_flask_sqlite\perft.db"; \
;   DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; \
    Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Iniciar {#MyAppName}"; \
    Flags: nowait postinstall skipifsilent
