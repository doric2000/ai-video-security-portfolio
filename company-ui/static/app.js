const state = {
  cameras: [],
  cameraMeta: {},
  camera: "front_door",
  events: [],
  alerts: [],
  frigateConfig: {},
  filter: "all",
  snapshotTimer: null,
  selectedEventId: null,
  pendingDelete: null,
  lastFocus: null,
  timeline: { camera: "all", range: "7d", type: "all" },
  setup: {
    mode: "existing",
    stage: 1,
    proposal: null,
    drawings: { masks: [], zones: [] },
    currentPoints: [],
    profiles: [],
    profile: "",
    rtspTested: false,
  },
};

const WIZARD_TOTAL_STAGES = 6;

const els = {
  status: document.getElementById("systemStatus"),
  systemText: document.getElementById("systemText"),
  pageTitle: document.getElementById("pageTitle"),
  pageSubtitle: document.getElementById("pageSubtitle"),
  cameraSelect: document.getElementById("cameraSelect"),
  refreshButton: document.getElementById("refreshButton"),
  activeCamera: document.getElementById("activeCamera"),
  aiMode: document.getElementById("aiMode"),
  openAlerts: document.getElementById("openAlerts"),
  eventsToday: document.getElementById("eventsToday"),
  alertCount: document.getElementById("alertCount"),
  eventCount: document.getElementById("eventCount"),
  cameraWall: document.getElementById("cameraWall"),
  cameraWallCount: document.getElementById("cameraWallCount"),
  liveImage: document.getElementById("liveImage"),
  liveFallback: document.getElementById("liveFallback"),
  snapshotTime: document.getElementById("snapshotTime"),
  alertList: document.getElementById("alertList"),
  decisionTable: document.getElementById("decisionTable"),
  eventReviewList: document.getElementById("eventReviewList"),
  policyEditor: document.getElementById("policyEditor"),
  savePolicy: document.getElementById("savePolicy"),
  policyStatus: document.getElementById("policyStatus"),
  policyCamera: document.getElementById("policyCamera"),
  policyProfile: document.getElementById("policyProfile"),
  policySensitivity: document.getElementById("policySensitivity"),
  policyHours: document.getElementById("policyHours"),
  policyLocation: document.getElementById("policyLocation"),
  frigateEditor: document.getElementById("frigateEditor"),
  frigateStatus: document.getElementById("frigateStatus"),
  saveFrigateConfig: document.getElementById("saveFrigateConfig"),
  applyQuickConfig: document.getElementById("applyQuickConfig"),
  trackedObjects: document.getElementById("trackedObjects"),
  globalDetect: document.getElementById("globalDetect"),
  recordEnabled: document.getElementById("recordEnabled"),
  mqttEnabled: document.getElementById("mqttEnabled"),
  frigateCameras: document.getElementById("frigateCameras"),
  frigateObjects: document.getElementById("frigateObjects"),
  frigateDetect: document.getElementById("frigateDetect"),
  frigateRecord: document.getElementById("frigateRecord"),
  frigateMqtt: document.getElementById("frigateMqtt"),
  eventModal: document.getElementById("eventModal"),
  closeEventModal: document.getElementById("closeEventModal"),
  manageCamerasList: document.getElementById("manageCamerasList"),
  manageCamerasCount: document.getElementById("manageCamerasCount"),
  cameraInfoModal: document.getElementById("cameraInfoModal"),
  closeCameraInfoModal: document.getElementById("closeCameraInfoModal"),
  cameraInfoTitle: document.getElementById("cameraInfoTitle"),
  cameraInfoSubtitle: document.getElementById("cameraInfoSubtitle"),
  cameraInfoLocation: document.getElementById("cameraInfoLocation"),
  cameraInfoProfileTag: document.getElementById("cameraInfoProfileTag"),
  cameraInfoProfileDesc: document.getElementById("cameraInfoProfileDesc"),
  cameraInfoSensitivity: document.getElementById("cameraInfoSensitivity"),
  cameraInfoHours: document.getElementById("cameraInfoHours"),
  cameraInfoNormal: document.getElementById("cameraInfoNormal"),
  cameraInfoSuspicious: document.getElementById("cameraInfoSuspicious"),
  cameraInfoDescriptionRow: document.getElementById("cameraInfoDescriptionRow"),
  cameraInfoDescription: document.getElementById("cameraInfoDescription"),
  editCameraFromInfo: document.getElementById("editCameraFromInfo"),
  deleteCameraDialog: document.getElementById("deleteCameraDialog"),
  deleteCameraName: document.getElementById("deleteCameraName"),
  deleteCameraCancel: document.getElementById("deleteCameraCancel"),
  deleteCameraConfirm: document.getElementById("deleteCameraConfirm"),
  eventModalTitle: document.getElementById("eventModalTitle"),
  eventModalSubtitle: document.getElementById("eventModalSubtitle"),
  eventVideo: document.getElementById("eventVideo"),
  eventVideoError: document.getElementById("eventVideoError"),
  modalDecision: document.getElementById("modalDecision"),
  modalSeverity: document.getElementById("modalSeverity"),
  modalConfidence: document.getElementById("modalConfidence"),
  modalMode: document.getElementById("modalMode"),
  eventModalSummary: document.getElementById("eventModalSummary"),
  setupStatus: document.getElementById("setupStatus"),
  setupCameraSelect: document.getElementById("setupCameraSelect"),
  setupCameraId: document.getElementById("setupCameraId"),
  setupRtspUrl: document.getElementById("setupRtspUrl"),
  setupLocation: document.getElementById("setupLocation"),
  setupSensitivity: document.getElementById("setupSensitivity"),
  setupWorkingDays: document.getElementById("setupWorkingDays"),
  setupTimezone: document.getElementById("setupTimezone"),
  setupStartTime: document.getElementById("setupStartTime"),
  setupEndTime: document.getElementById("setupEndTime"),
  setupHoursEnabled: document.getElementById("setupHoursEnabled"),
  setupNormalActivity: document.getElementById("setupNormalActivity"),
  setupRisks: document.getElementById("setupRisks"),
  setupDescription: document.getElementById("setupDescription"),
  setupTrackedObjects: document.getElementById("setupTrackedObjects"),
  setupDetectWidth: document.getElementById("setupDetectWidth"),
  setupDetectHeight: document.getElementById("setupDetectHeight"),
  setupFps: document.getElementById("setupFps"),
  setupRetainDays: document.getElementById("setupRetainDays"),
  setupMinSeverity: document.getElementById("setupMinSeverity"),
  setupMinConfidence: document.getElementById("setupMinConfidence"),
  setupRecordingEnabled: document.getElementById("setupRecordingEnabled"),
  drawingType: document.getElementById("drawingType"),
  drawingName: document.getElementById("drawingName"),
  drawingCount: document.getElementById("drawingCount"),
  timelineCameraSelect: document.getElementById("timelineCameraSelect"),
  timelineChart: document.getElementById("timelineChart"),
  timelineList: document.getElementById("timelineList"),
  timelineCount: document.getElementById("timelineCount"),
  setupSnapshot: document.getElementById("setupSnapshot"),
  drawingCanvas: document.getElementById("drawingCanvas"),
  setupSnapshotFallback: document.getElementById("setupSnapshotFallback"),
  finishDrawing: document.getElementById("finishDrawing"),
  clearDrawings: document.getElementById("clearDrawings"),
  drawingList: document.getElementById("drawingList"),
  generateSetup: document.getElementById("generateSetup"),
  saveSetup: document.getElementById("saveSetup"),
  resetSetup: document.getElementById("resetSetup"),
  setupSummary: document.getElementById("setupSummary"),
  setupContextPreview: document.getElementById("setupContextPreview"),
  setupFrigatePreview: document.getElementById("setupFrigatePreview"),
  setupPrev: document.getElementById("setupPrev"),
  setupNext: document.getElementById("setupNext"),
  rtspTestButton: document.getElementById("rtspTestButton"),
  rtspTestStatus: document.getElementById("rtspTestStatus"),
  rtspTestAlert: document.getElementById("rtspTestAlert"),
  rtspTestPreview: document.getElementById("rtspTestPreview"),
  rtspSnapshot: document.getElementById("rtspSnapshot"),
  rtspCodec: document.getElementById("rtspCodec"),
  rtspResolution: document.getElementById("rtspResolution"),
  profileCards: document.getElementById("profileCards"),
  wizardProgress: document.getElementById("wizardProgress"),
  setupDayGrid: document.getElementById("setupDayGrid"),
  workingHoursFields: document.getElementById("workingHoursFields"),
  normalActivityHint: document.getElementById("normalActivityHint"),
  risksHint: document.getElementById("risksHint"),
};

function fmtTime(value) {
  if (!value) return "-";
  const date = typeof value === "number" ? new Date(value * 1000) : new Date(value);
  if (Number.isNaN(date.getTime())) return "-";
  return date.toLocaleString([], { month: "short", day: "2-digit", hour: "2-digit", minute: "2-digit" });
}

function severityClass(severity) {
  if (severity >= 4) return "critical";
  if (severity >= 3) return "warn";
  return "";
}

function setHealthy(ok, text) {
  els.status.classList.toggle("ok", ok);
  els.status.classList.toggle("bad", !ok);
  els.systemText.textContent = text;
}

