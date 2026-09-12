; Inno Setup script for Acey Duecy.
;
; Build locally (after `pyinstaller AceyDuecy.spec`) with:
;   iscc installer.iss /DMyAppVersion=0.1.0
; (the CI/CD pipeline passes /DMyAppVersion from the git tag automatically)
;
; Produces installer_output\AceyDuecySetup-<version>.exe -- a normal
; Windows installer: license-free wizard, Start Menu + optional desktop
; shortcut, proper uninstaller registered in "Add or Remove Programs".
;
; Re-running a newer version's installer over an existing install upgrades
; it in place (same AppId below) without touching save data, because
; Paths.py keeps all of that in %APPDATA%\AceyDuecy, outside {app}.

#ifndef MyAppVersion
  #define MyAppVersion "0.0.0-dev"
#endif

#define MyAppName "Acey Duecy"
#define MyAppPublisher "Skunkard Studios"
#define MyAppExeName "AceyDuecy.exe"

[Setup]
; Fixed AppId so every version's installer is recognized as the same app
; for in-place upgrade/uninstall. Do not change this once shipped.
AppId={{B6C2E4B0-6E9A-4E7B-9C90-1ACE0DEC0001}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=installer_output
OutputBaseFilename=AceyDuecySetup-{#MyAppVersion}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
Source: "dist\AceyDuecy\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent
