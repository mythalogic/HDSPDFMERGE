; Inno Setup Script for HDS Route Sequencer
; This script creates a professional Windows installer (.exe)
; 
; REQUIREMENTS:
; - Download and install Inno Setup from: https://jrsoftware.org/isinfo.php
; 
; TO COMPILE:
; Option 1: Use Inno Setup GUI
;   - File > Compile
;   - Browse to this script
;   - Click Compile
;
; Option 2: Command line
;   "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" "path\to\installer.iss"

[Setup]
; Application information
AppName=HDS Route Sequencer
AppVersion=1.0.0
AppPublisher=Your Company Name
AppPublisherURL=https://yourcompany.com
AppSupportURL=https://yourcompany.com/support
AppUpdatesURL=https://yourcompany.com/download
AppCopyright=Copyright © 2026. All rights reserved.
AppComments=Professional PDF Route Sequencing & Merging Application

; Default installation location
DefaultDirName={commonpf}\HDS Route Sequencer
DefaultGroupName=HDS Route Sequencer

; Installer settings
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

; UI settings
WizardStyle=modern
DisableProgramGroupPage=no
UninstallDisplayIcon={app}\HDS_Route_Sequencer.exe
LicenseFile=LICENSE.txt

; Compression
Compression=lzma
SolidCompression=yes

; Output settings
OutputDir=.
OutputBaseFilename=HDS_Route_Sequencer_Setup

; Execution
PrivilegesRequired=lowest
ChangesEnvironment=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
; Create Desktop shortcut
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

; Create Quick Launch shortcut
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Main executable
Source: "..\dist\HDS_Route_Sequencer.exe"; DestDir: "{app}"; Flags: ignoreversion

; Documentation
Source: "README.txt"; DestDir: "{app}"; Flags: isreadme
Source: "LICENSE.txt"; DestDir: "{app}"; Flags: isreadme

; Create version file
Source: "VERSION.txt"; DestDir: "{app}"

[Icons]
; Start Menu shortcuts
Name: "{group}\HDS Route Sequencer"; Filename: "{app}\HDS_Route_Sequencer.exe"; \
    Comment: "Professional PDF Route Sequencing Application"; \
    IconFilename: "{app}\HDS_Route_Sequencer.exe"

Name: "{group}\{cm:UninstallProgram,HDS Route Sequencer}"; Filename: "{uninstallexe}"

; Desktop shortcut
Name: "{commondesktop}\HDS Route Sequencer"; Filename: "{app}\HDS_Route_Sequencer.exe"; \
    Comment: "Professional PDF Route Sequencing Application"; \
    IconFilename: "{app}\HDS_Route_Sequencer.exe"; \
    Tasks: desktopicon

; Quick Launch shortcut
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\HDS Route Sequencer"; \
    Filename: "{app}\HDS_Route_Sequencer.exe"; \
    Tasks: quicklaunchicon

[Run]
; Run application after installation
Filename: "{app}\HDS_Route_Sequencer.exe"; Description: "{cm:LaunchProgram,HDS Route Sequencer}"; Flags: nowait postinstall skipifsilent

[Registry]
; Add to Windows Programs list for uninstall
Root: HKLM; Subkey: "Software\Microsoft\Windows\CurrentVersion\Uninstall\HDS Route Sequencer"; \
    ValueType: string; ValueName: "DisplayName"; ValueData: "HDS Route Sequencer"

Root: HKLM; Subkey: "Software\Microsoft\Windows\CurrentVersion\Uninstall\HDS Route Sequencer"; \
    ValueType: string; ValueName: "DisplayVersion"; ValueData: "1.0.0"

Root: HKLM; Subkey: "Software\Microsoft\Windows\CurrentVersion\Uninstall\HDS Route Sequencer"; \
    ValueType: string; ValueName: "DisplayIcon"; ValueData: "{app}\HDS_Route_Sequencer.exe"

Root: HKLM; Subkey: "Software\Microsoft\Windows\CurrentVersion\Uninstall\HDS Route Sequencer"; \
    ValueType: string; ValueName: "Publisher"; ValueData: "Your Company Name"
