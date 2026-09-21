/**
 * app.js — Lógica completa de la UI de MxCorreo en 4 pasos.
 * Se comunica con el backend Python a través de window.MxCorreo (preload.js).
 */

"use strict";

// ─── Estado de la app ──────────────────────────────────────────────────────
const state = {
  currentStep: 1,
  filePath: null,
  verificacionResult: null,
  configPath: null,
  configData: null,
  simulacionResult: null,
  envioEnCurso: false,
};

// ─── Utilidades ─────────────────────────────────────────────────────────────
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => [...document.querySelectorAll(sel)];

function toast(msg, type = "info", dur = 4000) {
  const el = document.createElement("div");
  el.className = `toast ${type}`;
  el.textContent = msg;
  el.onclick = () => el.remove();
  $("#toast-container").appendChild(el);
  setTimeout(() => el.remove(), dur);
}

function modal({ icon = "⚠️", title, body, confirmLabel = "Confirmar", confirmClass = "btn-danger", onConfirm }) {
  const overlay = $("#modal-overlay");
  $("#modal-icon").textContent = icon;
  $("#modal-title").textContent = title;
  $("#modal-body").textContent = body;
  const confirmBtn = $("#modal-confirm");
  confirmBtn.textContent = confirmLabel;
  confirmBtn.className = `btn ${confirmClass}`;
  overlay.style.display = "flex";

  const cleanup = () => (overlay.style.display = "none");
  $("#modal-cancel").onclick = cleanup;
  confirmBtn.onclick = () => { cleanup(); onConfirm?.(); };
}

function setProgress(id, label, pct) {
  const card = $(`#${id}`);
  if (!card) return;
  card.style.display = "block";
  $(`#${id} .progress-header span:first-child`).textContent = label;
  const pctEl = $(`#${id} .progress-header span:last-child`);
  if (pctEl && pct >= 0) pctEl.textContent = `${pct}%`;
  const bar = $(`#${id} .progress-bar-fill`);
  if (bar && pct >= 0) bar.style.width = `${pct}%`;
}

function goToStep(n) {
  // Actualizar paneles
  $$(".panel").forEach((p) => p.classList.remove("active"));
  $(`#panel-${n}`).classList.add("active");

  // Actualizar sidebar
  $$(".step-item").forEach((item) => {
    const s = parseInt(item.dataset.step);
    item.classList.remove("active", "locked");
    if (s === n) item.classList.add("active");
    else if (s > n && !isStepUnlocked(s)) item.classList.add("locked");
  });

  state.currentStep = n;
}

function isStepUnlocked(n) {
  if (n <= 1) return true;
  if (n === 2) return !!state.verificacionResult;
  if (n === 3) return !!state.verificacionResult;
  if (n === 4) return !!state.simulacionResult;
  return false;
}

function unlockStep(n) {
  const el = $(`#nav-step-${n}`);
  if (!el) return;
  el.classList.remove("locked");
  el.style.pointerEvents = "";
  el.style.opacity = "";
  el.onclick = () => goToStep(n);
}

function markStepDone(n) {
  const el = $(`#nav-step-${n}`);
  if (!el) return;
  el.classList.add("done");
  el.classList.remove("active");
}

// ─── Status del backend ──────────────────────────────────────────────────────
function setStatus(state_, label) {
  const dot = $("#status-dot");
  dot.className = `dot-${state_}`;
  $("#status-label").textContent = label;
}

// ─── Paso 1: Carga de archivo ────────────────────────────────────────────────
function initStep1() {
  const dropzone = $("#dropzone");
  const btnSelect = $("#btn-select-file");
  const btnChange = $("#btn-change-file");
  const btnPurge = $("#btn-purge");

  // Botón seleccionar
  const selectFile = async () => {
    const path = await window.MxCorreo.openFile({
      title: "Seleccionar lista de correos",
      filters: [
        { name: "Listas de correos", extensions: ["csv", "txt", "mxlista"] },
        { name: "CSV", extensions: ["csv"] },
        { name: "Todos", extensions: ["*"] },
      ],
    });
    if (path) setSelectedFile(path);
  };

  btnSelect.onclick = selectFile;
  btnChange.onclick = selectFile;

  dropzone.onclick = (e) => {
    if (e.target === dropzone || e.target.closest(".upload-text") || e.target.closest(".upload-icon")) {
      selectFile();
    }
  };

  // Drag & drop
  dropzone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropzone.classList.add("dragover");
  });
  dropzone.addEventListener("dragleave", () => dropzone.classList.remove("dragover"));
  dropzone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropzone.classList.remove("dragover");
    const file = e.dataTransfer.files[0];
    if (file && file.path) setSelectedFile(file.path);
  });

  // Botón purgar
  btnPurge.onclick = runVerificacion;
}

