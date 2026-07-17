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

[Files]
Source: "..\dist\IMD\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Criar atalho na area de trabalho"; GroupDescription: "Atalhos:"; Flags: unchecked

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

function InitialConfig(MusicDir: String; StateDir: String; SheetUrl: String): String;
begin
  Result :=
    'source:' + #13#10 +
    '  google_sheet_csv: "' + SheetUrl + '"' + #13#10 +
    #13#10 +
    'paths:' + #13#10 +
    '  music_dir: "' + MusicDir + '"' + #13#10 +
    '  state_dir: "' + StateDir + '"' + #13#10 +
    #13#10 +
    'execution:' + #13#10 +
    '  reescan_list: false' + #13#10 +
    '  dry_run: false' + #13#10 +
    '  tagmusic: false' + #13#10 +
    '  tag_force: false' + #13#10 +
    '  only_row: null' + #13#10 +
    '  only_url: null' + #13#10 +
    '  log_level: "INFO"' + #13#10 +
    #13#10 +
    'network:' + #13#10 +
    '  disable_ssl_verify: false' + #13#10 +
    #13#10 +
    'audio:' + #13#10 +
    '  format: "mp3"' + #13#10 +
    '  quality: 320' + #13#10 +
    '  detect_bpm: false' + #13#10 +
    '  bpm_seconds: 20' + #13#10 +
    '  embed_metadata: false' + #13#10 +
    '  embed_thumbnail: false' + #13#10 +
    '  auto_tag_after_download: true' + #13#10 +
    '  auto_tag_force: false' + #13#10 +
    #13#10 +
    'conversion:' + #13#10 +
    '  enable: false' + #13#10 +
    '  conversion_only: false' + #13#10 +
    '  verbose: true' + #13#10 +
    '  music_dir: "' + MusicDir + '"' + #13#10 +
    '  source_format: "m4a"' + #13#10 +
    '  destination_format: "mp3"' + #13#10 +
    '  dry_run: true' + #13#10 +
    '  delete_source: false' + #13#10 +
    '  workers: 4' + #13#10 +
    '  ffmpeg_threads: 1' + #13#10 +
    #13#10 +
    'spotify:' + #13#10 +
    '  mode: "EMBED"' + #13#10 +
    '  embed_timeout_seconds: 20' + #13#10 +
    '  artist_mode: "top_tracks"' + #13#10 +
    '  artist_market: "BR"' + #13#10 +
    '  artist_album_groups:' + #13#10 +
    '    - "album"' + #13#10 +
    '    - "single"' + #13#10 +
    '  artist_max_albums: null' + #13#10 +
    '  artist_max_tracks: null' + #13#10 +
    '  credentials_file: "spotify_secrets.yaml"' + #13#10 +
    '  client_id: null' + #13#10 +
    '  client_secret: null' + #13#10 +
    #13#10 +
    'history:' + #13#10 +
    '  mark_collection_done_with_failures: false' + #13#10 +
    '  max_failures_to_mark_done: 2' + #13#10 +
    #13#10 +
    'ytdlp:' + #13#10 +
    '  verbose: false' + #13#10 +
    '  format: "bestaudio/best"' + #13#10 +
    '  query_template: "{artist} {title} {term}"' + #13#10 +
    '  search_results: 3' + #13#10 +
    '  player_client: "android"' + #13#10 +
    '  player_clients:' + #13#10 +
    '    - "android"' + #13#10 +
    '    - "web"' + #13#10 +
    '    - "ios"' + #13#10 +
    '  concurrent_fragments: 8' + #13#10 +
    '  extractor_retries: 3' + #13#10 +
    '  remote_components:' + #13#10 +
    '    - "ejs:github"' + #13#10 +
    '  cookies_from_browser: null' + #13#10 +
    '  search_terms:' + #13#10 +
    '    - "extended"' + #13#10 +
    '    - "official audio"' + #13#10 +
    '    - "official music video"' + #13#10 +
    '    - "lyrics"' + #13#10 +
    '    - "audio"' + #13#10;
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
