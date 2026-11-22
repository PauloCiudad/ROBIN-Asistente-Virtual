; Instalador de ROBIN (Inno Setup 6). Se compila con packaging\build.ps1.
#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

[Setup]
AppId={{7E3B9C2A-5D41-4F8E-9A6B-2C7D1E0F4B85}
AppName=ROBIN
AppVersion={#AppVersion}
AppVerName=ROBIN {#AppVersion}
AppPublisher=Paulo Ciudad
AppPublisherURL=https://github.com/PauloCiudad/ROBIN-Asistente-Virtual
AppSupportURL=https://github.com/PauloCiudad/ROBIN-Asistente-Virtual/issues
DefaultDirName={localappdata}\Programs\ROBIN
DefaultGroupName=ROBIN
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\build\installer
OutputBaseFilename=ROBIN-Setup-{#AppVersion}
SetupIconFile=robin.ico
UninstallDisplayIcon={app}\ROBIN.exe
UninstallDisplayName=ROBIN — Asistente virtual
Compression=lzma2/ultra64
SolidCompression=yes
LZMAUseSeparateProcess=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "Crear un icono en el escritorio"; GroupDescription: "Accesos directos:"; Flags: unchecked
Name: "autostart"; Description: "Iniciar ROBIN al encender el PC"; GroupDescription: "Inicio:"

[Files]
Source: "..\build\dist\ROBIN\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\ROBIN"; Filename: "{app}\ROBIN.exe"; Comment: "Asistente virtual ROBIN"
Name: "{autodesktop}\ROBIN"; Filename: "{app}\ROBIN.exe"; Tasks: desktopicon

[Registry]
; Mismo valor que usa el ajuste "Iniciar con Windows" de la app.
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "ROBIN"; \
    ValueData: """{app}\ROBIN.exe"""; Flags: uninsdeletevalue; Tasks: autostart

[Run]
Filename: "{app}\ROBIN.exe"; Description: "Iniciar ROBIN ahora"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "{sys}\taskkill.exe"; Parameters: "/IM ROBIN.exe /F /T"; Flags: runhidden; RunOnceId: "CerrarROBIN"

[Code]
// Cierra ROBIN (y su runtime de Codex) antes de instalar/actualizar para poder reemplazar los archivos.
function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  ResultCode: Integer;
begin
  Exec(ExpandConstant('{sys}\taskkill.exe'), '/IM ROBIN.exe /F /T', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Result := '';
end;

[Messages]
spanish.WelcomeLabel2=Se instalará ROBIN {#AppVersion}, tu asistente virtual de escritorio.%n%nLa primera vez te pedirá iniciar sesión con tu cuenta de ChatGPT y descargará los modelos de voz (~250 MB).