function get(obj, path, fallback) {
  let current = obj;
  for (const key of path) {
    if (current === null || current === undefined) return fallback;
    current = current[key];
  }
  return current === undefined || current === null ? fallback : current;
}

function escapeHtml(value) {
  return String(value === undefined || value === null ? "" : value).replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    "\"": "&quot;",
    "'": "&#39;",
  })[char]);
}

async function fetchJson(url, options) {
  const res = await fetch(url, options);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

async function loadCameras() {
  const data = await fetchJson("/api/cameras");
  state.cameras = data.cameras && data.cameras.length ? data.cameras : ["front_door"];
  if (!state.cameras.includes(state.camera)) state.camera = state.cameras[0];
  els.cameraSelect.innerHTML = state.cameras.map((camera) => (
    `<option value="${camera}" ${camera === state.camera ? "selected" : ""}>${camera}</option>`
  )).join("");
  els.setupCameraSelect.innerHTML = state.cameras.map((camera) => (
    `<option value="${camera}" ${camera === state.camera ? "selected" : ""}>${camera}</option>`
  )).join("");
  if (!els.setupCameraId.value) els.setupCameraId.value = state.camera;
  const prevTlCamera = state.timeline.camera;
  els.timelineCameraSelect.innerHTML = `<option value="all">All cameras</option>` +
    state.cameras.map((camera) => `<option value="${camera}">${camera}</option>`).join("");
  els.timelineCameraSelect.value = prevTlCamera;
}

function cameraSnapshotUrl(camera) {
  return `/api/frigate/${encodeURIComponent(camera)}/latest.jpg?bbox=1&ts=${Date.now()}`;
}

async function loadCamerasWithMeta() {
  const meta = {};
  await Promise.all(state.cameras.map(async (camera) => {
    try {
      const data = await fetchJson(`/api/context?camera=${encodeURIComponent(camera)}`);
      meta[camera] = data.parsed || {};
    } catch (err) {
      console.warn("Failed to load context for", camera, err);
      meta[camera] = {};
    }
  }));
  state.cameraMeta = meta;
  renderManageCameras();
}

function profileDisplayName(profileName) {
  const profile = (state.setup.profiles || []).find((p) => p.name === profileName);
  return profile ? (profile.display_name || profile.name) : (profileName || "—");
}

function renderManageCameras() {
  if (!els.manageCamerasList) return;
  const cameras = state.cameras || [];
  els.manageCamerasCount.textContent = `${cameras.length} ${cameras.length === 1 ? "camera" : "cameras"}`;
  if (!cameras.length) {
    els.manageCamerasList.innerHTML = `<div class="empty">No cameras configured yet. Add one below.</div>`;
    return;
  }
  els.manageCamerasList.innerHTML = cameras.map((camera) => {
    const ctx = state.cameraMeta[camera] || {};
    const location = get(ctx, ["camera_view", "location_name"], "");
    const profile = ctx.profile || "";
    const displayName = profileDisplayName(profile);
    return `
      <div class="manage-camera-row">
        <div class="manage-camera-main">
          <strong>${escapeHtml(camera)}</strong>
          ${location ? `<span class="muted">${escapeHtml(location)}</span>` : ""}
        </div>
        <sl-tag size="small" variant="neutral">${escapeHtml(displayName)}</sl-tag>
        <sl-icon-button class="manage-camera-delete" name="trash" label="Remove camera" data-camera="${escapeHtml(camera)}"></sl-icon-button>
      </div>
    `;
  }).join("");
}

function confirmDeleteCamera(camera) {
  if (!camera) return;
  state.pendingDelete = camera;
  els.deleteCameraName.textContent = camera;
  els.deleteCameraDialog.show();
}

async function performDeleteCamera() {
  const camera = state.pendingDelete;
  if (!camera) return;
  els.deleteCameraConfirm.loading = true;
  try {
    await fetchJson("/api/setup/delete", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ camera_id: camera }),
    });
    state.pendingDelete = null;
    els.deleteCameraDialog.hide();
    await loadCameras();
    await loadCamerasWithMeta();
    if (state.camera === camera) {
      state.camera = state.cameras[0] || "";
      els.cameraSelect.value = state.camera;
    }
    await Promise.all([loadPolicy(), loadFrigateConfig()]);
    updateSnapshot();
    renderAll();
  } catch (err) {
    console.error("delete failed", err);
    alert(`Delete failed: ${err.message}`);
  } finally {
    els.deleteCameraConfirm.loading = false;
  }
}

// ---------- Camera info modal ----------

function formatWorkingHoursPretty(wh) {
  if (!wh || wh.enabled === false) return "Active 24/7";
  const days = Array.isArray(wh.days) ? wh.days : [];
  const start = wh.start || "00:00";
  const end = wh.end || "23:59";
  const tz = wh.timezone ? ` (${wh.timezone})` : "";
  if (!days.length) return `Always, ${start}–${end}${tz}`;
  const order = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
  const sorted = order.filter((d) => days.includes(d));
  // Detect contiguous range to render Sun–Thu style
  const indices = sorted.map((d) => order.indexOf(d));
  const isContiguous = indices.length > 1 && indices.every((v, i, a) => i === 0 || v === a[i - 1] + 1);
  const daysText = isContiguous ? `${sorted[0]}–${sorted[sorted.length - 1]}` : sorted.join(", ");
  return `${daysText}, ${start}–${end}${tz}`;
}

async function openCameraInfoModal(camera) {
  if (!camera) return;
  state.lastFocus = document.activeElement;
  let ctx = state.cameraMeta[camera];
  if (!ctx) {
    try {
      const data = await fetchJson(`/api/context?camera=${encodeURIComponent(camera)}`);
      ctx = data.parsed || {};
      state.cameraMeta[camera] = ctx;
    } catch (err) {
      console.error(err);
      ctx = {};
    }
  }
  const view = ctx.camera_view || {};
  const intent = ctx.security_intent || {};
  const wh = ctx.working_hours || {};
  const profileName = ctx.profile || "";
  els.cameraInfoTitle.textContent = camera;
  els.cameraInfoSubtitle.textContent = view.location_name || "Camera details";
  els.cameraInfoLocation.textContent = view.location_name || "—";
  els.cameraInfoProfileTag.textContent = profileDisplayName(profileName) || "—";
  const profile = (state.setup.profiles || []).find((p) => p.name === profileName);
  els.cameraInfoProfileDesc.textContent = profile ? (profile.description || "") : "";
  els.cameraInfoSensitivity.textContent = (ctx.sensitivity || "—").replace(/^./, (c) => c.toUpperCase());
  els.cameraInfoHours.textContent = formatWorkingHoursPretty(wh);
  const normal = Array.isArray(intent.what_is_normal) ? intent.what_is_normal : [];
  const suspicious = Array.isArray(intent.what_is_suspicious) ? intent.what_is_suspicious : (intent.primary_risks || []);
  els.cameraInfoNormal.innerHTML = normal.length
    ? normal.map((item) => `<li>${escapeHtml(item)}</li>`).join("")
    : `<li class="muted">No notes.</li>`;
  els.cameraInfoSuspicious.innerHTML = suspicious.length
    ? suspicious.map((item) => `<li>${escapeHtml(item)}</li>`).join("")
    : `<li class="muted">No notes.</li>`;
  if (view.description) {
    els.cameraInfoDescription.textContent = view.description;
    els.cameraInfoDescriptionRow.hidden = false;
  } else {
    els.cameraInfoDescriptionRow.hidden = true;
  }
  els.editCameraFromInfo.dataset.camera = camera;
  els.cameraInfoModal.classList.remove("hidden");
  els.cameraInfoModal.setAttribute("aria-hidden", "false");
  document.body.classList.add("modal-open");
  els.closeCameraInfoModal.focus();
}

function closeCameraInfoModal() {
  els.cameraInfoModal.classList.add("hidden");
  els.cameraInfoModal.setAttribute("aria-hidden", "true");
  document.body.classList.remove("modal-open");
  if (state.lastFocus && typeof state.lastFocus.focus === "function") {
    state.lastFocus.focus();
  }
}

async function editCameraFromInfo() {
  const camera = els.editCameraFromInfo.dataset.camera;
  if (!camera) return;
  closeCameraInfoModal();
  setView("setup");
  updateSetupMode("existing");
  if (state.cameras.includes(camera)) {
    state.camera = camera;
    els.cameraSelect.value = camera;
    els.setupCameraSelect.value = camera;
  }
  await loadSetupDefaults(camera);
  showStage(1);
}

async function loadEvents() {
  const [events, alerts] = await Promise.all([
    fetchJson("/api/ai/events?limit=80"),
    fetchJson("/api/ai/alerts?limit=40"),
  ]);
  state.events = events.events || [];
  state.alerts = alerts.alerts || [];
}

async function loadPolicy() {
  const data = await fetchJson(`/api/context?camera=${encodeURIComponent(state.camera)}`);
  els.policyEditor.value = data.content || "";
  els.policyCamera.textContent = `${state.camera}.yaml`;
  const parsed = data.parsed || {};
  els.policyProfile.textContent = parsed.profile || "-";
  els.policySensitivity.textContent = parsed.sensitivity || "-";
  els.policyLocation.textContent = get(parsed, ["camera_view", "location_name"], "-");
  const wh = parsed.working_hours || {};
  els.policyHours.textContent = wh.enabled ? `${(wh.days || []).join(", ")} ${wh.start || ""}-${wh.end || ""}` : "Disabled";
}

function yamlScalar(value) {
  if (value === null || value === undefined) return "null";
  if (typeof value === "boolean") return value ? "true" : "false";
  if (typeof value === "number") return String(value);
  const text = String(value);
  if (!text || /[:#\n\r\t[\]{},&*?|-]|^\s|\s$|^(true|false|null|yes|no|on|off)$/i.test(text)) {
    return JSON.stringify(text);
  }
  return text;
}

function dumpYaml(value, indent = 0) {
  const pad = " ".repeat(indent);
  if (Array.isArray(value)) {
    if (!value.length) return "[]";
    return value.map((item) => {
      if (item && typeof item === "object") {
        return `${pad}-\n${dumpYaml(item, indent + 2)}`;
      }
      return `${pad}- ${yamlScalar(item)}`;
    }).join("\n");
  }
  if (value && typeof value === "object") {
    const entries = Object.entries(value);
    if (!entries.length) return "{}";
    return entries.map(([key, item]) => {
      if (item && typeof item === "object") {
        return `${pad}${key}:\n${dumpYaml(item, indent + 2)}`;
      }
      return `${pad}${key}: ${yamlScalar(item)}`;
    }).join("\n");
  }
  return `${pad}${yamlScalar(value)}`;
}

async function loadFrigateConfig() {
  const data = await fetchJson("/api/frigate-config");
  state.frigateConfig = data.parsed || {};
  els.frigateEditor.value = data.content || "";
  renderFrigateConfig();
}

function renderFrigateConfig() {
  const cfg = state.frigateConfig || {};
  const objects = get(cfg, ["objects", "track"], []);
  const cameras = Object.keys(cfg.cameras || {});
  els.trackedObjects.value = objects.join(", ");
  els.globalDetect.checked = get(cfg, ["detect", "enabled"], true) !== false;
  els.recordEnabled.checked = get(cfg, ["record", "enabled"], false) === true;
  els.mqttEnabled.checked = get(cfg, ["mqtt", "enabled"], false) === true;
  els.frigateCameras.textContent = cameras.length ? cameras.join(", ") : "-";
  els.frigateObjects.textContent = objects.length ? objects.join(", ") : "-";
  els.frigateDetect.textContent = get(cfg, ["detect", "enabled"], true) === false ? "Disabled" : "Enabled";
  els.frigateRecord.textContent = get(cfg, ["record", "enabled"], false) ? "Enabled" : "Disabled";
  els.frigateMqtt.textContent = get(cfg, ["mqtt", "enabled"], false) ? `${get(cfg, ["mqtt", "host"], "mqtt")}:${get(cfg, ["mqtt", "port"], 1883)}` : "Disabled";
}

function applyQuickConfig() {
  const cfg = JSON.parse(JSON.stringify(state.frigateConfig || {}));
  cfg.objects = cfg.objects || {};
  cfg.objects.track = els.trackedObjects.value.split(",").map((item) => item.trim()).filter(Boolean);
  cfg.detect = cfg.detect || {};
  cfg.detect.enabled = els.globalDetect.checked;
  cfg.record = cfg.record || {};
  cfg.record.enabled = els.recordEnabled.checked;
  cfg.mqtt = cfg.mqtt || {};
  cfg.mqtt.enabled = els.mqttEnabled.checked;
  state.frigateConfig = cfg;
  els.frigateEditor.value = dumpYaml(cfg) + "\n";
  renderFrigateConfig();
  els.frigateStatus.textContent = "Quick settings applied to editor";
}

async function saveFrigateConfig() {
  els.frigateStatus.textContent = "Saving";
  try {
    const data = await fetchJson("/api/frigate-config", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content: els.frigateEditor.value }),
    });
    state.frigateConfig = data.parsed || {};
    els.frigateStatus.textContent = data.ok ? "Saved. Restart Frigate to apply service-level changes." : "Save failed";
    renderFrigateConfig();
  } catch (err) {
    els.frigateStatus.textContent = "Save failed";
    console.error(err);
  }
}

function lines(value) {
  return String(value || "").split(/\n|,/).map((item) => item.trim()).filter(Boolean);
}

function setSetupStatus(text, isError) {
  els.setupStatus.textContent = text;
  els.setupStatus.classList.toggle("bad-text", Boolean(isError));
}

function setupCameraId() {
  return state.setup.mode === "existing" ? els.setupCameraSelect.value : els.setupCameraId.value.trim();
}

// ---------- Wizard navigation ----------

function toggleHidden(el, hidden) {
  if (!el) return;
  if (hidden) {
    el.setAttribute("hidden", "");
    el.style.display = "none";
  } else {
    el.removeAttribute("hidden");
    el.style.removeProperty("display");
  }
}

function showStage(stage) {
  state.setup.stage = stage;
  document.querySelectorAll(".wizard-stage").forEach((el) => {
    el.classList.toggle("active", Number(el.dataset.stage) === stage);
  });
  document.querySelectorAll(".wizard-progress-item").forEach((el) => {
    const idx = Number(el.dataset.stage);
    el.classList.toggle("active", idx === stage);
    el.classList.toggle("done", idx < stage);
  });
  // Show Next on stages < final, Save on the final stage.
  // Use both the hidden attribute AND an inline style — Shoelace web components
  // don't always honor the global `hidden` attribute due to shadow-DOM display rules.
  const onLast = stage === WIZARD_TOTAL_STAGES;
  toggleHidden(els.setupNext, onLast);
  toggleHidden(els.saveSetup, !onLast);
  // Disable Back on first stage.
  els.setupPrev.disabled = stage === 1;
  setSetupStatus(`Step ${stage} of ${WIZARD_TOTAL_STAGES}`, false);
  if (onLast) {
    generateSetupProposal();
  }
}

function nextStage() {
  const stage = state.setup.stage;
  const err = validateStage(stage);
  if (err) {
    setSetupStatus(err, true);
    return;
  }
  let target = stage + 1;
  // Skip the working-hours stage if the chosen profile does not need it.
  if (target === 4 && !profileNeedsWorkingHours()) target = 5;
  if (target > WIZARD_TOTAL_STAGES) target = WIZARD_TOTAL_STAGES;
  showStage(target);
}

function prevStage() {
  let target = state.setup.stage - 1;
  if (target === 4 && !profileNeedsWorkingHours()) target = 3;
  if (target < 1) target = 1;
  showStage(target);
}

function validateStage(stage) {
  if (stage === 1) {
    const id = setupCameraId();
    if (!id) return "Pick a camera or enter an ID.";
    if (state.setup.mode === "new" && !els.setupRtspUrl.value.trim()) return "RTSP URL is required.";
    if (state.setup.mode === "new" && !state.setup.rtspTested) return "Test the connection before continuing.";
    return null;
  }
  if (stage === 2) {
    if (!state.setup.profile) return "Pick a profile to continue.";
    return null;
  }
  if (stage === 3) {
    if (!els.setupLocation.value.trim()) return "Give the camera a location name.";
    return null;
  }
  if (stage === 4) {
    if (els.setupHoursEnabled.checked && selectedDays().length === 0) {
      return "Select at least one working day.";
    }
    return null;
  }
  return null;
}

function profileNeedsWorkingHours() {
  const profile = state.setup.profiles.find((p) => p.name === state.setup.profile);
  if (!profile) return true;
  return Boolean(profile.working_hours_required);
}

// ---------- Profile cards ----------

async function loadProfiles() {
  try {
    const data = await fetchJson("/api/profiles");
    state.setup.profiles = Array.isArray(data.profiles) ? data.profiles : [];
  } catch (err) {
    console.error("Failed to load profiles", err);
    state.setup.profiles = [];
  }
  renderProfileCards();
}

function renderProfileCards() {
  const cards = state.setup.profiles;
  if (!cards.length) {
    els.profileCards.innerHTML = `<div class="empty">No profiles available.</div>`;
    return;
  }
  els.profileCards.innerHTML = cards.map((p) => `
    <button type="button" class="profile-card${state.setup.profile === p.name ? " selected" : ""}" data-profile="${escapeHtml(p.name)}">
      <div class="profile-card-header">
        <strong>${escapeHtml(p.display_name || p.name)}</strong>
        <sl-tag size="small" variant="${p.working_hours_required ? "neutral" : "success"}">
          ${p.working_hours_required ? "Uses working hours" : "Active 24/7"}
        </sl-tag>
      </div>
      <p>${escapeHtml(p.description || "")}</p>
    </button>
  `).join("");
  els.profileCards.querySelectorAll(".profile-card").forEach((btn) => {
    btn.addEventListener("click", () => selectProfile(btn.dataset.profile));
  });
}

function selectProfile(name) {
  state.setup.profile = name;
  document.querySelectorAll(".profile-card").forEach((card) => {
    card.classList.toggle("selected", card.dataset.profile === name);
  });
  updateActivityHints();
  resetSetupPreview();
}

