"use client";

import React, { useState, useEffect, useMemo } from "react";
import {
  BarChart3,
  ShieldCheck,
  Send,
  CheckCircle2,
  Building2,
  TrendingUp,
  MapPin,
  RefreshCw,
  Clock,
  Download,
  Search,
  Layers,
  Database,
  AlertCircle,
} from "lucide-react";
import {
  TelemetriaActuariosa,
  LeadRespuesta,
  initialTelemetryData,
} from "@/lib/data-store";
import { getSupabaseBrowserClient } from "@/lib/supabase";

export default function DashboardGerencial() {
  const [data, setData] = useState<TelemetriaActuariosa>(initialTelemetryData);
  const [activeTab, setActiveTab] = useState<"general" | "respuestas" | "empresas" | "flujo">("general");
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [lastSyncTime, setLastSyncTime] = useState<string>("");
  const [isRealtimeActive, setIsRealtimeActive] = useState<boolean>(false);

  // CRM / Leads state (Solo Monitoreo)
  const [leads, setLeads] = useState<LeadRespuesta[]>(initialTelemetryData.leads_respuestas);
  const [filtroEstado, setFiltroEstado] = useState<string>("Todos");
  const [busquedaLead, setBusquedaLead] = useState<string>("");
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

  useEffect(() => {
    fetchTelemetry(true);

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

  // Filtrado de leads / respuestas para visualización
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

  // Contadores de respuestas recibidas
  const conteoRespuestas = useMemo(() => {
    const positivos = leads.filter(
      (l) => l.estado === "Positivo / Interesado" || l.estado === "Cotización Solicitada" || l.estado === "En Negociación" || l.estado === "Cerrado / Cliente"
    ).length;
    const cotizaciones = leads.filter((l) => l.estado === "Cotización Solicitada" || l.estado === "En Negociación" || l.estado === "Cerrado / Cliente").length;
    const cerrados = leads.filter((l) => l.estado === "Cerrado / Cliente").length;
    const descartes = leads.filter((l) => l.estado === "No Interesado").length;
    return { positivos, cotizaciones, cerrados, descartes, total: leads.length };
  }, [leads]);

  // Exportar Reporte de Leads a CSV
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
    link.setAttribute("download", `monitoreo_prospectos_actuariosa_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    showToast("Reporte descargado con éxito.", "ok");
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

      {/* ── TOP EXECUTIVE BAR (WHITE & CLEAN MONITORING) ───────────── */}
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
                  PANEL DE MONITOREO
                </span>
                <span
                  className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold ${
                    isRealtimeActive
                      ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                      : "bg-amber-50 text-amber-700 border border-amber-200"
                  }`}
                  title="Conexión WebSocket directa con Supabase. Cero recargas periódicas."
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

          <div className="flex items-center gap-4">
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
          </div>
        </div>

        {/* Navigation Tabs (Solo Monitoreo) */}
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
                <div>
                  <div className="flex justify-between text-xs font-medium mb-1.5">
                    <span className="text-slate-700">1. Recolección Cruda de Correos (Histórico + Pendrives)</span>
                    <span className="font-mono text-slate-500">247,997 (100%)</span>
                  </div>
                  <div className="h-3.5 w-full bg-slate-100 rounded-full overflow-hidden">
                    <div className="h-full bg-slate-400 rounded-full" style={{ width: "100%" }}></div>
                  </div>
                </div>

                <div>
                  <div className="flex justify-between text-xs font-medium mb-1.5">
                    <span className="text-slate-700">2. Normalización, Sintaxis Limpia y Unicidad</span>
                    <span className="font-mono text-slate-500">136,602 (55.1%)</span>
                  </div>
                  <div className="h-3.5 w-full bg-slate-100 rounded-full overflow-hidden">
                    <div className="h-full bg-sky-500 rounded-full" style={{ width: "55.1%" }}></div>
                  </div>
                </div>

                <div>
                  <div className="flex justify-between text-xs font-medium mb-1.5">
                    <span className="text-[#262478] font-bold">3. Empresas Activas en Supercias y Dominios Corporativos (100% Funcionales)</span>
                    <span className="font-mono text-[#262478] font-bold">42,648 (17.2%)</span>
                  </div>
                  <div className="h-3.5 w-full bg-slate-100 rounded-full overflow-hidden">
                    <div className="h-full bg-[#262478] rounded-full" style={{ width: "17.2%" }}></div>
                  </div>
                </div>

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

        {/* ════ TAB 2: RESPUESTAS & PROSPECTOS (MONITOREO CRM) ════ */}
        {activeTab === "respuestas" && (
          <div className="space-y-6 animate-fadeIn">
            {/* Header del Monitoreo de Respuestas */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 glass-card p-6">
              <div>
                <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
                  <CheckCircle2 className="w-5 h-5 text-emerald-600" />
                  Monitoreo de Respuestas y Oportunidades
                </h2>
                <p className="text-xs text-slate-500 mt-1">
                  Supervisión directa de las empresas que responden interesadas en los estudios actuariales y consultoría NIC 19.
                </p>
              </div>

              <div>
                <button
                  onClick={exportarLeadsCSV}
                  className="px-4 py-2.5 rounded-xl bg-slate-50 hover:bg-slate-100 border border-slate-200 text-xs font-semibold text-slate-700 transition-all flex items-center gap-2 shadow-xs"
                >
                  <Download className="w-4 h-4 text-[#262478]" />
                  <span>Exportar Reporte CSV</span>
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
                      <th className="py-3 px-4">Estado</th>
                      <th className="py-3 px-4">Notas / Resumen</th>
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
                      </tr>
                    ))}
                    {leadsFiltrados.length === 0 && (
                      <tr>
                        <td colSpan={5} className="py-8 text-center text-slate-400">
                          No hay empresas registradas con el filtro seleccionado.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* ════ TAB 3: BASES DEPURADAS (EXPLORADOR DE SEGMENTOS) ════ */}
        {activeTab === "empresas" && (
          <div className="space-y-6 animate-fadeIn">
            <div className="glass-card p-6">
              <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
                <Building2 className="w-5 h-5 text-[#262478]" />
                Desglose Estructurado de las Bases Depuradas
              </h2>
              <p className="text-xs text-slate-500 mt-1">
                Estructura exacta de archivos depurados en <code>Mx/resultados/depuracion_supercias_2026/</code>.
              </p>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-6">
                <div className="p-5 rounded-xl bg-white border-l-4 border-l-emerald-600 border border-slate-200 shadow-xs">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-slate-900 text-sm">1. Supercias Activas con RUC</span>
                    <span className="font-mono text-emerald-700 font-bold text-sm">11,779</span>
                  </div>
                  <p className="text-xs text-slate-600 mt-2">
                    Empresas con razón social, RUC y estado legal activo validado ante la Superintendencia de Compañías. Base objetivo para auditorías y estudios de jubilación patronal NIC 19.
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
                    Sociedades en liquidación, cancelación o disolución según catastro oficial. Se apartaron en carpeta de descarte para proteger la reputación SMTP del remitente.
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

        {/* ════ TAB 4: FLUJO DE DATOS & ARQUITECTURA ════ */}
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
          </div>
        )}
      </main>
    </div>
  );
}
