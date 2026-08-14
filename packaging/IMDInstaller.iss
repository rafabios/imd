#define MyAppName "IMD Insane Music Downloader"
#define MyAppExeName "IMD.exe"
#define MyAppPublisher "IMD"
#define MyAppVersion GetEnv("PRODUCT_VERSION")

[Setup]
AppId={{7FBA81F6-19D2-461F-8BA2-657A5A2C696B}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\IMD Insane Music Downloader
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=..\dist
OutputBaseFilename=IMD-Insane-Music-Downloader-{#MyAppVersion}-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}
CloseApplications=yes
RestartApplications=no
SetupLogging=yes

[Files]
Source: "..\dist\IMD\*"; DestDir: "{app}"; Excludes: "config.yaml,spotify_secrets.yaml,runtime_updates\*,config_backups\*,imports\*,tasks\*"; Flags: ignoreversion recursesubdirs createallsubdirs

[InstallDelete]
Type: files; Name: "{app}\IMD.exe"
Type: filesandordirs; Name: "{app}\_internal"
Type: filesandordirs; Name: "{app}\web"
Type: filesandordirs; Name: "{app}\vendor"
Type: files; Name: "{app}\*.dll"
Type: files; Name: "{app}\*.pyd"
Type: files; Name: "{app}\*.manifest"
Type: files; Name: "{app}\base_library.zip"
Type: files; Name: "{app}\config.sample.yaml"
Type: files; Name: "{app}\spotify_secrets.sample.yaml"

[UninstallDelete]
Type: files; Name: "{app}\IMD.exe"
Type: filesandordirs; Name: "{app}\_internal"
Type: filesandordirs; Name: "{app}\web"
Type: filesandordirs; Name: "{app}\vendor"
Type: files; Name: "{app}\*.dll"
Type: files; Name: "{app}\*.pyd"
Type: files; Name: "{app}\*.manifest"
Type: files; Name: "{app}\base_library.zip"
Type: files; Name: "{app}\config.sample.yaml"
Type: files; Name: "{app}\spotify_secrets.sample.yaml"

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Criar atalho na area de trabalho"; GroupDescription: "Atalhos:"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Abrir o IMD agora"; Flags: nowait postinstall skipifsilent

[Code]
var
  MusicDirPage: TInputDirWizardPage;

function ExpandEnvironmentPath(Value: String): String;
var
  StartPos: Integer;
  EndOffset: Integer;
  VariableName: String;
  VariableValue: String;
  Tail: String;
begin
  Result := Value;
  while True do begin
    StartPos := Pos('%', Result);
    if StartPos = 0 then
      Break;
    Tail := Copy(Result, StartPos + 1, Length(Result));
    EndOffset := Pos('%', Tail);
    if EndOffset = 0 then
      Break;
    VariableName := Copy(Tail, 1, EndOffset - 1);
    VariableValue := GetEnv(VariableName);
    if VariableValue = '' then begin
      Result := '';
      Exit;
    end;
    Delete(Result, StartPos, EndOffset + 1);
    Insert(VariableValue, Result, StartPos);
  end;
end;

function DefaultMusicFolder(): String;
var
  MusicRoot: String;
  UserProfile: String;
begin
  MusicRoot := '';
  RegQueryStringValue(
    HKEY_CURRENT_USER,
    'Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders',
    'My Music',
    MusicRoot
  );
  MusicRoot := ExpandEnvironmentPath(MusicRoot);

  if MusicRoot = '' then begin
    UserProfile := GetEnv('USERPROFILE');
    if UserProfile <> '' then
      MusicRoot := AddBackslash(UserProfile) + 'Music'
    else
      MusicRoot := AddBackslash(ExtractFileDir(ExpandConstant('{userdocs}'))) + 'Music';
  end;

  Result := AddBackslash(MusicRoot) + 'IMD';
end;

function DefaultStateFolder(): String;
begin
  Result := ExpandConstant('{localappdata}\IMD Insane Music Downloader\state');
end;

function YamlString(Value: String): String;
begin
  StringChangeEx(Value, '\', '/', True);
  StringChangeEx(Value, '"', '\"', True);
  Result := Value;
end;

procedure InitialConfig(MusicDir: String; StateDir: String; var ConfigLines: TArrayOfString);
var
  I: Integer;
  SamplePath: String;
begin
  SamplePath := ExpandConstant('{app}\config.sample.yaml');
  if not LoadStringsFromFile(SamplePath, ConfigLines) then
    RaiseException('Nao foi possivel ler o modelo de configuracao: ' + SamplePath);

  for I := 0 to GetArrayLength(ConfigLines) - 1 do begin
    StringChangeEx(
      ConfigLines[I],
      'C:/Users/SEU_USUARIO/AppData/Local/IMD Insane Music Downloader/state',
      StateDir,
      True
    );
    StringChangeEx(ConfigLines[I], 'C:/Users/SEU_USUARIO/Music/IMD-State', StateDir, True);
    StringChangeEx(ConfigLines[I], 'C:/Users/SEU_USUARIO/Music/IMD', MusicDir, True);
  end;
end;

procedure InitializeWizard;
begin
  MusicDirPage := CreateInputDirPage(
    wpSelectDir,
    'Pasta de musicas',
    'Escolha onde as musicas serao salvas.',
    'O instalador usa a pasta Musicas real do seu Windows, mesmo quando ela foi traduzida ou movida. Voce pode manter a sugestao e clicar em Avancar.',
    False,
    ''
  );
  MusicDirPage.Add('Pasta de musicas:');
  MusicDirPage.Values[0] := DefaultMusicFolder();
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  ConfigPath: String;
  MusicDir: String;
  MusicDirRaw: String;
  StateDir: String;
  StateDirRaw: String;
  ConfigLines: TArrayOfString;
begin
  if CurStep <> ssPostInstall then
    Exit;

  ConfigPath := ExpandConstant('{app}\config.yaml');

  if FileExists(ConfigPath) then begin
    Log('Config existente preservado durante a atualizacao: ' + ConfigPath);
    Exit;
  end;

  if WizardSilent then begin
    MusicDirRaw := DefaultMusicFolder();
  end else begin
    MusicDirRaw := MusicDirPage.Values[0];
  end;
  StateDirRaw := DefaultStateFolder();

  MusicDir := YamlString(MusicDirRaw);
  StateDir := YamlString(StateDirRaw);

  ForceDirectories(MusicDirRaw);
  ForceDirectories(StateDirRaw);

  InitialConfig(MusicDir, StateDir, ConfigLines);
  if not SaveStringsToUTF8FileWithoutBOM(ConfigPath, ConfigLines, False) then
    RaiseException('Nao foi possivel criar o config.yaml em: ' + ConfigPath);
end;

