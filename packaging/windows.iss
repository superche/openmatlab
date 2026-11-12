#ifndef Version
  #define Version "0.0.2"
#endif
[Setup]
AppId=org.openmatlab.workbench
AppName=OpenMATLAB
AppVersion={#Version}
DefaultDirName={localappdata}\Programs\OpenMATLAB
DefaultGroupName=OpenMATLAB
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\dist\installers
OutputBaseFilename=OpenMATLAB-{#Version}-windows-x64-setup
Compression=lzma2
SolidCompression=yes
UninstallDisplayIcon={app}\OpenMATLAB.exe
[Files]
Source: "..\dist\OpenMATLAB\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{group}\OpenMATLAB"; Filename: "{app}\OpenMATLAB.exe"
[Run]
Filename: "{app}\OpenMATLAB.exe"; Description: "Launch OpenMATLAB"; Flags: nowait postinstall skipifsilent