function updateActivityHints() {
  const profile = state.setup.profiles.find((p) => p.name === state.setup.profile);
  if (!profile) return;
  const map = {
    office_standard: {
      normal: "e.g. Employees walking through during the day. Visitors waiting at reception.",
      risks: "e.g. After-hours presence. Loitering near equipment. Removing devices.",
    },
    facility_24x7: {
      normal: "e.g. Drivers arriving with deliveries. Forklifts moving pallets.",
      risks: "e.g. Loitering near restricted zones. Tampering with equipment.",
    },
    datacenter_high: {
      normal: "e.g. Authorized engineers during scheduled maintenance windows.",
      risks: "e.g. Any unauthorized presence. Tampering with racks. Photographing screens.",
    },
  };
  const m = map[profile.name];
  if (m) {
    if (els.normalActivityHint) els.normalActivityHint.textContent = m.normal;
    if (els.risksHint) els.risksHint.textContent = m.risks;
  }
}

// ---------- Working days ----------

function selectedDays() {
  if (!els.setupDayGrid) return [];
  return Array.from(els.setupDayGrid.querySelectorAll("input[type=checkbox]:checked")).map((el) => el.value);
}

function setSelectedDays(days) {
  if (!els.setupDayGrid) return;
  const want = new Set((days || []).map(String));
  els.setupDayGrid.querySelectorAll("input[type=checkbox]").forEach((el) => {
    el.checked = want.has(el.value);
  });
}

// ---------- RTSP probe ----------

async function testRtspConnection() {
  const url = els.setupRtspUrl.value.trim();
  if (!url) {
    setRtspStatus("Enter an RTSP URL first.", "warning");
    return;
  }
  els.rtspTestButton.loading = true;
  setRtspStatus("Testing connection…", "neutral");
  els.rtspTestPreview.classList.add("hidden");
  try {
    const data = await fetchJson("/api/rtsp-probe", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ rtsp_url: url }),
    });
    if (!data.ok) {
      state.setup.rtspTested = false;
      setRtspStatus(`Connection failed: ${data.error || "unknown error"}`, "danger");
      return;
    }
    state.setup.rtspTested = true;
    setRtspStatus("Connection OK — stream is reachable.", "success");
    els.rtspCodec.textContent = data.codec || "-";
    els.rtspResolution.textContent = data.resolution || "-";
    if (data.snapshot_b64) {
      els.rtspSnapshot.src = `data:image/jpeg;base64,${data.snapshot_b64}`;
      els.rtspSnapshot.classList.remove("hidden");
    } else {
      els.rtspSnapshot.classList.add("hidden");
    }
    els.rtspTestPreview.classList.remove("hidden");
  } catch (err) {
    state.setup.rtspTested = false;
    setRtspStatus(`Connection failed: ${err.message}`, "danger");
  } finally {
    els.rtspTestButton.loading = false;
  }
}

function setRtspStatus(text, variant) {
  els.rtspTestStatus.textContent = text;
  if (els.rtspTestAlert) {
    const v = variant || "neutral";
    els.rtspTestAlert.variant = v;
    const iconSlot = els.rtspTestAlert.querySelector('sl-icon[slot="icon"]');
    if (iconSlot) {
      iconSlot.name = ({
        success: "check2-circle",
        danger: "exclamation-octagon",
        warning: "exclamation-triangle",
        neutral: "info-circle",
      })[v] || "info-circle";
    }
  }
}

function clearSetupFormForNew() {
  els.setupCameraId.value = "";
  els.setupRtspUrl.value = "";
  els.setupLocation.value = "";
  els.setupSensitivity.value = "medium";
  els.setupDescription.value = "";
  els.setupNormalActivity.value = "";
  els.setupRisks.value = "";
  els.setupHoursEnabled.checked = true;
  els.setupTimezone.value = "Asia/Jerusalem";
  setSelectedDays(["Sun", "Mon", "Tue", "Wed", "Thu"]);
  els.setupStartTime.value = "09:00";
  els.setupEndTime.value = "17:00";
  els.setupTrackedObjects.value = "person";
  els.setupDetectWidth.value = "896";
  els.setupDetectHeight.value = "512";
  els.setupFps.value = "5";
  els.setupRetainDays.value = "7";
  els.setupMinSeverity.value = "3";
  els.setupMinConfidence.value = "0.70";
  els.setupRecordingEnabled.checked = true;
  state.setup.rtspTested = false;
  state.setup.profile = "";
  document.querySelectorAll(".profile-card").forEach((card) => card.classList.remove("selected"));
  setRtspStatus("Click \"Test connection\" to verify the stream before continuing.", "neutral");
  if (els.rtspTestPreview) els.rtspTestPreview.classList.add("hidden");
}

function updateSetupMode(mode) {
  state.setup.mode = mode;
  document.querySelectorAll("[data-setup-mode]").forEach((button) => {
    button.classList.toggle("active", button.dataset.setupMode === mode);
  });
  document.querySelectorAll(".new-camera-field").forEach((field) => field.classList.toggle("hidden", mode !== "new"));
  document.querySelectorAll(".existing-camera-field").forEach((field) => field.classList.toggle("hidden", mode !== "existing"));
  els.setupCameraId.disabled = mode === "existing";
  if (mode === "existing") {
    els.setupCameraId.value = els.setupCameraSelect.value || state.camera;
    state.setup.rtspTested = true;
    setRtspStatus("Existing camera — already connected.", "success");
    updateSetupSnapshot();
  } else {
    els.setupCameraId.disabled = false;
    els.setupSnapshot.classList.add("hidden");
    els.setupSnapshotFallback.classList.remove("hidden");
    clearSetupFormForNew();
    resetSetupWizard();
  }
  resetSetupPreview();
  if (state.setup.stage !== 1) showStage(1);
}

async function loadSetupDefaults(camera) {
  const cameraId = camera || setupCameraId() || state.camera;
  try {
    const data = await fetchJson(`/api/setup/defaults?camera=${encodeURIComponent(cameraId)}`);
    const ctx = data.context || {};
    const defaults = data.defaults || {};
    const wh = ctx.working_hours || defaults.working_hours || {};
    const view = ctx.camera_view || {};
    const intent = ctx.security_intent || {};
    const detect = defaults.detect || {};
    const recording = defaults.recording || {};
    const notifications = defaults.notifications || {};
    if (Array.isArray(data.profiles) && data.profiles.length) {
      state.setup.profiles = data.profiles;
      renderProfileCards();
    }
    els.setupCameraId.value = data.camera_id || cameraId;
    els.setupRtspUrl.value = data.rtsp_url || "";
    els.setupLocation.value = view.location_name || "";
    els.setupSensitivity.value = ctx.sensitivity || "medium";
    els.setupDescription.value = view.description || "";
    els.setupNormalActivity.value = (intent.what_is_normal || []).join("\n");
    els.setupRisks.value = (intent.what_is_suspicious || intent.primary_risks || []).join("\n");
    els.setupHoursEnabled.checked = wh.enabled !== false;
    els.setupTimezone.value = wh.timezone || defaults.timezone || "Asia/Jerusalem";
    setSelectedDays(wh.days || defaults.working_days || ["Sun", "Mon", "Tue", "Wed", "Thu"]);
    els.setupStartTime.value = wh.start || defaults.working_start || "09:00";
    els.setupEndTime.value = wh.end || defaults.working_end || "17:00";
    els.setupTrackedObjects.value = (data.tracked_objects || ["person"]).join(", ");
    els.setupDetectWidth.value = detect.width || 896;
    els.setupDetectHeight.value = detect.height || 512;
    els.setupFps.value = detect.fps || 5;
    els.setupRecordingEnabled.checked = recording.enabled !== false;
    els.setupRetainDays.value = recording.retain_days || 7;
    els.setupMinSeverity.value = notifications.min_severity || 3;
    els.setupMinConfidence.value = notifications.min_confidence || 0.7;
    if (ctx.profile) {
      selectProfile(ctx.profile);
    }
    // For existing cameras, the stream is already verified by Frigate — skip the probe gate.
    if (state.setup.mode === "existing") state.setup.rtspTested = true;
    updateSetupSnapshot();
  } catch (err) {
    setSetupStatus("Defaults failed", true);
    console.error(err);
  }
}

function setupAnswers() {
  return {
    location_name: els.setupLocation.value,
    sensitivity: els.setupSensitivity.value,
    camera_description: els.setupDescription.value,
    normal_activity: lines(els.setupNormalActivity.value),
    risks_to_monitor: lines(els.setupRisks.value),
    tracked_objects: lines(els.setupTrackedObjects.value),
    profile: state.setup.profile || "",
    working_hours: {
      enabled: els.setupHoursEnabled.checked && profileNeedsWorkingHours(),
      timezone: els.setupTimezone.value,
      days: selectedDays(),
      start: els.setupStartTime.value,
      end: els.setupEndTime.value,
    },
    notifications: {
      min_severity: Number(els.setupMinSeverity.value || 3),
      min_confidence: Number(els.setupMinConfidence.value || 0.7),
    },
    recording: {
      enabled: els.setupRecordingEnabled.checked,
      retain_days: Number(els.setupRetainDays.value || 7),
    },
    detect: {
      enabled: true,
      width: Number(els.setupDetectWidth.value || 896),
      height: Number(els.setupDetectHeight.value || 512),
      fps: Number(els.setupFps.value || 5),
    },
  };
}

