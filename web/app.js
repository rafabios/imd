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
const startLibraryAnalysisEl = document.querySelector("#start-library-analysis");
const cancelAnalysisEl = document.querySelector("#cancel-analysis");
const analysisStatusEl = document.querySelector("#analysis-status");
const analysisProgressEl = document.querySelector("#analysis-progress");
const analysisGeneratedEl = document.querySelector("#analysis-generated");
const analysisSummaryEl = document.querySelector("#analysis-summary");
const analysisDropZoneEl = document.querySelector("#analysis-drop-zone");
const analysisFileEl = document.querySelector("#analysis-file");
const analysisChartEl = document.querySelector("#analysis-chart");
const analysisChartTitleEl = document.querySelector("#analysis-chart-title");
const analysisChartSubtitleEl = document.querySelector("#analysis-chart-subtitle");
const analysisChartRatingEl = document.querySelector("#analysis-chart-rating");
const analysisMessageEl = document.querySelector("#analysis-message");
const analysisDetailEl = document.querySelector("#analysis-detail");
const analysisResultsEl = document.querySelector("#analysis-results");
const analysisLogEl = document.querySelector("#analysis-log");
const analysisLogFilterEl = document.querySelector("#analysis-log-filter");
const loadSheetEl = document.querySelector("#load-sheet");
const validateSheetEl = document.querySelector("#validate-sheet");
const downloadSelectedSheetEl = document.querySelector("#download-selected-sheet");
const sheetSearchEl = document.querySelector("#sheet-search");
const sheetTypeFilterEl = document.querySelector("#sheet-type-filter");
const sheetStatusEl = document.querySelector("#sheet-status");
const sheetIssuesEl = document.querySelector("#sheet-issues");
const sheetSummaryEl = document.querySelector("#sheet-summary");
const sheetRowsEl = document.querySelector("#sheet-rows");
const sheetRowSelectionEl = document.querySelector("#sheet-row-selection");
const applySheetSelectionEl = document.querySelector("#apply-sheet-selection");
const selectVisibleSheetEl = document.querySelector("#select-visible-sheet");
const selectAllSheetEl = document.querySelector("#select-all-sheet");
const clearSheetSelectionEl = document.querySelector("#clear-sheet-selection");
const sheetSelectionHelpEl = document.querySelector("#sheet-selection-help");
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
const testSpotifyLinkEl = document.querySelector("#test-spotify-link");
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
const downloadShortcutEls = Array.from(document.querySelectorAll("[data-download-shortcut]"));
const openMusicFolderEls = Array.from(document.querySelectorAll("[data-open-music-folder]"));
const tagMusicEls = Array.from(document.querySelectorAll("[data-tag-music]"));
const openAnalysisEls = Array.from(document.querySelectorAll("[data-open-analysis]"));

let currentConfig = {};
let fieldTypes = new Map();
let activeConversionTaskId = null;
let conversionPollTimer = null;
let activeDownloadTaskId = null;
let downloadPollTimer = null;
let activeAnalysisTaskId = null;
let analysisPollTimer = null;
let analysisTaskRunning = false;
let analysisResults = [];
let selectedAnalysisIndex = -1;
let analysisLogs = [];
let loadedAnalysisReportDate = "";
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

function appendTextCell(row, value) {
  const cell = document.createElement("td");
  cell.textContent = value === null || value === undefined ? "" : String(value);
  row.appendChild(cell);
  return cell;
}

function spotifyLink(value) {
  try {
    const url = new URL(String(value || ""));
    if (url.protocol !== "https:" || url.hostname !== "open.spotify.com") return null;
    return url.href;
  } catch {
    return null;
  }
}

