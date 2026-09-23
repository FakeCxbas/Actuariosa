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
import { getSupabaseBrowserClient } from "@/lib/supabase";

export default function DashboardGerencial() {
  const [data, setData] = useState<TelemetriaActuariosa>(initialTelemetryData);
  const [activeTab, setActiveTab] = useState<"general" | "flujo" | "respuestas" | "empresas" | "actualizaciones">("general");
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [lastSyncTime, setLastSyncTime] = useState<string>("");
  const [isRealtimeActive, setIsRealtimeActive] = useState<boolean>(false);

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
  const [toastMsg, setToastMsg] = useState<{ text: string; type: "ok" | "err" } | null>(null);

  const showToast = (text: string, type: "ok" | "err" = "ok") => {
    setToastMsg({ text, type });
    setTimeout(() => setToastMsg(null), 3500);
  };

  // Cargar datos del servidor
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
        if (!silent) showToast("Panel sincronizado con la nube.", "ok");
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
        showToast(`Versión v${targetVersion} publicada en producción.`, "ok");
      } else {
        throw new Error(json.error || "Error al publicar");
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      showToast(msg, "err");
    } finally {
      setIsPublishing(false);
    }
  };

  useEffect(() => {
    fetchTelemetry(true);
    fetchUpdates();

    const supabase = getSupabaseBrowserClient();
    let channel: ReturnType<NonNullable<typeof supabase>["channel"]> | null = null;

    if (supabase) {
      channel = supabase
        .channel("panel-web-realtime")
        .on(
          "postgres_changes",
          { event: "*", schema: "public", table: "actuariosa_telemetria" },
          (payload) => {
            if (payload.new && (payload.new as { data?: TelemetriaActuariosa }).data) {
              const freshData = (payload.new as { data: TelemetriaActuariosa }).data;
              setData(freshData);
              if (freshData.leads_respuestas) {
                setLeads(freshData.leads_respuestas);
              }
              setLastSyncTime(new Date().toLocaleTimeString("es-EC"));
              showToast("⚡ Métricas actualizadas en tiempo real", "ok");
            }
          }
        )
        .on(
          "postgres_changes",
          { event: "*", schema: "public", table: "actuariosa_leads" },
          () => {
            fetchTelemetry(true);
            showToast("⚡ Nueva respuesta de empresa recibida", "ok");
          }
        )
        .on(
          "postgres_changes",
          { event: "*", schema: "public", table: "actuariosa_releases" },
          () => {
            fetchUpdates();
            showToast("⚡ Nueva versión del software publicada", "ok");
          }
        )
        .subscribe((status) => {
          if (status === "SUBSCRIBED") {
            setIsRealtimeActive(true);
          } else if (status === "CLOSED" || status === "CHANNEL_ERROR") {
            setIsRealtimeActive(false);
          }
        });
    }

    return () => {
      if (supabase && channel) {
        supabase.removeChannel(channel);
      }
    };
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

          const payload = {
            resumen_general: resGeneral,
            distribucion_provincias: parsed.distribucion_geografica_supercias || data.distribucion_provincias,
            top_dominios: parsed.top_dominios_corporativos || data.top_dominios,
            timestamp: new Date().toISOString(),
          };

          const res = await fetch("/api/sync", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
          });

          const json = await res.json();
          if (json.ok) {
            setData((prev) => ({ ...prev, ...payload }));
            setUploadStatus("¡Datos actualizados y guardados en la nube con éxito!");
            showToast("Reporte local subido a la nube.", "ok");
            setTimeout(() => {
              setShowUploadModal(false);
              setUploadStatus("");
            }, 1200);
          } else {
            setUploadStatus("Error al guardar en la nube.");
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
    <div className="min-h-screen bg-[#f8fafc] text-slate-900 flex flex-col">
      {/* Toast Notification */}
      {toastMsg && (
        <div
          className={`fixed bottom-6 right-6 z-50 px-5 py-3 rounded-xl shadow-lg flex items-center gap-3 border text-sm font-medium transition-all ${
            toastMsg.type === "ok"
              ? "bg-white border-emerald-300 text-emerald-800 shadow-emerald-500/10"
              : "bg-white border-rose-300 text-rose-800 shadow-rose-500/10"
          }`}
        >
          {toastMsg.type === "ok" ? <CheckCircle2 className="w-5 h-5 text-emerald-600" /> : <AlertCircle className="w-5 h-5 text-rose-600" />}
          <span>{toastMsg.text}</span>
        </div>
      )}

      {/* ── TOP EXECUTIVE BAR (WHITE & CLEAN) ────────────────────────── */}
      <header className="border-b border-slate-200/90 bg-white sticky top-0 z-40 shadow-xs">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-20 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="w-11 h-11 rounded-xl bg-white border border-slate-200/90 flex items-center justify-center shadow-xs overflow-hidden shrink-0">
              <img
                src="/avatar-humano-azul-oficial.svg"
                alt="Emblema Actuariosa"
                className="w-9 h-9 object-contain"
              />
            </div>
            <div>
              <div className="flex items-center gap-3 flex-wrap">
                <img
                  src="/actuariosa.svg"
                  alt="Actuariosa"
                  className="h-7 w-auto object-contain"
                />
                <span className="text-[#262478] font-bold text-xs px-2.5 py-0.5 rounded-full bg-blue-50 border border-blue-200/70 font-mono tracking-wide">
                  PANEL GERENCIAL
                </span>
                <span
                  className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold ${
                    isRealtimeActive
                      ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                      : "bg-amber-50 text-amber-700 border border-amber-200"
                  }`}
                  title="Conexión WebSocket directa con Supabase. Cero recargas o consultas periódicas."
                >
                  <span className={`w-2 h-2 rounded-full ${isRealtimeActive ? "bg-emerald-500 animate-pulse" : "bg-amber-500"}`}></span>
                  {isRealtimeActive ? "Tiempo Real • WebSockets" : "Conectando Tiempo Real…"}
                </span>
              </div>
              <p className="text-xs text-slate-500 mt-1">
                Supervisión del flujo de datos, depuración Supercias y prospección comercial B2B
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="hidden md:flex flex-col text-right text-xs">
              <span className="text-slate-500 flex items-center gap-1 justify-end">
                <Clock className="w-3.5 h-3.5 text-[#262478]" /> Sincronización en vivo:
              </span>
              <span className="text-slate-700 font-mono font-medium">{lastSyncTime || "En vivo"}</span>
            </div>

            <button
              onClick={() => fetchTelemetry(false)}
              disabled={isRefreshing}
              className="p-2.5 rounded-xl bg-slate-50 hover:bg-slate-100 border border-slate-200 text-slate-600 hover:text-slate-900 transition-all disabled:opacity-50 shadow-xs"
              title="Refrescar métricas de la nube"
            >
              <RefreshCw className={`w-4 h-4 ${isRefreshing ? "animate-spin text-[#262478]" : ""}`} />
            </button>

            <button
              onClick={() => setShowUploadModal(true)}
              className="hidden sm:inline-flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-semibold bg-[#262478] hover:bg-[#1e1d61] text-white shadow-xs transition-all"
            >
              <UploadCloud className="w-4 h-4 text-white" />
              <span>Cargar Reporte JSON</span>
            </button>
          </div>
        </div>

        {/* Navigation Tabs */}
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex gap-1 border-t border-slate-100">
          <button
            onClick={() => setActiveTab("general")}
            className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-all ${
              activeTab === "general"
                ? "border-[#262478] text-[#262478] bg-blue-50/50 font-semibold"
                : "border-transparent text-slate-500 hover:text-slate-900 hover:border-slate-300"
            }`}
          >
            <BarChart3 className="w-4 h-4 text-[#262478]" />
            <span>Visión Ejecutiva</span>
          </button>

          <button
            onClick={() => setActiveTab("respuestas")}
            className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-all ${
              activeTab === "respuestas"
                ? "border-emerald-600 text-emerald-700 bg-emerald-50/50 font-semibold"
                : "border-transparent text-slate-500 hover:text-slate-900 hover:border-slate-300"
            }`}
          >
            <CheckCircle2 className="w-4 h-4" />
            <span>Respuestas & Prospectos</span>
            <span className="ml-1 px-1.5 py-0.2 rounded-full text-[10px] bg-emerald-100 text-emerald-800 font-bold">
              {conteoRespuestas.positivos}
            </span>
          </button>

          <button
            onClick={() => setActiveTab("flujo")}
            className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-all ${
              activeTab === "flujo"
                ? "border-blue-600 text-blue-700 bg-blue-50/50 font-semibold"
                : "border-transparent text-slate-500 hover:text-slate-900 hover:border-slate-300"
            }`}
          >
            <Layers className="w-4 h-4" />
            <span>Flujo de Datos & Arquitectura</span>
          </button>

          <button
            onClick={() => setActiveTab("empresas")}
            className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-all ${
              activeTab === "empresas"
                ? "border-[#262478] text-[#262478] bg-blue-50/50 font-semibold"
                : "border-transparent text-slate-500 hover:text-slate-900 hover:border-slate-300"
            }`}
          >
            <Building2 className="w-4 h-4" />
            <span>Bases Depuradas</span>
          </button>

          <button
            onClick={() => setActiveTab("actualizaciones")}
            className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-all ${
              activeTab === "actualizaciones"
                ? "border-purple-600 text-purple-700 bg-purple-50/50 font-semibold"
                : "border-transparent text-slate-500 hover:text-slate-900 hover:border-slate-300"
            }`}
          >
            <Rocket className="w-4 h-4" />
            <span>Lanzar Actualizaciones</span>
            <span className="ml-1 px-1.5 py-0.5 rounded-full text-[10px] bg-purple-100 text-purple-800 font-bold font-mono">
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
                <div className="absolute top-0 left-0 h-1 w-full bg-blue-600"></div>
                <div className="flex items-center justify-between text-slate-500 mb-3">
                  <span className="text-xs font-semibold uppercase tracking-wider">Inventario Bruto Total</span>
                  <div className="p-2 rounded-lg bg-blue-50 text-blue-700">
                    <Database className="w-4 h-4" />
                  </div>
                </div>
                <div className="text-3xl font-extrabold text-slate-900 font-mono tracking-tight">
                  {kpis.total_recopilados_brutos.toLocaleString("es-EC")}
                </div>
                <div className="mt-3 text-xs text-slate-500 flex items-center justify-between">
                  <span>69 archivos recopilados</span>
                  <span className="text-blue-700 font-semibold">{kpis.total_base_activa.toLocaleString("es-EC")} activos 2026</span>
                </div>
              </div>

              {/* Card 2: Negocios Depurados 100% Funcionales */}
              <div className="glass-card p-6 relative overflow-hidden group border-l-4 border-l-[#262478]">
                <div className="flex items-center justify-between text-slate-500 mb-3">
                  <span className="text-xs font-semibold uppercase tracking-wider text-[#262478]">Empresas 100% Funcionales</span>
                  <div className="p-2 rounded-lg bg-blue-50 text-[#262478]">
                    <ShieldCheck className="w-4 h-4" />
                  </div>
                </div>
                <div className="text-3xl font-extrabold text-[#262478] font-mono tracking-tight flex items-baseline gap-2">
                  <span>{kpis.total_negocios_unicos.toLocaleString("es-EC")}</span>
                </div>
                <div className="mt-3 text-xs text-slate-500 flex items-center justify-between">
                  <span className="text-[#262478] font-semibold">{kpis.supercias_activas_con_ruc.toLocaleString("es-EC")} Supercias RUC</span>
                  <span>{kpis.negocios_corporativos.toLocaleString("es-EC")} corporativos</span>
                </div>
              </div>

              {/* Card 3: Correos Enviados y Entrega */}
              <div className="glass-card p-6 relative overflow-hidden group">
                <div className="absolute top-0 left-0 h-1 w-full bg-slate-300"></div>
                <div className="flex items-center justify-between text-slate-500 mb-3">
                  <span className="text-xs font-semibold uppercase tracking-wider">Correos Enviados</span>
                  <div className="p-2 rounded-lg bg-slate-100 text-slate-700">
                    <Send className="w-4 h-4" />
                  </div>
                </div>
                <div className="text-3xl font-extrabold text-slate-900 font-mono tracking-tight">
                  {kpis.total_enviados_campanas.toLocaleString("es-EC")}
                </div>
                <div className="mt-3 text-xs text-slate-500 flex items-center justify-between">
                  <span className="text-emerald-600 font-semibold flex items-center gap-1">
                    <CheckCircle2 className="w-3.5 h-3.5" /> {kpis.tasa_entrega}% entrega
                  </span>
                  <span>{kpis.total_errores_envio} errores evitados</span>
                </div>
              </div>

              {/* Card 4: Respuestas Positivas y Oportunidades */}
              <div className="glass-card p-6 relative overflow-hidden group border-l-4 border-l-emerald-600">
                <div className="flex items-center justify-between text-slate-500 mb-3">
                  <span className="text-xs font-semibold uppercase tracking-wider text-emerald-700">Empresas Interesadas (Positivos)</span>
                  <div className="p-2 rounded-lg bg-emerald-50 text-emerald-700">
                    <TrendingUp className="w-4 h-4" />
                  </div>
                </div>
                <div className="text-3xl font-extrabold text-slate-900 font-mono tracking-tight flex items-baseline gap-2">
                  <span>{conteoRespuestas.positivos}</span>
                  <span className="text-xs text-emerald-600 font-sans font-normal">
                    ({((conteoRespuestas.positivos / (kpis.total_enviados_campanas || 1)) * 100).toFixed(1)}% respuesta)
                  </span>
                </div>
                <div className="mt-3 text-xs text-slate-500 flex items-center justify-between">
                  <span className="font-semibold text-emerald-600">{conteoRespuestas.cotizaciones} cotizaciones pedidas</span>
                  <span className="text-emerald-700">{conteoRespuestas.cerrados} contratadas</span>
                </div>
              </div>
            </div>

            {/* ── EMBUDO DE CONVERSIÓN COMERCIAL (FUNNEL) ───────────── */}
            <div className="glass-card p-6">
              <div className="flex items-center justify-between mb-6">
                <div>
                  <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
                    <TrendingUp className="w-5 h-5 text-[#262478]" />
                    Embudo de Depuración y Rendimiento Comercial
                  </h3>
                  <p className="text-xs text-slate-500 mt-1">
                    Visualiza el flujo de filtrado desde la recolección cruda hasta las respuestas de contratación actuarial.
                  </p>
                </div>
                <span className="text-xs px-3 py-1 rounded-lg bg-blue-50 text-[#262478] border border-blue-200/80 font-semibold font-mono">
                  Eficiencia de Purga: 82.8%
                </span>
              </div>

              {/* Funnel Stages */}
              <div className="space-y-4">
                {/* Etapa 1 */}
                <div>
                  <div className="flex justify-between text-xs font-medium mb-1.5">
                    <span className="text-slate-700">1. Recolección Cruda de Correos (Histórico + Pendrives)</span>
                    <span className="font-mono text-slate-500">247,997 (100%)</span>
                  </div>
                  <div className="h-3.5 w-full bg-slate-100 rounded-full overflow-hidden">
                    <div className="h-full bg-slate-400 rounded-full" style={{ width: "100%" }}></div>
                  </div>
                </div>

                {/* Etapa 2 */}
                <div>
                  <div className="flex justify-between text-xs font-medium mb-1.5">
                    <span className="text-slate-700">2. Normalización, Sintaxis Limpia y Unicidad</span>
                    <span className="font-mono text-slate-500">136,602 (55.1%)</span>
                  </div>
                  <div className="h-3.5 w-full bg-slate-100 rounded-full overflow-hidden">
                    <div className="h-full bg-sky-500 rounded-full" style={{ width: "55.1%" }}></div>
                  </div>
                </div>

                {/* Etapa 3 */}
                <div>
                  <div className="flex justify-between text-xs font-medium mb-1.5">
                    <span className="text-[#262478] font-bold">3. Empresas Activas en Supercias y Dominios Corporativos (100% Funcionales)</span>
                    <span className="font-mono text-[#262478] font-bold">42,648 (17.2%)</span>
                  </div>
                  <div className="h-3.5 w-full bg-slate-100 rounded-full overflow-hidden">
                    <div className="h-full bg-[#262478] rounded-full" style={{ width: "17.2%" }}></div>
                  </div>
                </div>

                {/* Etapa 4 */}
                <div>
                  <div className="flex justify-between text-xs font-medium mb-1.5">
                    <span className="text-slate-700">4. Contactadas en Campañas de Email B2B (NIC 19 / Jubilación)</span>
                    <span className="font-mono text-slate-500">
                      {kpis.total_enviados_campanas.toLocaleString("es-EC")} ({kpis.total_negocios_unicos > 0 ? ((kpis.total_enviados_campanas / kpis.total_negocios_unicos) * 100).toFixed(1) : "0.0"}% de base funcional)
                    </span>
                  </div>
                  <div className="h-3.5 w-full bg-slate-100 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-indigo-500 rounded-full transition-all duration-500"
                      style={{
                        width: `${Math.min(100, Math.max(kpis.total_enviados_campanas > 0 ? 2 : 0, (kpis.total_enviados_campanas / (kpis.total_negocios_unicos || 1)) * 100))}%`,
                      }}
                    ></div>
                  </div>
                </div>

                {/* Etapa 5 */}
                <div>
                  <div className="flex justify-between text-xs font-medium mb-1.5">
                    <span className="text-emerald-700 font-semibold">5. Respuestas Comerciales Positivas y Solicitudes de Cotización</span>
                    <span className="font-mono text-emerald-700 font-bold">{conteoRespuestas.positivos} empresas interesadas</span>
                  </div>
                  <div className="h-3.5 w-full bg-slate-100 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-emerald-500 rounded-full transition-all duration-500"
                      style={{
                        width: `${Math.min(100, Math.max(conteoRespuestas.positivos > 0 ? 2 : 0, (conteoRespuestas.positivos / (kpis.total_enviados_campanas || 1)) * 100))}%`,
                      }}
                    ></div>
                  </div>
                </div>
              </div>
            </div>

            {/* ── 2 COLUMNAS: PROVINCIAS Y DOMINIOS ──────────────────── */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Provincias */}
              <div className="glass-card p-6">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                    <MapPin className="w-4 h-4 text-rose-500" />
                    Empresas Supercias por Provincia (Ecuador)
                  </h3>
                  <span className="text-xs text-slate-500 font-mono">11,779 con RUC</span>
                </div>

                <div className="space-y-3 mt-4">
                  {Object.entries(data.distribucion_provincias).map(([prov, cant]) => {
                    const max = 11236;
                    const pct = Math.max(3, Math.round((cant / max) * 100));
                    return (
                      <div key={prov}>
                        <div className="flex justify-between text-xs font-medium mb-1">
                          <span className="text-slate-700">{prov}</span>
                          <span className="font-mono text-slate-500">{cant.toLocaleString("es-EC")}</span>
                        </div>
                        <div className="h-2 w-full bg-slate-100 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-[#262478] rounded-full"
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
                  <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                    <Building2 className="w-4 h-4 text-[#262478]" />
                    Top Dominios y Proveedores de Empresas
                  </h3>
                  <span className="text-xs text-slate-500">Redes corporativas EC</span>
                </div>

                <div className="grid grid-cols-2 gap-3 mt-2">
                  {Object.entries(data.top_dominios).slice(0, 10).map(([dom, cant]) => (
                    <div key={dom} className="p-3 rounded-xl bg-slate-50 border border-slate-200/80 flex justify-between items-center">
                      <span className="text-xs font-mono text-slate-700 truncate max-w-[130px]" title={dom}>
                        {dom}
                      </span>
                      <span className="text-xs font-bold text-[#262478] font-mono">
                        {cant.toLocaleString("es-EC")}
                      </span>
                    </div>
                  ))}
                </div>

                <div className="mt-5 p-3.5 rounded-xl bg-amber-50 border border-amber-200 text-xs text-amber-900 flex items-start gap-2.5">
                  <ShieldCheck className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
                  <span>
                    <strong>Protección de Reputación:</strong> Se eliminaron 3,496 empresas con estado "Disolución" o "Inactiva" en la Superintendencia de Compañías para evitar bloqueos del servidor SMTP.
                  </span>
                </div>
              </div>
            </div>

            {/* ── HISTORIAL DE CAMPAÑAS ──────────────────────────────── */}
            <div className="glass-card p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                  <Send className="w-4 h-4 text-emerald-600" />
                  Campañas Recientes de Envío a Empresas
                </h3>
                <span className="text-xs text-slate-500">Registrado por MxCorreo</span>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50 text-slate-600 border-b border-slate-200 font-semibold">
                    <tr>
                      <th className="py-2.5 px-3">Campaña / Asunto</th>
                      <th className="py-2.5 px-3">Fecha</th>
                      <th className="py-2.5 px-3 text-center">Total Lote</th>
                      <th className="py-2.5 px-3 text-center">Enviados OK</th>
                      <th className="py-2.5 px-3 text-center">Errores</th>
                      <th className="py-2.5 px-3 text-right">Efectividad</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 text-slate-700">
                    {data.campanas.map((c) => {
                      const eff = c.total > 0 ? (((c.enviados) / c.total) * 100).toFixed(1) : "100";
                      return (
                        <tr key={c.id} className="hover:bg-slate-50/60">
                          <td className="py-3 px-3">
                            <div className="font-semibold text-slate-900">{c.nombre}</div>
                            <div className="text-[11px] text-slate-500 truncate max-w-md">{c.asunto}</div>
                          </td>
                          <td className="py-3 px-3 font-mono text-slate-500">{c.fecha}</td>
                          <td className="py-3 px-3 text-center font-mono font-semibold text-slate-800">{c.total.toLocaleString("es-EC")}</td>
                          <td className="py-3 px-3 text-center font-mono text-emerald-600 font-semibold">{c.enviados.toLocaleString("es-EC")}</td>
                          <td className="py-3 px-3 text-center font-mono text-rose-600">{c.errores}</td>
                          <td className="py-3 px-3 text-right font-mono font-bold text-emerald-600">{eff}%</td>
                        </tr>
                      );
                    })}
                    {data.campanas.length === 0 && (
                      <tr>
                        <td colSpan={6} className="py-8 text-center text-slate-400">
                          No hay campañas registradas todavía. Las campañas que se envíen desde MxCorreo aparecerán aquí automáticamente en tiempo real.
                        </td>
                      </tr>
                    )}
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
                <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
                  <CheckCircle2 className="w-5 h-5 text-emerald-600" />
                  Control de Respuestas y Oportunidades Comerciales
                </h2>
                <p className="text-xs text-slate-500 mt-1">
                  Monitorea cuántas empresas responden a las propuestas y clasifica los prospectos que avanzan a cotización de estudios actuariales.
                </p>
              </div>

              <div className="flex items-center gap-3">
                <button
                  onClick={exportarLeadsCSV}
                  className="px-4 py-2.5 rounded-xl bg-slate-50 hover:bg-slate-100 border border-slate-200 text-xs font-semibold text-slate-700 transition-all flex items-center gap-2 shadow-xs"
                >
                  <Download className="w-4 h-4 text-[#262478]" />
                  <span>Exportar CSV</span>
                </button>
                <button
                  onClick={() => setShowAddLeadModal(true)}
                  className="px-4 py-2.5 rounded-xl bg-[#262478] hover:bg-[#1e1d61] text-xs font-bold text-white transition-all shadow-xs flex items-center gap-2"
                >
                  <Plus className="w-4 h-4" />
                  <span>Registrar Respuesta de Empresa</span>
                </button>
              </div>
            </div>

            {/* Metricas rápidas de respuestas */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              <div className="glass-card p-4 text-center">
                <span className="text-xs text-slate-500">Total Contactadas</span>
                <div className="text-2xl font-extrabold text-slate-900 font-mono mt-1">{kpis.total_enviados_campanas.toLocaleString("es-EC")}</div>
              </div>
              <div className="glass-card p-4 text-center border-l-4 border-l-emerald-500">
                <span className="text-xs text-emerald-700 font-semibold">Respuestas Positivas</span>
                <div className="text-2xl font-extrabold text-emerald-600 font-mono mt-1">{conteoRespuestas.positivos}</div>
              </div>
              <div className="glass-card p-4 text-center border-l-4 border-l-[#262478]">
                <span className="text-xs text-[#262478] font-semibold">Cotizaciones Solicitadas</span>
                <div className="text-2xl font-extrabold text-[#262478] font-mono mt-1">{conteoRespuestas.cotizaciones}</div>
              </div>
              <div className="glass-card p-4 text-center border-l-4 border-l-teal-500">
                <span className="text-xs text-teal-700 font-semibold">Contratos Cerrados</span>
                <div className="text-2xl font-extrabold text-teal-600 font-mono mt-1">{conteoRespuestas.cerrados}</div>
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
                  className="w-full pl-9 pr-4 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:border-[#262478] focus:bg-white"
                />
              </div>

              <div className="flex items-center gap-2 overflow-x-auto w-full sm:w-auto">
                {["Todos", "Positivo / Interesado", "Cotización Solicitada", "En Negociación", "Cerrado / Cliente", "No Interesado"].map((st) => (
                  <button
                    key={st}
                    onClick={() => setFiltroEstado(st)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition-all ${
                      filtroEstado === st
                        ? "bg-[#262478] text-white shadow-xs"
                        : "bg-slate-100 text-slate-600 hover:text-slate-900 hover:bg-slate-200"
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
                  <thead className="bg-slate-50 text-slate-600 border-b border-slate-200 font-semibold">
                    <tr>
                      <th className="py-3 px-4">Empresa / RUC</th>
                      <th className="py-3 px-4">Correo Electrónico</th>
                      <th className="py-3 px-4">Servicio de Interés</th>
                      <th className="py-3 px-4">Estado Actual</th>
                      <th className="py-3 px-4">Notas de la Respuesta</th>
                      <th className="py-3 px-4 text-right">Acción Rápida</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 text-slate-700">
                    {leadsFiltrados.map((l) => (
                      <tr key={l.id} className="hover:bg-slate-50/70 transition-colors">
                        <td className="py-3 px-4">
                          <div className="font-bold text-slate-900">{l.empresa}</div>
                          <div className="text-[11px] font-mono text-slate-500">
                            {l.ruc ? `RUC: ${l.ruc}` : "Sin RUC"} • {l.provincia || "EC"}
                          </div>
                        </td>
                        <td className="py-3 px-4 font-mono text-[#262478] font-medium">{l.correo}</td>
                        <td className="py-3 px-4 text-slate-700">{l.servicio_interes}</td>
                        <td className="py-3 px-4">
                          <span
                            className={`inline-flex px-2.5 py-1 rounded-full text-[11px] font-semibold ${
                              l.estado === "Cerrado / Cliente"
                                ? "bg-teal-50 text-teal-800 border border-teal-200"
                                : l.estado === "Cotización Solicitada"
                                ? "bg-blue-50 text-blue-800 border border-blue-200"
                                : l.estado === "En Negociación"
                                ? "bg-amber-50 text-amber-800 border border-amber-200"
                                : l.estado === "No Interesado"
                                ? "bg-rose-50 text-rose-800 border border-rose-200"
                                : "bg-emerald-50 text-emerald-800 border border-emerald-200"
                            }`}
                          >
                            {l.estado}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-slate-500 max-w-xs truncate" title={l.notas}>
                          {l.notas || "—"}
                        </td>
                        <td className="py-3 px-4 text-right">
                          <select
                            value={l.estado}
                            onChange={(e) => handleUpdateStatus(l.id, e.target.value as LeadRespuesta["estado"])}
                            className="bg-slate-50 border border-slate-200 text-[11px] text-slate-800 rounded-lg px-2 py-1 focus:outline-none focus:border-[#262478]"
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
                        <td colSpan={6} className="py-8 text-center text-slate-400">
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
            <div className="glass-card p-6">
              <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
                <Layers className="w-5 h-5 text-[#262478]" />
                Arquitectura de Transmisión y Flujo de Datos
              </h2>
              <p className="text-xs text-slate-500 mt-1">
                Cómo viajan los datos desde tus herramientas de depuración locales hacia la nube en Vercel y Supabase para supervisión en tiempo real.
              </p>

              {/* Diagrama Visual */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mt-8 relative">
                <div className="p-5 rounded-xl border border-slate-200 bg-slate-50/60">
                  <div className="w-8 h-8 rounded-full bg-blue-100 text-[#262478] flex items-center justify-center font-bold text-xs mb-3">
                    1
                  </div>
                  <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider">Depuración Local</h4>
                  <p className="text-xs text-slate-600 mt-1.5">
                    <code>depurar_correos_supercias.py</code> cruza 136k correos con las bases de la Superintendencia de Compañías.
                  </p>
                  <div className="mt-3 text-[11px] font-mono text-emerald-700 bg-emerald-50 border border-emerald-200 px-2 py-1 rounded">
                    42,648 empresas activas
                  </div>
                </div>

                <div className="p-5 rounded-xl border border-slate-200 bg-slate-50/60">
                  <div className="w-8 h-8 rounded-full bg-indigo-100 text-indigo-700 flex items-center justify-center font-bold text-xs mb-3">
                    2
                  </div>
                  <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider">MxCorreo Desktop</h4>
                  <p className="text-xs text-slate-600 mt-1.5">
                    Lanza campañas B2B con pausas anti-spam y genera bitácora de correos enviados, fallidos y respuestas.
                  </p>
                  <div className="mt-3 text-[11px] font-mono text-[#262478] bg-blue-50 border border-blue-200 px-2 py-1 rounded">
                    sync_telemetria.py
                  </div>
                </div>

                <div className="p-5 rounded-xl border border-slate-200 bg-slate-50/60">
                  <div className="w-8 h-8 rounded-full bg-teal-100 text-teal-700 flex items-center justify-center font-bold text-xs mb-3">
                    3
                  </div>
                  <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider">Endpoint Vercel & Supabase</h4>
                  <p className="text-xs text-slate-600 mt-1.5">
                    Ruta Serverless <code>/api/sync</code> autenticada que persiste datos y emite eventos WebSocket en tiempo real.
                  </p>
                  <div className="mt-3 text-[11px] font-mono text-teal-800 bg-teal-50 border border-teal-200 px-2 py-1 rounded">
                    WebSockets Realtime
                  </div>
                </div>

                <div className="p-5 rounded-xl border border-slate-200 bg-slate-50/60">
                  <div className="w-8 h-8 rounded-full bg-emerald-100 text-emerald-700 flex items-center justify-center font-bold text-xs mb-3">
                    4
                  </div>
                  <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider">Panel Gerencial</h4>
                  <p className="text-xs text-slate-600 mt-1.5">
                    El jefe abre el enlace de Vercel y consulta los indicadores clave de negocio sin tocar código ni terminales.
                  </p>
                  <div className="mt-3 text-[11px] font-mono text-emerald-800 bg-emerald-50 border border-emerald-200 px-2 py-1 rounded">
                    Dashboard 24/7
                  </div>
                </div>
              </div>
            </div>

            {/* Código de Sincronización */}
            <div className="glass-card p-6">
              <h3 className="text-sm font-bold text-slate-900 mb-2">Comando para Sincronizar desde tu Computadora</h3>
              <p className="text-xs text-slate-500 mb-4">
                Puedes ejecutar este comando en la carpeta <code>Mx/</code> en cualquier momento para actualizar los números del jefe:
              </p>

              <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 font-mono text-xs text-emerald-400 flex items-center justify-between">
                <span>python sync_telemetria.py --url https://panel-web-six-plum.vercel.app/api/sync</span>
                <button
                  onClick={() => {
                    navigator.clipboard.writeText("python sync_telemetria.py");
                    showToast("Comando copiado al portapapeles.", "ok");
                  }}
                  className="px-3 py-1 rounded-lg bg-white/10 hover:bg-white/20 text-white text-[11px]"
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
              <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
                <Building2 className="w-5 h-5 text-[#262478]" />
                Desglose Estructurado de las Bases Depuradas
              </h2>
              <p className="text-xs text-slate-500 mt-1">
                Estructura exacta de archivos generados en <code>Mx/resultados/depuracion_supercias_2026/</code> y organizados en Google Drive.
              </p>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-6">
                <div className="p-5 rounded-xl bg-white border-l-4 border-l-emerald-600 border border-slate-200 shadow-xs">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-slate-900 text-sm">1. Supercias Activas con RUC</span>
                    <span className="font-mono text-emerald-700 font-bold text-sm">11,779</span>
                  </div>
                  <p className="text-xs text-slate-600 mt-2">
                    Empresas con razón social, RUC y estado legal activo validado ante la Superintendencia de Compañías. Ideales para auditorías y estudios de jubilación patronal NIC 19.
                  </p>
                </div>

                <div className="p-5 rounded-xl bg-white border-l-4 border-l-[#262478] border border-slate-200 shadow-xs">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-slate-900 text-sm">2. Negocios Corporativos Activos</span>
                    <span className="font-mono text-[#262478] font-bold text-sm">30,869</span>
                  </div>
                  <p className="text-xs text-slate-600 mt-2">
                    Correos alojados en dominios empresariales propios y redes de telecomunicaciones (Satnet, Andinanet, Telconet, etc.) con servidores MX operativos.
                  </p>
                </div>

                <div className="p-5 rounded-xl bg-white border-l-4 border-l-rose-500 border border-slate-200 shadow-xs">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-slate-900 text-sm">3. Descartados (Disolución / Inactivas)</span>
                    <span className="font-mono text-rose-600 font-bold text-sm">3,496</span>
                  </div>
                  <p className="text-xs text-slate-600 mt-2">
                    Sociedades en liquidación, cancelación o disolución según catastro oficial. Se apartaron en carpeta de descarte para evitar rebotar correos.
                  </p>
                </div>

                <div className="p-5 rounded-xl bg-white border-l-4 border-l-blue-500 border border-slate-200 shadow-xs">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-slate-900 text-sm">4. Instituciones Educativas y Colegios</span>
                    <span className="font-mono text-blue-700 font-bold text-sm">4,809</span>
                  </div>
                  <p className="text-xs text-slate-600 mt-2">
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
                  <h2 className="text-xl font-bold text-slate-900 flex items-center gap-2">
                    <Rocket className="w-5 h-5 text-purple-600" />
                    Centro de Lanzamiento de Actualizaciones
                  </h2>
                  <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-purple-100 text-purple-800 border border-purple-200">
                    Versión Activa: v{releaseData?.version || "2.1.0"}
                  </span>
                </div>
                <p className="text-xs text-slate-500 mt-1">
                  Gestiona y publica las versiones oficiales de la aplicación de escritorio MxCorreo. Los clientes conectados detectarán inmediatamente si están desactualizados.
                </p>
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={fetchUpdates}
                  className="px-3 py-2 rounded-xl bg-white hover:bg-slate-50 border border-slate-200 text-xs font-semibold text-slate-700 transition-all flex items-center gap-2 shadow-xs"
                >
                  <RefreshCw className="w-3.5 h-3.5 text-purple-600" />
                  <span>Comprobar Estado</span>
                </button>
              </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
              {/* Columna Izquierda: Formulario de Lanzamiento */}
              <div className="lg:col-span-7 glass-card p-6">
                <h3 className="text-sm font-bold text-slate-900 mb-1 flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-purple-600" />
                  Publicar Nueva Versión a Usuarios
                </h3>
                <p className="text-xs text-slate-500 mb-5">
                  Al pulsar publicar, cualquier usuario que abra la app con una versión inferior recibirá el aviso de <strong>"Desactualizada"</strong> y podrá auto-instalarla.
                </p>

                <form onSubmit={handlePublishUpdate} className="space-y-4 text-xs">
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-slate-700 font-semibold mb-1">
                        Número de Versión (SemVer) *
                      </label>
                      <input
                        type="text"
                        required
                        value={targetVersion}
                        onChange={(e) => setTargetVersion(e.target.value)}
                        placeholder="Ej: 2.1.0 o 2.2.0"
                        className="w-full px-3.5 py-2.5 rounded-xl bg-slate-50 border border-slate-300 text-slate-900 font-mono placeholder:text-slate-400 focus:outline-none focus:border-purple-600 focus:bg-white transition-all"
                      />
                    </div>

                    <div>
                      <label className="block text-slate-700 font-semibold mb-1">
                        Canal de Distribución
                      </label>
                      <select
                        disabled
                        className="w-full px-3.5 py-2.5 rounded-xl bg-slate-100 border border-slate-200 text-slate-500 focus:outline-none"
                      >
                        <option>Producción Oficial (Stable)</option>
                      </select>
                    </div>
                  </div>

                  <div>
                    <label className="block text-slate-700 font-semibold mb-1">
                      Título Descriptivo del Parche *
                    </label>
                    <input
                      type="text"
                      required
                      value={targetTitle}
                      onChange={(e) => setTargetTitle(e.target.value)}
                      placeholder="Ej: Actualización v2.1.0 — Motor Masivo & Telemetría"
                      className="w-full px-3.5 py-2.5 rounded-xl bg-slate-50 border border-slate-300 text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-purple-600 focus:bg-white transition-all"
                    />
                  </div>

                  <div>
                    <label className="block text-slate-700 font-semibold mb-1">
                      Notas de la Versión (Changelog) *
                    </label>
                    <textarea
                      rows={4}
                      required
                      value={targetChangelog}
                      onChange={(e) => setTargetChangelog(e.target.value)}
                      placeholder="Escribe cada novedad en una línea separada..."
                      className="w-full px-3.5 py-2.5 rounded-xl bg-slate-50 border border-slate-300 text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-purple-600 focus:bg-white transition-all font-mono text-xs leading-relaxed"
                    />
                    <span className="text-[11px] text-slate-500 mt-1 block">
                      Estas notas aparecerán directamente dentro de la ventana de actualización en la pantalla del usuario.
                    </span>
                  </div>

                  <div className="flex items-center gap-3 p-3 rounded-xl bg-purple-50 border border-purple-200">
                    <input
                      type="checkbox"
                      id="chk-mandatory"
                      checked={isMandatory}
                      onChange={(e) => setIsMandatory(e.target.checked)}
                      className="w-4 h-4 rounded text-purple-600 focus:ring-purple-500 border-slate-300 bg-white"
                    />
                    <label htmlFor="chk-mandatory" className="text-xs text-slate-700 cursor-pointer">
                      <span className="font-semibold text-purple-800">Actualización Obligatoria:</span> Exigir al usuario actualizar antes de permitir envíos masivos.
                    </label>
                  </div>

                  <div className="pt-2">
                    <button
                      type="submit"
                      disabled={isPublishing}
                      className="w-full py-3 rounded-xl bg-purple-700 hover:bg-purple-800 text-white font-bold shadow-xs flex items-center justify-center gap-2 transition-all disabled:opacity-50 text-sm"
                    >
                      <Rocket className={`w-4 h-4 ${isPublishing ? "animate-bounce" : ""}`} />
                      <span>{isPublishing ? "Lanzando Versión a Servidores…" : `Publicar Versión v${targetVersion} a Clientes`}</span>
                    </button>
                  </div>
                </form>
              </div>

              {/* Columna Derecha: Estado Actual y Diagnóstico */}
              <div className="lg:col-span-5 space-y-5">
                <div className="glass-card p-6 border-purple-200">
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-xs font-bold uppercase tracking-wider text-slate-500">
                      Versión Transmitida en Vivo
                    </span>
                    <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                      <span className="live-pulse"></span>
                      En Producción
                    </span>
                  </div>

                  <div className="flex items-baseline gap-2 mb-2">
                    <span className="text-3xl font-extrabold text-slate-900 font-mono">
                      v{releaseData?.version || "2.1.0"}
                    </span>
                    <span className="text-xs text-slate-500">
                      (Publicada: {releaseData?.release_date || "2026-09-21"})
                    </span>
                  </div>

                  <div className="text-xs font-semibold text-purple-800 mb-3">
                    {releaseData?.title}
                  </div>

                  <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 space-y-1.5 mb-4">
                    <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block mb-1">
                      Novedades incluidas en el paquete:
                    </span>
                    {(releaseData?.changelog || []).map((item, idx) => (
                      <div key={idx} className="flex items-start gap-2 text-xs text-slate-700">
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0 mt-0.5" />
                        <span>{item}</span>
                      </div>
                    ))}
                  </div>

                  <div className="grid grid-cols-2 gap-3 text-xs">
                    <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200">
                      <span className="text-slate-500 block text-[10px]">Paquete Incremental</span>
                      <span className="text-slate-800 font-mono font-medium">{releaseData?.package_size || "3.8 MB"}</span>
                    </div>
                    <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200">
                      <span className="text-slate-500 block text-[10px]">Tipo de Parche</span>
                      <span className="text-emerald-700 font-medium">Reinicio Autónomo</span>
                    </div>
                  </div>
                </div>

                <div className="glass-card p-5 border-blue-200">
                  <h4 className="text-xs font-bold text-[#262478] mb-2 flex items-center gap-1.5">
                    <Layers className="w-4 h-4" />
                    ¿Cómo Funciona para el Usuario?
                  </h4>
                  <ol className="text-xs text-slate-600 space-y-2 list-decimal list-inside leading-relaxed">
                    <li>
                      El usuario abre <strong>MxCorreo</strong>.
                    </li>
                    <li>
                      La app consulta automáticamente la API de Vercel (<code>/api/updates</code>).
                    </li>
                    <li>
                      Al detectar versión superior, aparece la pantalla de <strong>"Aplicación Desactualizada"</strong>.
                    </li>
                    <li>
                      Al dar clic en <strong>"Actualizar Ahora"</strong>, descarga e instala los parches en segundo plano.
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
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 border border-slate-200 shadow-xl relative text-slate-900">
            <h3 className="text-lg font-bold text-slate-900 mb-1 flex items-center gap-2">
              <CheckCircle2 className="w-5 h-5 text-emerald-600" />
              Registrar Respuesta de Empresa
            </h3>
            <p className="text-xs text-slate-500 mb-5">
              Anota la empresa que respondió a la propuesta para sumarla al embudo del jefe.
            </p>

            <form onSubmit={handleCreateLead} className="space-y-4 text-xs">
              <div>
                <label className="block text-slate-700 font-semibold mb-1">Nombre de la Empresa / Razón Social *</label>
                <input
                  type="text"
                  required
                  placeholder="Ej: PESQUERA INDUSTRIAL DEL PACÍFICO S.A."
                  value={newEmpresa}
                  onChange={(e) => setNewEmpresa(e.target.value)}
                  className="w-full p-2.5 rounded-xl bg-slate-50 border border-slate-300 text-slate-900 focus:outline-none focus:border-[#262478] focus:bg-white"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-700 font-semibold mb-1">Correo de Contacto *</label>
                  <input
                    type="email"
                    required
                    placeholder="gerencia@pesquera.com.ec"
                    value={newCorreo}
                    onChange={(e) => setNewCorreo(e.target.value)}
                    className="w-full p-2.5 rounded-xl bg-slate-50 border border-slate-300 text-slate-900 focus:outline-none focus:border-[#262478] focus:bg-white"
                  />
                </div>
                <div>
                  <label className="block text-slate-700 font-semibold mb-1">RUC (opcional)</label>
                  <input
                    type="text"
                    placeholder="0992384912001"
                    value={newRuc}
                    onChange={(e) => setNewRuc(e.target.value)}
                    className="w-full p-2.5 rounded-xl bg-slate-50 border border-slate-300 text-slate-900 focus:outline-none focus:border-[#262478] focus:bg-white"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-700 font-semibold mb-1">Estado de Respuesta</label>
                  <select
                    value={newEstado}
                    onChange={(e) => setNewEstado(e.target.value as LeadRespuesta["estado"])}
                    className="w-full p-2.5 rounded-xl bg-slate-50 border border-slate-300 text-slate-900 focus:outline-none focus:border-[#262478]"
                  >
                    <option value="Positivo / Interesado">Positivo / Interesado</option>
                    <option value="Cotización Solicitada">Cotización Solicitada</option>
                    <option value="En Negociación">En Negociación</option>
                    <option value="Cerrado / Cliente">Cerrado / Cliente</option>
                    <option value="No Interesado">No Interesado</option>
                  </select>
                </div>
                <div>
                  <label className="block text-slate-700 font-semibold mb-1">Servicio de Interés</label>
                  <select
                    value={newServicio}
                    onChange={(e) => setNewServicio(e.target.value as LeadRespuesta["servicio_interes"])}
                    className="w-full p-2.5 rounded-xl bg-slate-50 border border-slate-300 text-slate-900 focus:outline-none focus:border-[#262478]"
                  >
                    <option value="Jubilación Patronal / NIC 19">Jubilación Patronal / NIC 19</option>
                    <option value="Desahucio y Pasivos Laborales">Desahucio y Pasivos Laborales</option>
                    <option value="Estudio Actuarial Completo">Estudio Actuarial Completo</option>
                    <option value="Consultoría Financiera">Consultoría Financiera</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-slate-700 font-semibold mb-1">Notas / Detalle de la Conversación</label>
                <textarea
                  rows={3}
                  placeholder="Detalles de la llamada o lo que respondieron en el correo…"
                  value={newNotas}
                  onChange={(e) => setNewNotas(e.target.value)}
                  className="w-full p-2.5 rounded-xl bg-slate-50 border border-slate-300 text-slate-900 focus:outline-none focus:border-[#262478] focus:bg-white"
                ></textarea>
              </div>

              <div className="flex justify-end gap-3 pt-3 border-t border-slate-200">
                <button
                  type="button"
                  onClick={() => setShowAddLeadModal(false)}
                  className="px-4 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 font-medium"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 rounded-xl bg-[#262478] hover:bg-[#1e1d61] font-bold text-white shadow-xs"
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
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 border border-slate-200 shadow-xl relative text-slate-900">
            <h3 className="text-base font-bold text-slate-900 mb-1 flex items-center gap-2">
              <UploadCloud className="w-5 h-5 text-[#262478]" />
              Cargar Reporte JSON al Panel
            </h3>
            <p className="text-xs text-slate-500 mb-4">
              Arrastra el archivo <code>Resumen_Depuracion_Supercias.json</code> generado en tu computadora para actualizar el panel de inmediato.
            </p>

            <div
              onDragOver={(e) => e.preventDefault()}
              onDrop={(e) => {
                e.preventDefault();
                const file = e.dataTransfer.files[0];
                if (file) handleFileUpload(file);
              }}
              className="border-2 border-dashed border-slate-300 hover:border-[#262478] rounded-2xl p-8 text-center bg-slate-50 hover:bg-blue-50/30 cursor-pointer transition-colors"
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
              <FileSpreadsheet className="w-8 h-8 text-[#262478] mx-auto mb-2" />
              <span className="text-xs text-slate-800 font-semibold block">
                Haz clic o arrastra un archivo .json aquí
              </span>
              <span className="text-[11px] text-slate-500 block mt-1">
                Resumen_Depuracion_Supercias.json
              </span>
            </div>

            {uploadStatus && (
              <p className="text-xs font-semibold text-center text-[#262478] mt-3">{uploadStatus}</p>
            )}

            <div className="flex justify-end mt-5 pt-3 border-t border-slate-200">
              <button
                type="button"
                onClick={() => {
                  setShowUploadModal(false);
                  setUploadStatus("");
                }}
                className="px-4 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-xs text-slate-700 font-medium"
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