function resetSetupPreview() {
  state.setup.proposal = null;
  if (els.setupContextPreview) els.setupContextPreview.value = "";
  if (els.setupFrigatePreview) els.setupFrigatePreview.value = "";
  if (els.setupSummary) {
    els.setupSummary.textContent = "Preview will appear on the review step.";
    els.setupSummary.classList.add("empty");
  }
  if (els.saveSetup) els.saveSetup.disabled = true;
}

function resetSetupWizard() {
  state.setup.drawings = { masks: [], zones: [] };
  state.setup.currentPoints = [];
  resetSetupPreview();
  renderDrawingList();
  drawSetupOverlay();
}

function updateSetupSnapshot() {
  if (state.setup.mode !== "existing") return;
  const camera = setupCameraId();
  if (!camera) return;
  els.setupSnapshot.classList.remove("hidden");
  els.setupSnapshotFallback.classList.add("hidden");
  els.setupSnapshot.src = cameraSnapshotUrl(camera);
}

function resizeDrawingCanvas() {
  const rect = els.drawingCanvas.getBoundingClientRect();
  const width = Math.max(1, Math.round(rect.width));
  const height = Math.max(1, Math.round(rect.height));
  if (els.drawingCanvas.width !== width) els.drawingCanvas.width = width;
  if (els.drawingCanvas.height !== height) els.drawingCanvas.height = height;
}