function appendSpotifyCell(row, value) {
  const cell = document.createElement("td");
  const href = spotifyLink(value);
  if (href) {
    const link = document.createElement("a");
    link.href = href;
    link.target = "_blank";
    link.rel = "noreferrer";
    link.textContent = "abrir";
    cell.appendChild(link);
  }
  row.appendChild(cell);
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
    const label = document.createElement("span");
    const strong = document.createElement("strong");
    label.textContent = labels[key] || key;
    strong.textContent = valueText(value);
    item.append(label, strong);
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
    const heading = document.createElement("h3");
    heading.textContent = labelText;
    section.appendChild(heading);

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
    tagMusicEls.forEach((button) => { button.disabled = false; });
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
  tagMusicEls.forEach((button) => { button.disabled = running; });

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

function startAnalysisPolling() {
  if (analysisPollTimer) return;
  analysisPollTimer = window.setInterval(loadLatestAnalysis, 1500);
}

function stopAnalysisPolling() {
  if (!analysisPollTimer) return;
  window.clearInterval(analysisPollTimer);
  analysisPollTimer = null;
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

async function loadLatestAnalysis() {
  const response = await fetch("/api/analysis/latest");
  const data = await response.json();
  if (response.ok && data.ok) {
    renderAnalysisTask(data.task, data.report);
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
    await loadLatestAnalysis();
  } catch (error) {
    healthEl.textContent = "Erro";
    healthEl.className = "status-pill error";
    validationEl.innerHTML = "";
    const item = document.createElement("li");
    item.className = "error";
    item.textContent = friendlyError(error);
    validationEl.appendChild(item);
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

function openAnalysisSection() {
  document.querySelector("#analysis").scrollIntoView({ behavior: "smooth", block: "start" });
}

async function startLibraryAnalysis() {
  startLibraryAnalysisEl.disabled = true;
  analysisMessageEl.textContent = "Preparando análise completa da biblioteca...";
  analysisMessageEl.className = "save-status";
  openAnalysisSection();
  try {
    const response = await fetch("/api/analysis/start-library", { method: "POST" });
    const data = await response.json();
    if (!response.ok || !data.ok) {
      throw new Error(data.error || "Falha ao iniciar a análise da biblioteca.");
    }
    analysisMessageEl.textContent = "Análise iniciada. Os arquivos originais não serão modificados.";
    analysisMessageEl.className = "save-status ok";
    renderAnalysisTask(data.task);
  } catch (error) {
    analysisMessageEl.textContent = friendlyError(error);
    analysisMessageEl.className = "save-status error";
    startLibraryAnalysisEl.disabled = false;
  }
}

async function cancelAnalysis() {
  if (!activeAnalysisTaskId) return;
  cancelAnalysisEl.disabled = true;
  await fetch(`/api/tasks/${activeAnalysisTaskId}/cancel`, { method: "POST" });
  await loadLatestAnalysis();
}

async function analyzeAudioFiles(fileList) {
  const files = Array.from(fileList || []);
  if (!files.length) return;
  openAnalysisSection();
  if (analysisTaskRunning) {
    analysisMessageEl.textContent = "Aguarde a análise da biblioteca terminar ou clique em Parar.";
    analysisMessageEl.className = "save-status error";
    return;
  }
  startLibraryAnalysisEl.disabled = true;
  analysisFileEl.disabled = true;
  analysisDropZoneEl.classList.add("busy");
  analysisStatusEl.textContent = "Analisando arquivos";
  analysisProgressEl.textContent = `0 / ${files.length}`;
  let completed = 0;
  let failures = 0;
  try {
    for (const file of files) {
      if (file.size > 100 * 1024 * 1024) {
        failures += 1;
        analysisProgressEl.textContent = `${completed + failures} / ${files.length}`;
        analysisMessageEl.textContent = `${file.name}: excede o limite de 100 MB.`;
        analysisMessageEl.className = "save-status error";
        continue;
      }
      analysisMessageEl.textContent = `Analisando ${file.name} (${completed + failures + 1}/${files.length})...`;
      analysisMessageEl.className = "save-status";
      const formData = new FormData();
      formData.append("file", file, file.name);
      try {
        const response = await fetch("/api/analysis/upload", { method: "POST", body: formData });
        const data = await response.json();
        if (!response.ok || !data.ok) {
          throw new Error(data.error || `Falha ao analisar ${file.name}.`);
        }
        analysisResults.unshift(data.result);
        selectedAnalysisIndex = 0;
        completed += 1;
        analysisProgressEl.textContent = `${completed + failures} / ${files.length}`;
        renderAnalysisResults();
      } catch (error) {
        failures += 1;
        analysisProgressEl.textContent = `${completed + failures} / ${files.length}`;
        analysisMessageEl.textContent = friendlyError(error);
        analysisMessageEl.className = "save-status error";
      }
    }
    if (!failures) {
      analysisStatusEl.textContent = "Concluída";
      analysisMessageEl.textContent = `${completed} arquivo(s) analisado(s). Nenhum original foi alterado.`;
      analysisMessageEl.className = "save-status ok";
    } else if (completed) {
      analysisStatusEl.textContent = "Concluída com falhas";
      analysisMessageEl.textContent = `${completed} arquivo(s) analisado(s) e ${failures} com falha.`;
      analysisMessageEl.className = "save-status error";
    }
  } finally {
    if (!completed && failures) analysisStatusEl.textContent = "Falhou";
    startLibraryAnalysisEl.disabled = false;
    analysisFileEl.disabled = false;
    analysisFileEl.value = "";
    analysisDropZoneEl.classList.remove("busy", "drag-active");
  }
}

function collectDownloadOptions() {
  return {
    reescan_list: downloadReescanEl.checked,
    dry_run: downloadDryRunEl.checked,
    tagmusic: downloadTagmusicEl.checked,
    row_selection: downloadOnlyRowEl.value.trim() || null,
    only_url: null,
  };
}

function updateDownloadSourcePanels() {
  const source = downloadSourceEl.value;
  downloadSourcePanels.forEach((panel) => {
    panel.hidden = panel.dataset.downloadSourcePanel !== source;
  });
}

function openDownloadShortcut(source) {
  downloadSourceEl.value = source;
  updateDownloadSourcePanels();
  document.querySelector("#download").scrollIntoView({ behavior: "smooth", block: "start" });
}

async function openMusicFolder() {
  openMusicFolderEls.forEach((button) => { button.disabled = true; });
  try {
    const response = await fetch("/api/music-folder/open", { method: "POST" });
    const data = await response.json();
    if (!response.ok || !data.ok) {
      throw new Error(data.error || "Falha ao abrir a pasta de musicas");
    }
  } catch (error) {
    healthEl.textContent = friendlyError(error);
    healthEl.className = "status-pill error";
  } finally {
    openMusicFolderEls.forEach((button) => { button.disabled = false; });
  }
}

function analysisMetric(value, suffix = "") {
  const number = Number(value);
  if (!Number.isFinite(number)) return "—";
  return `${number.toFixed(1)}${suffix}`;
}

function renderAnalysisSummary() {
  const counts = {
    total: analysisResults.length,
    good: analysisResults.filter((item) => item.rating === "good").length,
    medium: analysisResults.filter((item) => item.rating === "medium").length,
    bad: analysisResults.filter((item) => item.rating === "bad").length,
    errors: analysisResults.filter((item) => item.error).length,
  };
  const entries = [
    ["Total", counts.total],
    ["Boas", counts.good],
    ["Médias", counts.medium],
    ["Ruins", counts.bad],
    ["Falhas", counts.errors],
  ];
  analysisSummaryEl.textContent = "";
  entries.forEach(([labelText, value]) => {
    const metric = document.createElement("div");
    metric.className = "metric";
    const label = document.createElement("span");
    const strong = document.createElement("strong");
    label.textContent = labelText;
    strong.textContent = String(value);
    metric.append(label, strong);
    analysisSummaryEl.appendChild(metric);
  });
}

function addAnalysisDetailCard(titleText, bodyText, kind = "") {
  const card = document.createElement("div");
  card.className = `analysis-detail-card ${kind}`.trim();
  const title = document.createElement("strong");
  const body = document.createElement("span");
  title.textContent = titleText;
  body.textContent = bodyText;
  card.append(title, body);
  analysisDetailEl.appendChild(card);
}

function drawAnalysisChart(item) {
  const context = analysisChartEl.getContext("2d");
  const pixelRatio = window.devicePixelRatio || 1;
  const cssWidth = Math.max(320, analysisChartEl.clientWidth || 960);
  const cssHeight = 240;
  analysisChartEl.width = Math.round(cssWidth * pixelRatio);
  analysisChartEl.height = Math.round(cssHeight * pixelRatio);
  context.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
  context.fillStyle = "#091018";
  context.fillRect(0, 0, cssWidth, cssHeight);

  const padding = { left: 48, right: 16, top: 14, bottom: 28 };
  const plotWidth = cssWidth - padding.left - padding.right;
  const plotHeight = cssHeight - padding.top - padding.bottom;
  const levels = [-6, -12, -18, -24, -36, -48, -60];
  context.font = "11px system-ui";
  context.lineWidth = 1;
  levels.forEach((level) => {
    const y = padding.top + ((0 - level) / 60) * plotHeight;
    context.strokeStyle = "rgba(166, 195, 210, 0.16)";
    context.beginPath();
    context.moveTo(padding.left, y);
    context.lineTo(cssWidth - padding.right, y);
    context.stroke();
    context.fillStyle = "#86a0ae";
    context.fillText(`${level}`, 10, y + 4);
  });
  context.fillStyle = "#86a0ae";
  context.fillText("LUFS", 8, 12);

  const timeline = Array.isArray(item?.timeline) ? item.timeline : [];
  if (!timeline.length) {
    context.fillStyle = "#9fb4c2";
    context.textAlign = "center";
    context.font = "14px system-ui";
    context.fillText("Sem dados temporais para este arquivo", cssWidth / 2, cssHeight / 2);
    context.textAlign = "left";
    return;
  }

  const maxSeconds = Math.max(1, Number(timeline[timeline.length - 1].seconds) || 1);
  const gradient = context.createLinearGradient(padding.left, 0, cssWidth - padding.right, 0);
  gradient.addColorStop(0, "#16c7b0");
  gradient.addColorStop(0.55, "#4da9ff");
  gradient.addColorStop(1, item.rating === "bad" ? "#ff5267" : item.rating === "medium" ? "#ffb22e" : "#9b6cff");
  context.strokeStyle = gradient;
  context.lineWidth = 2.5;
  context.beginPath();
  timeline.forEach((point, index) => {
    const seconds = Math.max(0, Number(point.seconds) || 0);
    const loudness = Math.max(-60, Math.min(0, Number(point.lufs) || -60));
    const x = padding.left + (seconds / maxSeconds) * plotWidth;
    const y = padding.top + ((0 - loudness) / 60) * plotHeight;
    if (index === 0) context.moveTo(x, y);
    else context.lineTo(x, y);
  });
  context.stroke();
  context.fillStyle = "#86a0ae";
  context.fillText("0:00", padding.left, cssHeight - 8);
  const minutes = Math.floor(maxSeconds / 60);
  const seconds = String(Math.round(maxSeconds % 60)).padStart(2, "0");
  const durationLabel = `${minutes}:${seconds}`;
  const labelWidth = context.measureText(durationLabel).width;
  context.fillText(durationLabel, cssWidth - padding.right - labelWidth, cssHeight - 8);
}

function selectAnalysisResult(index) {
  const item = analysisResults[index];
  if (!item) return;
  selectedAnalysisIndex = index;
  analysisResultsEl.querySelectorAll("tr[data-analysis-index]").forEach((row) => {
    row.classList.toggle("selected", Number(row.dataset.analysisIndex) === index);
  });
  analysisChartTitleEl.textContent = item.file || "Música analisada";
  analysisChartSubtitleEl.textContent = [
    `Integrada ${analysisMetric(item.integrated_lufs, " LUFS")}`,
    `Pico ${analysisMetric(item.true_peak_dbtp, " dBTP")}`,
    `Faixa ${analysisMetric(item.loudness_range_lu, " LU")}`,
  ].join(" · ");
  analysisChartRatingEl.textContent = item.rating_label || "Sem nota";
  analysisChartRatingEl.className = `quality-badge ${item.rating || ""}`.trim();
  drawAnalysisChart(item);

  analysisDetailEl.textContent = "";
  (item.reasons || []).forEach((reason) => addAnalysisDetailCard("Diagnóstico", reason, item.rating === "bad" ? "error" : item.rating === "medium" ? "warning" : ""));
  (item.recommendations || []).forEach((recommendation) => addAnalysisDetailCard("Sugestão", recommendation, "warning"));
  if (item.error) addAnalysisDetailCard("Falha na leitura", item.error, "error");
}

function renderAnalysisResults() {
  analysisResultsEl.textContent = "";
  renderAnalysisSummary();
  if (!analysisResults.length) {
    const row = document.createElement("tr");
    const cell = document.createElement("td");
    cell.colSpan = 8;
    cell.textContent = "Analise a biblioteca ou arraste uma música para começar.";
    row.appendChild(cell);
    analysisResultsEl.appendChild(row);
    return;
  }

  analysisResults.forEach((item, index) => {
    const row = document.createElement("tr");
    row.dataset.analysisIndex = String(index);
    const ratingCell = document.createElement("td");
    const badge = document.createElement("span");
    badge.className = `quality-badge ${item.rating || ""}`.trim();
    badge.textContent = item.rating_label || "Sem nota";
    ratingCell.appendChild(badge);
    row.appendChild(ratingCell);

    const fileCell = document.createElement("td");
    const fileButton = document.createElement("button");
    fileButton.type = "button";
    fileButton.className = "analysis-file-button";
    fileButton.textContent = item.file || "arquivo";
    fileButton.addEventListener("click", () => selectAnalysisResult(index));
    fileCell.appendChild(fileButton);
    row.appendChild(fileCell);
    appendTextCell(row, analysisMetric(item.integrated_lufs));
    appendTextCell(row, analysisMetric(item.true_peak_dbtp));
    appendTextCell(row, analysisMetric(item.loudness_range_lu));
    appendTextCell(row, `${item.codec || "?"} / ${item.sample_rate_hz ? `${Math.round(item.sample_rate_hz / 100) / 10} kHz` : "?"}`);
    appendTextCell(row, item.bit_rate_bps ? `${Math.round(item.bit_rate_bps / 1000)} kbps` : item.codec || "—");
    appendTextCell(row, Number.isFinite(Number(item.score)) ? `${item.score}/100` : "—");
    row.addEventListener("click", (event) => {
      if (event.target !== fileButton) selectAnalysisResult(index);
    });
    analysisResultsEl.appendChild(row);
  });
  selectAnalysisResult(Math.min(Math.max(selectedAnalysisIndex, 0), analysisResults.length - 1));
}

function applyAnalysisReport(report) {
  if (!report || !Array.isArray(report.items)) return;
  const generatedAt = String(report.generated_at || "");
  if (generatedAt && generatedAt === loadedAnalysisReportDate) return;
  loadedAnalysisReportDate = generatedAt;
  analysisGeneratedEl.textContent = valueText(report.generated_at);
  analysisResults = report.items;
  selectedAnalysisIndex = analysisResults.length ? 0 : -1;
  renderAnalysisResults();
}

function renderAnalysisTask(task, report = null) {
  applyAnalysisReport(report);
  if (!task) {
    activeAnalysisTaskId = null;
    analysisTaskRunning = false;
    analysisStatusEl.textContent = analysisResults.length ? "Relatório carregado" : "Sem análise";
    analysisProgressEl.textContent = "0 / 0";
    startLibraryAnalysisEl.disabled = false;
    cancelAnalysisEl.disabled = true;
    analysisFileEl.disabled = false;
    analysisDropZoneEl.classList.remove("busy");
    return;
  }

  activeAnalysisTaskId = task.id;
  analysisStatusEl.textContent = task.status;
  const progress = task.progress || {};
  analysisProgressEl.textContent = `${progress.processed || 0} / ${progress.total || 0}`;
  analysisLogs = task.logs || [];
  renderTaskLog(analysisLogEl, analysisLogs, analysisLogFilterEl.value);
  const running = ["pending", "running", "canceling"].includes(task.status);
  analysisTaskRunning = running;
  startLibraryAnalysisEl.disabled = running;
  cancelAnalysisEl.disabled = !running;
  analysisFileEl.disabled = running;
  analysisDropZoneEl.classList.toggle("busy", running);
  if (running) startAnalysisPolling();
  else stopAnalysisPolling();
}

async function startTagMusic() {
  tagMusicEls.forEach((button) => { button.disabled = true; });
  downloadLogEl.textContent = "Iniciando tageamento da pasta de musicas...";
  document.querySelector("#download").scrollIntoView({ behavior: "smooth", block: "start" });
  try {
    const response = await fetch("/api/tag-music/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ force: false }),
    });
    const data = await response.json();
    if (!response.ok || !data.ok) {
      throw new Error(data.error || "Falha ao iniciar o tageamento");
    }
    renderDownloadTask(data.task);
  } catch (error) {
    downloadLogEl.textContent = friendlyError(error);
    tagMusicEls.forEach((button) => { button.disabled = false; });
  }
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
      if (!/open\.spotify\.com\/(?:intl-[a-z]{2}\/)?(?:embed\/)?(?:playlist|artist)\//i.test(spotifyUrl)) {
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

async function testSpotifyLink() {
  try {
    const spotifyUrl = requireValue(downloadSpotifyUrlEl, "Informe o link da playlist ou artista do Spotify.");
    if (!/open\.spotify\.com\/(?:intl-[a-z]{2}\/)?(?:embed\/)?(?:playlist|artist)\//i.test(spotifyUrl)) {
      throw new Error("Use um link de playlist ou artista do Spotify.");
    }
    testSpotifyLinkEl.disabled = true;
    downloadProgressEl.textContent = "Testando link do Spotify...";
    downloadLogEl.textContent = "";
    const response = await fetch("/api/spotify/check", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: spotifyUrl }),
    });
    const data = await response.json();
    if (!response.ok || !data.ok) {
      throw new Error(data.error || "Nao foi possivel extrair musicas desse link.");
    }
    const typeLabel = data.entity_type === "artist" ? "artista" : "playlist";
    const sample = (data.sample || [])
      .map((track) => [track.artist, track.title].filter(Boolean).join(" - "))
      .filter(Boolean)
      .slice(0, 3)
      .join(" | ");
    const partialWarning = data.partial_possible ? " O embed publico pode conter apenas parte da playlist." : "";
    downloadProgressEl.textContent = `Spotify OK: ${typeLabel} "${data.name || "sem nome"}" com ${data.count} musicas.${partialWarning}`;
    downloadLogEl.textContent = sample ? `Amostra: ${sample}` : "";
  } catch (error) {
    downloadProgressEl.textContent = "Falha ao testar Spotify.";
    downloadLogEl.textContent = friendlyError(error);
  } finally {
    testSpotifyLinkEl.disabled = false;
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
    const labelElement = document.createElement("span");
    const valueElement = document.createElement("strong");
    labelElement.textContent = label;
    valueElement.textContent = String(value || 0);
    item.append(labelElement, valueElement);
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

function parseSheetRowSelection(value) {
  const text = String(value || "").trim().toLowerCase();
  if (!text) throw new Error("Digite linhas como 1-5, 8, 12-15 ou todos.");
  if (["*", "all", "todas", "todos"].includes(text)) {
    return sheetRows.map((row) => row.row_number);
  }

  const available = new Set(sheetRows.map((row) => row.row_number));
  const selected = new Set();
  const tokens = text.split(/[,;\s]+/).filter(Boolean);
  tokens.forEach((token) => {
    const match = token.match(/^(\d+)(?:-(\d+))?$/);
    if (!match) throw new Error(`Selecao invalida: ${token}. Use 2,5,8-12 ou todos.`);
    const start = Number(match[1]);
    const end = Number(match[2] || match[1]);
    if (start < 1 || end < 1) throw new Error("Os numeros das linhas devem comecar em 1.");
    if (end < start) throw new Error(`Intervalo invertido: ${start}-${end}.`);
    if (end - start + 1 > 10000) throw new Error("O intervalo pode ter no maximo 10000 linhas.");
    for (let rowNumber = start; rowNumber <= end; rowNumber += 1) {
      if (!available.has(rowNumber)) throw new Error(`A linha ${rowNumber} nao esta entre as linhas carregadas.`);
      selected.add(rowNumber);
    }
  });
  return Array.from(selected).sort((left, right) => left - right);
}

function setSheetSelection(rowNumbers, message) {
  selectedSheetRows = new Set(rowNumbers);
  renderSheetRows();
  sheetStatusEl.textContent = message;
  sheetStatusEl.className = "save-status ok";
}

function applySheetSelection() {
  try {
    const rowNumbers = parseSheetRowSelection(sheetRowSelectionEl.value);
    setSheetSelection(rowNumbers, `${rowNumbers.length} linhas selecionadas pelos numeros informados.`);
  } catch (error) {
    sheetStatusEl.textContent = friendlyError(error);
    sheetStatusEl.className = "save-status error";
  }
}

function selectVisibleSheetRows() {
  const rowNumbers = sheetRows.filter(rowMatchesFilters).map((row) => row.row_number);
  setSheetSelection(rowNumbers, `${rowNumbers.length} linhas filtradas selecionadas.`);
}

function selectAllSheetRows() {
  const rowNumbers = sheetRows.map((row) => row.row_number);
  setSheetSelection(rowNumbers, `${rowNumbers.length} linhas carregadas selecionadas.`);
}

function clearSheetSelection() {
  selectedSheetRows = new Set();
  sheetRowSelectionEl.value = "";
  renderSheetRows();
  sheetStatusEl.textContent = "Selecao de linhas limpa.";
  sheetStatusEl.className = "save-status";
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
    appendTextCell(tr, row.row_number);

    const actionsCell = document.createElement("td");
    const actions = document.createElement("div");
    actions.className = "row-actions";
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.dataset.sheetSelect = String(row.row_number);
    checkbox.checked = selectedSheetRows.has(row.row_number);
    const button = document.createElement("button");
    button.className = "tiny-button";
    button.type = "button";
    button.dataset.sheetDownload = String(row.row_number);
    button.textContent = "Baixar";
    actions.append(checkbox, button);
    actionsCell.appendChild(actions);
    tr.appendChild(actionsCell);

    const typeCell = document.createElement("td");
    const badge = document.createElement("span");
    badge.className = "type-badge";
    badge.textContent = valueText(row.type);
    typeCell.appendChild(badge);
    tr.appendChild(typeCell);
    appendTextCell(tr, row.artist || "");
    appendTextCell(tr, row.title || "");
    appendTextCell(tr, row.genre || "");
    appendSpotifyCell(tr, row.spotify_url);
    sheetRowsEl.appendChild(tr);
  });
  updateSelectedSheetButton();
}

function renderRows(target, rows, emptyMessage) {
  if (!rows.length) {
    target.innerHTML = "";
    const row = document.createElement("tr");
    const cell = document.createElement("td");
    cell.colSpan = 6;
    cell.textContent = emptyMessage;
    row.appendChild(cell);
    target.appendChild(row);
    return;
  }

  target.innerHTML = "";
  rows.forEach((row) => {
    const tr = document.createElement("tr");
    appendTextCell(tr, row.row_number);
    const typeCell = document.createElement("td");
    const badge = document.createElement("span");
    badge.className = "type-badge";
    badge.textContent = valueText(row.type);
    typeCell.appendChild(badge);
    tr.appendChild(typeCell);
    appendTextCell(tr, row.artist || "");
    appendTextCell(tr, row.title || "");
    appendTextCell(tr, row.genre || "");
    appendSpotifyCell(tr, row.spotify_url);
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
    [sheetRowSelectionEl, applySheetSelectionEl, selectVisibleSheetEl, selectAllSheetEl, clearSheetSelectionEl]
      .forEach((control) => { control.disabled = false; });
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
  sheetSelectionHelpEl.textContent = sheetRows.length
    ? `${selectedSheetRows.size} de ${sheetRows.length} linhas carregadas selecionadas.`
    : "Carregue a planilha para selecionar linhas.";
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
    appendTextCell(tr, task.kind);
    const statusCell = document.createElement("td");
    const badge = document.createElement("span");
    badge.className = "type-badge";
    badge.textContent = valueText(task.status);
    statusCell.appendChild(badge);
    tr.appendChild(statusCell);
    appendTextCell(tr, valueText(task.started_at));
    appendTextCell(tr, valueText(task.finished_at));
    appendTextCell(tr, valueText(task.returncode));
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
    const title = document.createElement("strong");
    const detail = document.createElement("span");
    title.textContent = `${check.ok ? "OK" : "Falha"} - ${check.name}`;
    detail.textContent = check.detail || "";
    item.append(title, detail);
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
startLibraryAnalysisEl.addEventListener("click", startLibraryAnalysis);
cancelAnalysisEl.addEventListener("click", cancelAnalysis);
analysisFileEl.addEventListener("change", () => analyzeAudioFiles(analysisFileEl.files));
analysisDropZoneEl.addEventListener("dragenter", (event) => {
  event.preventDefault();
  analysisDropZoneEl.classList.add("drag-active");
});
analysisDropZoneEl.addEventListener("dragover", (event) => {
  event.preventDefault();
  if (event.dataTransfer) event.dataTransfer.dropEffect = "copy";
  analysisDropZoneEl.classList.add("drag-active");
});
analysisDropZoneEl.addEventListener("dragleave", () => analysisDropZoneEl.classList.remove("drag-active"));
analysisDropZoneEl.addEventListener("drop", (event) => {
  event.preventDefault();
  analysisDropZoneEl.classList.remove("drag-active");
  analyzeAudioFiles(event.dataTransfer?.files);
});
analysisDropZoneEl.addEventListener("keydown", (event) => {
  if (event.key === "Enter" || event.key === " ") {
    event.preventDefault();
    analysisFileEl.click();
  }
});
startDownloadEl.addEventListener("click", startDownload);
cancelDownloadEl.addEventListener("click", cancelDownload);
testSpotifyLinkEl.addEventListener("click", testSpotifyLink);
downloadSourceEl.addEventListener("change", updateDownloadSourcePanels);
loadSheetEl.addEventListener("click", loadSheetPreview);
validateSheetEl.addEventListener("click", validateSheetRows);
sheetSearchEl.addEventListener("input", renderSheetRows);
sheetTypeFilterEl.addEventListener("change", renderSheetRows);
downloadSelectedSheetEl.addEventListener("click", startSelectedSheetDownload);
applySheetSelectionEl.addEventListener("click", applySheetSelection);
selectVisibleSheetEl.addEventListener("click", selectVisibleSheetRows);
selectAllSheetEl.addEventListener("click", selectAllSheetRows);
clearSheetSelectionEl.addEventListener("click", clearSheetSelection);
sheetRowSelectionEl.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    event.preventDefault();
    applySheetSelection();
  }
});
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
analysisLogFilterEl.addEventListener("input", () => renderTaskLog(analysisLogEl, analysisLogs, analysisLogFilterEl.value));
downloadShortcutEls.forEach((button) => {
  button.addEventListener("click", () => openDownloadShortcut(button.dataset.downloadShortcut));
});
openMusicFolderEls.forEach((button) => {
  button.addEventListener("click", openMusicFolder);
});
tagMusicEls.forEach((button) => {
  button.addEventListener("click", startTagMusic);
});
openAnalysisEls.forEach((button) => {
  button.addEventListener("click", openAnalysisSection);
});
window.addEventListener("resize", () => {
  drawAnalysisChart(analysisResults[selectedAnalysisIndex]);
});

updateDownloadSourcePanels();
renderAnalysisResults();
drawAnalysisChart(null);
loadConfig();
loadTasks();
loadEnvironment();
