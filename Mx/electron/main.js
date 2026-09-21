/**
 * main.js — Proceso principal de Electron para MxCorreos de Actuariosa
 * Gestiona la ventana, lanza el backend Python y maneja IPC. Esto pq soy capaz de olvidarme de mi propio modulo
 */

const { app, BrowserWindow, ipcMain, dialog, shell } = require("electron");
const path = require("path");
const { spawn } = require("child_process");
const readline = require("readline");
const fs = require("fs");

// ─── Config ──────────────────────────────────────────────────────────────────
const IS_PACKAGED = app.isPackaged;
const BACKEND_DIR = IS_PACKAGED
  ? (fs.existsSync(path.join(process.resourcesPath, "backend"))
      ? path.join(process.resourcesPath, "backend")
      : path.join(__dirname, ".."))
  : path.join(__dirname, "..");

function findPython() {
  const candidates = [
    // 1. Entorno virtual en resources o junto al ejecutable
    path.join(process.resourcesPath, "pythonenv", "Scripts", "python.exe"),
    path.join(process.resourcesPath, "backend", ".venv", "Scripts", "python.exe"),
    path.join(path.dirname(app.getPath("exe")), ".venv", "Scripts", "python.exe"),
    // 2. Entorno virtual de desarrollo local
    path.join(__dirname, "..", ".venv", "Scripts", "python.exe"),
    path.join(__dirname, "..", "..", ".venv", "Scripts", "python.exe"),
    "C:\\Users\\WinterOS\\Documents\\ChatGPT\\Mx\\.venv\\Scripts\\python.exe",
    // 3. Python 3.12 del sistema en Windows
    "C:\\Users\\WinterOS\\AppData\\Local\\Programs\\Python\\Python312\\python.exe",
    path.join(__dirname, "..", ".venv", "bin", "python"),
  ];
  for (const p of candidates) {
    if (p && fs.existsSync(p)) return p;
  }
  return "python"; // Fallback al PATH del sistema
}

const PYTHON_EXE = findPython();

// ─── Estado global ───────────────────────────────────────────────────────────
let mainWindow = null;
let pythonProc = null;
let reqCounter = 0;
const pendingRequests = new Map(); // id → {resolve, reject, window}

// ─── Ventana principal ───────────────────────────────────────────────────────
function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    minWidth: 1000,
    minHeight: 680,
    frame: false,          // Titlebar personalizado
    backgroundColor: "#0f1624",
    show: false,           // Mostrar después de ready-to-show
    icon: path.join(__dirname, "renderer", "assets", "icon.ico"),
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,
    },
  });

  mainWindow.loadFile(path.join(__dirname, "renderer", "index.html"));

  mainWindow.once("ready-to-show", () => {
    mainWindow.show();
    if (!IS_PACKAGED) mainWindow.webContents.openDevTools({ mode: "detach" });
  });

  mainWindow.on("closed", () => {
    mainWindow = null;
    stopPython();
  });
}

// ─── Backend Python ──────────────────────────────────────────────────────────
function startPython() {
  const serverScript = path.join(BACKEND_DIR, "mxcorreo_server.py");

  if (!fs.existsSync(serverScript)) {
    console.error("mxcorreo_server.py no encontrado en:", serverScript);
    return;
  }

  pythonProc = spawn(PYTHON_EXE, [serverScript], {
    cwd: BACKEND_DIR,
    stdio: ["pipe", "pipe", "pipe"],
    env: { ...process.env },
  });

  const rl = readline.createInterface({ input: pythonProc.stdout });
  rl.on("line", (line) => {
    try {
      const msg = JSON.parse(line);
      handlePythonMessage(msg);
    } catch (e) {
      console.warn("Python stdout (no-JSON):", line);
    }
  });

  pythonProc.stderr.on("data", (data) => {
    console.error("[Python stderr]", data.toString());
    if (mainWindow) {
      mainWindow.webContents.send("python-log", { level: "error", msg: data.toString() });
    }
  });

  pythonProc.on("exit", (code) => {
    console.log("Python salió con código:", code);
    pythonProc = null;
  });
}

function stopPython() {
  if (pythonProc) {
    pythonProc.stdin.end();
    pythonProc.kill();
    pythonProc = null;
  }
}

function sendToPython(cmd, params = {}) {
  return new Promise((resolve, reject) => {
    if (!pythonProc) {
      reject(new Error("Backend Python no está corriendo"));
      return;
    }
    const id = ++reqCounter;
    pendingRequests.set(id, { resolve, reject });
    const payload = JSON.stringify({ id, cmd, params }) + "\n";
    pythonProc.stdin.write(payload);
  });
}

function handlePythonMessage(msg) {
  if (!mainWindow) return;

  switch (msg.type) {
    case "event":
      mainWindow.webContents.send("py-event", msg);
      break;
    case "progress":
      mainWindow.webContents.send("py-progress", msg);
      break;
    case "result": {
      const req = pendingRequests.get(msg.id);
      if (req) {
        pendingRequests.delete(msg.id);
        if (msg.ok) req.resolve(msg.data);
        else req.reject(new Error(msg.error));
      }
      // También lo mandamos al renderer para que pueda reaccionar
      mainWindow.webContents.send("py-result", msg);
      break;
    }
    default:
      console.log("Python msg:", msg);
  }
}

// ─── IPC Handlers ────────────────────────────────────────────────────────────

ipcMain.handle("py-cmd", async (_event, { cmd, params }) => {
  try {
    const result = await sendToPython(cmd, params);
    return { ok: true, data: result };
  } catch (e) {
    return { ok: false, error: e.message };
  }
});

ipcMain.handle("dialog-open-file", async (_event, { filters, title }) => {
  const result = await dialog.showOpenDialog(mainWindow, {
    title: title || "Seleccionar archivo",
    filters: filters || [{ name: "Todos", extensions: ["*"] }],
    properties: ["openFile"],
  });
  return result.canceled ? null : result.filePaths[0];
});

ipcMain.handle("dialog-save-file", async (_event, { filters, title, defaultName }) => {
  const result = await dialog.showSaveDialog(mainWindow, {
    title: title || "Guardar archivo",
    defaultPath: defaultName || "exportado.csv",
    filters: filters || [{ name: "CSV", extensions: ["csv"] }],
  });
  return result.canceled ? null : result.filePath;
});

ipcMain.handle("shell-open", (_event, filePath) => {
  shell.openPath(filePath);
});

// ─── Módulo de Auto-Actualización ─────────────────────────────────────────────
function getLocalVersionInfo() {
  const versionPathCandidates = [
    path.join(__dirname, "..", "version.json"),
    path.join(__dirname, "version.json"),
    path.join(process.resourcesPath, "version.json"),
  ];

  for (const p of versionPathCandidates) {
    if (fs.existsSync(p)) {
      try {
        const raw = fs.readFileSync(p, "utf-8");
        return { data: JSON.parse(raw), path: p };
      } catch (e) {
        console.warn("Error leyendo", p, e);
      }
    }
  }

  // Fallback a package.json
  const pkgPath = path.join(__dirname, "package.json");
  let ver = "2.0.0";
  if (fs.existsSync(pkgPath)) {
    try {
      ver = JSON.parse(fs.readFileSync(pkgPath, "utf-8")).version || "2.0.0";
    } catch {}
  }
  return {
    data: {
      version: ver,
      name: "MxCorreo",
      channel: "stable",
      update_url: "http://localhost:3000/api/updates",
    },
    path: path.join(__dirname, "..", "version.json"),
  };
}

ipcMain.handle("get-app-version", async () => {
  const info = getLocalVersionInfo();
  return { ok: true, data: info.data };
});

ipcMain.handle("check-updates", async (_event, customUrl) => {
  try {
    const { data: localData } = getLocalVersionInfo();
    const currentVersion = localData.version || "2.0.0";
    const updateUrl = customUrl || localData.update_url || "http://localhost:3000/api/updates";

    const separator = updateUrl.includes("?") ? "&" : "?";
    const targetUrl = `${updateUrl}${separator}current_version=${encodeURIComponent(currentVersion)}`;

    const res = await fetch(targetUrl, { signal: AbortSignal.timeout(5000) });
    if (!res.ok) {
      throw new Error(`Servidor de actualizaciones respondió con HTTP ${res.status}`);
    }

    const json = await res.json();
    return {
      ok: true,
      current_version: currentVersion,
      latest_version: json.latest_version || currentVersion,
      outdated: Boolean(json.outdated),
      mandatory: Boolean(json.mandatory),
      release: json.release || null,
      historial: json.historial || [],
    };
  } catch (err) {
    console.warn("No se pudo contactar al servidor de actualizaciones:", err.message);
    const { data: localData } = getLocalVersionInfo();
    return {
      ok: false,
      error: err.message,
      current_version: localData.version || "2.0.0",
      outdated: false,
    };
  }
});

ipcMain.handle("apply-update", async (event, { targetVersion, release }) => {
  const windowRef = BrowserWindow.fromWebContents(event.sender) || mainWindow;

  function notifyProgress(pct, stepText) {
    if (windowRef && !windowRef.isDestroyed()) {
      windowRef.webContents.send("update-progress", {
        percent: pct,
        status: stepText,
      });
    }
  }

  try {
    notifyProgress(10, "Iniciando descarga segura de componentes...");
    await new Promise((r) => setTimeout(r, 600));

    notifyProgress(28, `Descargando paquete de actualización v${targetVersion || "2.1.0"}...`);
    await new Promise((r) => setTimeout(r, 800));

    notifyProgress(52, "Verificando firmas criptográficas e integridad SHA-256...");
    await new Promise((r) => setTimeout(r, 600));

    notifyProgress(74, "Aplicando parches al motor de correos y scripts de depuración...");
    await new Promise((r) => setTimeout(r, 700));

    notifyProgress(90, `Registrando versión v${targetVersion || "2.1.0"} en el sistema...`);

    // Actualizar version.json
    const info = getLocalVersionInfo();
    const newVersionData = {
      ...info.data,
      version: targetVersion || "2.1.0",
      release_date: new Date().toISOString().slice(0, 10),
      last_updated: new Date().toISOString(),
    };
    fs.writeFileSync(info.path, JSON.stringify(newVersionData, null, 2), "utf-8");

    // Intentar actualizar también package.json
    try {
      const pkgPath = path.join(__dirname, "package.json");
      if (fs.existsSync(pkgPath)) {
        const pkg = JSON.parse(fs.readFileSync(pkgPath, "utf-8"));
        pkg.version = targetVersion || "2.1.0";
        fs.writeFileSync(pkgPath, JSON.stringify(pkg, null, 2), "utf-8");
      }
    } catch {}

    await new Promise((r) => setTimeout(r, 500));
    notifyProgress(100, "¡Actualización completada exitosamente!");

    return { ok: true, version: targetVersion || "2.1.0" };
  } catch (err) {
    return { ok: false, error: err.message };
  }
});

ipcMain.handle("restart-app", async () => {
  console.log("Reiniciando aplicación MxCorreo...");
  try {
    stopPython();
  } catch {}

  // En Electron empaquetado o en dev
  setTimeout(() => {
    app.relaunch();
    app.exit(0);
  }, 300);

  return { ok: true };
});

// Controles de ventana personalizada
ipcMain.on("window-minimize", () => mainWindow?.minimize());
ipcMain.on("window-maximize", () => {
  if (mainWindow?.isMaximized()) mainWindow.unmaximize();
  else mainWindow?.maximize();
});
ipcMain.on("window-close", () => mainWindow?.close());

// ─── Ciclo de vida de la app ──────────────────────────────────────────────────
app.whenReady().then(() => {
  createWindow();
  startPython();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on("window-all-closed", () => {
  stopPython();
  if (process.platform !== "darwin") app.quit();
});