function drawPolygon(ctx, points, color, fill) {
  if (!points.length) return;
  ctx.beginPath();
  points.forEach((point, index) => {
    const x = point[0] * els.drawingCanvas.width;
    const y = point[1] * els.drawingCanvas.height;
    if (index === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  if (fill && points.length > 2) ctx.closePath();
  ctx.strokeStyle = color;
  ctx.fillStyle = fill ? color.replace("1)", "0.16)") : color;
  ctx.lineWidth = 2;
  ctx.stroke();
  if (fill && points.length > 2) ctx.fill();
}

function drawSetupOverlay() {
  resizeDrawingCanvas();
  const ctx = els.drawingCanvas.getContext("2d");
  ctx.clearRect(0, 0, els.drawingCanvas.width, els.drawingCanvas.height);
  state.setup.drawings.masks.forEach((shape) => drawPolygon(ctx, shape.points, "rgba(223, 107, 100, 1)", true));
  state.setup.drawings.zones.forEach((shape) => drawPolygon(ctx, shape.points, "rgba(84, 192, 131, 1)", true));
  drawPolygon(ctx, state.setup.currentPoints, "rgba(106, 167, 216, 1)", false);
  state.setup.currentPoints.forEach((point) => {
    ctx.beginPath();
    ctx.arc(point[0] * els.drawingCanvas.width, point[1] * els.drawingCanvas.height, 4, 0, Math.PI * 2);
    ctx.fillStyle = "rgba(106, 167, 216, 1)";
    ctx.fill();
  });
}

function renderDrawingList() {
  const masks = state.setup.drawings.masks.map((shape) => ({ type: "mask", shape }));
  const zones = state.setup.drawings.zones.map((shape) => ({ type: "zone", shape }));
  const items = masks.concat(zones);
  els.drawingCount.textContent = `${items.length} ${items.length === 1 ? "shape" : "shapes"}`;
  if (!items.length) {
    els.drawingList.innerHTML = `<div class="empty">No masks or zones</div>`;
    return;
  }
  els.drawingList.innerHTML = items.map((item) => `
    <div class="drawing-item">
      <span>${escapeHtml(item.type)} · ${escapeHtml(item.shape.name)}</span>
      <span class="muted">${item.shape.points.length} points</span>
    </div>
  `).join("");
}

function finishCurrentDrawing() {
  if (state.setup.currentPoints.length < 3) {
    setSetupStatus("Draw at least 3 points", true);
    return;
  }
  const type = els.drawingType.value === "zone" ? "zones" : "masks";
  const fallback = type === "zones" ? "monitored_zone" : "ignore_mask";
  const name = els.drawingName.value.trim() || fallback;
  state.setup.drawings[type].push({ name, points: state.setup.currentPoints.slice() });
  state.setup.currentPoints = [];
  els.drawingName.value = "";
  resetSetupPreview();
  renderDrawingList();
  drawSetupOverlay();
}

async function generateSetupProposal() {
  const cameraId = setupCameraId();
  if (!cameraId) {
    setSetupStatus("Camera ID required", true);
    return;
  }
  setSetupStatus("Generating", false);
  els.generateSetup.disabled = true;
  els.saveSetup.disabled = true;
  try {
    const payload = {
      mode: state.setup.mode,
      camera_id: cameraId,
      rtsp_url: els.setupRtspUrl.value,
      answers: setupAnswers(),
      drawings: state.setup.drawings,
    };
    const proposal = await fetchJson("/api/setup/propose", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    state.setup.proposal = proposal;
    els.setupContextPreview.value = proposal.camera_context_yaml || dumpYaml(proposal.camera_context || {});
    els.setupFrigatePreview.value = proposal.frigate_config_yaml || dumpYaml(proposal.frigate_config || {});
    const warnings = proposal.warnings && proposal.warnings.length ? `\n\nWarnings:\n${proposal.warnings.join("\n")}` : "";
    els.setupSummary.textContent = `${proposal.summary || "Generated setup proposal."}${warnings}`;
    els.setupSummary.classList.remove("empty");
    els.saveSetup.disabled = false;
    setSetupStatus("Preview ready", false);
  } catch (err) {
    setSetupStatus("Generate failed", true);
    els.setupSummary.textContent = `Generate failed: ${err.message}`;
    els.setupSummary.classList.remove("empty");
    console.error(err);
  } finally {
    els.generateSetup.disabled = false;
  }
}

async function saveSetupProposal() {
  const proposal = state.setup.proposal;
  if (!proposal) return;
  setSetupStatus("Saving", false);
  els.saveSetup.disabled = true;
  try {
    const data = await fetchJson("/api/setup/apply", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        camera_id: proposal.camera_id,
        camera_context: proposal.camera_context,
        frigate_config: proposal.frigate_config,
      }),
    });
    setSetupStatus("Saved", false);
    els.setupSummary.textContent = data.message || "Saved. Restart Frigate to apply service-level changes.";
    await loadCameras();
    if (state.cameras.includes(proposal.camera_id)) {
      state.camera = proposal.camera_id;
      els.cameraSelect.value = state.camera;
      els.setupCameraSelect.value = state.camera;
    }
    await Promise.all([loadPolicy(), loadFrigateConfig(), loadCamerasWithMeta()]);
    updateSnapshot();
    renderAll();
    // Reset the wizard for the next camera and bounce back to Overview.
    clearSetupFormForNew();
    resetSetupPreview();
    state.setup.proposal = null;
    showStage(1);
    setView("overview");
  } catch (err) {
    setSetupStatus("Save failed", true);
    els.saveSetup.disabled = false;
    console.error(err);
  }
}

function updateSnapshot() {
  els.liveImage.onload = () => {
    els.liveImage.classList.remove("hidden");
    els.liveFallback.classList.add("hidden");
    els.snapshotTime.textContent = new Date().toLocaleTimeString();
  };
  els.liveImage.onerror = () => {
    els.liveImage.classList.add("hidden");
    els.liveFallback.classList.remove("hidden");
  };
  els.liveImage.src = cameraSnapshotUrl(state.camera);
}

function renderCameraWall() {
  const cameras = state.cameras || [];
  els.cameraWallCount.textContent = `${cameras.length} ${cameras.length === 1 ? "camera" : "cameras"}`;
  if (!cameras.length) {
    els.cameraWall.innerHTML = `<div class="empty">No cameras configured</div>`;
    return;
  }
  els.cameraWall.innerHTML = cameras.map((camera) => `
    <button class="camera-tile ${camera === state.camera ? "active" : ""}" type="button" data-camera="${escapeHtml(camera)}" aria-label="${escapeHtml(`Show details for ${camera}`)}">
      <div class="camera-tile-frame">
        <img src="${cameraSnapshotUrl(camera)}" alt="${escapeHtml(`${camera} camera frame`)}">
        <div class="camera-tile-empty empty hidden">No camera frame</div>
        <sl-icon-button class="camera-tile-focus" name="eye" label="Focus this camera" data-camera="${escapeHtml(camera)}"></sl-icon-button>
      </div>
      <div class="camera-tile-meta">
        <strong>${escapeHtml(camera)}</strong>
        <span>${camera === state.camera ? "Focused" : "Live"}</span>
      </div>
    </button>
  `).join("");
}

function refreshCameraWallFrames() {
  els.cameraWall.querySelectorAll(".camera-tile").forEach((tile) => {
    const camera = tile.dataset.camera;
    const img = tile.querySelector("img");
    const fallback = tile.querySelector(".camera-tile-empty");
    if (!camera || !img) return;
    if (fallback) fallback.classList.add("hidden");
    img.classList.remove("hidden");
    img.src = cameraSnapshotUrl(camera);
  });
}

function renderMetrics() {
  const today = new Date().toDateString();
  const eventsToday = state.events.filter((event) => {
    const ts = get(event, ["timeline", "end_time"], null) || get(event, ["timeline", "start_time"], null);
    return ts && new Date(ts * 1000).toDateString() === today;
  }).length;
  const latestEventWithMode = state.events.find((event) => event.analysis_mode);
  const latestMode = latestEventWithMode ? latestEventWithMode.analysis_mode : "video";
  els.openAlerts.textContent = state.alerts.length;
  els.eventsToday.textContent = eventsToday;
  els.aiMode.textContent = latestMode;
  els.activeCamera.textContent = state.camera;
  els.alertCount.textContent = String(state.alerts.length);
  els.eventCount.textContent = String(state.events.length);
}

function renderAlerts() {
  const alerts = state.alerts.slice(0, 6);
  if (!alerts.length) {
    els.alertList.innerHTML = `<div class="empty">No priority alerts</div>`;
    return;
  }
  els.alertList.innerHTML = alerts.map((alert) => `
    <article class="alert-item">
      <div class="alert-top">
        <strong>${alert.category || "Alert"}</strong>
        <span class="pill ${severityClass(alert.severity)}">S${alert.severity || 0}</span>
      </div>
      <div class="summary">${alert.summary || "No summary"}</div>
      <div class="muted">${alert.camera_id || "-"} · ${fmtTime(alert.timestamp)}</div>
    </article>
  `).join("");
}

function renderDecisionTable() {
  const rows = state.events.slice(0, 10);
  if (!rows.length) {
    els.decisionTable.innerHTML = `<div class="empty">No AI decisions</div>`;
    return;
  }
  els.decisionTable.innerHTML = rows.map((event) => {
    const decision = event.decision || {};
    const ts = get(event, ["timeline", "end_time"], null) || get(event, ["timeline", "start_time"], null);
    return `
      <div class="table-row">
        <div>${fmtTime(ts)}</div>
        <div><span class="pill ${decision.is_event ? severityClass(decision.severity) : ""}">${decision.is_event ? "Event" : "Clear"}</span></div>
        <div class="summary">${decision.summary || "No summary"}</div>
        <div class="muted">${event.analysis_mode || "-"}</div>
      </div>
    `;
  }).join("");
}

// Returns a Set of event_ids that triggered a stored alert
function alertEventIdSet() {
  return new Set((state.alerts || []).map((a) => a.event_id).filter(Boolean));
}

// Classifies one event record as "alert" | "event" | "clear"
function classifyEvent(event, alertIds) {
  if (alertIds.has(event.event_id)) return "alert";
  if (get(event, ["decision", "is_event"], false)) return "event";
  return "clear";
}

function filteredEvents() {
  const alertIds = alertEventIdSet();
  if (state.filter === "alert") return state.events.filter((e) => alertIds.has(e.event_id));
  if (state.filter === "event") return state.events.filter((e) => !alertIds.has(e.event_id));
  return state.events;
}

function findEventById(eventId) {
  return state.events.find((event) => String(event.event_id || "") === String(eventId));
}

function openEventModal(eventId) {
  const event = findEventById(eventId);
  if (!event || !event.event_id) return;

  const decision = event.decision || {};
  const ts = get(event, ["timeline", "end_time"], null) || get(event, ["timeline", "start_time"], null);
  const confidence = Math.round((decision.confidence || 0) * 100);
  const category = decision.category || "AI Review";
  const status = decision.is_event ? "Event" : "Clear";
  const severity = decision.severity === undefined || decision.severity === null ? "-" : `S${decision.severity}`;
  const mode = event.video_model || event.analysis_mode || "-";

  state.selectedEventId = event.event_id;
  state.lastFocus = document.activeElement;
  els.eventModalTitle.textContent = category;
  els.eventModalSubtitle.textContent = `${event.camera_id || "-"} | ${fmtTime(ts)}`;
  els.modalDecision.textContent = status;
  els.modalSeverity.textContent = severity;
  els.modalConfidence.textContent = `${confidence}%`;
  els.modalMode.textContent = mode;
  els.eventModalSummary.textContent = decision.summary || decision.reason || "No summary";
  els.eventVideoError.classList.add("hidden");
  els.eventVideo.removeAttribute("src");
  els.eventVideo.src = `/api/frigate/events/${encodeURIComponent(event.event_id)}/clip.mp4`;
  els.eventVideo.load();
  els.eventModal.classList.remove("hidden");
  els.eventModal.setAttribute("aria-hidden", "false");
  document.body.classList.add("modal-open");
  els.closeEventModal.focus();
}

function closeEventModal() {
  if (els.eventModal.classList.contains("hidden")) return;
  els.eventVideo.pause();
  els.eventVideo.removeAttribute("src");
  els.eventVideo.load();
  els.eventVideoError.classList.add("hidden");
  els.eventModal.classList.add("hidden");
  els.eventModal.setAttribute("aria-hidden", "true");
  document.body.classList.remove("modal-open");
  state.selectedEventId = null;
  if (state.lastFocus && typeof state.lastFocus.focus === "function") {
    state.lastFocus.focus();
  }
  state.lastFocus = null;
}

function renderReviewList() {
  const rows = filteredEvents().slice(0, 40);
  if (!rows.length) {
    els.eventReviewList.innerHTML = `<div class="empty">No matching events</div>`;
    return;
  }
  const alertIds = alertEventIdSet();
  els.eventReviewList.innerHTML = rows.map((event) => {
    const decision = event.decision || {};
    const ts = get(event, ["timeline", "end_time"], null) || get(event, ["timeline", "start_time"], null);
    const id = event.event_id;
    const thumb = id ? `/api/frigate/events/${encodeURIComponent(id)}/thumbnail.jpg` : "";
    const confidence = Math.round((decision.confidence || 0) * 100);
    const label = id ? `Open event clip ${id}` : "Event clip unavailable";
    const type = classifyEvent(event, alertIds);
    const typePillClass = type === "alert" ? "critical" : type === "event" ? "warn" : "";
    const typePillLabel = type === "alert" ? "ALERT" : "EVENT";
    return `
      <article class="review-item ${id ? "" : "disabled"}" tabindex="${id ? "0" : "-1"}" role="${id ? "button" : "article"}" data-event-id="${escapeHtml(id || "")}" aria-label="${escapeHtml(label)}">
        <div class="review-thumb">${thumb ? `<img src="${thumb}" alt="Event thumbnail">` : ""}</div>
        <div class="review-body">
          <div class="row-top">
            <strong>${escapeHtml(decision.category || "AI Review")}</strong>
            <span class="pill ${typePillClass}">${typePillLabel}</span>
          </div>
          <div class="summary">${escapeHtml(decision.summary || "No summary")}</div>
          <div class="muted">${escapeHtml(decision.reason || "")}</div>
        </div>
        <div class="review-meta">
          <span>${escapeHtml(event.camera_id || "-")}</span>
          <span>${fmtTime(ts)}</span>
          <span>${escapeHtml(event.video_model || event.analysis_mode || "-")}</span>
          <span>Confidence ${confidence}%</span>
        </div>
      </article>
    `;
  }).join("");
}

function renderAll() {
  renderMetrics();
  renderCameraWall();
  renderAlerts();
  renderDecisionTable();
  renderReviewList();
  renderTimeline();
}

async function selectCamera(camera) {
  if (!camera || !state.cameras.includes(camera)) return;
  state.camera = camera;
  els.cameraSelect.value = camera;
  els.setupCameraSelect.value = camera;
  if (state.setup.mode === "existing") {
    els.setupCameraId.value = camera;
    await loadSetupDefaults(camera);
  }
  await loadPolicy();
  updateSnapshot();
  renderMetrics();
  renderCameraWall();
}

async function refresh() {
  try {
    await Promise.all([loadEvents(), loadPolicy()]);
    await loadFrigateConfig();
    updateSnapshot();
    renderAll();
    setHealthy(true, "Online");
  } catch (err) {
    setHealthy(false, "Attention");
    console.error(err);
  }
}

async function savePolicy() {
  els.policyStatus.textContent = "Saving";
  try {
    const data = await fetchJson(`/api/context?camera=${encodeURIComponent(state.camera)}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content: els.policyEditor.value }),
    });
    els.policyStatus.textContent = data.ok ? "Saved" : "Save failed";
    await loadPolicy();
  } catch (err) {
    els.policyStatus.textContent = "Save failed";
    console.error(err);
  }
}

const VIEWS = ["overview", "events", "timeline", "setup", "policy", "frigate"];

function setView(name) {
  if (!VIEWS.includes(name)) name = "overview";
  document.querySelectorAll(".view").forEach((view) => view.classList.remove("active"));
  document.getElementById(`${name}View`).classList.add("active");
  document.querySelectorAll(".nav-item").forEach((item) => item.classList.toggle("active", item.dataset.view === name));
  const titles = {
    overview: ["Overview", "Live site state and AI-reviewed security activity."],
    events: ["Events", "Reviewed activity, confidence, severity, and final AI decisions."],
    timeline: ["Timeline", "Interactive history of events and alerts by date and time."],
    setup: ["Setup", "Guided camera onboarding, AI context, masks, zones, and Frigate settings."],
    policy: ["Policy", "Camera context used by the AI decision pipeline."],
    frigate: ["Frigate", "Detection, recording, MQTT, cameras, and full Frigate YAML."],
  };
  els.pageTitle.textContent = titles[name][0];
  els.pageSubtitle.textContent = titles[name][1];
  location.hash = name;
}

document.querySelectorAll(".nav-item").forEach((button) => {
  button.addEventListener("click", () => setView(button.dataset.view));
});

window.addEventListener("hashchange", () => {
  const view = location.hash.replace("#", "");
  if (VIEWS.includes(view)) setView(view);
});

const initialView = location.hash.replace("#", "");
if (VIEWS.includes(initialView)) setView(initialView);

document.querySelectorAll(".segment[data-filter]").forEach((button) => {
  button.addEventListener("click", () => {
    state.filter = button.dataset.filter;
    document.querySelectorAll(".segment[data-filter]").forEach((item) => item.classList.toggle("active", item === button));
    renderReviewList();
  });
});

els.cameraSelect.addEventListener("change", async () => {
  await selectCamera(els.cameraSelect.value);
});

els.refreshButton.addEventListener("click", refresh);
els.savePolicy.addEventListener("click", savePolicy);
els.applyQuickConfig.addEventListener("click", applyQuickConfig);
els.saveFrigateConfig.addEventListener("click", saveFrigateConfig);
els.closeEventModal.addEventListener("click", closeEventModal);
els.eventVideo.addEventListener("error", () => {
  els.eventVideoError.classList.remove("hidden");
});
els.eventVideo.addEventListener("loadedmetadata", () => {
  els.eventVideoError.classList.add("hidden");
});

els.eventModal.addEventListener("click", (event) => {
  if (event.target && event.target.hasAttribute("data-modal-close")) {
    closeEventModal();
  }
});

// ---------- Camera info modal wiring ----------
els.closeCameraInfoModal.addEventListener("click", closeCameraInfoModal);
els.cameraInfoModal.addEventListener("click", (event) => {
  const closer = event.target && event.target.closest("[data-modal-close]");
  if (closer) closeCameraInfoModal();
});
els.editCameraFromInfo.addEventListener("click", editCameraFromInfo);

// ---------- Manage cameras (delete) wiring ----------
els.manageCamerasList.addEventListener("click", (event) => {
  const btn = event.target.closest(".manage-camera-delete");
  if (btn && btn.dataset.camera) {
    event.stopPropagation();
    confirmDeleteCamera(btn.dataset.camera);
  }
});
els.deleteCameraCancel.addEventListener("click", () => {
  state.pendingDelete = null;
  els.deleteCameraDialog.hide();
});
els.deleteCameraConfirm.addEventListener("click", performDeleteCamera);

document.querySelectorAll("[data-setup-mode]").forEach((button) => {
  button.addEventListener("click", () => updateSetupMode(button.dataset.setupMode));
});

els.setupCameraSelect.addEventListener("change", async () => {
  els.setupCameraId.value = els.setupCameraSelect.value;
  resetSetupWizard();
  await loadSetupDefaults(els.setupCameraSelect.value);
});

[
  els.setupCameraId,
  els.setupRtspUrl,
  els.setupLocation,
  els.setupSensitivity,
  els.setupTimezone,
  els.setupStartTime,
  els.setupEndTime,
  els.setupHoursEnabled,
  els.setupNormalActivity,
  els.setupRisks,
  els.setupDescription,
  els.setupTrackedObjects,
  els.setupDetectWidth,
  els.setupDetectHeight,
  els.setupFps,
  els.setupRetainDays,
  els.setupMinSeverity,
  els.setupMinConfidence,
  els.setupRecordingEnabled,
].forEach((input) => {
  if (!input) return;
  input.addEventListener("input", resetSetupPreview);
  input.addEventListener("change", resetSetupPreview);
});

// RTSP URL edits invalidate any prior probe result.
els.setupRtspUrl.addEventListener("input", () => {
  state.setup.rtspTested = false;
  setRtspStatus("URL changed — test the connection again.", "neutral");
  els.rtspTestPreview.classList.add("hidden");
});

// Day grid + hours toggle invalidate the preview.
if (els.setupDayGrid) {
  els.setupDayGrid.querySelectorAll("input[type=checkbox]").forEach((cb) => {
    cb.addEventListener("change", resetSetupPreview);
  });
}
els.setupHoursEnabled.addEventListener("change", () => {
  els.workingHoursFields.classList.toggle("disabled", !els.setupHoursEnabled.checked);
  resetSetupPreview();
});

// Wizard navigation.
els.setupNext.addEventListener("click", nextStage);
els.setupPrev.addEventListener("click", prevStage);
els.rtspTestButton.addEventListener("click", testRtspConnection);

els.setupSnapshot.addEventListener("load", () => {
  els.setupSnapshot.classList.remove("hidden");
  els.setupSnapshotFallback.classList.add("hidden");
  drawSetupOverlay();
});

els.setupSnapshot.addEventListener("error", () => {
  els.setupSnapshot.classList.add("hidden");
  els.setupSnapshotFallback.classList.remove("hidden");
});

els.drawingCanvas.addEventListener("click", (event) => {
  if (state.setup.mode !== "existing") {
    setSetupStatus("Drawings need an existing snapshot", true);
    return;
  }
  const rect = els.drawingCanvas.getBoundingClientRect();
  if (!rect.width || !rect.height) return;
  const x = Math.max(0, Math.min(1, (event.clientX - rect.left) / rect.width));
  const y = Math.max(0, Math.min(1, (event.clientY - rect.top) / rect.height));
  state.setup.currentPoints.push([Number(x.toFixed(4)), Number(y.toFixed(4))]);
  resetSetupPreview();
  drawSetupOverlay();
});

els.finishDrawing.addEventListener("click", finishCurrentDrawing);
els.clearDrawings.addEventListener("click", () => {
  state.setup.drawings = { masks: [], zones: [] };
  state.setup.currentPoints = [];
  resetSetupPreview();
  renderDrawingList();
  drawSetupOverlay();
});
els.generateSetup.addEventListener("click", generateSetupProposal);
els.saveSetup.addEventListener("click", saveSetupProposal);
els.resetSetup.addEventListener("click", resetSetupWizard);
window.addEventListener("resize", drawSetupOverlay);

els.cameraWall.addEventListener("click", async (event) => {
  // The small "focus" overlay switches the active camera without opening the popup.
  const focusBtn = event.target.closest(".camera-tile-focus");
  if (focusBtn && focusBtn.dataset.camera) {
    event.stopPropagation();
    event.preventDefault();
    await selectCamera(focusBtn.dataset.camera);
    return;
  }
  const tile = event.target.closest(".camera-tile");
  if (tile && tile.dataset.camera) {
    await openCameraInfoModal(tile.dataset.camera);
  }
});

els.cameraWall.addEventListener("load", (event) => {
  if (!event.target || event.target.tagName !== "IMG") return;
  const frame = event.target.closest(".camera-tile-frame");
  if (!frame) return;
  const fallback = frame.querySelector(".camera-tile-empty");
  event.target.classList.remove("hidden");
  if (fallback) fallback.classList.add("hidden");
}, true);

els.cameraWall.addEventListener("error", (event) => {
  if (!event.target || event.target.tagName !== "IMG") return;
  const frame = event.target.closest(".camera-tile-frame");
  if (!frame) return;
  const fallback = frame.querySelector(".camera-tile-empty");
  event.target.classList.add("hidden");
  if (fallback) fallback.classList.remove("hidden");
}, true);

els.eventReviewList.addEventListener("click", (event) => {
  const item = event.target.closest(".review-item");
  if (item && item.dataset.eventId) {
    openEventModal(item.dataset.eventId);
  }
});

els.eventReviewList.addEventListener("keydown", (event) => {
  if (event.key !== "Enter" && event.key !== " ") return;
  const item = event.target.closest(".review-item");
  if (item && item.dataset.eventId) {
    event.preventDefault();
    openEventModal(item.dataset.eventId);
  }
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    closeEventModal();
    if (els.cameraInfoModal && !els.cameraInfoModal.classList.contains("hidden")) {
      closeCameraInfoModal();
    }
  }
});

// ─── Timeline ────────────────────────────────────────────────────────────────

function tlEventTs(event) {
  return get(event, ["timeline", "end_time"], null) || get(event, ["timeline", "start_time"], null);
}

function tlRangeCutoff(range) {
  if (range === "all") return 0;
  const ms = range === "24h" ? 86400000 : range === "7d" ? 7 * 86400000 : 30 * 86400000;
  return (Date.now() - ms) / 1000;
}

function tlDayKey(ts) {
  const d = new Date(ts * 1000);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

function tlDayLabel(key) {
  const [y, m, d] = key.split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString([], { weekday: "short", month: "short", day: "numeric" });
}

function tlTimeLabel(ts) {
  return new Date(ts * 1000).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

// Maps a Unix timestamp to a grouping slot key based on the active range
function tlSlotKey(ts, range) {
  const d = new Date(ts * 1000);
  const y = d.getFullYear();
  const mo = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  if (range === "24h") return `${y}-${mo}-${day}T${String(d.getHours()).padStart(2, "0")}`;
  return `${y}-${mo}-${day}`;
}

// Human-readable label for a slot key
function tlSlotLabel(key, range) {
  if (range === "24h") return `${key.split("T")[1]}:00`;
  return tlDayLabel(key);
}

// Pre-generates the complete ordered list of slot keys for finite ranges; null for "all"
function tlAllSlots(range) {
  if (range === "all") return null;
  const slots = [];
  const now = Date.now();
  if (range === "24h") {
    for (let i = 23; i >= 0; i--) {
      const d = new Date(now - i * 3600000);
      const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}T${String(d.getHours()).padStart(2, "0")}`;
      if (!slots.includes(key)) slots.push(key);
    }
  } else {
    const days = range === "7d" ? 7 : 30;
    for (let i = days - 1; i >= 0; i--) {
      slots.push(tlDayKey((now - i * 86400000) / 1000));
    }
  }
  return slots;
}

function timelineEvents() {
  const cutoff = tlRangeCutoff(state.timeline.range);
  const alertIds = alertEventIdSet();
  return state.events.filter((event) => {
    const ts = tlEventTs(event);
    if (!ts) return false;
    if (cutoff && ts < cutoff) return false;
    if (state.timeline.camera !== "all" && event.camera_id !== state.timeline.camera) return false;
    if (state.timeline.type === "alert" && !alertIds.has(event.event_id)) return false;
    if (state.timeline.type === "event" && alertIds.has(event.event_id)) return false;
    return true;
  });
}

function renderTimelineDensity(events) {
  const range = state.timeline.range;
  const allSlots = tlAllSlots(range); // null for "all" range

  // For "all" range with no events, show empty state
  if (!events.length && !allSlots) {
    els.timelineChart.innerHTML = `<div class="empty" style="margin:auto">No events in range</div>`;
    return;
  }

  // Group events by slot, tracking alert/event presence
  const alertIds = alertEventIdSet();
  const bySlot = {};
  events.forEach((event) => {
    const ts = tlEventTs(event);
    if (!ts) return;
    const key = tlSlotKey(ts, range);
    if (!bySlot[key]) bySlot[key] = { count: 0, hasAlert: false, hasEvent: false };
    bySlot[key].count += 1;
    const type = classifyEvent(event, alertIds);
    if (type === "alert") bySlot[key].hasAlert = true;
    else if (type === "event") bySlot[key].hasEvent = true;
  });

  // Use pre-generated slots for finite ranges; fall back to dynamic for "all"
  const slots = allSlots || Object.keys(bySlot).sort();

  if (!slots.length) {
    els.timelineChart.innerHTML = `<div class="empty" style="margin:auto">No events in range</div>`;
    return;
  }

  const maxCount = Math.max(...slots.map((k) => (bySlot[k] || {}).count || 0), 1);

  els.timelineChart.innerHTML = slots.map((key) => {
    const slot = bySlot[key] || { count: 0, hasAlert: false, hasEvent: false };
    const { count, hasAlert, hasEvent } = slot;
    const isEmpty = count === 0;
    const pct = isEmpty ? 0 : Math.max(8, Math.round((count / maxCount) * 100));
    const colorVar = hasAlert ? "var(--red)" : hasEvent ? "var(--amber)" : "var(--green)";
    const label = tlSlotLabel(key, range);
    const titleText = label + (count ? ": " + count + " event" + (count !== 1 ? "s" : "") : ": no events");
    return `
      <div class="tl-col${isEmpty ? " tl-col-empty" : ""}" data-day="${escapeHtml(key)}"
           title="${escapeHtml(titleText)}"
           tabindex="${isEmpty ? "-1" : "0"}"
           role="${isEmpty ? "presentation" : "button"}"
           aria-label="${escapeHtml(titleText)}">
        <div class="tl-bar-wrap">
          <div class="tl-bar" style="${isEmpty ? "" : `height:${pct}%;background:${colorVar}`}"></div>
        </div>
        <div class="tl-bar-count">${count || ""}</div>
        <div class="tl-bar-label">${escapeHtml(label)}</div>
      </div>
    `;
  }).join("");
}

function renderTimelineList(events) {
  if (!events.length) {
    els.timelineList.innerHTML = `<div class="empty">No events in the selected range</div>`;
    return;
  }

  const range = state.timeline.range;

  // Sort newest-first, then group by slot key (hour for 24h, day otherwise)
  const sorted = events.slice().sort((a, b) => (tlEventTs(b) || 0) - (tlEventTs(a) || 0));
  const groups = {};
  const groupOrder = [];
  sorted.forEach((event) => {
    const ts = tlEventTs(event);
    if (!ts) return;
    const key = tlSlotKey(ts, range);
    if (!groups[key]) { groups[key] = []; groupOrder.push(key); }
    groups[key].push(event);
  });

  const alertIds = alertEventIdSet();
  els.timelineList.innerHTML = groupOrder.map((key) => {
    const slotEvents = groups[key];
    const rows = slotEvents.map((event) => {
      const ts = tlEventTs(event);
      const decision = event.decision || {};
      const id = event.event_id;
      const thumb = id ? `/api/frigate/events/${encodeURIComponent(id)}/thumbnail.jpg` : "";
      const confidence = Math.round((decision.confidence || 0) * 100);
      const sevLabel = decision.severity != null ? `S${decision.severity}` : "-";
      const type = classifyEvent(event, alertIds);
      const typePillClass = type === "alert" ? "critical" : type === "event" ? "warn" : "";
      const typePillLabel = type === "alert" ? "ALERT" : "EVENT";
      return `
        <article class="timeline-entry ${id ? "" : "disabled"}" tabindex="${id ? "0" : "-1"}" role="${id ? "button" : "article"}" data-event-id="${escapeHtml(id || "")}" aria-label="Open event ${escapeHtml(id || "")}">
          <div class="tl-entry-thumb">
            ${thumb ? `<img src="${escapeHtml(thumb)}" alt="Event thumbnail" loading="lazy">` : `<div class="tl-thumb-empty"></div>`}
          </div>
          <div class="tl-entry-time">${ts ? tlTimeLabel(ts) : "-"}</div>
          <div class="tl-entry-body">
            <strong>${escapeHtml(decision.category || "AI Review")}</strong>
            <span class="tl-entry-summary">${escapeHtml(decision.summary || "No summary")}</span>
          </div>
          <div class="tl-entry-meta">
            <span class="pill ${typePillClass}">${typePillLabel}</span>
            <span class="pill ${typePillClass}">${escapeHtml(sevLabel)}</span>
            <span class="muted">${confidence}%</span>
            <span class="muted">${escapeHtml(event.camera_id || "-")}</span>
          </div>
        </article>
      `;
    }).join("");

    return `
      <div class="timeline-day" id="tl-day-${escapeHtml(key)}">
        <span>${escapeHtml(tlSlotLabel(key, range))}</span>
        <span class="muted">${slotEvents.length} event${slotEvents.length !== 1 ? "s" : ""}</span>
      </div>
      ${rows}
    `;
  }).join("");
}

function renderTimeline() {
  const events = timelineEvents();
  els.timelineCount.textContent = `${events.length} event${events.length !== 1 ? "s" : ""}`;
  renderTimelineDensity(events);
  renderTimelineList(events);
}

function timelineScrollToDay(key) {
  const target = document.getElementById(`tl-day-${key}`);
  if (target) target.scrollIntoView({ behavior: "smooth", block: "start" });
}

// Timeline filter controls
els.timelineCameraSelect.addEventListener("change", () => {
  state.timeline.camera = els.timelineCameraSelect.value;
  renderTimeline();
});

document.querySelectorAll(".tl-range-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    state.timeline.range = btn.dataset.range;
    document.querySelectorAll(".tl-range-btn").forEach((b) => b.classList.toggle("active", b === btn));
    renderTimeline();
  });
});

