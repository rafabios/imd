const healthEl = document.querySelector("#health");
const summaryEl = document.querySelector("#summary");
const validationEl = document.querySelector("#validation");
const configFormEl = document.querySelector("#config-form");
const saveStatusEl = document.querySelector("#save-status");
const saveButtonEl = document.querySelector("#save-config");
const reloadButtonEl = document.querySelector("#reload-config");
const configTabsEl = document.querySelector("#config-tabs");
const dangerWarningEl = document.querySelector("#danger-warning");
const startConversionEl = document.querySelector("#start-conversion");
const cancelConversionEl = document.querySelector("#cancel-conversion");
const conversionStatusEl = document.querySelector("#conversion-status");
const conversionStartedEl = document.querySelector("#conversion-started");
const conversionFinishedEl = document.querySelector("#conversion-finished");
const conversionLogEl = document.querySelector("#conversion-log");
const conversionLogFilterEl = document.querySelector("#conversion-log-filter");
const loadSheetEl = document.querySelector("#load-sheet");
const validateSheetEl = document.querySelector("#validate-sheet");
const downloadSelectedSheetEl = document.querySelector("#download-selected-sheet");
const sheetSearchEl = document.querySelector("#sheet-search");
const sheetTypeFilterEl = document.querySelector("#sheet-type-filter");
const sheetStatusEl = document.querySelector("#sheet-status");
const sheetIssuesEl = document.querySelector("#sheet-issues");
const sheetSummaryEl = document.querySelector("#sheet-summary");
const sheetRowsEl = document.querySelector("#sheet-rows");
const startDownloadEl = document.querySelector("#start-download");
const cancelDownloadEl = document.querySelector("#cancel-download");
const downloadSourceEl = document.querySelector("#download-source");
const downloadSourcePanels = Array.from(document.querySelectorAll("[data-download-source-panel]"));
const downloadReescanEl = document.querySelector("#download-reescan");
const downloadDryRunEl = document.querySelector("#download-dry-run");
const downloadTagmusicEl = document.querySelector("#download-tagmusic");
const downloadOnlyRowEl = document.querySelector("#download-only-row");
const downloadYoutubeArtistEl = document.querySelector("#download-youtube-artist");
const downloadYoutubeTitleEl = document.querySelector("#download-youtube-title");
const downloadYoutubeGenreEl = document.querySelector("#download-youtube-genre");
const downloadSpotifyArtistEl = document.querySelector("#download-spotify-artist");
const downloadSpotifyTitleEl = document.querySelector("#download-spotify-title");
const downloadSpotifyGenreEl = document.querySelector("#download-spotify-genre");
const downloadSpotifyUrlEl = document.querySelector("#download-spotify-url");
const downloadSpotifyUrlGenreEl = document.querySelector("#download-spotify-url-genre");
const downloadStatusEl = document.querySelector("#download-status");
const downloadStartedEl = document.querySelector("#download-started");
const downloadFinishedEl = document.querySelector("#download-finished");
const downloadLogEl = document.querySelector("#download-log");
const downloadLogFilterEl = document.querySelector("#download-log-filter");
const downloadProgressEl = document.querySelector("#download-progress");
const importFileEl = document.querySelector("#import-file");
const previewImportEl = document.querySelector("#preview-import");
const validateImportEl = document.querySelector("#validate-import");
const downloadImportEl = document.querySelector("#download-import");
const importStatusEl = document.querySelector("#import-status");
const importIssuesEl = document.querySelector("#import-issues");
const importSummaryEl = document.querySelector("#import-summary");
const importRowsEl = document.querySelector("#import-rows");
const refreshTasksEl = document.querySelector("#refresh-tasks");
const taskRowsEl = document.querySelector("#task-rows");
const checkEnvironmentEl = document.querySelector("#check-environment");
const environmentGridEl = document.querySelector("#environment-grid");
const refreshHistoryEl = document.querySelector("#refresh-history");
const retryFailuresEl = document.querySelector("#retry-failures");
const historySummaryEl = document.querySelector("#history-summary");
const historySearchEl = document.querySelector("#history-search");
const historyFileFilterEl = document.querySelector("#history-file-filter");
const historyLogEl = document.querySelector("#history-log");

let currentConfig = {};
let fieldTypes = new Map();
let activeConversionTaskId = null;
let conversionPollTimer = null;
let activeDownloadTaskId = null;
let downloadPollTimer = null;
let sheetRows = [];
let activeImportId = null;
let selectedSheetRows = new Set();
let conversionLogs = [];
let downloadLogs = [];
let historyData = null;

const labels = {
  music_dir: "Pasta das musicas",
  state_dir: "Pasta de estado",
  audio_format: "Formato de download",
  dry_run: "Modo teste",
  reescan_list: "Reescan",
  conversion_enabled: "Conversao ligada",
  conversion_only: "Apenas conversao",
  conversion: "Conversao",
  conversion_workers: "Conversoes paralelas",
  google_sheet_configured: "Google Sheets",
};