function setSelectedFile(filePath) {
  state.filePath = filePath;
  const name = filePath.split(/[\\/]/).pop();
  $("#dropzone").style.display = "none";
  const fileInfo = $("#file-info");
  fileInfo.style.display = "block";
  $("#file-name-display").textContent = name;
  $("#file-path-display").textContent = filePath;
  $("#column-config").style.display = "block";
  $("#btn-purge").disabled = false;
  // Reset de resultados anteriores
  $("#progress-card").style.display = "none";
}

async function runVerificacion() {
  const columna = $("#input-column").value.trim() || "correo";
  const verificarDns = $("#check-dns").checked;

  setStatus("loading", "Verificando correos…");
  $("#btn-purge").disabled = true;
  setProgress("progress-card", "Iniciando verificación…", 0);
  $("#progress-card").style.display = "block";

  try {
    const result = await window.MxCorreo.py("verificar", {
      lista: state.filePath,
      columna,
      verificar_dns: verificarDns,
    });

    if (!result.ok) throw new Error(result.error);

    state.verificacionResult = result.data;
    setStatus("ok", "Verificación completa");
    $("#progress-card").style.display = "none";
    markStepDone(1);
    unlockStep(2);
    unlockStep(3);
    populateResultados(result.data);
    goToStep(2);
    toast(`Verificación completada: ${result.data.validos} correos válidos`, "ok");
  } catch (err) {
    setStatus("error", "Error en verificación");
    toast(`Error: ${err.message}`, "error", 8000);
    $("#btn-purge").disabled = false;
    console.error(err);
  }
}

// ─── Paso 2: Resultados ──────────────────────────────────────────────────────
function populateResultados(data) {
  const animNum = (elId, target) => {
    const el = $(elId);
    if (!el) return;
    let start = 0;
    const step = Math.ceil(target / 30);
    const timer = setInterval(() => {
      start = Math.min(start + step, target);
      el.textContent = typeof target === "string"
        ? target
        : start.toLocaleString("es-EC");
      if (start >= target) clearInterval(timer);
    }, 20);
  };

  animNum("#m-validos", data.validos);
  animNum("#m-invalidos", data.invalidos);
  animNum("#m-duplicados", data.duplicados);
  animNum("#m-sinmx", data.sin_mx || 0);
  animNum("#m-purgados", data.purgados);

  const tasa = data.total_entrada > 0
    ? Math.round((data.purgados / data.total_entrada) * 100)
    : 0;
  $("#m-tasa").textContent = `${tasa}%`;

  // Tabla de inválidos
  const tbody = $("#tbody-invalid");
  tbody.innerHTML = "";
  const invalidos = data.lista_invalidos || [];
  invalidos.slice(0, 500).forEach((item, i) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `<td>${i + 1}</td><td>${escHtml(item.correo)}</td><td>${escHtml(item.razon)}</td>`;
    tbody.appendChild(tr);
  });
  if (invalidos.length === 0) {
    tbody.innerHTML = '<tr><td colspan="3" style="text-align:center;color:var(--text-muted);padding:20px">Sin correos inválidos 🎉</td></tr>';
  }

  // Filtro
  $("#filter-invalid").oninput = (e) => {
    const q = e.target.value.toLowerCase();
    $$(`#table-invalid tbody tr`).forEach((tr) => {
      tr.style.display = tr.textContent.toLowerCase().includes(q) ? "" : "none";
    });
  };
}

function initStep2() {
  // Exportar CSV
  $("#btn-export-csv").onclick = async () => {
    if (!state.verificacionResult) return;
    const dest = await window.MxCorreo.saveFile({
      title: "Guardar lista de correos válidos",
      defaultName: "correos_validos.csv",
      filters: [{ name: "CSV UTF-8", extensions: ["csv"] }],
    });
    if (!dest) return;
    const result = await window.MxCorreo.py("exportar_purgados", {
      lista_validos: state.verificacionResult.lista_validos,
      destino: dest,
    });
    if (result.ok) {
      toast(`Exportado: ${result.data.total} correos → ${dest}`, "ok");
      window.MxCorreo.openPath(dest);
    } else {
      toast(`Error exportando: ${result.error}`, "error");
    }
  };

  $("#btn-go-config").onclick = () => goToStep(3);
}

// ─── Paso 3: Configuración ───────────────────────────────────────────────────
function initStep3() {
  $("#btn-select-config").onclick = async () => {
    const path = await window.MxCorreo.openFile({
      title: "Seleccionar configuración de campaña",
      filters: [
        { name: "Configuración de campaña", extensions: ["json"] },
        { name: "Todos", extensions: ["*"] },
      ],
    });
    if (!path) return;
    state.configPath = path;
    $("#input-config-path").value = path;
    await loadConfig(path);
  };

  $("#btn-simular").onclick = runSimulacion;
}

