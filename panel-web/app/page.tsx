"use client";

import React, { useState, useEffect, useMemo } from "react";
import {
  BarChart3,
  Mail,
  ShieldCheck,
  Send,
  CheckCircle2,
  Users,
  Building2,
  TrendingUp,
  MapPin,
  RefreshCw,
  UploadCloud,
  FileSpreadsheet,
  AlertCircle,
  Clock,
  ArrowRight,
  Filter,
  Download,
  Search,
  Plus,
  Lock,
  Unlock,
  Layers,
  Database,
  Server,
  FileText,
  Percent,
  Rocket,
  Sparkles,
} from "lucide-react";
import {
  TelemetriaActuariosa,
  LeadRespuesta,
  VersionRelease,
  initialTelemetryData,
} from "@/lib/data-store";

export default function DashboardGerencial() {
  const [data, setData] = useState<TelemetriaActuariosa>(initialTelemetryData);
  const [activeTab, setActiveTab] = useState<"general" | "flujo" | "respuestas" | "empresas" | "actualizaciones">("general");
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [lastSyncTime, setLastSyncTime] = useState<string>("");

  // Version Release / Updates state
  const [releaseData, setReleaseData] = useState<VersionRelease>(initialTelemetryData.version_actual_cliente!);
  const [targetVersion, setTargetVersion] = useState<string>("2.1.0");
  const [targetTitle, setTargetTitle] = useState<string>("Actualización v2.1.0 — Motor Masivo & Telemetría");
  const [targetChangelog, setTargetChangelog] = useState<string>(
    "- Apartado independiente para envíos masivos directos a empresas\n- Sincronización en tiempo real con panel web en Vercel\n- Validación y detección inteligente de rebotes\n- Módulo de auto-actualizaciones con reinicio automático"
  );
  const [isMandatory, setIsMandatory] = useState<boolean>(false);
  const [isPublishing, setIsPublishing] = useState<boolean>(false);

  // CRM / Leads state
  const [leads, setLeads] = useState<LeadRespuesta[]>(initialTelemetryData.leads_respuestas);
  const [filtroEstado, setFiltroEstado] = useState<string>("Todos");
  const [busquedaLead, setBusquedaLead] = useState<string>("");
  const [showAddLeadModal, setShowAddLeadModal] = useState<boolean>(false);
  const [showUploadModal, setShowUploadModal] = useState<boolean>(false);

  // New Lead Form State
  const [newEmpresa, setNewEmpresa] = useState<string>("");
  const [newCorreo, setNewCorreo] = useState<string>("");
  const [newRuc, setNewRuc] = useState<string>("");
  const [newProvincia, setNewProvincia] = useState<string>("GUAYAS");
  const [newEstado, setNewEstado] = useState<LeadRespuesta["estado"]>("Positivo / Interesado");
  const [newServicio, setNewServicio] = useState<LeadRespuesta["servicio_interes"]>("Jubilación Patronal / NIC 19");
  const [newNotas, setNewNotas] = useState<string>("");

  // Direct Drag & Drop upload status
  const [uploadStatus, setUploadStatus] = useState<string>("");

  // PIN / Auth state
  const [isAdminUnlocked, setIsAdminUnlocked] = useState<boolean>(true);
  const [toastMsg, setToastMsg] = useState<{ text: string; type: "ok" | "err" } | null>(null);

  const showToast = (text: string, type: "ok" | "err" = "ok") => {
    setToastMsg({ text, type });
    setTimeout(() => setToastMsg(null), 3500);
  };

  // Cargar datos del servidor (con soporte para auto-polling silencioso)
  const fetchTelemetry = async (silent: boolean = false) => {
    if (!silent) setIsRefreshing(true);
    try {
      const res = await fetch("/api/sync");
      const json = await res.json();
      if (json.ok && json.data) {
        setData(json.data);
        if (json.data.leads_respuestas) {
          setLeads(json.data.leads_respuestas);
        }
        setLastSyncTime(new Date().toLocaleTimeString("es-EC"));
        if (!silent) showToast("Panel actualizado con la nube.", "ok");
      }
    } catch (e) {
      if (!silent) console.warn("Usando datos locales consolidados:", e);
    } finally {
      if (!silent) setIsRefreshing(false);
    }
  };

  const fetchUpdates = async () => {
    try {
      const res = await fetch("/api/updates");
      const json = await res.json();
      if (json.ok && json.release) {
        setReleaseData(json.release);
      }
    } catch (e) {
      console.warn("Error cargando versión:", e);
    }
  };

  const handlePublishUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!targetVersion.trim()) {
      showToast("La versión no puede estar vacía", "err");
      return;
    }
    setIsPublishing(true);
    try {
      const res = await fetch("/api/updates", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          version: targetVersion.trim(),
          title: targetTitle.trim(),
          changelog: targetChangelog,
          mandatory: isMandatory,
        }),
      });
      const json = await res.json();
      if (json.ok && json.release) {
        setReleaseData(json.release);
        showToast(`¡Versión v${json.release.version} publicada exitosamente a clientes!`, "ok");
      } else {
        showToast(json.error || "Error al publicar actualización", "err");
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      showToast(`Error de conexión: ${msg}`, "err");
    } finally {
      setIsPublishing(false);
    }
  };

  useEffect(() => {
    fetchTelemetry(true);
    fetchUpdates();
    setLastSyncTime(new Date().toLocaleTimeString("es-EC"));

    // Auto-polling inteligente cada 20 segundos para el jefe (100% automático, sin F5)
    const liveTimer = setInterval(() => {
      fetchTelemetry(true);
    }, 20000);

    return () => clearInterval(liveTimer);
  }, []);

  // Filtrado de leads / respuestas
  const leadsFiltrados = useMemo(() => {
    return leads.filter((l) => {
      const matchEstado = filtroEstado === "Todos" || l.estado === filtroEstado;
      const q = busquedaLead.toLowerCase();
      const matchTexto =
        l.empresa.toLowerCase().includes(q) ||
        l.correo.toLowerCase().includes(q) ||
        (l.ruc && l.ruc.includes(q)) ||
        l.servicio_interes.toLowerCase().includes(q);
      return matchEstado && matchTexto;
    });
  }, [leads, filtroEstado, busquedaLead]);

  // Contadores de respuestas
  const conteoRespuestas = useMemo(() => {
    const positivos = leads.filter(
      (l) => l.estado === "Positivo / Interesado" || l.estado === "Cotización Solicitada" || l.estado === "En Negociación" || l.estado === "Cerrado / Cliente"
    ).length;
    const cotizaciones = leads.filter((l) => l.estado === "Cotización Solicitada" || l.estado === "En Negociación" || l.estado === "Cerrado / Cliente").length;
    const cerrados = leads.filter((l) => l.estado === "Cerrado / Cliente").length;
    const descartes = leads.filter((l) => l.estado === "No Interesado").length;
    return { positivos, cotizaciones, cerrados, descartes, total: leads.length };
  }, [leads]);

  // Agregar Lead nuevo
  const handleCreateLead = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newEmpresa || !newCorreo) {
      showToast("Completa la empresa y el correo.", "err");
      return;
    }

    try {
      const res = await fetch("/api/leads", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          empresa: newEmpresa,
          correo: newCorreo,
          ruc: newRuc,
          provincia: newProvincia,
          estado: newEstado,
          servicio_interes: newServicio,
          notas: newNotas,
        }),
      });
      const json = await res.json();
      if (json.ok && json.lead) {
        setLeads((prev) => [json.lead, ...prev]);
        setShowAddLeadModal(false);
        setNewEmpresa("");
        setNewCorreo("");
        setNewRuc("");
        setNewNotas("");
        showToast("¡Respuesta de empresa registrada con éxito!", "ok");
      } else {
        throw new Error(json.error || "Error al registrar");
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      showToast(msg, "err");
    }
  };

  // Actualizar estado de Lead
  const handleUpdateStatus = async (id: string, estado: LeadRespuesta["estado"]) => {
    try {
      const res = await fetch("/api/leads", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id, estado }),
      });
      const json = await res.json();
      if (json.ok) {
        setLeads((prev) =>
          prev.map((l) => (l.id === id ? { ...l, estado } : l))
        );
        showToast(`Estado cambiado a "${estado}"`, "ok");
      }
    } catch (e) {
      showToast("No se pudo actualizar el estado", "err");
    }
  };

  // Exportar Leads a CSV
  const exportarLeadsCSV = () => {
    const headers = ["ID", "Empresa", "Correo", "RUC", "Provincia", "Estado", "Servicio_Interes", "Fecha_Contacto", "Notas"];
    const rows = leads.map((l) => [
      l.id,
      `"${l.empresa.replace(/"/g, '""')}"`,
      `"${l.correo}"`,
      `"${l.ruc || ""}"`,
      `"${l.provincia || ""}"`,
      `"${l.estado}"`,
      `"${l.servicio_interes}"`,
      `"${l.fecha_contacto}"`,
      `"${(l.notas || "").replace(/"/g, '""')}"`,
    ]);

    const csvContent = "data:text/csv;charset=utf-8,\uFEFF" + [headers.join(","), ...rows.map((e) => e.join(","))].join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `prospectos_positivos_actuariosa_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    showToast("Reporte CSV descargado con éxito.", "ok");
  };

  // Carga manual de JSON en el cliente
  const handleFileUpload = (file: File) => {
    setUploadStatus("Leyendo archivo…");
    const reader = new FileReader();
    reader.onload = async (event) => {
      try {
        const text = event.target?.result as string;
        const parsed = JSON.parse(text);

        // Validar si es un Resumen_Depuracion_Supercias
        if (parsed.segmentos || parsed.total_entrada_20_septiembre) {
          const resGeneral = {
            total_recopilados_brutos: data.resumen_general.total_recopilados_brutos,
            total_base_activa: parsed.total_entrada_20_septiembre || data.resumen_general.total_base_activa,
            total_negocios_unicos: parsed.segmentos?.total_negocios_depurados_unicos || data.resumen_general.total_negocios_unicos,
            supercias_activas_con_ruc: parsed.segmentos?.supercias_activas_con_ruc || data.resumen_general.supercias_activas_con_ruc,
            negocios_corporativos: parsed.segmentos?.negocios_corporativos_activos || data.resumen_general.negocios_corporativos,
            descartados_inactivas: parsed.segmentos?.descartados_disolucion_o_inactivas || data.resumen_general.descartados_inactivas,
            instituciones_educativas: parsed.segmentos?.instituciones_educativas_colegios || data.resumen_general.instituciones_educativas,
            otros_genericos: parsed.segmentos?.otros_genericos_conservados || data.resumen_general.otros_genericos,
            correos_con_error_formato: data.resumen_general.correos_con_error_formato,
            duplicados_eliminados: data.resumen_general.duplicados_eliminados,
            total_enviados_campanas: data.resumen_general.total_enviados_campanas,
            total_errores_envio: data.resumen_general.total_errores_envio,
            tasa_entrega: data.resumen_general.tasa_entrega,
          };

          const payloadSync = {
            fuente: `Carga manual: ${file.name}`,
            resumen_general: resGeneral,
            distribucion_provincias: parsed.top_provincias_supercias_activas || data.distribucion_provincias,
            top_dominios: parsed.top_dominios_corporativos || data.top_dominios,
          };

          const res = await fetch("/api/sync", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payloadSync),
          });
          const json = await res.json();
          if (json.ok) {
            setData((prev) => ({
              ...prev,
              resumen_general: resGeneral,
              distribucion_provincias: payloadSync.distribucion_provincias,
              top_dominios: payloadSync.top_dominios,
              ultima_actualizacion: new Date().toISOString(),
            }));
            setUploadStatus("¡Datos sincronizados exitosamente!");
            showToast("Reporte importado y métricas actualizadas.", "ok");
            setTimeout(() => setShowUploadModal(false), 1200);
          }
        } else {
          setUploadStatus("Formato de JSON no reconocido como reporte de depuración.");
        }
      } catch (err) {
        setUploadStatus("Error al procesar el archivo JSON.");
      }
    };
    reader.readAsText(file);
  };

  const { resumen_general: kpis } = data;

  return (
    <div className="min-h-screen bg-[#070a12] text-slate-100 flex flex-col">
      {/* Toast Notification */}
      {toastMsg && (
        <div
          className={`fixed bottom-6 right-6 z-50 px-5 py-3 rounded-xl shadow-2xl flex items-center gap-3 border text-sm font-medium transition-all transform animate-bounce ${
            toastMsg.type === "ok"
              ? "bg-emerald-950/90 border-emerald-500/40 text-emerald-200"
              : "bg-rose-950/90 border-rose-500/40 text-rose-200"
          }`}
        >
          {toastMsg.type === "ok" ? <CheckCircle2 className="w-5 h-5 text-emerald-400" /> : <AlertCircle className="w-5 h-5 text-rose-400" />}
          <span>{toastMsg.text}</span>
        </div>
      )}

      {/* ── TOP EXECUTIVE BAR ─────────────────────────────────────── */}
      <header className="border-b border-white/[0.08] bg-[#0c1120]/80 backdrop-blur-md sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-20 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-indigo-600 to-blue-700 flex items-center justify-center shadow-lg shadow-indigo-600/30 ring-1 ring-white/20">
              <Building2 className="w-6 h-6 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-2.5">
                <h1 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
                  Actuariosa <span className="text-indigo-400 font-semibold text-sm px-2 py-0.5 rounded-full bg-indigo-500/10 border border-indigo-500/20">PANEL GERENCIAL</span>
                </h1>
                <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" title="El panel se actualiza automáticamente solo cada 20 segundos sin necesidad de recargar la página">
                  <span className="live-pulse"></span>
                  En Vivo • Auto-Sync
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                Supervisión del flujo de datos, depuración Supercias y prospección comercial B2B
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="hidden md:flex flex-col text-right text-xs">
              <span className="text-slate-400 flex items-center gap-1 justify-end">
                <Clock className="w-3.5 h-3.5 text-emerald-400" /> Auto-Sincronizado:
              </span>
              <span className="text-slate-200 font-mono font-medium">{lastSyncTime || "En vivo"}</span>
            </div>

            <button
              onClick={() => fetchTelemetry(false)}
              disabled={isRefreshing}
              className="p-2.5 rounded-xl bg-white/[0.05] hover:bg-white/[0.1] border border-white/[0.08] text-slate-300 hover:text-white transition-all disabled:opacity-50"
              title="Refrescar métricas de la nube"
            >
              <RefreshCw className={`w-4 h-4 ${isRefreshing ? "animate-spin text-indigo-400" : ""}`} />
            </button>

            <button
              onClick={() => setShowUploadModal(true)}
              className="hidden sm:inline-flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-semibold bg-white/[0.06] hover:bg-white/[0.12] border border-white/[0.1] text-slate-200 hover:text-white transition-all"
            >
              <UploadCloud className="w-4 h-4 text-indigo-400" />
              <span>Cargar Reporte JSON</span>
            </button>
          </div>
        </div>

        {/* Navigation Tabs */}
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex gap-1 border-t border-white/[0.04]">
          <button
            onClick={() => setActiveTab("general")}
            className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-all ${
              activeTab === "general"
                ? "border-indigo-500 text-indigo-400 bg-indigo-500/[0.04]"
                : "border-transparent text-slate-400 hover:text-slate-200 hover:border-slate-700"
            }`}
          >
            <BarChart3 className="w-4 h-4" />
            <span>Visión Ejecutiva</span>
          </button>

          <button
            onClick={() => setActiveTab("respuestas")}
            className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-all ${
              activeTab === "respuestas"
                ? "border-emerald-500 text-emerald-400 bg-emerald-500/[0.04]"
                : "border-transparent text-slate-400 hover:text-slate-200 hover:border-slate-700"
            }`}
          >
            <CheckCircle2 className="w-4 h-4" />
            <span>Respuestas & Prospectos</span>
            <span className="ml-1 px-1.5 py-0.2 rounded-full text-[10px] bg-emerald-500/20 text-emerald-300 font-bold">
              {conteoRespuestas.positivos}
            </span>
          </button>

          <button
            onClick={() => setActiveTab("flujo")}
            className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-all ${
              activeTab === "flujo"
                ? "border-blue-500 text-blue-400 bg-blue-500/[0.04]"
                : "border-transparent text-slate-400 hover:text-slate-200 hover:border-slate-700"
            }`}
          >
            <Layers className="w-4 h-4" />
            <span>Flujo de Datos & Arquitectura</span>
          </button>

          <button
            onClick={() => setActiveTab("empresas")}
            className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-all ${
              activeTab === "empresas"
                ? "border-amber-500 text-amber-400 bg-amber-500/[0.04]"
                : "border-transparent text-slate-400 hover:text-slate-200 hover:border-slate-700"
            }`}
          >
            <Building2 className="w-4 h-4" />
            <span>Bases Depuradas</span>
          </button>

          <button
            onClick={() => setActiveTab("actualizaciones")}
            className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-all ${
              activeTab === "actualizaciones"
                ? "border-purple-500 text-purple-400 bg-purple-500/[0.04]"
                : "border-transparent text-slate-400 hover:text-slate-200 hover:border-slate-700"
            }`}
          >
            <Rocket className="w-4 h-4" />
            <span>Lanzar Actualizaciones</span>
            <span className="ml-1 px-1.5 py-0.5 rounded-full text-[10px] bg-purple-500/20 text-purple-300 font-bold font-mono">
              v{releaseData?.version || "2.1.0"}
            </span>
          </button>
        </div>
      </header>

      {/* ── MAIN CONTENT AREA ─────────────────────────────────────── */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* ════ TAB 1: VISIÓN EJECUTIVA ════ */}
        {activeTab === "general" && (
          <div className="space-y-8 animate-fadeIn">
            {/* KPI Cards Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
              {/* Card 1: Total Recopilados */}
              <div className="glass-card p-6 relative overflow-hidden group">
                <div className="absolute top-0 left-0 h-1 w-full bg-gradient-to-r from-blue-500 to-indigo-500"></div>
                <div className="flex items-center justify-between text-slate-400 mb-3">
                  <span className="text-xs font-semibold uppercase tracking-wider">Inventario Bruto Total</span>
                  <div className="p-2 rounded-lg bg-blue-500/10 text-blue-400">
                    <Database className="w-4 h-4" />
                  </div>
                </div>
                <div className="text-3xl font-extrabold text-white font-mono tracking-tight">
                  {kpis.total_recopilados_brutos.toLocaleString("es-EC")}
                </div>
                <div className="mt-3 text-xs text-slate-400 flex items-center justify-between">
                  <span>69 archivos recopilados</span>
                  <span className="text-blue-400 font-semibold">{kpis.total_base_activa.toLocaleString("es-EC")} activos 2026</span>
                </div>
              </div>

              {/* Card 2: Negocios Depurados 100% Funcionales */}
              <div className="glass-card p-6 relative overflow-hidden group border-indigo-500/30">
                <div className="absolute top-0 left-0 h-1 w-full bg-gradient-to-r from-indigo-500 to-emerald-500"></div>
                <div className="flex items-center justify-between text-slate-400 mb-3">
                  <span className="text-xs font-semibold uppercase tracking-wider text-indigo-300">Empresas 100% Funcionales</span>
                  <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400">
                    <ShieldCheck className="w-4 h-4" />
                  </div>
                </div>
                <div className="text-3xl font-extrabold text-emerald-400 font-mono tracking-tight">
                  {kpis.total_negocios_unicos.toLocaleString("es-EC")}
                </div>
                <div className="mt-3 text-xs text-slate-400 flex items-center justify-between">
                  <span className="text-emerald-400 font-semibold">{kpis.supercias_activas_con_ruc.toLocaleString("es-EC")} Supercias RUC</span>
                  <span>{kpis.negocios_corporativos.toLocaleString("es-EC")} corporativos</span>
                </div>
              </div>

              {/* Card 3: Correos Enviados y Entrega */}
              <div className="glass-card p-6 relative overflow-hidden group">
                <div className="absolute top-0 left-0 h-1 w-full bg-gradient-to-r from-emerald-500 to-teal-500"></div>
                <div className="flex items-center justify-between text-slate-400 mb-3">
                  <span className="text-xs font-semibold uppercase tracking-wider">Correos Enviados</span>
                  <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400">
                    <Send className="w-4 h-4" />
                  </div>
                </div>
                <div className="text-3xl font-extrabold text-white font-mono tracking-tight">
                  {kpis.total_enviados_campanas.toLocaleString("es-EC")}
                </div>
                <div className="mt-3 text-xs text-slate-400 flex items-center justify-between">
                  <span className="text-emerald-400 font-semibold flex items-center gap-1">
                    <CheckCircle2 className="w-3.5 h-3.5" /> {kpis.tasa_entrega}% entrega
                  </span>
                  <span className="text-slate-400">{kpis.total_errores_envio} errores evitados</span>
                </div>
              </div>

              {/* Card 4: Respuestas Positivas y Oportunidades */}
              <div className="glass-card p-6 relative overflow-hidden group border-emerald-500/30 bg-gradient-to-br from-[#131b31] to-[#0d2222]">
                <div className="absolute top-0 left-0 h-1 w-full bg-gradient-to-r from-teal-400 to-emerald-400"></div>
                <div className="flex items-center justify-between text-slate-400 mb-3">
                  <span className="text-xs font-semibold uppercase tracking-wider text-emerald-300">Empresas Interesadas (Positivos)</span>
                  <div className="p-2 rounded-lg bg-emerald-500/20 text-emerald-300">
                    <TrendingUp className="w-4 h-4" />
                  </div>
                </div>
                <div className="text-3xl font-extrabold text-white font-mono tracking-tight flex items-baseline gap-2">
                  <span>{conteoRespuestas.positivos}</span>
                  <span className="text-xs text-emerald-400 font-sans font-normal">
                    ({((conteoRespuestas.positivos / (kpis.total_enviados_campanas || 1)) * 100).toFixed(1)}% respuesta)
                  </span>
                </div>
                <div className="mt-3 text-xs text-slate-300 flex items-center justify-between">
                  <span className="font-semibold text-emerald-400">{conteoRespuestas.cotizaciones} cotizaciones pedidas</span>
                  <span className="text-teal-300">{conteoRespuestas.cerrados} contratadas</span>
                </div>
              </div>
            </div>

            {/* ── EMBUDO DE CONVERSIÓN COMERCIAL (FUNNEL) ───────────── */}
            <div className="glass-card p-6">
              <div className="flex items-center justify-between mb-6">
                <div>
                  <h3 className="text-base font-bold text-white flex items-center gap-2">
                    <TrendingUp className="w-5 h-5 text-indigo-400" />
                    Embudo de Depuración y Rendimiento Comercial
                  </h3>
                  <p className="text-xs text-slate-400 mt-1">
                    Visualiza el flujo de filtrado desde la recolección cruda hasta las respuestas de contratación actuarial.
                  </p>
                </div>
                <span className="text-xs px-3 py-1 rounded-lg bg-indigo-500/10 text-indigo-300 border border-indigo-500/20 font-semibold">
                  Eficiencia de Purga: 82.8%
                </span>
              </div>

              {/* Funnel Stages */}
              <div className="space-y-4">
                {/* Etapa 1 */}
                <div>
                  <div className="flex justify-between text-xs font-medium mb-1.5">
                    <span className="text-slate-300">1. Recolección Cruda de Correos (Histórico + Pendrives)</span>
                    <span className="font-mono text-slate-400">247,997 (100%)</span>
                  </div>
                  <div className="h-4 w-full bg-slate-800 rounded-full overflow-hidden">
                    <div className="h-full bg-slate-500 rounded-full" style={{ width: "100%" }}></div>
                  </div>
                </div>

                {/* Etapa 2 */}
                <div>
                  <div className="flex justify-between text-xs font-medium mb-1.5">
                    <span className="text-slate-300">2. Normalización, Sintaxis Limpia y Unicidad</span>
                    <span className="font-mono text-slate-400">136,602 (55.1%)</span>
                  </div>
                  <div className="h-4 w-full bg-slate-800 rounded-full overflow-hidden">
                    <div className="h-full bg-blue-600 rounded-full" style={{ width: "55.1%" }}></div>
                  </div>
                </div>

                {/* Etapa 3 */}
                <div>
                  <div className="flex justify-between text-xs font-medium mb-1.5">
                    <span className="text-indigo-300 font-semibold">3. Empresas Activas en Supercias y Dominios Corporativos (100% Funcionales)</span>
                    <span className="font-mono text-emerald-400 font-bold">42,648 (17.2%)</span>
                  </div>
                  <div className="h-4 w-full bg-slate-800 rounded-full overflow-hidden">
                    <div className="h-full bg-indigo-500 rounded-full" style={{ width: "17.2%" }}></div>
                  </div>
                </div>

                {/* Etapa 4 */}
                <div>
                  <div className="flex justify-between text-xs font-medium mb-1.5">
                    <span className="text-slate-300">4. Contactadas en Campañas de Email B2B (NIC 19 / Jubilación)</span>
                    <span className="font-mono text-slate-400">9,116 (21.4% de base funcional)</span>
                  </div>
                  <div className="h-4 w-full bg-slate-800 rounded-full overflow-hidden">
                    <div className="h-full bg-teal-500 rounded-full" style={{ width: "9.1%" }}></div>
                  </div>
                </div>

                {/* Etapa 5 */}
                <div>
                  <div className="flex justify-between text-xs font-medium mb-1.5">
                    <span className="text-emerald-400 font-semibold">5. Respuestas Comerciales Positivas y Solicitudes de Cotización</span>
                    <span className="font-mono text-emerald-400 font-bold">{conteoRespuestas.positivos} empresas interesadas</span>
                  </div>
                  <div className="h-4 w-full bg-slate-800 rounded-full overflow-hidden">
                    <div className="h-full bg-emerald-400 rounded-full" style={{ width: "3.8%" }}></div>
                  </div>
                </div>
              </div>
            </div>

            {/* ── 2 COLUMNAS: PROVINCIAS Y DOMINIOS ──────────────────── */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Provincias */}
              <div className="glass-card p-6">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-sm font-bold text-white flex items-center gap-2">
                    <MapPin className="w-4 h-4 text-rose-400" />
                    Empresas Supercias por Provincia (Ecuador)
                  </h3>
                  <span className="text-xs text-slate-400 font-mono">11,779 con RUC</span>
                </div>

                <div className="space-y-3 mt-4">
                  {Object.entries(data.distribucion_provincias).map(([prov, cant]) => {
                    const max = 11236;
                    const pct = Math.max(3, Math.round((cant / max) * 100));
                    return (
                      <div key={prov}>
                        <div className="flex justify-between text-xs font-medium mb-1">
                          <span className="text-slate-300">{prov}</span>
                          <span className="font-mono text-slate-400">{cant.toLocaleString("es-EC")}</span>
                        </div>
                        <div className="h-2 w-full bg-white/[0.05] rounded-full overflow-hidden">
                          <div
                            className="h-full bg-gradient-to-r from-indigo-500 to-blue-500 rounded-full"
                            style={{ width: `${pct}%` }}
                          ></div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Dominios Corporativos Top */}
              <div className="glass-card p-6">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-sm font-bold text-white flex items-center gap-2">
                    <Building2 className="w-4 h-4 text-indigo-400" />
                    Top Dominios y Proveedores de Empresas
                  </h3>
                  <span className="text-xs text-slate-400">Redes corporativas EC</span>
                </div>

                <div className="grid grid-cols-2 gap-3 mt-2">
                  {Object.entries(data.top_dominios).slice(0, 10).map(([dom, cant]) => (
                    <div key={dom} className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.05] flex justify-between items-center">
                      <span className="text-xs font-mono text-slate-300 truncate max-w-[130px]" title={dom}>
                        {dom}
                      </span>
                      <span className="text-xs font-bold text-indigo-400 font-mono">
                        {cant.toLocaleString("es-EC")}
                      </span>
                    </div>
                  ))}
                </div>

                <div className="mt-5 p-3.5 rounded-xl bg-amber-500/10 border border-amber-500/20 text-xs text-amber-200/90 flex items-start gap-2.5">
                  <ShieldCheck className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                  <span>
                    <strong>Protección de Reputación:</strong> Se eliminaron 3,496 empresas con estado "Disolución" o "Inactiva" en la Superintendencia de Compañías para evitar bloqueos del servidor SMTP.
                  </span>
                </div>
              </div>
            </div>

            {/* ── HISTORIAL DE CAMPAÑAS ──────────────────────────────── */}
            <div className="glass-card p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-sm font-bold text-white flex items-center gap-2">
                  <Send className="w-4 h-4 text-emerald-400" />
                  Campañas Recientes de Envío a Empresas
                </h3>
                <span className="text-xs text-slate-400">Registrado por MxCorreo</span>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="text-slate-400 border-b border-white/[0.08] font-semibold">
                    <tr>
                      <th className="pb-3">Campaña / Asunto</th>
                      <th className="pb-3">Fecha</th>
                      <th className="pb-3 text-center">Total Lote</th>
                      <th className="pb-3 text-center">Enviados OK</th>
                      <th className="pb-3 text-center">Errores</th>
                      <th className="pb-3 text-right">Efectividad</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/[0.04] text-slate-300">
                    {data.campanas.map((c) => {
                      const eff = c.total > 0 ? (((c.enviados) / c.total) * 100).toFixed(1) : "100";
                      return (
                        <tr key={c.id} className="hover:bg-white/[0.02]">
                          <td className="py-3.5">
                            <div className="font-semibold text-white">{c.nombre}</div>
                            <div className="text-[11px] text-slate-400 truncate max-w-md">{c.asunto}</div>
                          </td>
                          <td className="py-3.5 font-mono text-slate-400">{c.fecha}</td>
                          <td className="py-3.5 text-center font-mono font-semibold">{c.total.toLocaleString("es-EC")}</td>
                          <td className="py-3.5 text-center font-mono text-emerald-400 font-semibold">{c.enviados.toLocaleString("es-EC")}</td>
                          <td className="py-3.5 text-center font-mono text-rose-400">{c.errores}</td>
                          <td className="py-3.5 text-right font-mono font-bold text-emerald-400">{eff}%</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* ════ TAB 2: RESPUESTAS & PROSPECTOS (CRM COMERCIAL) ════ */}
        {activeTab === "respuestas" && (
          <div className="space-y-6 animate-fadeIn">
            {/* Header del CRM */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 glass-card p-6">
              <div>
                <h2 className="text-lg font-bold text-white flex items-center gap-2">
                  <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                  Control de Respuestas y Oportunidades Comerciales
                </h2>
                <p className="text-xs text-slate-400 mt-1">
                  Monitorea cuántas empresas responden a las propuestas y clasifica los prospectos que avanzan a cotización de estudios actuariales.
                </p>
              </div>

              <div className="flex items-center gap-3">
                <button
                  onClick={exportarLeadsCSV}
                  className="px-4 py-2.5 rounded-xl bg-white/[0.06] hover:bg-white/[0.1] border border-white/[0.1] text-xs font-semibold text-slate-200 hover:text-white transition-all flex items-center gap-2"
                >
                  <Download className="w-4 h-4 text-indigo-400" />
                  <span>Exportar CSV</span>
                </button>
                <button
                  onClick={() => setShowAddLeadModal(true)}
                  className="px-4 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-xs font-bold text-white transition-all shadow-lg shadow-emerald-600/30 flex items-center gap-2"
                >
                  <Plus className="w-4 h-4" />
                  <span>Registrar Respuesta de Empresa</span>
                </button>
              </div>
            </div>

            {/* Metricas rápidas de respuestas */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              <div className="glass-card p-4 text-center">
                <span className="text-xs text-slate-400">Total Contactadas</span>
                <div className="text-2xl font-extrabold text-white font-mono mt-1">{kpis.total_enviados_campanas.toLocaleString("es-EC")}</div>
              </div>
              <div className="glass-card p-4 text-center border-emerald-500/20">
                <span className="text-xs text-emerald-400">Respuestas Positivas</span>
                <div className="text-2xl font-extrabold text-emerald-400 font-mono mt-1">{conteoRespuestas.positivos}</div>
              </div>
              <div className="glass-card p-4 text-center border-indigo-500/20">
                <span className="text-xs text-indigo-400">Cotizaciones Solicitadas</span>
                <div className="text-2xl font-extrabold text-indigo-400 font-mono mt-1">{conteoRespuestas.cotizaciones}</div>
              </div>
              <div className="glass-card p-4 text-center border-teal-500/20">
                <span className="text-xs text-teal-300">Contratos Cerrados</span>
                <div className="text-2xl font-extrabold text-teal-300 font-mono mt-1">{conteoRespuestas.cerrados}</div>
              </div>
            </div>

            {/* Filtros y Buscador */}
            <div className="glass-card p-4 flex flex-col sm:flex-row gap-4 justify-between items-center">
              <div className="relative w-full sm:w-80">
                <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  placeholder="Buscar empresa, correo o RUC…"
                  value={busquedaLead}
                  onChange={(e) => setBusquedaLead(e.target.value)}
                  className="w-full pl-9 pr-4 py-2 bg-white/[0.04] border border-white/[0.08] rounded-xl text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="flex items-center gap-2 overflow-x-auto w-full sm:w-auto">
                {["Todos", "Positivo / Interesado", "Cotización Solicitada", "En Negociación", "Cerrado / Cliente", "No Interesado"].map((st) => (
                  <button
                    key={st}
                    onClick={() => setFiltroEstado(st)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition-all ${
                      filtroEstado === st
                        ? "bg-indigo-600 text-white shadow-md shadow-indigo-600/30"
                        : "bg-white/[0.04] text-slate-400 hover:text-white"
                    }`}
                  >
                    {st}
                  </button>
                ))}
              </div>
            </div>

            {/* Tabla de Leads / Empresas */}
            <div className="glass-card overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-white/[0.03] text-slate-400 border-b border-white/[0.08] font-semibold">
                    <tr>
                      <th className="py-3.5 px-4">Empresa / RUC</th>
                      <th className="py-3.5 px-4">Correo Electrónico</th>
                      <th className="py-3.5 px-4">Servicio de Interés</th>
                      <th className="py-3.5 px-4">Estado Actual</th>
                      <th className="py-3.5 px-4">Notas de la Respuesta</th>
                      <th className="py-3.5 px-4 text-right">Acción Rápida</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/[0.04] text-slate-300">
                    {leadsFiltrados.map((l) => (
                      <tr key={l.id} className="hover:bg-white/[0.02] transition-colors">
                        <td className="py-3.5 px-4">
                          <div className="font-bold text-white">{l.empresa}</div>
                          <div className="text-[11px] font-mono text-slate-400">
                            {l.ruc ? `RUC: ${l.ruc}` : "Sin RUC"} • {l.provincia || "EC"}
                          </div>
                        </td>
                        <td className="py-3.5 px-4 font-mono text-indigo-300">{l.correo}</td>
                        <td className="py-3.5 px-4 text-slate-300">{l.servicio_interes}</td>
                        <td className="py-3.5 px-4">
                          <span
                            className={`inline-flex px-2.5 py-1 rounded-full text-[11px] font-semibold ${
                              l.estado === "Cerrado / Cliente"
                                ? "bg-teal-500/20 text-teal-300 border border-teal-500/30"
                                : l.estado === "Cotización Solicitada"
                                ? "bg-indigo-500/20 text-indigo-300 border border-indigo-500/30"
                                : l.estado === "En Negociación"
                                ? "bg-amber-500/20 text-amber-300 border border-amber-500/30"
                                : l.estado === "No Interesado"
                                ? "bg-rose-500/20 text-rose-300 border border-rose-500/30"
                                : "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30"
                            }`}
                          >
                            {l.estado}
                          </span>
                        </td>
                        <td className="py-3.5 px-4 text-slate-400 max-w-xs truncate" title={l.notas}>
                          {l.notas || "—"}
                        </td>
                        <td className="py-3.5 px-4 text-right">
                          <select
                            value={l.estado}
                            onChange={(e) => handleUpdateStatus(l.id, e.target.value as LeadRespuesta["estado"])}
                            className="bg-white/[0.06] border border-white/[0.1] text-[11px] text-slate-200 rounded-lg px-2 py-1 focus:outline-none"
                          >
                            <option value="Positivo / Interesado">Positivo / Interesado</option>
                            <option value="Cotización Solicitada">Cotización Solicitada</option>
                            <option value="En Negociación">En Negociación</option>
                            <option value="Cerrado / Cliente">Cerrado / Cliente</option>
                            <option value="No Interesado">No Interesado</option>
                          </select>
                        </td>
                      </tr>
                    ))}
                    {leadsFiltrados.length === 0 && (
                      <tr>
                        <td colSpan={6} className="py-8 text-center text-slate-500">
                          No se encontraron empresas con el filtro seleccionado.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* ════ TAB 3: FLUJO DE DATOS & ARQUITECTURA ════ */}
        {activeTab === "flujo" && (
          <div className="space-y-6 animate-fadeIn">
            {/* Header del Flujo */}
            <div className="glass-card p-6">
              <h2 className="text-lg font-bold text-white flex items-center gap-2">
                <Layers className="w-5 h-5 text-blue-400" />
                Arquitectura de Transmisión y Flujo de Datos
              </h2>
              <p className="text-xs text-slate-400 mt-1">
                Cómo viajan los datos desde tus herramientas de depuración locales hacia la nube en Vercel para que el jefe supervise en tiempo real.
              </p>

              {/* Diagrama Visual */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mt-8 relative">
                {/* Paso 1 */}
                <div className="glass-card p-5 border-blue-500/30 relative">
                  <div className="w-8 h-8 rounded-full bg-blue-500/20 text-blue-400 flex items-center justify-center font-bold text-xs mb-3">
                    1
                  </div>
                  <h4 className="text-xs font-bold text-white uppercase tracking-wider">Depuración Local</h4>
                  <p className="text-xs text-slate-400 mt-1.5">
                    <code>depurar_correos_supercias.py</code> cruza 136k correos con las bases de la Superintendencia de Compañías.
                  </p>
                  <div className="mt-3 text-[11px] font-mono text-emerald-400 bg-emerald-500/10 px-2 py-1 rounded">
                    42,648 empresas activas
                  </div>
                </div>

                {/* Paso 2 */}
                <div className="glass-card p-5 border-indigo-500/30 relative">
                  <div className="w-8 h-8 rounded-full bg-indigo-500/20 text-indigo-400 flex items-center justify-center font-bold text-xs mb-3">
                    2
                  </div>
                  <h4 className="text-xs font-bold text-white uppercase tracking-wider">MxCorreo Desktop</h4>
                  <p className="text-xs text-slate-400 mt-1.5">
                    Lanza campañas B2B con pausas anti-spam y genera bitácora de correos enviados, fallidos y respuestas.
                  </p>
                  <div className="mt-3 text-[11px] font-mono text-indigo-300 bg-indigo-500/10 px-2 py-1 rounded">
                    sync_telemetria.py
                  </div>
                </div>

                {/* Paso 3 */}
                <div className="glass-card p-5 border-teal-500/30 relative">
                  <div className="w-8 h-8 rounded-full bg-teal-500/20 text-teal-400 flex items-center justify-center font-bold text-xs mb-3">
                    3
                  </div>
                  <h4 className="text-xs font-bold text-white uppercase tracking-wider">Endpoint Vercel</h4>
                  <p className="text-xs text-slate-400 mt-1.5">
                    Ruta Serverless <code>/api/sync</code> autenticada con clave Bearer que recibe y unifica la telemetría.
                  </p>
                  <div className="mt-3 text-[11px] font-mono text-teal-300 bg-teal-500/10 px-2 py-1 rounded">
                    HTTPS / JSON-RPC
                  </div>
                </div>

                {/* Paso 4 */}
                <div className="glass-card p-5 border-emerald-500/30 relative">
                  <div className="w-8 h-8 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center font-bold text-xs mb-3">
                    4
                  </div>
                  <h4 className="text-xs font-bold text-white uppercase tracking-wider">Panel Gerencial</h4>
                  <p className="text-xs text-slate-400 mt-1.5">
                    El jefe abre el enlace de Vercel y consulta los indicadores clave de negocio sin tocar código ni terminales.
                  </p>
                  <div className="mt-3 text-[11px] font-mono text-emerald-400 bg-emerald-500/10 px-2 py-1 rounded">
                    Dashboard 24/7
                  </div>
                </div>
              </div>
            </div>

            {/* Código de Sincronización para el Operador */}
            <div className="glass-card p-6">
              <h3 className="text-sm font-bold text-white mb-2">Comando para Sincronizar desde tu Computadora</h3>
              <p className="text-xs text-slate-400 mb-4">
                Puedes ejecutar este comando en la carpeta <code>Mx/</code> en cualquier momento para actualizar los números del jefe:
              </p>

              <div className="p-4 rounded-xl bg-black/50 border border-white/[0.08] font-mono text-xs text-emerald-400 flex items-center justify-between">
                <span>python sync_telemetria.py --url https://tu-panel.vercel.app/api/sync</span>
                <button
                  onClick={() => {
                    navigator.clipboard.writeText("python sync_telemetria.py");
                    showToast("Comando copiado al portapapeles.", "ok");
                  }}
                  className="px-3 py-1 rounded-lg bg-white/[0.1] hover:bg-white/[0.2] text-white text-[11px]"
                >
                  Copiar
                </button>
              </div>
            </div>
          </div>
        )}

        {/* ════ TAB 4: BASES DEPURADAS (EXPLORADOR) ════ */}
        {activeTab === "empresas" && (
          <div className="space-y-6 animate-fadeIn">
            <div className="glass-card p-6">
              <h2 className="text-lg font-bold text-white flex items-center gap-2">
                <Building2 className="w-5 h-5 text-amber-400" />
                Desglose Estructurado de las Bases Depuradas
              </h2>
              <p className="text-xs text-slate-400 mt-1">
                Estructura exacta de archivos generados en <code>Mx/resultados/depuracion_supercias_2026/</code> y organizados en Google Drive.
              </p>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-6">
                <div className="p-4 rounded-xl bg-white/[0.03] border border-emerald-500/30">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-white text-sm">1. Supercias Activas con RUC</span>
                    <span className="font-mono text-emerald-400 font-bold text-sm">11,779</span>
                  </div>
                  <p className="text-xs text-slate-400 mt-2">
                    Empresas con razón social, RUC y estado legal activo validado ante la Superintendencia de Compañías. Ideales para auditorías y estudios de jubilación patronal NIC 19.
                  </p>
                </div>

                <div className="p-4 rounded-xl bg-white/[0.03] border border-indigo-500/30">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-white text-sm">2. Negocios Corporativos Activos</span>
                    <span className="font-mono text-indigo-400 font-bold text-sm">30,869</span>
                  </div>
                  <p className="text-xs text-slate-400 mt-2">
                    Correos alojados en dominios empresariales propios y redes de telecomunicaciones (Satnet, Andinanet, Telconet, etc.) con servidores MX operativos.
                  </p>
                </div>

                <div className="p-4 rounded-xl bg-white/[0.03] border border-rose-500/30">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-white text-sm">3. Descartados (Disolución / Inactivas)</span>
                    <span className="font-mono text-rose-400 font-bold text-sm">3,496</span>
                  </div>
                  <p className="text-xs text-slate-400 mt-2">
                    Sociedades en liquidación, cancelación o disolución según catastro oficial. Se apartaron en carpeta de descarte para evitar rebotar correos.
                  </p>
                </div>

                <div className="p-4 rounded-xl bg-white/[0.03] border border-blue-500/30">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-white text-sm">4. Instituciones Educativas y Colegios</span>
                    <span className="font-mono text-blue-400 font-bold text-sm">4,809</span>
                  </div>
                  <p className="text-xs text-slate-400 mt-2">
                    Unidades educativas fiscales y particulares clasificadas por separado para propuestas especiales de docencia o exención actuarial.
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ════ TAB 5: LANZAR ACTUALIZACIONES ════ */}
        {activeTab === "actualizaciones" && (
          <div className="space-y-6 animate-fadeIn">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="text-xl font-bold text-white flex items-center gap-2">
                    <Rocket className="w-5 h-5 text-purple-400" />
                    Centro de Lanzamiento de Actualizaciones
                  </h2>
                  <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-purple-500/20 text-purple-300 border border-purple-500/30">
                    Versión Activa: v{releaseData?.version || "2.1.0"}
                  </span>
                </div>
                <p className="text-xs text-slate-400 mt-1">
                  Gestiona y publica las versiones oficiales de la aplicación de escritorio MxCorreo. Los clientes conectados detectarán inmediatamente si están desactualizados.
                </p>
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={fetchUpdates}
                  className="px-3 py-2 rounded-xl bg-white/[0.05] hover:bg-white/[0.1] border border-white/[0.08] text-xs font-semibold text-slate-300 hover:text-white transition-all flex items-center gap-2"
                >
                  <RefreshCw className="w-3.5 h-3.5 text-purple-400" />
                  <span>Comprobar Estado</span>
                </button>
              </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
              {/* Columna Izquierda: Formulario de Lanzamiento */}
              <div className="lg:col-span-7 glass-card p-6">
                <h3 className="text-sm font-bold text-white mb-1 flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-amber-400" />
                  Publicar Nueva Versión a Usuarios
                </h3>
                <p className="text-xs text-slate-400 mb-5">
                  Al pulsar publicar, cualquier usuario que abra la app con una versión inferior recibirá el aviso de <strong>"Desactualizada"</strong> y podrá auto-instalarla.
                </p>

                <form onSubmit={handlePublishUpdate} className="space-y-4 text-xs">
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-slate-300 font-semibold mb-1">
                        Número de Versión (SemVer) *
                      </label>
                      <input
                        type="text"
                        required
                        value={targetVersion}
                        onChange={(e) => setTargetVersion(e.target.value)}
                        placeholder="Ej: 2.1.0 o 2.2.0"
                        className="w-full px-3.5 py-2.5 rounded-xl bg-black/40 border border-white/10 text-white font-mono placeholder:text-slate-500 focus:outline-none focus:border-purple-500 transition-all"
                      />
                    </div>

                    <div>
                      <label className="block text-slate-300 font-semibold mb-1">
                        Canal de Distribución
                      </label>
                      <select
                        disabled
                        className="w-full px-3.5 py-2.5 rounded-xl bg-black/40 border border-white/10 text-slate-300 focus:outline-none"
                      >
                        <option>Producción Oficial (Stable)</option>
                      </select>
                    </div>
                  </div>

                  <div>
                    <label className="block text-slate-300 font-semibold mb-1">
                      Título Descriptivo del Parche *
                    </label>
                    <input
                      type="text"
                      required
                      value={targetTitle}
                      onChange={(e) => setTargetTitle(e.target.value)}
                      placeholder="Ej: Actualización v2.1.0 — Motor Masivo & Telemetría"
                      className="w-full px-3.5 py-2.5 rounded-xl bg-black/40 border border-white/10 text-white placeholder:text-slate-500 focus:outline-none focus:border-purple-500 transition-all"
                    />
                  </div>

                  <div>
                    <label className="block text-slate-300 font-semibold mb-1">
                      Notas de la Versión (Changelog) *
                    </label>
                    <textarea
                      rows={4}
                      required
                      value={targetChangelog}
                      onChange={(e) => setTargetChangelog(e.target.value)}
                      placeholder="Escribe cada novedad en una línea separada..."
                      className="w-full px-3.5 py-2.5 rounded-xl bg-black/40 border border-white/10 text-white placeholder:text-slate-500 focus:outline-none focus:border-purple-500 transition-all font-mono text-xs leading-relaxed"
                    />
                    <span className="text-[11px] text-slate-500 mt-1 block">
                      Estas notas aparecerán directamente dentro de la ventana de actualización en la pantalla del usuario.
                    </span>
                  </div>

                  <div className="flex items-center gap-3 p-3 rounded-xl bg-purple-500/10 border border-purple-500/20">
                    <input
                      type="checkbox"
                      id="chk-mandatory"
                      checked={isMandatory}
                      onChange={(e) => setIsMandatory(e.target.checked)}
                      className="w-4 h-4 rounded text-purple-600 focus:ring-purple-500 border-white/20 bg-black/40"
                    />
                    <label htmlFor="chk-mandatory" className="text-xs text-slate-300 cursor-pointer">
                      <span className="font-semibold text-purple-300">Actualización Obligatoria:</span> Exigir al usuario actualizar antes de permitir envíos masivos.
                    </label>
                  </div>

                  <div className="pt-2">
                    <button
                      type="submit"
                      disabled={isPublishing}
                      className="w-full py-3 rounded-xl bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white font-bold shadow-lg shadow-purple-500/25 flex items-center justify-center gap-2 transition-all disabled:opacity-50 text-sm"
                    >
                      <Rocket className={`w-4 h-4 ${isPublishing ? "animate-bounce" : ""}`} />
                      <span>{isPublishing ? "Lanzando Versión a Servidores…" : `🚀 Publicar Versión v${targetVersion} a Clientes`}</span>
                    </button>
                  </div>
                </form>
              </div>

              {/* Columna Derecha: Estado Actual y Diagnóstico */}
              <div className="lg:col-span-5 space-y-5">
                {/* Tarjeta de Versión Vigente */}
                <div className="glass-card p-6 border-purple-500/30">
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-xs font-bold uppercase tracking-wider text-slate-400">
                      Versión Transmitida en Vivo
                    </span>
                    <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                      <span className="live-pulse"></span>
                      En Producción
                    </span>
                  </div>

                  <div className="flex items-baseline gap-2 mb-2">
                    <span className="text-3xl font-extrabold text-white font-mono">
                      v{releaseData?.version || "2.1.0"}
                    </span>
                    <span className="text-xs text-slate-400">
                      (Publicada: {releaseData?.release_date || "2026-09-21"})
                    </span>
                  </div>

                  <div className="text-xs font-semibold text-purple-300 mb-3">
                    {releaseData?.title}
                  </div>

                  <div className="p-3 rounded-xl bg-black/40 border border-white/5 space-y-1.5 mb-4">
                    <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block mb-1">
                      Novedades incluidas en el paquete:
                    </span>
                    {(releaseData?.changelog || []).map((item, idx) => (
                      <div key={idx} className="flex items-start gap-2 text-xs text-slate-300">
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0 mt-0.5" />
                        <span>{item}</span>
                      </div>
                    ))}
                  </div>

                  <div className="grid grid-cols-2 gap-3 text-xs">
                    <div className="p-2.5 rounded-lg bg-white/[0.03] border border-white/5">
                      <span className="text-slate-400 block text-[10px]">Paquete Incremental</span>
                      <span className="text-slate-200 font-mono font-medium">{releaseData?.package_size || "3.8 MB"}</span>
                    </div>
                    <div className="p-2.5 rounded-lg bg-white/[0.03] border border-white/5">
                      <span className="text-slate-400 block text-[10px]">Tipo de Parche</span>
                      <span className="text-emerald-400 font-medium">Reinicio Autónomo</span>
                    </div>
                  </div>
                </div>

                {/* Tarjeta de Instrucción Técnica */}
                <div className="glass-card p-5 border-blue-500/20">
                  <h4 className="text-xs font-bold text-blue-300 mb-2 flex items-center gap-1.5">
                    <Layers className="w-4 h-4" />
                    ¿Cómo Funciona para el Usuario?
                  </h4>
                  <ol className="text-xs text-slate-300 space-y-2 list-decimal list-inside leading-relaxed">
                    <li>
                      El usuario abre <strong>MxCorreo</strong> (versión v2.0.0).
                    </li>
                    <li>
                      La app consulta automáticamente la API de Vercel (<code>/api/updates</code>).
                    </li>
                    <li>
                      Al detectar <strong>v2.1.0 &gt; v2.0.0</strong>, aparece la pantalla animada de <strong>"Aplicación Desactualizada"</strong>.
                    </li>
                    <li>
                      Al dar clic en <strong>"Actualizar Ahora"</strong>, la app ejecuta la animación con barra de brillo, descarga e instala los parches en segundo plano.
                    </li>
                    <li>
                      Muestra <strong>"¡Actualizada con Éxito!"</strong> y se reinicia sola en 3 segundos.
                    </li>
                  </ol>
                </div>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* ── MODAL: REGISTRAR RESPUESTA DE EMPRESA ─────────────────── */}
      {showAddLeadModal && (
        <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="glass-card max-w-lg w-full p-6 border-indigo-500/40 relative">
            <h3 className="text-lg font-bold text-white mb-1 flex items-center gap-2">
              <CheckCircle2 className="w-5 h-5 text-emerald-400" />
              Registrar Respuesta de Empresa
            </h3>
            <p className="text-xs text-slate-400 mb-5">
              Anota la empresa que respondió a la propuesta para sumarla al embudo del jefe.
            </p>

            <form onSubmit={handleCreateLead} className="space-y-4 text-xs">
              <div>
                <label className="block text-slate-300 font-semibold mb-1">Nombre de la Empresa / Razón Social *</label>
                <input
                  type="text"
                  required
                  placeholder="Ej: PESQUERA INDUSTRIAL DEL PACÍFICO S.A."
                  value={newEmpresa}
                  onChange={(e) => setNewEmpresa(e.target.value)}
                  className="w-full p-2.5 rounded-xl bg-white/[0.05] border border-white/[0.1] text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-300 font-semibold mb-1">Correo de Contacto *</label>
                  <input
                    type="email"
                    required
                    placeholder="gerencia@pesquera.com.ec"
                    value={newCorreo}
                    onChange={(e) => setNewCorreo(e.target.value)}
                    className="w-full p-2.5 rounded-xl bg-white/[0.05] border border-white/[0.1] text-white focus:outline-none focus:border-indigo-500"
                  />
                </div>
                <div>
                  <label className="block text-slate-300 font-semibold mb-1">RUC (opcional)</label>
                  <input
                    type="text"
                    placeholder="0992384912001"
                    value={newRuc}
                    onChange={(e) => setNewRuc(e.target.value)}
                    className="w-full p-2.5 rounded-xl bg-white/[0.05] border border-white/[0.1] text-white focus:outline-none focus:border-indigo-500"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-300 font-semibold mb-1">Estado de Respuesta</label>
                  <select
                    value={newEstado}
                    onChange={(e) => setNewEstado(e.target.value as LeadRespuesta["estado"])}
                    className="w-full p-2.5 rounded-xl bg-white/[0.05] border border-white/[0.1] text-white focus:outline-none"
                  >
                    <option value="Positivo / Interesado">Positivo / Interesado</option>
                    <option value="Cotización Solicitada">Cotización Solicitada</option>
                    <option value="En Negociación">En Negociación</option>
                    <option value="Cerrado / Cliente">Cerrado / Cliente</option>
                    <option value="No Interesado">No Interesado</option>
                  </select>
                </div>
                <div>
                  <label className="block text-slate-300 font-semibold mb-1">Servicio de Interés</label>
                  <select
                    value={newServicio}
                    onChange={(e) => setNewServicio(e.target.value as LeadRespuesta["servicio_interes"])}
                    className="w-full p-2.5 rounded-xl bg-white/[0.05] border border-white/[0.1] text-white focus:outline-none"
                  >
                    <option value="Jubilación Patronal / NIC 19">Jubilación Patronal / NIC 19</option>
                    <option value="Desahucio y Pasivos Laborales">Desahucio y Pasivos Laborales</option>
                    <option value="Estudio Actuarial Completo">Estudio Actuarial Completo</option>
                    <option value="Consultoría Financiera">Consultoría Financiera</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1">Notas / Detalle de la Conversación</label>
                <textarea
                  rows={3}
                  placeholder="Detalles de la llamada o lo que respondieron en el correo…"
                  value={newNotas}
                  onChange={(e) => setNewNotas(e.target.value)}
                  className="w-full p-2.5 rounded-xl bg-white/[0.05] border border-white/[0.1] text-white focus:outline-none focus:border-indigo-500"
                ></textarea>
              </div>

              <div className="flex justify-end gap-3 pt-3 border-t border-white/[0.08]">
                <button
                  type="button"
                  onClick={() => setShowAddLeadModal(false)}
                  className="px-4 py-2 rounded-xl bg-white/[0.05] hover:bg-white/[0.1] text-slate-300"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 font-bold text-white shadow-lg shadow-emerald-600/30"
                >
                  Guardar Respuesta
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── MODAL: CARGAR REPORTE JSON ───────────────────────────── */}
      {showUploadModal && (
        <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="glass-card max-w-md w-full p-6 border-white/[0.1] relative">
            <h3 className="text-base font-bold text-white mb-1 flex items-center gap-2">
              <UploadCloud className="w-5 h-5 text-indigo-400" />
              Cargar Reporte JSON al Panel
            </h3>
            <p className="text-xs text-slate-400 mb-4">
              Arrastra el archivo <code>Resumen_Depuracion_Supercias.json</code> generado en tu computadora para actualizar el panel de inmediato.
            </p>

            <div
              onDragOver={(e) => e.preventDefault()}
              onDrop={(e) => {
                e.preventDefault();
                const file = e.dataTransfer.files[0];
                if (file) handleFileUpload(file);
              }}
              className="border-2 border-dashed border-white/[0.15] hover:border-indigo-500 rounded-2xl p-8 text-center bg-white/[0.02] cursor-pointer transition-colors"
              onClick={() => {
                const input = document.createElement("input");
                input.type = "file";
                input.accept = ".json";
                input.onchange = (e) => {
                  const target = e.target as HTMLInputElement;
                  if (target.files && target.files[0]) {
                    handleFileUpload(target.files[0]);
                  }
                };
                input.click();
              }}
            >
              <FileSpreadsheet className="w-8 h-8 text-indigo-400 mx-auto mb-2" />
              <span className="text-xs text-slate-300 font-semibold block">
                Haz clic o arrastra un archivo .json aquí
              </span>
              <span className="text-[11px] text-slate-500 block mt-1">
                Resumen_Depuracion_Supercias.json
              </span>
            </div>

            {uploadStatus && (
              <p className="text-xs font-semibold text-center text-indigo-300 mt-3">{uploadStatus}</p>
            )}

            <div className="flex justify-end mt-5 pt-3 border-t border-white/[0.08]">
              <button
                type="button"
                onClick={() => {
                  setShowUploadModal(false);
                  setUploadStatus("");
                }}
                className="px-4 py-2 rounded-xl bg-white/[0.05] hover:bg-white/[0.1] text-xs text-slate-300"
              >
                Cerrar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
