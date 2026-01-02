#define MyAppName "BDC Generator"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "BDC-AUTO"
#define MyAppExeName "BDC Generator.exe"
#define MyAppDirName "BDC Generator"

[Setup]
AppId={{8D11B9C7-5D9A-4C70-9A62-0D2B5D1D1234}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\{#MyAppDirName}
DefaultGroupName={#MyAppName}
PrivilegesRequired=lowest
OutputDir=installer\Output
OutputBaseFilename=BDC_Generator_Setup
SetupLogging=yes
ArchitecturesInstallIn64BitMode=x64
DisableDirPage=yes
DisableProgramGroupPage=yes

[Languages]
Name: "french"; MessagesFile: "compiler:Languages\\French.isl"

[Files]
Source: "dist\\{#MyAppName}\\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "config.json"; DestDir: "{app}"; Flags: ignoreversion
; Copy template if available
Source: "assets\\bon de commande V1.pdf"; DestDir: "{userappdata}\\{#MyAppName}\\Templates"; Flags: ignoreversion; Check: FileExists(ExpandConstant('assets\\bon de commande V1.pdf'))

[Dirs]
Name: "{userappdata}\\{#MyAppName}\\Templates"; Flags: uninsalwaysuninstall
Name: "{userprofile}\\Desktop\\BDC_Output"; Flags: uninsneveruninstall

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\\{#MyAppExeName}"; Description: "Lancer {#MyAppName}"; Flags: nowait postinstall skipifsilent
