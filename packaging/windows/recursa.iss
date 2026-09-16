; Inno Setup script for Recursa (Windows installer).
; Built by .github/workflows/build.yml:  iscc /DAppVersion=9.5.0 packaging\windows\recursa.iss
; Installs per user (no administrator rights), adds a Start menu entry, an
; optional desktop shortcut and an uninstaller. The learner's progress lives in
; %USERPROFILE%\.nj_re_trainer and is never touched by install or uninstall.

#ifndef AppVersion
  #define AppVersion "9.5.0"
#endif

[Setup]
AppId={{6C5E6F2B-8F3A-4F0B-9E2D-2B7A5C1D9E41}
AppName=Recursa
AppVersion={#AppVersion}
AppVerName=Recursa {#AppVersion}
AppPublisher=Bear Properties Management LLC
DefaultDirName={localappdata}\Programs\Recursa
DefaultGroupName=Recursa
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=..\..\release
OutputBaseFilename=Recursa-Setup-{#AppVersion}-windows-x64
SetupIconFile=..\..\assets\recursa.ico
UninstallDisplayIcon={app}\Recursa.exe
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"

[Files]
Source: "..\..\dist\Recursa\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Recursa"; Filename: "{app}\Recursa.exe"
Name: "{group}\Uninstall Recursa"; Filename: "{uninstallexe}"
Name: "{userdesktop}\Recursa"; Filename: "{app}\Recursa.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\Recursa.exe"; Description: "Open Recursa now"; Flags: nowait postinstall skipifsilent