document.querySelectorAll(".tl-type-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    state.timeline.type = btn.dataset.type;
    document.querySelectorAll(".tl-type-btn").forEach((b) => b.classList.toggle("active", b === btn));
    renderTimeline();
  });
});

// Timeline density bar click → scroll to slot (skip empty slots)
document.getElementById("timelineChart").addEventListener("click", (event) => {
  const col = event.target.closest(".tl-col");
  if (col && col.dataset.day && !col.classList.contains("tl-col-empty")) {
    timelineScrollToDay(col.dataset.day);
  }
});

document.getElementById("timelineChart").addEventListener("keydown", (event) => {
  if (event.key !== "Enter" && event.key !== " ") return;
  const col = event.target.closest(".tl-col");
  if (col && col.dataset.day && !col.classList.contains("tl-col-empty")) {
    event.preventDefault();
    timelineScrollToDay(col.dataset.day);
  }
});

// Timeline entry click → open event modal
document.getElementById("timelineList").addEventListener("click", (event) => {
  const entry = event.target.closest(".timeline-entry");
  if (entry && entry.dataset.eventId) openEventModal(entry.dataset.eventId);
});

document.getElementById("timelineList").addEventListener("keydown", (event) => {
  if (event.key !== "Enter" && event.key !== " ") return;
  const entry = event.target.closest(".timeline-entry");
  if (entry && entry.dataset.eventId) { event.preventDefault(); openEventModal(entry.dataset.eventId); }
});

// ─── End Timeline ─────────────────────────────────────────────────────────────

async function boot() {
  try {
    await loadCameras();
    await refresh();
    await loadProfiles();
    await loadCamerasWithMeta();
    updateSetupMode("existing");
    await loadSetupDefaults(state.camera);
    showStage(1);
    renderDrawingList();
    state.snapshotTimer = window.setInterval(() => {
      updateSnapshot();
      refreshCameraWallFrames();
      updateSetupSnapshot();
    }, 5000);
    window.setInterval(refresh, 30000);
  } catch (err) {
    setHealthy(false, "Offline");
    console.error(err);
  }
}

boot();
