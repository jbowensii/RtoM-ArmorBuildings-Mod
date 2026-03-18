; ═══════════════════════════════════════════════════════════════════
; Inno Setup 6 configuration for RtoM Mod Tools
;
; Packages the PyInstaller exe + staged data files into a Windows
; installer.  Run build/build_release.py to generate everything
; automatically, or compile this .iss manually after staging.
;
; Prerequisites:
;   1. PyInstaller exe at: release\RtoMModTools.exe
;   2. Staged data at:     build\staging\
;   3. Inno Setup 6+ installed
; ═══════════════════════════════════════════════════════════════════

#define MyAppName "RtoM Mod Tools"
#define MyAppExeName "RtoMModTools.exe"
; Version is overridden by build_release.py via /D flag
#ifndef MyAppVersion
  #define MyAppVersion "1.1.0"
#endif
#define MyAppPublisher "TobiIchiro and Contributors"
#define MyAppURL "https://github.com/TobiIchiro/RtoM-ArmorBuildings-Mod"

[Setup]
AppId={{A7F3D2E1-8B4C-4E5A-9D6F-1C2B3A4E5F6D}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
DefaultDirName={localappdata}\RtoMModTools
DefaultGroupName={#MyAppName}
LicenseFile=..\..\LICENSE
OutputDir=..\..\release
OutputBaseFilename=RtoMModTools_Setup_v{#MyAppVersion}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
; Uncomment when app_icon.ico is available:
; SetupIconFile=..\..\assets\icons\app_icon.ico
DisableProgramGroupPage=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; ── Application executable ──
Source: "..\..\release\RtoMModTools.exe"; DestDir: "{app}"; Flags: ignoreversion

; ── Config template ──
Source: "..\..\config.ini.example"; DestDir: "{app}"; Flags: ignoreversion

; ── License ──
Source: "..\..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion

; ── Data files from staging ──
Source: "..\..\build\staging\data\*"; DestDir: "{app}\data"; Flags: ignoreversion recursesubdirs createallsubdirs

; ── Localization files from staging ──
Source: "..\..\build\staging\localization\*"; DestDir: "{app}\localization"; Flags: ignoreversion recursesubdirs createallsubdirs

; ── Documentation from staging ──
Source: "..\..\build\staging\docs\*"; DestDir: "{app}\docs"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
// Create config.ini from template on first install if it doesn't exist
procedure CurStepChanged(CurStep: TSetupStep);
var
  ConfigPath: String;
  ExamplePath: String;
begin
  if CurStep = ssPostInstall then
  begin
    ConfigPath := ExpandConstant('{app}\config.ini');
    ExamplePath := ExpandConstant('{app}\config.ini.example');
    if not FileExists(ConfigPath) then
    begin
      FileCopy(ExamplePath, ConfigPath, False);
    end;
  end;
end;