const selectOptions = {
  "audio.format": ["mp3", "m4a"],
  "execution.log_level": ["DEBUG", "INFO", "QUIET"],
  "spotify.mode": ["EMBED", "INDEX_ONLY", "YOUTUBE_ONLY", "OFF"],
  "spotify.artist_mode": ["top_tracks", "discography", "albums", "all"],
  "conversion.source_format": ["mp3", "m4a", "mp4", "flac", "wav", "ogg", "opus", "aac"],
  "conversion.destination_format": ["mp3", "m4a", "flac", "wav", "ogg", "opus", "aac"],
  "ytdlp.player_client": ["android", "web", "ios"],
  "ytdlp.cookies_from_browser": ["", "edge", "chrome", "firefox", "off"],
};

const fieldNames = {
  "source.google_sheet_csv": "URL da planilha",
  "paths.music_dir": "Pasta das musicas",
  "paths.state_dir": "Pasta de estado",
  "execution.reescan_list": "Reescan de playlists/artistas",
  "execution.dry_run": "Modo teste",
  "execution.tagmusic": "Apenas preencher metadados",
  "execution.only_row": "Linha especifica",
  "execution.only_url": "Link especifico",
  "execution.log_level": "Nivel de log",
  "audio.format": "Formato de download",
  "audio.quality": "Qualidade",
  "audio.auto_tag_after_download": "Preencher metadados apos baixar",
  "conversion.enable": "Conversao ligada",
  "conversion.conversion_only": "Somente conversao",
  "conversion.music_dir": "Pasta para converter",
  "conversion.source_format": "Formato de origem",
  "conversion.destination_format": "Formato de destino",
  "conversion.dry_run": "Simular conversao",
  "conversion.delete_source": "Apagar origem depois",
  "conversion.workers": "Conversoes em paralelo",
  "conversion.ffmpeg_threads": "Threads por arquivo",
  "spotify.mode": "Modo Spotify",
  "ytdlp.cookies_from_browser": "Cookies do navegador",
};

const basicFields = new Set([
  "source.google_sheet_csv",
  "paths.music_dir",
  "paths.state_dir",
  "execution.reescan_list",
  "execution.dry_run",
  "execution.only_row",
  "execution.only_url",
  "audio.format",
  "audio.quality",
  "audio.auto_tag_after_download",
  "conversion.enable",
  "conversion.conversion_only",
  "conversion.music_dir",
  "conversion.source_format",
  "conversion.destination_format",
  "conversion.dry_run",
  "conversion.delete_source",
  "conversion.workers",
]);

const numberFields = new Set([
  "audio.quality",
  "audio.bpm_seconds",
  "spotify.embed_timeout_seconds",
  "spotify.artist_max_albums",
  "spotify.artist_max_tracks",
  "history.max_failures_to_mark_done",
  "ytdlp.search_results",
  "ytdlp.concurrent_fragments",
  "ytdlp.extractor_retries",
  "conversion.workers",
  "conversion.ffmpeg_threads",
  "execution.only_row",
]);

function valueText(value) {
  if (value === true) return "Sim";
  if (value === false) return "Nao";
  if (value === null || value === undefined || value === "") return "Vazio";
  return String(value);
}

function friendlyError(error) {
  const message = error?.message || String(error);
  if (message.toLowerCase().includes("failed to fetch")) {
    return "Servidor local desconectado. Feche e abra o start_ui.bat de novo, deixe a janela aberta e depois atualize esta pagina.";
  }
  return message;
}

function fieldLabel(path) {
  return fieldNames[path] || path.split(".").slice(1).join(".");
}

function flattenConfig(data, prefix = "") {
  return Object.entries(data).flatMap(([key, value]) => {
    const dotted = prefix ? `${prefix}.${key}` : key;
    if (value && typeof value === "object" && !Array.isArray(value)) {
      return flattenConfig(value, dotted);
    }
    return [[dotted, value]];
  });
}

function setNested(target, path, value) {
  const parts = path.split(".");
  let cur = target;
  parts.slice(0, -1).forEach((part) => {
    if (!cur[part] || typeof cur[part] !== "object" || Array.isArray(cur[part])) {
      cur[part] = {};
    }
    cur = cur[part];
  });
  cur[parts[parts.length - 1]] = value;
}

function renderSummary(summary) {
  summaryEl.innerHTML = "";
  Object.entries(summary).forEach(([key, value]) => {
    const item = document.createElement("div");
    item.className = "metric";
    item.innerHTML = `<span>${labels[key] || key}</span><strong>${valueText(value)}</strong>`;
    summaryEl.appendChild(item);
  });
}

function renderValidation(validation) {
  validationEl.innerHTML = "";
  validation.messages.forEach((message) => {
    const item = document.createElement("li");
    item.className = validation.ok ? "" : "error";
    item.textContent = message;
    validationEl.appendChild(item);
  });
}

function inputTypeFor(path, value) {
  if (Array.isArray(value)) return "list";
  if (typeof value === "boolean") return "boolean";
  if (numberFields.has(path) || typeof value === "number") return "number";
  if (selectOptions[path]) return "select";
  return "text";
}

function createInput(path, value, type) {
  if (type === "boolean") {
    const input = document.createElement("input");
    input.type = "checkbox";
    input.checked = Boolean(value);
    input.dataset.path = path;
    return input;
  }

  if (type === "list") {
    const textarea = document.createElement("textarea");
    textarea.value = Array.isArray(value) ? value.join("\n") : "";
    textarea.dataset.path = path;
    return textarea;
  }

  if (type === "select") {
    const select = document.createElement("select");
    select.dataset.path = path;
    selectOptions[path].forEach((optionValue) => {
      const option = document.createElement("option");
      option.value = optionValue;
      option.textContent = optionValue || "null";
      select.appendChild(option);
    });
    select.value = value === null || value === undefined ? "" : String(value);
    return select;
  }

  const input = document.createElement("input");
  input.type = type === "number" ? "number" : "text";
  input.value = value === null || value === undefined ? "" : String(value);
  input.dataset.path = path;
  return input;
}

function renderConfigEditor(config) {
  currentConfig = config;
  fieldTypes = new Map();
  configFormEl.innerHTML = "";
  configTabsEl.innerHTML = "";

  const groups = [
    ["basico", "Básico", flattenConfig(config).filter(([path]) => basicFields.has(path))],
    ["avancado", "Avançado", flattenConfig(config).filter(([path]) => !basicFields.has(path))],
  ];

  groups.forEach(([sectionName, labelText, fieldsForSection]) => {
    const tab = document.createElement("button");
    tab.type = "button";
    tab.className = "tab-button";
    tab.dataset.section = sectionName;
    tab.textContent = labelText;
    tab.addEventListener("click", () => showConfigSection(sectionName));
    configTabsEl.appendChild(tab);

    const section = document.createElement("section");
    section.className = "config-section";
    section.dataset.section = sectionName;
    section.innerHTML = `<h3>${labelText}</h3>`;

    const fields = document.createElement("div");
    fields.className = "config-fields";

    fieldsForSection.forEach(([path, value]) => {
      const type = inputTypeFor(path, value);
      fieldTypes.set(path, type);

      const wrapper = document.createElement("div");
      wrapper.className = `config-field ${type === "boolean" ? "boolean-field" : ""}`;

      const label = document.createElement("label");
      label.textContent = fieldLabel(path);

      const input = createInput(path, value, type);
      input.id = `field-${path.replaceAll(".", "-")}`;
      label.htmlFor = input.id;

      wrapper.appendChild(label);
      wrapper.appendChild(input);
      fields.appendChild(wrapper);
    });

    section.appendChild(fields);
    configFormEl.appendChild(section);
  });
  showConfigSection("basico");
  updateDangerWarning();
  configFormEl.addEventListener("change", updateDangerWarning);
}

function showConfigSection(sectionName) {
  configFormEl.querySelectorAll(".config-section").forEach((section) => {
    section.hidden = section.dataset.section !== sectionName;
  });
  configTabsEl.querySelectorAll(".tab-button").forEach((button) => {
    button.classList.toggle("active", button.dataset.section === sectionName);
  });
}

function updateDangerWarning() {
  const next = collectConfigFromForm();
  const deleteSource = next.conversion?.delete_source === true;
  const dryRun = next.conversion?.dry_run === true;
  if (deleteSource && !dryRun) {
    dangerWarningEl.textContent = "Atencao: conversion.delete_source esta ligado e dry_run esta desligado. Conversoes reais podem apagar os arquivos de origem.";
    dangerWarningEl.className = "danger-note visible";
  } else {
    dangerWarningEl.textContent = "";
    dangerWarningEl.className = "danger-note";
  }
}

function collectConfigFromForm() {
  const nextConfig = {};
  fieldTypes.forEach((type, path) => {
    const field = configFormEl.querySelector(`[data-path="${path}"]`);
    let value;

    if (type === "boolean") {
      value = field.checked;
    } else if (type === "list") {
      value = field.value.split(/\r?\n|,/).map((item) => item.trim()).filter(Boolean);
    } else if (type === "number") {
      value = field.value.trim() === "" ? null : Number(field.value);
    } else {
      value = field.value.trim() === "" ? null : field.value.trim();
    }

    setNested(nextConfig, path, value);
  });
  return nextConfig;
}

function setSaveStatus(message, kind = "") {
  saveStatusEl.textContent = message;
  saveStatusEl.className = `save-status ${kind}`.trim();
}

function renderConversionTask(task) {
  if (!task) {
    activeConversionTaskId = null;
    conversionStatusEl.textContent = "Sem tarefa";
    conversionStartedEl.textContent = "Vazio";
    conversionFinishedEl.textContent = "Vazio";
    conversionLogEl.textContent = "Nenhuma conversao iniciada nesta sessao.";
    startConversionEl.disabled = false;
    cancelConversionEl.disabled = true;
    return;
  }

  activeConversionTaskId = task.id;
  conversionStatusEl.textContent = task.status;
  conversionStartedEl.textContent = valueText(task.started_at);
  conversionFinishedEl.textContent = valueText(task.finished_at);
  conversionLogs = task.logs || [];
  renderTaskLog(conversionLogEl, conversionLogs, conversionLogFilterEl.value);

  const running = ["pending", "running", "canceling"].includes(task.status);
  startConversionEl.disabled = running;
  cancelConversionEl.disabled = !running;

  if (running) {
    startConversionPolling();
  } else {
    stopConversionPolling();
  }
}

function renderDownloadTask(task) {
  if (!task) {
    activeDownloadTaskId = null;
    downloadStatusEl.textContent = "Sem tarefa";
    downloadStartedEl.textContent = "Vazio";
    downloadFinishedEl.textContent = "Vazio";
    downloadLogEl.textContent = "Nenhum download iniciado nesta sessao.";
    startDownloadEl.disabled = false;
    cancelDownloadEl.disabled = true;
    return;
  }

  activeDownloadTaskId = task.id;
  downloadStatusEl.textContent = task.status;
  downloadStartedEl.textContent = valueText(task.started_at);
  downloadFinishedEl.textContent = valueText(task.finished_at);
  downloadLogs = task.logs || [];
  renderTaskLog(downloadLogEl, downloadLogs, downloadLogFilterEl.value);
  renderProgress(task.progress || {});

  const running = ["pending", "running", "canceling"].includes(task.status);
  startDownloadEl.disabled = running;
  cancelDownloadEl.disabled = !running;

  if (running) {
    startDownloadPolling();
  } else {
    stopDownloadPolling();
  }
}

function renderProgress(progress) {
  const parts = [];
  const names = { rows: "linhas", total: "total", new: "novas", existing: "existentes", converted: "convertidas", failed: "falhas", dry_run: "teste" };
  Object.keys(names).forEach((key) => {
    if (progress[key] !== undefined) parts.push(`${names[key]}: ${progress[key]}`);
  });
  downloadProgressEl.textContent = parts.length ? parts.join(" | ") : "";
}

function renderTaskLog(target, logs, filter) {
  const needle = (filter || "").trim().toLowerCase();
  const visible = needle ? logs.filter((line) => line.toLowerCase().includes(needle)) : logs;
  target.textContent = visible.length ? visible.join("\n") : "Nenhum log para mostrar.";
  target.scrollTop = target.scrollHeight;
}

function startConversionPolling() {
  if (conversionPollTimer) return;
  conversionPollTimer = window.setInterval(loadLatestConversionTask, 1500);
}

function stopConversionPolling() {
  if (!conversionPollTimer) return;
  window.clearInterval(conversionPollTimer);
  conversionPollTimer = null;
}

function startDownloadPolling() {
  if (downloadPollTimer) return;
  downloadPollTimer = window.setInterval(loadLatestDownloadTask, 1500);
}

function stopDownloadPolling() {
  if (!downloadPollTimer) return;
  window.clearInterval(downloadPollTimer);
  downloadPollTimer = null;
}

async function loadLatestConversionTask() {
  const response = await fetch("/api/conversion/latest");
  const data = await response.json();
  if (response.ok && data.ok) {
    renderConversionTask(data.task);
  }
}

async function loadLatestDownloadTask() {
  const response = await fetch("/api/download/latest");
  const data = await response.json();
  if (response.ok && data.ok) {
    renderDownloadTask(data.task);
  }
}

async function loadConfig() {
  try {
    const response = await fetch("/api/config");
    const data = await response.json();
    if (!response.ok || !data.ok) {
      throw new Error(data.error || "Falha ao carregar config");
    }
    healthEl.textContent = "Online";
    healthEl.className = "status-pill ok";
    renderSummary(data.summary);
    renderValidation(data.validation);
    renderConfigEditor(data.config);
    setSaveStatus("");
    await loadLatestConversionTask();
    await loadLatestDownloadTask();
  } catch (error) {
    healthEl.textContent = "Erro";
    healthEl.className = "status-pill error";
    validationEl.innerHTML = `<li class="error">${friendlyError(error)}</li>`;
  }
}

async function saveConfig() {
  saveButtonEl.disabled = true;
  setSaveStatus("Salvando...");
  try {
    const response = await fetch("/api/config", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ config: collectConfigFromForm() }),
    });
    const data = await response.json();
    if (!response.ok || !data.ok) {
      const messages = data.validation?.messages?.join(" | ") || data.error || "Falha ao salvar";
      throw new Error(messages);
    }
    renderSummary(data.summary);
    renderValidation(data.validation);
    renderConfigEditor(data.config);
    setSaveStatus(`Salvo. Backup criado em ${data.backup}`, "ok");
  } catch (error) {
    setSaveStatus(friendlyError(error), "error");
  } finally {
    saveButtonEl.disabled = false;
  }
}

async function startConversion() {
  startConversionEl.disabled = true;
  conversionLogEl.textContent = "Solicitando inicio da conversao...";
  try {
    const response = await fetch("/api/conversion/start", { method: "POST" });
    const data = await response.json();
    if (!response.ok || !data.ok) {
      throw new Error(data.error || "Falha ao iniciar conversao");
    }
    renderConversionTask(data.task);
  } catch (error) {
    conversionLogEl.textContent = friendlyError(error);
    startConversionEl.disabled = false;
  }
}

async function cancelConversion() {
  if (!activeConversionTaskId) return;
  cancelConversionEl.disabled = true;
  await fetch(`/api/tasks/${activeConversionTaskId}/cancel`, { method: "POST" });
  await loadLatestConversionTask();
}

function collectDownloadOptions() {
  return {
    reescan_list: downloadReescanEl.checked,
    dry_run: downloadDryRunEl.checked,
    tagmusic: downloadTagmusicEl.checked,
    only_row: downloadOnlyRowEl.value.trim() || null,
    only_url: null,
  };
}

function updateDownloadSourcePanels() {
  const source = downloadSourceEl.value;
  downloadSourcePanels.forEach((panel) => {
    panel.hidden = panel.dataset.downloadSourcePanel !== source;
  });
}

function requireValue(input, message) {
  const value = input.value.trim();
  if (!value) throw new Error(message);
  return value;
}

function manualRow(artist, title, genre = "", spotifyUrl = "") {
  return {
    row_number: 1,
    type: spotifyUrl ? "playlist" : "manual",
    artist,
    title,
    genre,
    spotify_url: spotifyUrl,
  };
}

async function startDownload() {
  startDownloadEl.disabled = true;
  downloadLogEl.textContent = "Solicitando inicio do download...";
  try {
    const source = downloadSourceEl.value;
    if (source === "google_sheet") {
      const response = await fetch("/api/download/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ options: collectDownloadOptions() }),
      });
      const data = await response.json();
      if (!response.ok || !data.ok) {
        throw new Error(data.error || "Falha ao iniciar download");
      }
      renderDownloadTask(data.task);
      return;
    }

    if (source === "import_file") {
      if (!activeImportId) {
        throw new Error("Pre-visualize um arquivo na area Importacao antes de baixar.");
      }
      await startImportedDownload();
      return;
    }

    if (source === "youtube_search") {
      const row = manualRow(
        requireValue(downloadYoutubeArtistEl, "Informe o artista para procurar no YouTube."),
        requireValue(downloadYoutubeTitleEl, "Informe a musica para procurar no YouTube."),
        downloadYoutubeGenreEl.value.trim()
      );
      await startRowsDownload([row], "Iniciando busca no YouTube...");
      return;
    }

    if (source === "spotify_search") {
      const row = manualRow(
        requireValue(downloadSpotifyArtistEl, "Informe o artista para procurar no Spotify."),
        requireValue(downloadSpotifyTitleEl, "Informe a musica para procurar no Spotify."),
        downloadSpotifyGenreEl.value.trim()
      );
      await startRowsDownload([row], "Iniciando busca por artista/musica...");
      return;
    }

    if (source === "spotify_playlist") {
      const spotifyUrl = requireValue(downloadSpotifyUrlEl, "Informe o link da playlist ou artista do Spotify.");
      if (!spotifyUrl.includes("open.spotify.com/playlist/") && !spotifyUrl.includes("open.spotify.com/artist/")) {
        throw new Error("Use um link de playlist ou artista do Spotify.");
      }
      const row = manualRow("", "", downloadSpotifyUrlGenreEl.value.trim(), spotifyUrl);
      await startRowsDownload([row], "Iniciando download do Spotify...");
      return;
    }

    throw new Error("Origem de download desconhecida.");
  } catch (error) {
    downloadLogEl.textContent = friendlyError(error);
    startDownloadEl.disabled = false;
  }
}

async function cancelDownload() {
  if (!activeDownloadTaskId) return;
  cancelDownloadEl.disabled = true;
  await fetch(`/api/tasks/${activeDownloadTaskId}/cancel`, { method: "POST" });
  await loadLatestDownloadTask();
}

function renderSheetSummary(counts) {
  renderCounts(sheetSummaryEl, counts);
}

function renderCounts(target, counts) {
  target.innerHTML = "";
  const items = [
    ["Total", counts.total],
    ["Playlists", counts.playlist],
    ["Artistas", counts.artist],
    ["Manuais", counts.manual],
    ["Vazios", counts.empty],
  ];
  items.forEach(([label, value]) => {
    const item = document.createElement("div");
    item.className = "metric";
    item.innerHTML = `<span>${label}</span><strong>${value || 0}</strong>`;
    target.appendChild(item);
  });
}

function rowMatchesFilters(row) {
  const typeFilter = sheetTypeFilterEl.value;
  const search = sheetSearchEl.value.trim().toLowerCase();
  if (typeFilter !== "all" && row.type !== typeFilter) return false;
  if (!search) return true;
  return [row.artist, row.title, row.genre, row.spotify_url, row.type]
    .join(" ")
    .toLowerCase()
    .includes(search);
}

function renderSheetRows() {
  const visibleRows = sheetRows.filter(rowMatchesFilters);
  if (!visibleRows.length) {
    sheetRowsEl.innerHTML = `<tr><td colspan="7">Nenhum item encontrado.</td></tr>`;
    downloadSelectedSheetEl.disabled = true;
    return;
  }

  sheetRowsEl.innerHTML = "";
  visibleRows.forEach((row) => {
    const tr = document.createElement("tr");
    const spotifyCell = row.spotify_url
      ? `<a href="${row.spotify_url}" target="_blank" rel="noreferrer">abrir</a>`
      : "";
    tr.innerHTML = `
      <td>${row.row_number}</td>
      <td>
        <div class="row-actions">
          <input type="checkbox" data-sheet-select="${row.row_number}" ${selectedSheetRows.has(row.row_number) ? "checked" : ""} />
          <button class="tiny-button" type="button" data-sheet-download="${row.row_number}">Baixar</button>
        </div>
      </td>
      <td><span class="type-badge">${row.type}</span></td>
      <td>${row.artist || ""}</td>
      <td>${row.title || ""}</td>
      <td>${row.genre || ""}</td>
      <td>${spotifyCell}</td>
    `;
    sheetRowsEl.appendChild(tr);
  });
  updateSelectedSheetButton();
}

function renderRows(target, rows, emptyMessage) {
  if (!rows.length) {
    target.innerHTML = `<tr><td colspan="6">${emptyMessage}</td></tr>`;
    return;
  }

  target.innerHTML = "";
  rows.forEach((row) => {
    const tr = document.createElement("tr");
    const spotifyCell = row.spotify_url
      ? `<a href="${row.spotify_url}" target="_blank" rel="noreferrer">abrir</a>`
      : "";
    tr.innerHTML = `
      <td>${row.row_number}</td>
      <td><span class="type-badge">${row.type}</span></td>
      <td>${row.artist || ""}</td>
      <td>${row.title || ""}</td>
      <td>${row.genre || ""}</td>
      <td>${spotifyCell}</td>
    `;
    target.appendChild(tr);
  });
}

async function loadSheetPreview() {
  loadSheetEl.disabled = true;
  sheetStatusEl.textContent = "Carregando planilha...";
  sheetStatusEl.className = "save-status";
  try {
    const response = await fetch("/api/sheet/preview");
    const data = await response.json();
    if (!response.ok || !data.ok) {
      throw new Error(data.error || "Falha ao carregar planilha");
    }
    sheetRows = data.rows;
    selectedSheetRows = new Set();
    validateSheetEl.disabled = false;
    renderSheetSummary(data.counts);
    renderSheetRows();
    sheetStatusEl.textContent = data.truncated
      ? `Mostrando ${data.rows.length} de ${data.counts.total} linhas.`
      : `${data.rows.length} linhas carregadas.`;
    sheetStatusEl.className = "save-status ok";
  } catch (error) {
    sheetStatusEl.textContent = friendlyError(error);
    sheetStatusEl.className = "save-status error";
  } finally {
    loadSheetEl.disabled = false;
  }
}

function renderIssues(target, result) {
  if (!result.issues || !result.issues.length) {
    target.innerHTML = `<div class="issue-item">Nenhum problema encontrado.</div>`;
    return;
  }
  target.innerHTML = "";
  result.issues.slice(0, 80).forEach((issue) => {
    const item = document.createElement("div");
    item.className = `issue-item ${issue.severity === "error" ? "error" : ""}`;
    item.textContent = `Linha ${issue.row_number}: ${issue.message}`;
    target.appendChild(item);
  });
}

async function validateRows(rows, target, statusTarget) {
  const response = await fetch("/api/rows/validate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ rows: rows.map(sheetRowToInput) }),
  });
  const data = await response.json();
  if (!response.ok || !data.ok) throw new Error(data.error || "Falha ao checar");
  renderIssues(target, data);
  statusTarget.textContent = `${data.counts.rows} linhas checadas | ${data.counts.issues} avisos/problemas.`;
  statusTarget.className = "save-status ok";
}

async function validateSheetRows() {
  try {
    await validateRows(sheetRows, sheetIssuesEl, sheetStatusEl);
  } catch (error) {
    sheetStatusEl.textContent = friendlyError(error);
    sheetStatusEl.className = "save-status error";
  }
}

function updateSelectedSheetButton() {
  downloadSelectedSheetEl.disabled = selectedSheetRows.size === 0;
}

function sheetRowToInput(row) {
  return {
    "Artista": row.artist || "",
    "Musica": row.title || "",
    "(opcional) Tag/Genero": row.genre || "",
    "Spotify Playlist (link)": row.spotify_url || "",
  };
}

async function startRowsDownload(rows, message = "Iniciando download das linhas selecionadas...") {
  downloadLogEl.textContent = message;
  const response = await fetch("/api/rows/start", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ rows: rows.map(sheetRowToInput), options: collectDownloadOptions() }),
  });
  const data = await response.json();
  if (!response.ok || !data.ok) {
    throw new Error(data.error || "Falha ao iniciar linhas selecionadas");
  }
  renderDownloadTask(data.task);
}

async function startSelectedSheetDownload() {
  const rows = sheetRows.filter((row) => selectedSheetRows.has(row.row_number));
  try {
    await startRowsDownload(rows);
    sheetStatusEl.textContent = "Download das linhas selecionadas iniciado.";
    sheetStatusEl.className = "save-status ok";
  } catch (error) {
    sheetStatusEl.textContent = friendlyError(error);
    sheetStatusEl.className = "save-status error";
  }
}

async function previewImportFile() {
  const file = importFileEl.files[0];
  if (!file) {
    importStatusEl.textContent = "Escolha um arquivo primeiro.";
    importStatusEl.className = "save-status error";
    return;
  }

  previewImportEl.disabled = true;
  importStatusEl.textContent = "Lendo arquivo...";
  importStatusEl.className = "save-status";
  try {
    const form = new FormData();
    form.append("file", file);
    const response = await fetch("/api/import/preview", {
      method: "POST",
      body: form,
    });
    const data = await response.json();
    if (!response.ok || !data.ok) {
      throw new Error(data.error || "Falha ao importar arquivo");
    }
    activeImportId = data.import_id;
    renderCounts(importSummaryEl, data.counts);
    renderRows(importRowsEl, data.rows, "Nenhum item encontrado no arquivo.");
    importRowsEl.dataset.rows = JSON.stringify(data.rows);
    downloadImportEl.disabled = false;
    validateImportEl.disabled = false;
    importStatusEl.textContent = data.truncated
      ? `${data.filename}: mostrando ${data.rows.length} de ${data.counts.total} linhas.`
      : `${data.filename}: ${data.rows.length} linhas carregadas.`;
    importStatusEl.className = "save-status ok";
  } catch (error) {
    importStatusEl.textContent = friendlyError(error);
    importStatusEl.className = "save-status error";
    downloadImportEl.disabled = true;
  } finally {
    previewImportEl.disabled = false;
  }
}

async function validateImportRows() {
  try {
    const rows = JSON.parse(importRowsEl.dataset.rows || "[]");
    await validateRows(rows, importIssuesEl, importStatusEl);
  } catch (error) {
    importStatusEl.textContent = friendlyError(error);
    importStatusEl.className = "save-status error";
  }
}

async function startImportedDownload() {
  if (!activeImportId) {
    importStatusEl.textContent = "Pre-visualize um arquivo primeiro.";
    importStatusEl.className = "save-status error";
    return;
  }
  downloadImportEl.disabled = true;
  downloadLogEl.textContent = "Iniciando download da lista importada...";
  try {
    const response = await fetch("/api/import/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ import_id: activeImportId, options: collectDownloadOptions() }),
    });
    const data = await response.json();
    if (!response.ok || !data.ok) {
      throw new Error(data.error || "Falha ao iniciar lista importada");
    }
    renderDownloadTask(data.task);
    importStatusEl.textContent = "Download da lista importada iniciado.";
    importStatusEl.className = "save-status ok";
  } catch (error) {
    importStatusEl.textContent = friendlyError(error);
    importStatusEl.className = "save-status error";
    downloadImportEl.disabled = false;
  }
}

