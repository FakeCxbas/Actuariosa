/**
 * preload.js — Puente seguro entre el proceso main y el renderer.
 * Expone solo las APIs necesarias con contextIsolation activado.
 */

const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("MxCorreo", {
  // ── Comandos al backend Python ──────────────────────────────────────────
  py: (cmd, params = {}) => ipcRenderer.invoke("py-cmd", { cmd, params }),

  // ── Eventos del backend Python ──────────────────────────────────────────
  onPyProgress: (cb) => {
    const handler = (_e, msg) => cb(msg);
    ipcRenderer.on("py-progress", handler);
    return () => ipcRenderer.removeListener("py-progress", handler);
  },
  onPyEvent: (cb) => {
    const handler = (_e, msg) => cb(msg);
    ipcRenderer.on("py-event", handler);
    return () => ipcRenderer.removeListener("py-event", handler);
  },
  onPyResult: (cb) => {
    const handler = (_e, msg) => cb(msg);
    ipcRenderer.on("py-result", handler);
    return () => ipcRenderer.removeListener("py-result", handler);
  },
  onPyLog: (cb) => {
    const handler = (_e, msg) => cb(msg);
    ipcRenderer.on("python-log", handler);
    return () => ipcRenderer.removeListener("python-log", handler);
  },

  // ── Diálogos del sistema ────────────────────────────────────────────────
  openFile: (opts) => ipcRenderer.invoke("dialog-open-file", opts || {}),
  saveFile: (opts) => ipcRenderer.invoke("dialog-save-file", opts || {}),
  openPath: (p) => ipcRenderer.invoke("shell-open", p),

  // ── Módulo de Auto-Actualizaciones ──────────────────────────────────────
  getVersion: () => ipcRenderer.invoke("get-app-version"),
  checkUpdates: (url) => ipcRenderer.invoke("check-updates", url),
  applyUpdate: (opts) => ipcRenderer.invoke("apply-update", opts),
  restartApp: () => ipcRenderer.invoke("restart-app"),
  onUpdateProgress: (cb) => {
    const handler = (_e, msg) => cb(msg);
    ipcRenderer.on("update-progress", handler);
    return () => ipcRenderer.removeListener("update-progress", handler);
  },

  // ── Controles de ventana ────────────────────────────────────────────────
  minimize: () => ipcRenderer.send("window-minimize"),
  maximize: () => ipcRenderer.send("window-maximize"),
  close: () => ipcRenderer.send("window-close"),
});