async function loadConfig(path) {
  setStatus("loading", "Validando config…");
  const result = await window.MxCorreo.py("cargar_config", { config: path });
  if (!result.ok) {
    toast(`Error en config: ${result.error}`, "error", 8000);
    setStatus("error", "Config inválida");
    return;
  }
  state.configData = result.data;
  setStatus("ok", "Configuración válida");

  // Poblar preview
  const d = result.data;
  $("#cfg-id").textContent = d.campana_id || "—";
  $("#cfg-remitente").textContent = `${d.nombre_remitente} <${d.remitente}>`;
  $("#cfg-asunto").textContent = d.asunto || "—";
  $("#cfg-smtp").textContent = `${d.smtp_host} (${d.smtp_seguridad?.toUpperCase()})`;
  $("#cfg-max").textContent = d.max_envios?.toLocaleString("es-EC") || "—";
  $("#cfg-aprobado").textContent = d.autorizacion?.envio_aprobado ? "✅ Sí" : "❌ No";

  // Checklist de autorización
  const auth = d.autorizacion || {};
  const checks = [
    ["auth-remitente", "remitente_autorizado"],
    ["auth-lista", "lista_revisada"],
    ["auth-exclusiones", "exclusiones_revisadas"],
    ["auth-limites", "limites_confirmados"],
    ["auth-aprobado", "envio_aprobado"],
  ];
  checks.forEach(([elId, key]) => {
    const el = $(`#${elId}`);
    if (!el) return;
    const ok = auth[key] === true;
    el.classList.toggle("ok", ok);
    el.classList.toggle("fail", !ok);
    el.querySelector(".auth-icon").textContent = ok ? "✅" : "❌";
  });

  $("#config-preview").style.display = "block";
  $("#btn-simular").disabled = false;
  toast("Configuración cargada correctamente", "ok");
}

async function runSimulacion() {
  if (!state.configPath || !state.filePath) {
    toast("Necesitas una lista de correos y una configuración.", "error");
    return;
  }

  setStatus("loading", "Simulando campaña…");
  $("#btn-simular").disabled = true;

  // Exportar lista válida temporalmente para la simulación
  const tmpPath = state.filePath.replace(/\.[^.]+$/, "_validos_tmp.csv");
  const expResult = await window.MxCorreo.py("exportar_purgados", {
    lista_validos: state.verificacionResult?.lista_validos || [],
    destino: tmpPath,
  });

  const result = await window.MxCorreo.py("simular", {
    config: state.configPath,
    lista: expResult.ok ? tmpPath : state.filePath,
  });

  if (!result.ok) {
    toast(`Error en simulación: ${result.error}`, "error", 8000);
    setStatus("error", "Error en simulación");
    $("#btn-simular").disabled = false;
    return;
  }

  state.simulacionResult = result.data;
  setStatus("ok", "Simulación exitosa");
  toast("Simulación completada correctamente ✅", "ok");

  // Mostrar resultado
  const d = result.data;
  $("#sim-contactos").textContent = d.contactos_validos?.toLocaleString("es-EC") || "—";
  $("#sim-asunto").textContent = d.asunto || "—";
  $("#sim-preview").textContent = d.preview_texto || "—";
  $("#simulation-result").style.display = "block";

  markStepDone(3);
  unlockStep(4);
  $("#btn-simular").disabled = false;

  // Preparar paso 4
  populateSendSummary();
}

// ─── Paso 4: Envío ───────────────────────────────────────────────────────────
function initStep4() {
  $("#btn-enviar").onclick = () => {
    if (!state.configData?.autorizacion?.envio_aprobado) {
      modal({
        icon: "🔒",
        title: "Envío no autorizado",
        body: 'El campo "envio_aprobado" en tu campana.json debe ser true para enviar. Edítalo y recarga la configuración.',
        confirmLabel: "Entendido",
        confirmClass: "btn-primary",
      });
      return;
    }

    const total = state.verificacionResult?.validos || 0;
    modal({
      icon: "🚀",
      title: "Confirmar envío real",
      body: `Estás a punto de enviar a ${total.toLocaleString("es-EC")} destinatarios. Esta acción no se puede deshacer.`,
      confirmLabel: `Enviar a ${total.toLocaleString("es-EC")} correos`,
      confirmClass: "btn-hero",
      onConfirm: runEnvio,
    });
  };
}

function populateSendSummary() {
  const listaName = state.filePath?.split(/[\\/]/).pop() || "—";
  const configName = state.configPath?.split(/[\\/]/).pop() || "—";
  const total = state.verificacionResult?.validos || 0;
  const aprobado = state.configData?.autorizacion?.envio_aprobado;

  $("#send-lista").textContent = listaName;
  $("#send-config").textContent = configName;
  $("#send-total").textContent = total.toLocaleString("es-EC") + " correos";
  $("#send-auth").textContent = aprobado ? "✅ Autorizado" : "❌ No autorizado";
  $("#btn-enviar").disabled = false;
}

async function runEnvio() {
  if (state.envioEnCurso) return;
  state.envioEnCurso = true;

  setStatus("loading", "Enviando campaña…");
  $("#btn-enviar").disabled = true;
  $("#send-progress-card").style.display = "block";
  $("#send-done").style.display = "none";
  $("#send-log").innerHTML = "";

  const tmpPath = state.filePath?.replace(/\.[^.]+$/, "_validos_tmp.csv");

  let enviados = 0;
  let errores = 0;

  // Escuchar eventos individuales de correo
  const unsubEvent = window.MxCorreo.onPyEvent((msg) => {
    if (msg.event === "correo_enviado") {
      enviados++;
      const el = document.createElement("div");
      el.className = "log-ok";
      el.textContent = `✅ ${msg.data.numero}. ${msg.data.correo}`;
      $("#send-log").appendChild(el);
      $("#send-log").scrollTop = 9999;
    } else if (msg.event === "correo_error") {
      errores++;
      const el = document.createElement("div");
      el.className = "log-err";
      el.textContent = `❌ ${msg.data.correo} → ${msg.data.error}`;
      $("#send-log").appendChild(el);
      $("#send-log").scrollTop = 9999;
    }
  });

  const result = await window.MxCorreo.py("enviar", {
    config: state.configPath,
    lista: tmpPath || state.filePath,
  });

  unsubEvent();
  state.envioEnCurso = false;

  if (!result.ok) {
    setStatus("error", "Error en envío");
    toast(`Error: ${result.error}`, "error", 10000);
    $("#btn-enviar").disabled = false;
    return;
  }

  const d = result.data;
  setStatus("ok", "Campaña enviada");
  markStepDone(4);
  $("#send-progress-card").style.display = "none";
  $("#send-done").style.display = "block";
  $("#done-title").textContent = "¡Campaña enviada exitosamente! 🎉";
  $("#done-summary").textContent =
    `${d.enviados?.toLocaleString("es-EC")} enviados de ${d.total_intentados?.toLocaleString("es-EC")} intentados. ` +
    (d.errores > 0 ? `${d.errores} errores registrados.` : "Sin errores.");
  toast(`Campaña completada: ${d.enviados} envíos`, "ok", 8000);
}

// ─── Suscripción a eventos del backend ──────────────────────────────────────
function initBackendEvents() {
  window.MxCorreo.onPyEvent((msg) => {
    if (msg.event === "ready") {
      setStatus("ok", "Backend listo");
    }
  });

  window.MxCorreo.onPyProgress((msg) => {
    if (state.currentStep === 1) {
      const pct = msg.value ?? -1;
      setProgress("progress-card", msg.message || "Procesando…", pct);
      const pctEl = $("#progress-pct");
      if (pctEl && pct >= 0) pctEl.textContent = `${pct}%`;
      const bar = $("#progress-bar");
      if (bar && pct >= 0) bar.style.width = `${pct}%`;
    } else if (state.currentStep === 4) {
      const pct = msg.value ?? -1;
      const label = $("#send-progress-label");
      if (label) label.textContent = msg.message || "Procesando…";
      const bar = $("#send-progress-bar");
      if (bar && pct >= 0) bar.style.width = `${pct}%`;
    }
  });

  window.MxCorreo.onPyLog?.((log) => {
    if (log.level === "error") {
      setStatus("error", "Error en backend");
      console.error("[Python]", log.msg);
    }
  });
}

// ─── Sidebar click navigation ─────────────────────────────────────────────
function initSidebarNav() {
  $$(".step-item").forEach((item) => {
    const n = parseInt(item.dataset.step);
    if (!item.classList.contains("locked")) {
      item.onclick = () => goToStep(n);
    }
  });
}

// ─── Window controls ──────────────────────────────────────────────────────────
function initWindowControls() {
  $("#btn-minimize").onclick = () => window.MxCorreo.minimize();
  $("#btn-maximize").onclick = () => window.MxCorreo.maximize();
  $("#btn-close").onclick = () => window.MxCorreo.close();
}

// ─── Helpers ──────────────────────────────────────────────────────────────────
function escHtml(str) {
  return String(str ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

// ─── Init ──────────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  initWindowControls();
  initBackendEvents();
  initStep1();
  initStep2();
  initStep3();
  initStep4();
  initSidebarNav();

  // Verificar que el backend esté listo
  setTimeout(async () => {
    const r = await window.MxCorreo.py("ping", {});
    if (r.ok) {
      setStatus("ok", `Backend v${r.data.version}`);
    } else {
      setStatus("error", "Backend no disponible");
      toast("No se pudo conectar al backend Python. Revisa la instalación.", "error", 0);
    }
  }, 800);
});