async function loadTasks() {
  const response = await fetch("/api/tasks");
  const data = await response.json();
  if (!response.ok || !data.ok || !data.tasks.length) {
    taskRowsEl.innerHTML = `<tr><td colspan="5">Nenhuma tarefa nesta sessao.</td></tr>`;
    return;
  }
  taskRowsEl.innerHTML = "";
  data.tasks.forEach((task) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${task.kind}</td>
      <td><span class="type-badge">${task.status}</span></td>
      <td>${valueText(task.started_at)}</td>
      <td>${valueText(task.finished_at)}</td>
      <td>${valueText(task.returncode)}</td>
    `;
    taskRowsEl.appendChild(tr);
  });
}

async function loadEnvironment() {
  const response = await fetch("/api/environment");
  const data = await response.json();
  if (!response.ok || !data.ok) return;
  environmentGridEl.innerHTML = "";
  data.checks.forEach((check) => {
    const item = document.createElement("div");
    item.className = `env-item ${check.ok ? "ok" : "fail"}`;
    item.innerHTML = `<strong>${check.ok ? "OK" : "Falha"} - ${check.name}</strong><span>${check.detail || ""}</span>`;
    environmentGridEl.appendChild(item);
  });
}

function renderHistory() {
  if (!historyData) {
    historyLogEl.textContent = "Clique em atualizar para carregar.";
    return;
  }
  const name = historyFileFilterEl.value;
  const search = historySearchEl.value.trim().toLowerCase();
  const lines = historyData.files[name] || [];
  const visible = search ? lines.filter((line) => line.toLowerCase().includes(search)) : lines;
  historyLogEl.textContent = visible.length ? visible.join("\n") : "Nenhuma linha encontrada.";
}

async function loadHistory() {
  const response = await fetch("/api/history");
  const data = await response.json();
  if (!response.ok || !data.ok) return;
  historyData = data;
  renderCounts(historySummaryEl, data.counts);
  renderHistory();
}

async function retryFailures() {
  historyLogEl.textContent = "Iniciando nova tentativa das falhas...";
  try {
    const response = await fetch("/api/history/retry-failures", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ options: collectDownloadOptions() }),
    });
    const data = await response.json();
    if (!response.ok || !data.ok) {
      throw new Error(data.error || "Falha ao tentar novamente");
    }
    renderDownloadTask(data.task);
    historyLogEl.textContent = "Nova tentativa das falhas iniciada. Veja o log em Download.";
  } catch (error) {
    historyLogEl.textContent = friendlyError(error);
  }
}

reloadButtonEl.addEventListener("click", loadConfig);
saveButtonEl.addEventListener("click", saveConfig);
startConversionEl.addEventListener("click", startConversion);
cancelConversionEl.addEventListener("click", cancelConversion);
startDownloadEl.addEventListener("click", startDownload);
cancelDownloadEl.addEventListener("click", cancelDownload);
downloadSourceEl.addEventListener("change", updateDownloadSourcePanels);
loadSheetEl.addEventListener("click", loadSheetPreview);
validateSheetEl.addEventListener("click", validateSheetRows);
sheetSearchEl.addEventListener("input", renderSheetRows);
sheetTypeFilterEl.addEventListener("change", renderSheetRows);
downloadSelectedSheetEl.addEventListener("click", startSelectedSheetDownload);
sheetRowsEl.addEventListener("change", (event) => {
  const rowNumber = Number(event.target.dataset.sheetSelect || 0);
  if (!rowNumber) return;
  if (event.target.checked) selectedSheetRows.add(rowNumber);
  else selectedSheetRows.delete(rowNumber);
  updateSelectedSheetButton();
});
sheetRowsEl.addEventListener("click", async (event) => {
  const rowNumber = Number(event.target.dataset.sheetDownload || 0);
  if (!rowNumber) return;
  const row = sheetRows.find((item) => item.row_number === rowNumber);
  if (!row) return;
  try {
    await startRowsDownload([row]);
    sheetStatusEl.textContent = `Download da linha ${rowNumber} iniciado.`;
    sheetStatusEl.className = "save-status ok";
  } catch (error) {
    sheetStatusEl.textContent = friendlyError(error);
    sheetStatusEl.className = "save-status error";
  }
});
previewImportEl.addEventListener("click", previewImportFile);
validateImportEl.addEventListener("click", validateImportRows);
downloadImportEl.addEventListener("click", startImportedDownload);
refreshTasksEl.addEventListener("click", loadTasks);
checkEnvironmentEl.addEventListener("click", loadEnvironment);
refreshHistoryEl.addEventListener("click", loadHistory);
retryFailuresEl.addEventListener("click", retryFailures);
historySearchEl.addEventListener("input", renderHistory);
historyFileFilterEl.addEventListener("change", renderHistory);
conversionLogFilterEl.addEventListener("input", () => renderTaskLog(conversionLogEl, conversionLogs, conversionLogFilterEl.value));
downloadLogFilterEl.addEventListener("input", () => renderTaskLog(downloadLogEl, downloadLogs, downloadLogFilterEl.value));

updateDownloadSourcePanels();
loadConfig();
loadTasks();
loadEnvironment();
