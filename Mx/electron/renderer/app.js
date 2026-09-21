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

// ─── Estado del Apartado de Envíos a Empresas ──────────────────────────────
const envioState = {
  destinatarios: [],
  adjuntos: [],
  enviando: false,
  logEnvios: [],
  totalLote: 0,
  enviadosCount: 0,
  erroresCount: 0,
  activeFormat: "text",
  activeSourceTab: "archivo",
};

// ─── Plantillas B2B Predefinidas para Actuariosa ─────────────────────────────
const B2B_TEMPLATES = {
  presentacion: {
    asunto: "Propuesta de Consultoría Actuarial y Financiera — Actuariosa S.A.",
    cuerpo: `Estimados directivos de \${empresa}:

Reciban un cordial saludo de parte de Actuariosa S.A., firma especializada en consultoría actuarial, valoración de pasivos laborales y asesoría financiera empresarial.

Nos ponemos a su disposición para colaborar con su organización en:
1. Estudios actuariales de jubilación patronal y desahucio (bajo normativa ecuatoriana e internacional NIC 19 / NIIF).
2. Optimización y planificación de pasivos laborales futuros.
3. Valoración financiera y análisis de riesgos actuariales.

Adjuntamos nuestro portafolio de servicios y credenciales corporativas para su revisión.

Nos encantaría coordinar una breve llamada de 15 minutos para conocer sus necesidades específicas.

Atentamente,

Actuariosa S.A.
Consultoría Actuarial y Financiera
contacto@actuariosa.com | www.actuariosa.com`,
    cuerpo_html: `<p>Estimados directivos de <strong>\${empresa}</strong>:</p>
<p>Reciban un cordial saludo de parte de <strong>Actuariosa S.A.</strong>, firma especializada en consultoría actuarial, valoración de pasivos laborales y asesoría financiera empresarial.</p>
<p>Nos ponemos a su disposición para colaborar con su organización en:</p>
<ol>
  <li><strong>Estudios actuariales</strong> de jubilación patronal y desahucio (bajo normativa ecuatoriana e internacional NIC 19 / NIIF).</li>
  <li><strong>Optimización y planificación</strong> de pasivos laborales futuros.</li>
  <li><strong>Valoración financiera</strong> y análisis de riesgos actuariales.</li>
</ol>
<p>Adjuntamos nuestro portafolio de servicios y credenciales corporativas para su revisión.</p>
<p>Nos encantaría coordinar una breve llamada de 15 minutos para conocer sus necesidades específicas.</p>
<br>
<p>Atentamente,<br>
<strong>Actuariosa S.A.</strong><br>
Consultoría Actuarial y Financiera<br>
<a href="mailto:contacto@actuariosa.com">contacto@actuariosa.com</a> | <a href="https://www.actuariosa.com">www.actuariosa.com</a></p>`,
  },
  laborales: {
    asunto: "Actualización y Valoración Actuarial de Pasivos Laborales (NIC 19) — \${empresa}",
    cuerpo: `Estimados señores de \${empresa}:

Nos dirigimos a ustedes con el propósito de ofrecerles nuestros servicios especializados en la Valoración Actuarial de Beneficios a Empleados (Jubilación Patronal y Bonificación por Desahucio) para el presente ejercicio fiscal, en cumplimiento estricto con el Código del Trabajo y la Norma Internacional de Contabilidad NIC 19 (NIIF para PYMES Sección 28).

Nuestro equipo de actuarios certificados garantiza:
• Metodología de la unidad de crédito proyectada rigurosa y aceptada por auditorías externas.
• Entrega ágil de informes ejecutivos y notas contables listas para sus estados financieros.
• Asesoría continua ante requerimientos de la Superintendencia de Compañías y SRI.

Quedamos a su entera disposición para remitirles una propuesta formal o reunirnos según su disponibilidad.

Saludos cordiales,

Departamento Actuarial
Actuariosa S.A.`,
    cuerpo_html: `<p>Estimados señores de <strong>\${empresa}</strong>:</p>
<p>Nos dirigimos a ustedes con el propósito de ofrecerles nuestros servicios especializados en la <strong>Valoración Actuarial de Beneficios a Empleados</strong> (Jubilación Patronal y Bonificación por Desahucio) para el presente ejercicio fiscal, en cumplimiento estricto con el Código del Trabajo y la Norma Internacional de Contabilidad NIC 19 (NIIF para PYMES Sección 28).</p>
<p>Nuestro equipo de actuarios certificados garantiza:</p>
<ul>
  <li>Metodología de la unidad de crédito proyectada rigurosa y aceptada por auditorías externas.</li>
  <li>Entrega ágil de informes ejecutivos y notas contables listas para sus estados financieros.</li>
  <li>Asesoría continua ante requerimientos de la Superintendencia de Compañías y SRI.</li>
</ul>
<p>Quedamos a su entera disposición para remitirles una propuesta formal o reunirnos según su disponibilidad.</p>
<br>
<p>Saludos cordiales,<br>
<strong>Departamento Actuarial</strong><br>
Actuariosa S.A.</p>`,
  },
  cotizacion: {
    asunto: "Cotización de Estudio Actuarial para \${empresa}",
    cuerpo: `Estimados directivos de \${empresa}:

Es un gusto saludarles. En respuesta a sus requerimientos de gestión corporativa, presentamos nuestra cotización para la elaboración del Estudio Actuarial correspondiente a su personal activo y jubilado.

Nuestra propuesta incluye:
- Censo y validación de la nómina laboral.
- Cálculo de reservas matemáticas bajo hipótesis demográficas y financieras vigentes.
- Emisión de informe técnico actuarial con certificación profesional.

Por favor indíquenos si desean coordinar una llamada para afinar detalles sobre el censo de empleados.

Atentamente,

Actuariosa S.A.`,
    cuerpo_html: `<p>Estimados directivos de <strong>\${empresa}</strong>:</p>
<p>Es un gusto saludarles. En respuesta a sus requerimientos de gestión corporativa, presentamos nuestra cotización para la elaboración del Estudio Actuarial correspondiente a su personal activo y jubilado.</p>
<p>Nuestra propuesta incluye:</p>
<ul>
  <li>Censo y validación de la nómina laboral.</li>
  <li>Cálculo de reservas matemáticas bajo hipótesis demográficas y financieras vigentes.</li>
  <li>Emisión de informe técnico actuarial con certificación profesional.</li>
</ul>
<p>Por favor indíquenos si desean coordinar una llamada para afinar detalles sobre el censo de empleados.</p>
<br>
<p>Atentamente,<br>
<strong>Actuariosa S.A.</strong></p>`,
  },
  custom: {
    asunto: "",
    cuerpo: "",
    cuerpo_html: "",
  },
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
  // Desactivar apartado independiente en la sidebar
  $("#nav-apartado-envio")?.classList.remove("active");

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

function goToApartadoEnvio() {
  // Actualizar paneles: mostrar panel-envio
  $$(".panel").forEach((p) => p.classList.remove("active"));
  const panelEnvio = $("#panel-envio");
  if (panelEnvio) panelEnvio.classList.add("active");

  // Desactivar pasos 1-4 en el sidebar
  $$(".step-item").forEach((item) => item.classList.remove("active"));

  // Activar ítem del apartado en el sidebar
  const navApartado = $("#nav-apartado-envio");
  if (navApartado) navApartado.classList.add("active");

  // Actualizar si hay contactos purgados disponibles en memoria
  updatePurgadosDisponibles();
}

function updatePurgadosDisponibles() {
  const validos = state.verificacionResult?.lista_validos || [];
  const msgEl = $("#env-purgados-msg");
  const btnCargar = $("#btn-env-cargar-purgados");
  if (!msgEl || !btnCargar) return;

  if (validos.length > 0) {
    msgEl.textContent = `Tienes ${validos.length.toLocaleString("es-EC")} correos válidos y verificados listos de la depuración previa.`;
    btnCargar.style.display = "inline-flex";
    btnCargar.textContent = `Cargar ${validos.length.toLocaleString("es-EC")} Empresas`;
  } else {
    msgEl.textContent = "No hay correos purgados en esta sesión. Puedes purgar primero en el paso 1 o cargar un archivo directamente.";
    btnCargar.style.display = "none";
  }
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
        { name: "Listas de correos (Excel, CSV, TXT)", extensions: ["xlsx", "xls", "csv", "txt", "mxlista"] },
        { name: "Archivos Excel", extensions: ["xlsx", "xls"] },
        { name: "Archivos CSV", extensions: ["csv"] },
        { name: "Archivos de texto", extensions: ["txt"] },
        { name: "Todos los archivos", extensions: ["*"] },
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
  const columna = $("#input-column").value.trim();
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
    triggerAutoSync("depuracion_completada");
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

  // Botón directo a Mandar Correos a estas Empresas
  const btnMandarEmpresas = $("#btn-enviar-empresas-desde-purga");
  if (btnMandarEmpresas) {
    btnMandarEmpresas.onclick = () => {
      const validos = state.verificacionResult?.lista_validos || [];
      if (validos.length === 0) {
        toast("No hay correos válidos para transferir.", "warning");
        return;
      }
      envioState.destinatarios = [...validos];
      renderDestinatarios();
      switchDestSourceTab("purgados");
      goToApartadoEnvio();
      toast(`Se cargaron ${validos.length.toLocaleString("es-EC")} empresas purgadas para envío directo`, "ok");
    };
  }

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
    // Si estamos en el apartado independiente de envíos directos
    if (envioState.enviando) {
      handleEnvioEvent(msg);
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
    } else if (envioState.enviando) {
      const pct = msg.value ?? -1;
      const label = $("#mon-status-text");
      if (label) label.textContent = msg.message || "Enviando…";
      const pctEl = $("#mon-pct-text");
      if (pctEl && pct >= 0) pctEl.textContent = `${pct}%`;
      const bar = $("#mon-progress-bar");
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

  const navApartado = $("#nav-apartado-envio");
  if (navApartado) {
    navApartado.onclick = () => goToApartadoEnvio();
  }
}

// ═════════════════════════════════════════════════════════════════════════════
// APARTADO INDEPENDIENTE: MANDAR CORREOS A EMPRESAS
// ═════════════════════════════════════════════════════════════════════════════

function initApartadoEnvio() {
  initDestinatariosSection();
  initSmtpSection();
  initMensajeSection();
  initEnvioSection();
}

function switchDestSourceTab(tabKey) {
  envioState.activeSourceTab = tabKey;
  $$(".dest-source-tabs .source-tab").forEach((tab) => tab.classList.remove("active"));
  $(`#tab-src-${tabKey}`)?.classList.add("active");

  $$(".dest-view").forEach((view) => (view.style.display = "none"));
  const targetView = $(`#dest-view-${tabKey}`);
  if (targetView) targetView.style.display = "block";
}

function renderDestinatarios() {
  const total = envioState.destinatarios.length;
  $("#env-count-badge").textContent = `${total.toLocaleString("es-EC")} correos`;

  const previewBox = $("#env-dest-preview");
  const chipsContainer = $("#env-dest-chips");

  if (total === 0) {
    if (previewBox) previewBox.style.display = "none";
    if (chipsContainer) chipsContainer.innerHTML = "";
    return;
  }

  if (previewBox) previewBox.style.display = "block";
  if (!chipsContainer) return;

  chipsContainer.innerHTML = "";
  // Muestra hasta 60 chips para mantener el rendimiento fluido de la UI
  const slice = envioState.destinatarios.slice(0, 60);
  slice.forEach((email, idx) => {
    const chip = document.createElement("span");
    chip.className = "dest-chip";
    chip.innerHTML = `${escHtml(email)} <button type="button" class="dest-chip-del" title="Eliminar correo" style="background:none;border:none;color:var(--danger);cursor:pointer;margin-left:4px;font-size:10px;">✕</button>`;
    chip.querySelector("button").onclick = (e) => {
      e.stopPropagation();
      envioState.destinatarios.splice(idx, 1);
      renderDestinatarios();
    };
    chipsContainer.appendChild(chip);
  });

  if (total > 60) {
    const extra = document.createElement("span");
    extra.className = "dest-chip";
    extra.style.background = "var(--bg-elevated)";
    extra.textContent = `+${(total - 60).toLocaleString("es-EC")} más…`;
    chipsContainer.appendChild(extra);
  }
}

function initDestinatariosSection() {
  // Pestañas de origen
  $("#tab-src-archivo").onclick = () => switchDestSourceTab("archivo");
  $("#tab-src-purgados").onclick = () => {
    updatePurgadosDisponibles();
    switchDestSourceTab("purgados");
  };
  $("#tab-src-manual").onclick = () => switchDestSourceTab("manual");

  // Tab 1: Cargar Archivo
  const dropMini = $("#drop-dest-archivo");
  const btnSelectArchivo = $("#btn-env-select-archivo");

  const seleccionarArchivo = async () => {
    const path = await window.MxCorreo.openFile({
      title: "Seleccionar archivo de empresas (Excel, CSV, TXT)",
      filters: [
        { name: "Archivos de datos (Excel, CSV, TXT)", extensions: ["xlsx", "xls", "csv", "txt", "mxlista"] },
        { name: "Archivos Excel (*.xlsx, *.xls)", extensions: ["xlsx", "xls"] },
        { name: "Archivos CSV (*.csv)", extensions: ["csv"] },
        { name: "Archivos de texto (*.txt)", extensions: ["txt"] },
        { name: "Todos los archivos", extensions: ["*"] },
      ],
    });
    if (path) cargarArchivoDestinatarios(path);
  };

  btnSelectArchivo.onclick = (e) => {
    e.stopPropagation();
    seleccionarArchivo();
  };
  dropMini.onclick = seleccionarArchivo;

  // Drag & drop en dropzone mini
  dropMini.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropMini.classList.add("dragover");
  });
  dropMini.addEventListener("dragleave", () => dropMini.classList.remove("dragover"));
  dropMini.addEventListener("drop", (e) => {
    e.preventDefault();
    dropMini.classList.remove("dragover");
    const file = e.dataTransfer.files[0];
    if (file && file.path) cargarArchivoDestinatarios(file.path);
  });

  // Tab 2: Usar Purgados
  $("#btn-env-cargar-purgados").onclick = () => {
    const validos = state.verificacionResult?.lista_validos || [];
    if (validos.length === 0) {
      toast("No hay correos purgados en memoria.", "warning");
      return;
    }
    envioState.destinatarios = [...validos];
    renderDestinatarios();
    toast(`Cargados ${validos.length.toLocaleString("es-EC")} correos purgados con éxito`, "ok");
  };

  // Tab 3: Pegar Correos Manuales
  $("#btn-env-procesar-manual").onclick = () => {
    const raw = $("#env-dest-textarea").value;
    if (!raw.trim()) {
      toast("Pega al menos un correo.", "warning");
      return;
    }
    const regex = /[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}/g;
    const matches = raw.match(regex) || [];
    if (matches.length === 0) {
      toast("No se encontraron correos válidos en el texto pegado.", "error");
      return;
    }
    const vistos = new Set(envioState.destinatarios.map((c) => c.toLowerCase()));
    let agregados = 0;
    matches.forEach((m) => {
      const low = m.toLowerCase();
      if (!vistos.has(low)) {
        vistos.add(low);
        envioState.destinatarios.push(m.trim());
        agregados++;
      }
    });
    renderDestinatarios();
    $("#env-dest-textarea").value = "";
    toast(`Se agregaron ${agregados.toLocaleString("es-EC")} correos únicos (${matches.length} encontrados).`, "ok");
  };

  // Botón Limpiar Destinatarios
  $("#btn-env-limpiar-dest").onclick = () => {
    envioState.destinatarios = [];
    $("#env-archivo-info").style.display = "none";
    $("#env-dest-textarea").value = "";
    renderDestinatarios();
    toast("Lista de destinatarios limpiada.", "info");
  };
}

async function cargarArchivoDestinatarios(filePath) {
  const nombre = filePath.split(/[\\/]/).pop();
  toast(`Extrayendo correos de ${nombre}…`, "info", 3000);
  try {
    const res = await window.MxCorreo.py("cargar_contactos_archivo", { ruta: filePath });
    if (!res.ok) throw new Error(res.error);

    const correos = res.data.correos || [];
    envioState.destinatarios = correos;

    $("#env-archivo-info").style.display = "flex";
    $("#env-archivo-nombre").textContent = nombre;
    $("#env-archivo-total").textContent = `${correos.length.toLocaleString("es-EC")} empresas`;

    renderDestinatarios();
    toast(`¡Éxito! ${correos.length.toLocaleString("es-EC")} correos extraídos de ${nombre}`, "ok");
  } catch (err) {
    toast(`Error cargando archivo: ${err.message}`, "error", 7000);
  }
}

function initSmtpSection() {
  // Presets
  const presetSelect = $("#env-smtp-preset");
  presetSelect.onchange = () => {
    const val = presetSelect.value;
    if (val === "gmail") {
      $("#env-smtp-host").value = "smtp.gmail.com";
      $("#env-smtp-port").value = "465";
      $("#env-smtp-sec").value = "ssl";
      $("#env-smtp-user").placeholder = "tu-empresa@gmail.com";
      toast("Configurado preset Gmail (SSL en puerto 465). Recuerda usar una Contraseña de Aplicación de Google.", "info", 6000);
    } else if (val === "outlook") {
      $("#env-smtp-host").value = "smtp.office365.com";
      $("#env-smtp-port").value = "587";
      $("#env-smtp-sec").value = "starttls";
      $("#env-smtp-user").placeholder = "tu-empresa@outlook.com";
      toast("Configurado preset Outlook / Microsoft 365 (STARTTLS en puerto 587).", "info", 5000);
    }
  };

  // Toggle Password
  const btnTogglePass = $("#btn-toggle-pass");
  const passInput = $("#env-smtp-pass");
  btnTogglePass.onclick = () => {
    if (passInput.type === "password") {
      passInput.type = "text";
      btnTogglePass.textContent = "🙈";
    } else {
      passInput.type = "password";
      btnTogglePass.textContent = "👁️";
    }
  };

  // Guardar credenciales en localStorage
  $("#btn-save-smtp-prefs").onclick = () => {
    const prefs = {
      preset: presetSelect.value,
      host: $("#env-smtp-host").value.trim(),
      port: $("#env-smtp-port").value.trim(),
      sec: $("#env-smtp-sec").value,
      user: $("#env-smtp-user").value.trim(),
      from_name: $("#env-smtp-from-name").value.trim(),
      from_email: $("#env-smtp-from-email").value.trim(),
      reply_to: $("#env-smtp-reply-to").value.trim(),
      intervalo: $("#env-intervalo").value.trim(),
      max_limit: $("#env-max-limit").value.trim(),
    };
    try {
      localStorage.setItem("mx_smtp_prefs_v2", JSON.stringify(prefs));
      toast("Credenciales y configuración guardadas en este equipo ✅", "ok");
    } catch (e) {
      toast("No se pudo guardar en almacenamiento local.", "error");
    }
  };

  // Cargar credenciales guardadas
  try {
    const saved = localStorage.getItem("mx_smtp_prefs_v2");
    if (saved) {
      const p = JSON.parse(saved);
      if (p.preset) presetSelect.value = p.preset;
      if (p.host) $("#env-smtp-host").value = p.host;
      if (p.port) $("#env-smtp-port").value = p.port;
      if (p.sec) $("#env-smtp-sec").value = p.sec;
      if (p.user) $("#env-smtp-user").value = p.user;
      if (p.from_name) $("#env-smtp-from-name").value = p.from_name;
      if (p.from_email) $("#env-smtp-from-email").value = p.from_email;
      if (p.reply_to) $("#env-smtp-reply-to").value = p.reply_to;
      if (p.intervalo) $("#env-intervalo").value = p.intervalo;
      if (p.max_limit) $("#env-max-limit").value = p.max_limit;
    }
  } catch (e) {
    console.warn("No se pudieron cargar las preferencias SMTP:", e);
  }

  // Probar conexión SMTP
  $("#btn-test-smtp").onclick = async () => {
    const host = $("#env-smtp-host").value.trim();
    const puerto = parseInt($("#env-smtp-port").value.trim()) || 465;
    const seguridad = $("#env-smtp-sec").value;
    const usuario = $("#env-smtp-user").value.trim();
    const password = $("#env-smtp-pass").value;

    if (!host || !usuario) {
      toast("Ingresa el host SMTP y el usuario antes de probar.", "warning");
      return;
    }

    const statusEl = $("#smtp-test-status");
    statusEl.className = "status-msg loading";
    statusEl.textContent = "Conectando al servidor SMTP…";

    try {
      const res = await window.MxCorreo.py("probar_smtp", {
        host,
        puerto,
        seguridad,
        usuario,
        password,
      });

      if (!res.ok) throw new Error(res.error);

      statusEl.className = "status-msg ok";
      statusEl.textContent = "✅ " + res.data.mensaje;
      toast(res.data.mensaje, "ok", 6000);
    } catch (err) {
      statusEl.className = "status-msg error";
      statusEl.textContent = "❌ Error: " + err.message;
      toast(`Error de conexión SMTP: ${err.message}`, "error", 8000);
    }
  };
}

function initMensajeSection() {
  // Plantillas
  const tplSelect = $("#env-template-select");
  const applyTemplate = (key) => {
    const tpl = B2B_TEMPLATES[key];
    if (!tpl) return;
    if (tpl.asunto !== undefined) $("#env-msg-subject").value = tpl.asunto;
    if (tpl.cuerpo !== undefined) $("#env-msg-body").value = tpl.cuerpo;
    if (tpl.cuerpo_html !== undefined) $("#env-msg-html").value = tpl.cuerpo_html;
  };

  // Cargar plantilla por defecto
  applyTemplate("presentacion");

  tplSelect.onchange = () => {
    applyTemplate(tplSelect.value);
    toast(`Plantilla "${tplSelect.options[tplSelect.selectedIndex].text}" aplicada`, "info", 2500);
  };

  // Alternar Formato Texto / HTML
  const btnText = $("#btn-format-text");
  const btnHtml = $("#btn-format-html");
  const areaText = $("#env-msg-body");
  const areaHtml = $("#env-msg-html");

  btnText.onclick = () => {
    envioState.activeFormat = "text";
    btnText.classList.add("active");
    btnHtml.classList.remove("active");
    areaText.style.display = "block";
    areaHtml.style.display = "none";
  };

  btnHtml.onclick = () => {
    envioState.activeFormat = "html";
    btnHtml.classList.add("active");
    btnText.classList.remove("active");
    areaHtml.style.display = "block";
    areaText.style.display = "none";
    if (!areaHtml.value.trim() && areaText.value.trim()) {
      // Auto-convertir párrafos de texto plano a HTML simple
      const htmlified = areaText.value
        .split(/\n\n+/)
        .map((p) => `<p>${escHtml(p).replace(/\n/g, "<br>")}</p>`)
        .join("\n");
      areaHtml.value = htmlified;
    }
  };

  // Inserción de variables dinámicas
  $$(".var-chips-row .chip-btn").forEach((btn) => {
    btn.onclick = () => {
      const varTag = btn.dataset.var;
      const targetArea = envioState.activeFormat === "html" ? areaHtml : areaText;
      const start = targetArea.selectionStart || targetArea.value.length;
      const end = targetArea.selectionEnd || targetArea.value.length;
      const current = targetArea.value;
      targetArea.value = current.substring(0, start) + varTag + current.substring(end);
      targetArea.focus();
      targetArea.selectionStart = targetArea.selectionEnd = start + varTag.length;
    };
  });

  // Adjuntos
  $("#btn-env-add-adjunto").onclick = async () => {
    const path = await window.MxCorreo.openFile({
      title: "Seleccionar archivo adjunto para empresas",
      filters: [
        { name: "Documentos (PDF, Office, Zip)", extensions: ["pdf", "xlsx", "xls", "docx", "zip", "png", "jpg"] },
        { name: "Todos los archivos", extensions: ["*"] },
      ],
    });
    if (path) {
      if (!envioState.adjuntos.includes(path)) {
        envioState.adjuntos.push(path);
        renderAdjuntos();
        toast("Archivo adjunto agregado.", "info", 2000);
      } else {
        toast("Este archivo ya está en la lista de adjuntos.", "warning");
      }
    }
  };
}

function renderAdjuntos() {
  const container = $("#env-adjuntos-list");
  if (!container) return;
  container.innerHTML = "";

  if (envioState.adjuntos.length === 0) {
    container.innerHTML = '<span class="no-adjuntos-hint">Sin archivos adjuntos.</span>';
    return;
  }

  envioState.adjuntos.forEach((p, idx) => {
    const name = p.split(/[\\/]/).pop();
    const item = document.createElement("div");
    item.className = "adjunto-item";
    item.innerHTML = `
      <span style="overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="${escHtml(p)}">📎 ${escHtml(name)}</span>
      <button type="button" class="adjunto-del" title="Eliminar adjunto">✕</button>
    `;
    item.querySelector(".adjunto-del").onclick = () => {
      envioState.adjuntos.splice(idx, 1);
      renderAdjuntos();
    };
    container.appendChild(item);
  });
}

function initEnvioSection() {
  // Envío individual de prueba
  $("#btn-send-test-single").onclick = async () => {
    const testEmail = $("#env-test-email").value.trim();
    if (!testEmail || !testEmail.includes("@")) {
      toast("Ingresa un correo de destino válido para la prueba.", "warning");
      $("#env-test-email").focus();
      return;
    }

    const host = $("#env-smtp-host").value.trim();
    const puerto = parseInt($("#env-smtp-port").value.trim()) || 465;
    const seguridad = $("#env-smtp-sec").value;
    const usuario = $("#env-smtp-user").value.trim();
    const password = $("#env-smtp-pass").value;
    const remitenteNombre = $("#env-smtp-from-name").value.trim();
    const remitenteCorreo = $("#env-smtp-from-email").value.trim() || usuario;
    const replyTo = $("#env-smtp-reply-to").value.trim();

    const asunto = $("#env-msg-subject").value.trim();
    const cuerpo = $("#env-msg-body").value;
    const cuerpoHtml = $("#env-msg-html").value;

    if (!host || !usuario) {
      toast("Completa el Host y Usuario SMTP antes de enviar una prueba.", "warning");
      return;
    }
    if (!asunto || (!cuerpo && !cuerpoHtml)) {
      toast("Escribe el asunto y cuerpo del mensaje.", "warning");
      return;
    }

    const btn = $("#btn-send-test-single");
    btn.disabled = true;
    btn.innerHTML = "<span>⏳ Enviando prueba…</span>";

    try {
      const res = await window.MxCorreo.py("enviar_prueba", {
        host,
        puerto,
        seguridad,
        usuario,
        password,
        remitente_nombre: remitenteNombre,
        remitente_correo: remitenteCorreo,
        reply_to: replyTo,
        destinatario_prueba: testEmail,
        asunto,
        cuerpo,
        cuerpo_html: cuerpoHtml,
        adjuntos: envioState.adjuntos,
      });

      if (!res.ok) throw new Error(res.error);

      toast(`¡Prueba enviada con éxito a ${testEmail}! Revisa tu bandeja de entrada.`, "ok", 7000);
      appendLiveConsole(`[Prueba] ✅ Enviado a: ${testEmail} | Asunto: ${asunto}`, "ok");
    } catch (err) {
      toast(`Error al enviar prueba: ${err.message}`, "error", 8000);
      appendLiveConsole(`[Prueba] ❌ Error enviando a ${testEmail}: ${err.message}`, "err");
    } finally {
      btn.disabled = false;
      btn.innerHTML = "<span>📨 Enviar Prueba a mi Correo</span>";
    }
  };

  // Botón Lanzar Envío Masivo
  $("#btn-launch-send").onclick = () => {
    if (envioState.destinatarios.length === 0) {
      modal({
        icon: "⚠️",
        title: "Sin Destinatarios",
        body: "No has seleccionado o cargado ninguna empresa en la sección de Destinatarios. Carga un archivo Excel/CSV o pega correos primero.",
        confirmLabel: "Entendido",
        confirmClass: "btn-primary",
      });
      return;
    }

    const host = $("#env-smtp-host").value.trim();
    const usuario = $("#env-smtp-user").value.trim();
    const password = $("#env-smtp-pass").value;
    const asunto = $("#env-msg-subject").value.trim();
    const cuerpo = $("#env-msg-body").value;
    const cuerpoHtml = $("#env-msg-html").value;

    if (!host || !usuario) {
      toast("Faltan credenciales SMTP (Host y Usuario).", "error");
      return;
    }
    if (!asunto) {
      toast("El asunto del correo no puede estar vacío.", "error");
      return;
    }
    if (!cuerpo && !cuerpoHtml) {
      toast("El cuerpo del correo no puede estar vacío.", "error");
      return;
    }

    const totalLista = envioState.destinatarios.length;
    const limit = parseInt($("#env-max-limit").value) || 0;
    const totalEnviar = limit > 0 ? Math.min(limit, totalLista) : totalLista;
    const intervalo = parseFloat($("#env-intervalo").value) || 3;

    modal({
      icon: "🚀",
      title: "¿Iniciar Envío a Empresas?",
      body: `Estás a punto de enviar correos a ${totalEnviar.toLocaleString("es-EC")} empresa(s). ` +
            `Se aplicará una pausa anti-spam de ${intervalo} segundos entre cada envío. ` +
            `Puedes detener el envío en cualquier momento con el botón "Detener".`,
      confirmLabel: `Sí, Enviar a ${totalEnviar.toLocaleString("es-EC")} Empresas`,
      confirmClass: "btn-hero",
      onConfirm: () => ejecutarEnvioDirecto(totalEnviar, intervalo),
    });
  };

  // Botón Detener Envío
  $("#btn-cancel-send").onclick = async () => {
    appendLiveConsole(`[Detener] Solicitando cancelación del envío…`, "warn");
    try {
      const r = await window.MxCorreo.py("cancelar_envio", {});
      if (r.ok) {
        toast("Señal de cancelación enviada.", "info");
      }
    } catch (e) {
      console.error(e);
    }
  };

  // Botón Exportar Bitácora
  $("#btn-export-log-csv").onclick = async () => {
    if (envioState.logEnvios.length === 0) {
      toast("No hay registros de envío para exportar.", "warning");
      return;
    }

    const dest = await window.MxCorreo.saveFile({
      title: "Guardar Bitácora de Envíos",
      defaultName: `bitacora_envios_${new Date().toISOString().slice(0, 10)}.csv`,
      filters: [{ name: "Archivo CSV (*.csv)", extensions: ["csv"] }],
    });
    if (!dest) return;

    try {
      const res = await window.MxCorreo.py("exportar_bitacora", {
        registros: envioState.logEnvios,
        destino: dest,
      });
      if (res.ok) {
        toast(`Bitácora guardada (${res.data.total} registros) → ${dest}`, "ok");
        window.MxCorreo.openPath(dest);
      } else {
        throw new Error(res.error);
      }
    } catch (e) {
      toast(`Error guardando bitácora: ${e.message}`, "error");
    }
  };
}

async function ejecutarEnvioDirecto(totalEnviar, intervalo) {
  if (envioState.enviando) return;
  envioState.enviando = true;
  envioState.totalLote = totalEnviar;
  envioState.enviadosCount = 0;
  envioState.erroresCount = 0;
  envioState.logEnvios = [];

  // Actualizar UI
  $("#btn-launch-send").style.display = "none";
  $("#btn-cancel-send").style.display = "inline-flex";
  $("#env-monitor-box").style.display = "block";
  $("#mon-enviados").textContent = "0";
  $("#mon-errores").textContent = "0";
  $("#mon-total").textContent = totalEnviar.toLocaleString("es-EC");
  $("#mon-progress-bar").style.width = "0%";
  $("#mon-status-text").textContent = "Conectando al servidor SMTP…";
  $("#mon-pct-text").textContent = "0%";

  const consoleBox = $("#env-live-console");
  consoleBox.innerHTML = "";
  appendLiveConsole(`[Inicio] Preparando tanda de ${totalEnviar.toLocaleString("es-EC")} envíos a empresas…`, "info");
  appendLiveConsole(`[Anti-Spam] Pausa de ${intervalo}s por correo activada.`, "info");

  const host = $("#env-smtp-host").value.trim();
  const puerto = parseInt($("#env-smtp-port").value.trim()) || 465;
  const seguridad = $("#env-smtp-sec").value;
  const usuario = $("#env-smtp-user").value.trim();
  const password = $("#env-smtp-pass").value;
  const remitenteNombre = $("#env-smtp-from-name").value.trim();
  const remitenteCorreo = $("#env-smtp-from-email").value.trim() || usuario;
  const replyTo = $("#env-smtp-reply-to").value.trim();
  const asunto = $("#env-msg-subject").value.trim();
  const cuerpo = $("#env-msg-body").value;
  const cuerpoHtml = $("#env-msg-html").value;

  const payload = {
    host,
    puerto,
    seguridad,
    usuario,
    password,
    remitente_nombre: remitenteNombre,
    remitente_correo: remitenteCorreo,
    reply_to: replyTo,
    destinatarios: envioState.destinatarios.slice(0, totalEnviar),
    asunto,
    cuerpo,
    cuerpo_html: cuerpoHtml,
    adjuntos: envioState.adjuntos,
    intervalo_segundos: intervalo,
    max_envios: totalEnviar,
  };

  try {
    const res = await window.MxCorreo.py("enviar_directo", payload);

    if (!res.ok) throw new Error(res.error);

    const d = res.data;
    if (d.cancelado) {
      appendLiveConsole(`[Detenido] Envío cancelado por el usuario. Enviados: ${d.enviados}, Errores: ${d.errores}`, "warn");
      toast(`Envío detenido. Se enviaron ${d.enviados} correos.`, "warning", 6000);
      $("#mon-status-text").textContent = "Envío detenido por el usuario";
    } else {
      appendLiveConsole(`[Fin] ✅ Proceso completado exitosamente. Total: ${d.enviados} enviados, ${d.errores} errores.`, "ok");
      toast(`¡Campaña finalizada! ${d.enviados} enviados de ${d.total_intentados}.`, "ok", 8000);
      $("#mon-status-text").textContent = "Envío finalizado con éxito 🎉";
      $("#mon-progress-bar").style.width = "100%";
      $("#mon-pct-text").textContent = "100%";
    }
  } catch (err) {
    appendLiveConsole(`[Error fatal] ${err.message}`, "err");
    toast(`Error en el proceso de envío: ${err.message}`, "error", 10000);
    $("#mon-status-text").textContent = "Error en el envío";
  } finally {
    envioState.enviando = false;
    $("#btn-launch-send").style.display = "inline-flex";
    $("#btn-cancel-send").style.display = "none";
    triggerAutoSync("fin_envio_empresas");
  }
}

