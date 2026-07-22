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
Source: "..\dist\IMD\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

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
  StateDirPage: TInputDirWizardPage;
  SheetPage: TInputQueryWizardPage;

function DefaultUserFolder(SubFolder: String): String;
var
  UserProfile: String;
begin
  UserProfile := GetEnv('USERPROFILE');
  if UserProfile = '' then
    UserProfile := ExpandConstant('{userdocs}');
  Result := AddBackslash(UserProfile) + SubFolder;
end;

function YamlString(Value: String): String;
begin
  StringChangeEx(Value, '\', '/', True);
  StringChangeEx(Value, '"', '\"', True);
  Result := Value;
end;

function NL(): String;
begin
  Result := Chr(13) + Chr(10);
end;

function InitialConfig(MusicDir: String; StateDir: String; SheetUrl: String): String;
begin
  Result :=
    'source:' + NL() +
    '  google_sheet_csv: "' + SheetUrl + '"' + NL() +
    NL() +
    'paths:' + NL() +
    '  music_dir: "' + MusicDir + '"' + NL() +
    '  state_dir: "' + StateDir + '"' + NL() +
    NL() +
    'execution:' + NL() +
    '  reescan_list: false' + NL() +
    '  dry_run: false' + NL() +
    '  tagmusic: false' + NL() +
    '  tag_force: false' + NL() +
    '  only_row: null' + NL() +
    '  only_url: null' + NL() +
    '  log_level: "INFO"' + NL() +
    NL() +
    'network:' + NL() +
    '  disable_ssl_verify: false' + NL() +
    NL() +
    'audio:' + NL() +
    '  format: "mp3"' + NL() +
    '  quality: 320' + NL() +
    '  detect_bpm: false' + NL() +
    '  bpm_seconds: 20' + NL() +
    '  embed_metadata: false' + NL() +
    '  embed_thumbnail: false' + NL() +
    '  auto_tag_after_download: true' + NL() +
    '  auto_tag_force: false' + NL() +
    NL() +
    'conversion:' + NL() +
    '  enable: false' + NL() +
    '  conversion_only: false' + NL() +
    '  verbose: true' + NL() +
    '  music_dir: "' + MusicDir + '"' + NL() +
    '  source_format: "m4a"' + NL() +
    '  destination_format: "mp3"' + NL() +
    '  dry_run: true' + NL() +
    '  delete_source: false' + NL() +
    '  workers: 4' + NL() +
    '  ffmpeg_threads: 1' + NL() +
    NL() +
    'spotify:' + NL() +
    '  mode: "EMBED"' + NL() +
    '  embed_timeout_seconds: 20' + NL() +
    NL() +
    'history:' + NL() +
    '  mark_collection_done_with_failures: false' + NL() +
    '  max_failures_to_mark_done: 2' + NL() +
    NL() +
    'ytdlp:' + NL() +
    '  verbose: false' + NL() +
    '  format: "bestaudio/best"' + NL() +
    '  query_template: "{artist} {title} {term}"' + NL() +
    '  search_results: 3' + NL() +
    '  player_client: "android"' + NL() +
    '  player_clients:' + NL() +
    '    - "android"' + NL() +
    '    - "web"' + NL() +
    '    - "ios"' + NL() +
    '  concurrent_fragments: 8' + NL() +
    '  extractor_retries: 3' + NL() +
    '  remote_components:' + NL() +
    '    - "ejs:github"' + NL() +
    '  cookies_from_browser: null' + NL() +
    '  search_terms:' + NL() +
    '    - "extended"' + NL() +
    '    - "official audio"' + NL() +
    '    - "official music video"' + NL() +
    '    - "lyrics"' + NL() +
    '    - "audio"' + NL();
end;

procedure InitializeWizard;
begin
  MusicDirPage := CreateInputDirPage(
    wpSelectDir,
    'Pastas do IMD',
    'Escolha onde as musicas serao salvas.',
    'O instalador ja sugere uma pasta dentro do seu usuario do Windows. Voce pode manter assim e clicar em Avancar.',
    False,
    ''
  );
  MusicDirPage.Add('Pasta de musicas:');
  MusicDirPage.Values[0] := DefaultUserFolder('Music\IMD');

  StateDirPage := CreateInputDirPage(
    MusicDirPage.ID,
    'Arquivos de estado',
    'Escolha onde o IMD vai guardar historico, erros e cache.',
    'Recomendado: deixar separado da pasta de instalacao, dentro do seu usuario do Windows.',
    False,
    ''
  );
  StateDirPage.Add('Pasta de estado:');
  StateDirPage.Values[0] := DefaultUserFolder('Music\IMD-State');

  SheetPage := CreateInputQueryPage(
    StateDirPage.ID,
    'Planilha do Google',
    'Informe a URL CSV da sua planilha.',
    'Use o link de exportacao CSV do Google Sheets. Se preferir configurar depois pelo painel, deixe o valor sugerido.'
  );
  SheetPage.Add('URL CSV da planilha:', False);
  SheetPage.Values[0] := 'https://docs.google.com/spreadsheets/d/SEU_ID/export?format=csv&gid=0';
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  ConfigPath: String;
  MusicDir: String;
  MusicDirRaw: String;
  StateDir: String;
  StateDirRaw: String;
  SheetUrl: String;
begin
  if CurStep <> ssPostInstall then
    Exit;

  ConfigPath := ExpandConstant('{app}\config.yaml');

  if FileExists(ConfigPath) then begin
    Log('Config existente preservado durante a atualizacao: ' + ConfigPath);
    Exit;
  end;

  if WizardSilent then begin
    MusicDirRaw := DefaultUserFolder('Music\IMD');
    StateDirRaw := DefaultUserFolder('Music\IMD-State');
    SheetUrl := YamlString('https://docs.google.com/spreadsheets/d/SEU_ID/export?format=csv&gid=0');
  end else begin
    MusicDirRaw := MusicDirPage.Values[0];
    StateDirRaw := StateDirPage.Values[0];
    SheetUrl := YamlString(SheetPage.Values[0]);
  end;

  MusicDir := YamlString(MusicDirRaw);
  StateDir := YamlString(StateDirRaw);

  ForceDirectories(MusicDirRaw);
  ForceDirectories(StateDirRaw);

  SaveStringToFile(ConfigPath, InitialConfig(MusicDir, StateDir, SheetUrl), False);
end;