function handleEnvioEvent(msg) {
  const d = msg.data || {};
  const timeStr = new Date().toLocaleTimeString("es-EC");

  if (msg.event === "correo_enviado") {
    envioState.enviadosCount++;
    $("#mon-enviados").textContent = envioState.enviadosCount.toLocaleString("es-EC");

    const sum = envioState.enviadosCount + envioState.erroresCount;
    const pct = envioState.totalLote > 0 ? Math.min(100, Math.round((sum / envioState.totalLote) * 100)) : 0;
    $("#mon-progress-bar").style.width = `${pct}%`;
    $("#mon-pct-text").textContent = `${pct}%`;
    $("#mon-status-text").textContent = `Enviando ${sum} de ${envioState.totalLote}…`;

    const emp = d.empresa ? ` (${d.empresa})` : "";
    appendLiveConsole(`[${timeStr}] ✅ ${d.numero}/${d.total} Enviado a: ${d.correo}${emp}`, "ok");
    envioState.logEnvios.push({
      numero: d.numero,
      hora: timeStr,
      correo: d.correo,
      empresa: d.empresa || "",
      estado: "ENVIADO",
      detalle: "Envío exitoso",
    });
  } else if (msg.event === "correo_error") {
    envioState.erroresCount++;
    $("#mon-errores").textContent = envioState.erroresCount.toLocaleString("es-EC");

    const sum = envioState.enviadosCount + envioState.erroresCount;
    const pct = envioState.totalLote > 0 ? Math.min(100, Math.round((sum / envioState.totalLote) * 100)) : 0;
    $("#mon-progress-bar").style.width = `${pct}%`;
    $("#mon-pct-text").textContent = `${pct}%`;

    appendLiveConsole(`[${timeStr}] ❌ Error en ${d.correo}: ${d.error}`, "err");
    envioState.logEnvios.push({
      numero: d.numero || envioState.enviadosCount + envioState.erroresCount,
      hora: timeStr,
      correo: d.correo,
      empresa: d.empresa || "",
      estado: "ERROR",
      detalle: d.error,
    });
  } else if (msg.event === "envio_cancelado") {
    appendLiveConsole(`[${timeStr}] ⏹️ Envío cancelado por solicitud del usuario.`, "warn");
  }
}

function appendLiveConsole(text, type = "info") {
  const c = $("#env-live-console");
  if (!c) return;
  const line = document.createElement("div");
  const cls = type === "ok" ? "success" : type === "err" ? "error" : type;
  line.className = `console-line ${cls}`;
  line.textContent = text;
  c.appendChild(line);
  c.scrollTop = c.scrollHeight;
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

// ─── Módulo de Auto-Actualización ───────────────────────────────────────────
const updateState = {
  currentVersion: "2.0.0",
  latestVersion: "2.1.0",
  isOutdated: false,
  release: null,
  updating: false,
};

function initAutoUpdateModule() {
  const modalOverlay = $("#update-modal-overlay");
  const viewOutdated = $("#update-view-outdated");
  const viewProgress = $("#update-view-progress");
  const viewSuccess = $("#update-view-success");

  const badgeTitlebar = $("#badge-update-available");
  const btnCheckSidebar = $("#btn-check-updates-sidebar");
  const btnStartUpdate = $("#btn-start-update");
  const btnPostpone = $("#btn-postpone-update");

  function showModalView(view) {
    if (!modalOverlay) return;
    modalOverlay.style.display = "flex";
    if (viewOutdated) viewOutdated.style.display = view === "outdated" ? "flex" : "none";
    if (viewProgress) viewProgress.style.display = view === "progress" ? "flex" : "none";
    if (viewSuccess) viewSuccess.style.display = view === "success" ? "flex" : "none";
  }

  function hideModal() {
    if (modalOverlay && !updateState.updating) {
      modalOverlay.style.display = "none";
    }
  }

  if (badgeTitlebar) {
    badgeTitlebar.onclick = () => showModalView("outdated");
  }

  if (btnCheckSidebar) {
    btnCheckSidebar.onclick = () => checkUpdates(false);
  }

  if (btnPostpone) {
    btnPostpone.onclick = () => hideModal();
  }

  // Escuchar progreso desde el proceso main de Electron
  if (window.MxCorreo && window.MxCorreo.onUpdateProgress) {
    window.MxCorreo.onUpdateProgress((prog) => {
      const bar = $("#update-progress-bar");
      const pctText = $("#update-percent-text");
      const stepLbl = $("#update-step-label");

      if (bar) bar.style.width = `${prog.percent}%`;
      if (pctText) pctText.textContent = `${prog.percent}%`;
      if (stepLbl) stepLbl.textContent = prog.status;

      // Actualizar terminal de pasos visuales
      const pct = prog.percent;
      updateStepLog(1, pct >= 10, pct > 20);
      updateStepLog(2, pct >= 25, pct > 50);
      updateStepLog(3, pct >= 50, pct > 70);
      updateStepLog(4, pct >= 70, pct > 88);
      updateStepLog(5, pct >= 90, pct >= 100);
    });
  }

  function updateStepLog(stepNum, isActive, isDone) {
    const el = $(`#step-log-${stepNum}`);
    if (!el) return;
    const dot = el.querySelector(".step-dot");
    if (isDone) {
      el.className = "step-log-item done";
      if (dot) dot.textContent = "✓";
    } else if (isActive) {
      el.className = "step-log-item active";
      if (dot) dot.textContent = "●";
    } else {
      el.className = "step-log-item";
      if (dot) dot.textContent = "○";
    }
  }

  // Clic en "⚡ Actualizar Ahora"
  if (btnStartUpdate) {
    btnStartUpdate.onclick = async () => {
      updateState.updating = true;
      btnStartUpdate.disabled = true;
      showModalView("progress");

      try {
        const res = await window.MxCorreo.applyUpdate({
          targetVersion: updateState.latestVersion || "2.1.0",
          release: updateState.release,
        });

        if (res && res.ok) {
          // Mostrar pantalla de éxito
          showModalView("success");
          const lblVer = $("#success-version-label");
          if (lblVer) lblVer.textContent = `v${res.version || updateState.latestVersion}`;

          // Cuenta regresiva de reinicio
          let countdown = 3;
          const lblCount = $("#restarting-countdown-label");
          const timer = setInterval(() => {
            countdown -= 1;
            if (countdown > 0) {
              if (lblCount) lblCount.textContent = `Reabriendo en ${countdown} segundos...`;
            } else {
              clearInterval(timer);
              if (lblCount) lblCount.textContent = "Reiniciando la aplicación ahora...";
              setTimeout(() => {
                if (window.MxCorreo && window.MxCorreo.restartApp) {
                  window.MxCorreo.restartApp();
                } else {
                  window.location.reload();
                }
              }, 400);
            }
          }, 1000);
        } else {
          toast(`Error durante la actualización: ${res?.error || "Desconocido"}`, "error", 8000);
          updateState.updating = false;
          btnStartUpdate.disabled = false;
          showModalView("outdated");
        }
      } catch (err) {
        toast(`Fallo en el proceso de actualización: ${err.message}`, "error", 8000);
        updateState.updating = false;
        btnStartUpdate.disabled = false;
        showModalView("outdated");
      }
    };
  }

  async function checkUpdates(silent = true) {
    const icon = $("#btn-updates-icon");
    const lbl = $("#btn-updates-label");
    if (!silent) {
      if (icon) icon.className = "animate-spin";
      if (lbl) lbl.textContent = "Comprobando…";
    }

    try {
      if (!window.MxCorreo || !window.MxCorreo.checkUpdates) return;

      const res = await window.MxCorreo.checkUpdates();
      if (res && res.ok) {
        updateState.currentVersion = res.current_version || "2.0.0";
        updateState.latestVersion = res.latest_version || "2.1.0";
        updateState.isOutdated = Boolean(res.outdated);
        updateState.release = res.release;

        // Actualizar version en titlebar
        const titlebarVer = $("#titlebar-version");
        if (titlebarVer) titlebarVer.textContent = `v${updateState.currentVersion}`;

        if (res.outdated) {
          // Mostrar badge en titlebar
          if (badgeTitlebar) {
            badgeTitlebar.style.display = "inline-flex";
            badgeTitlebar.textContent = `⚠️ Desactualizada (v${updateState.latestVersion})`;
          }

          // Rellenar modal
          const currEl = $("#modal-curr-version");
          const targetEl = $("#modal-target-version");
          if (currEl) currEl.textContent = `v${updateState.currentVersion}`;
          if (targetEl) targetEl.textContent = `v${updateState.latestVersion}`;

          if (res.release && Array.isArray(res.release.changelog)) {
            const listEl = $("#modal-changelog-list");
            if (listEl) {
              listEl.innerHTML = res.release.changelog
                .map((ch) => `<li>${escHtml(ch)}</li>`)
                .join("");
            }
          }

          // Si es la comprobación inicial o manual, abrir el modal
          showModalView("outdated");
        } else {
          if (badgeTitlebar) badgeTitlebar.style.display = "none";
          if (!silent) {
            toast(`¡Tu versión de MxCorreo está actualizada (v${updateState.currentVersion})! ✅`, "ok", 4500);
          }
        }
      } else {
        if (!silent) {
          toast(`No se pudo verificar actualizaciones: ${res?.error || "Servidor no disponible"}`, "warning", 5000);
        }
      }
    } catch (e) {
      if (!silent) {
        toast(`Error al buscar actualizaciones: ${e.message}`, "error", 5000);
      }
    } finally {
      if (!silent) {
        if (icon) icon.className = "";
        if (lbl) lbl.textContent = "Buscar Actualizaciones";
      }
    }
  }

  // Verificar actualizaciones automáticamente a los 1.5s de arrancar la app
  setTimeout(() => {
    checkUpdates(true);
  }, 1500);
}

// ─── Auto-Sincronización Silenciosa y Totalmente Autónoma ───────────────────
async function triggerAutoSync(motivo = "auto") {
  try {
    if (!window.MxCorreo || !window.MxCorreo.py) return;
    const res = await window.MxCorreo.py("sincronizar_panel", { motivo, silent: true });
    if (res && res.ok) {
      console.log(`[AutoSync] Telemetría enviada a la nube automáticamente (${motivo})`);
      const dot = $("#status-dot");
      if (dot) {
        dot.className = "dot-ok";
        dot.title = `Sincronizado con el panel web (${new Date().toLocaleTimeString("es-EC")})`;
      }
    }
  } catch (err) {
    console.warn(`[AutoSync] Segundo plano (${motivo}):`, err.message);
  }
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
  initApartadoEnvio();
  initAutoUpdateModule();

  // Auto-sincronización inicial a los 3 segundos de arrancar la app
  setTimeout(() => triggerAutoSync("inicio_app"), 3000);

  // Auto-sincronización periódica cada 4 minutos mientras la app esté abierta
  setInterval(() => triggerAutoSync("heartbeat_periodico"), 240000);

  // Botón Sincronizar con Panel Web (Manual opcional)
  const btnSync = $("#btn-sync-cloud-panel");
  if (btnSync) {
    btnSync.onclick = async () => {
      btnSync.disabled = true;
      btnSync.innerHTML = "<span>⏳ Sincronizando…</span>";
      toast("Enviando telemetría al Panel Web de Gerencia…", "info", 3000);

      try {
        const res = await window.MxCorreo.py("sincronizar_panel", {});
        if (res.ok) {
          toast("¡Métricas sincronizadas con el Panel Web con éxito! ✅", "ok", 6000);
        } else {
          toast(`Aviso al sincronizar: ${res.error}`, "warning", 7000);
        }
      } catch (err) {
        toast(`Error de red: ${err.message}`, "error");
      } finally {
        btnSync.disabled = false;
        btnSync.innerHTML = "<span>☁️ Sincronizar con Panel Web</span>";
      }
    };
  }

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

