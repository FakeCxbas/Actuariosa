/**
 * lib/data-store.ts
 * Estado y almacenamiento centralizado de telemetría de Actuariosa S.A.
 * Pre-poblado con los datos reales consolidados de las depuraciones 2026.
 */
import { getSupabaseServerClient } from "@/lib/supabase";


export interface ResumenGeneral {
  total_recopilados_brutos: number;
  total_base_activa: number;
  total_negocios_unicos: number;
  supercias_activas_con_ruc: number;
  negocios_corporativos: number;
  descartados_inactivas: number;
  instituciones_educativas: number;
  otros_genericos: number;
  correos_con_error_formato: number;
  duplicados_eliminados: number;
  total_enviados_campanas: number;
  total_errores_envio: number;
  tasa_entrega: number;
}

export interface CampanaRegistro {
  id: string;
  nombre: string;
  fecha: string;
  total: number;
  enviados: number;
  errores: number;
  asunto: string;
  remitente: string;
}

export interface LeadRespuesta {
  id: string;
  empresa: string;
  correo: string;
  ruc?: string;
  provincia?: string;
  fecha_contacto: string;
  fecha_respuesta: string;
  estado: "Positivo / Interesado" | "Cotización Solicitada" | "En Negociación" | "Cerrado / Cliente" | "No Interesado";
  servicio_interes: "Jubilación Patronal / NIC 19" | "Desahucio y Pasivos Laborales" | "Estudio Actuarial Completo" | "Consultoría Financiera";
  notas: string;
}

export interface VersionRelease {
  version: string;
  title: string;
  release_date: string;
  mandatory: boolean;
  min_version: string;
  changelog: string[];
  download_url?: string;
  package_size?: string;
  sha256?: string;
}

export interface TelemetriaActuariosa {
  fuente: string;
  ultima_actualizacion: string;
  version_sistema: string;
  resumen_general: ResumenGeneral;
  distribucion_provincias: Record<string, number>;
  top_dominios: Record<string, number>;
  campanas: CampanaRegistro[];
  leads_respuestas: LeadRespuesta[];
  version_actual_cliente?: VersionRelease;
  historial_versiones?: VersionRelease[];
}

// Datos iniciales reales consolidados de Actuariosa S.A.
export const initialTelemetryData: TelemetriaActuariosa = {
  fuente: "Consolidado Maestro Actuariosa + Supercias 2026",
  ultima_actualizacion: "2026-09-21T18:57:40.000Z",
  version_sistema: "v2.0 Enterprise Cloud",
  resumen_general: {
    total_recopilados_brutos: 247997,
    total_base_activa: 136602,
    total_negocios_unicos: 42648,
    supercias_activas_con_ruc: 11779,
    negocios_corporativos: 30869,
    descartados_inactivas: 3496,
    instituciones_educativas: 4809,
    otros_genericos: 85649,
    correos_con_error_formato: 563,
    duplicados_eliminados: 141437,
    total_enviados_campanas: 0,
    total_errores_envio: 0,
    tasa_entrega: 0.0,
  },
  distribucion_provincias: {
    "GUAYAS": 11236,
    "PICHINCHA": 307,
    "EL ORO": 52,
    "MANABI": 37,
    "SANTA ELENA": 35,
    "AZUAY": 32,
    "LOS RIOS": 30,
    "LOJA": 9,
    "GALAPAGOS": 7,
    "SANTO DOMINGO": 7,
  },
  top_dominios: {
    "gye.satnet.net": 1045,
    "andinanet.net": 739,
    "interactive.net.ec": 414,
    "uio.satnet.net": 386,
    "telconet.net": 338,
    "easynet.net.ec": 228,
    "ecua.net.ec": 195,
    "porta.net": 156,
    "claro.com.ec": 154,
    "impsat.net.ec": 149,
    "cablemodem.com.ec": 143,
    "yahoo.com.mx": 134,
    "iclaro.com.ec": 104,
    "ecutel.net": 86,
    "etapanet.net": 84,
    "hotmail.com": 44874,
    "gmail.com": 16983,
    "yahoo.com": 5726,
    "yahoo.es": 4019,
    "outlook.com": 1437,
  },
  campanas: [],
  leads_respuestas: [],
  version_actual_cliente: {
    version: "2.1.0",
    title: "Actualización v2.1.0 — Motor Masivo & Telemetría en la Nube",
    release_date: "2026-09-21",
    mandatory: false,
    min_version: "2.0.0",
    changelog: [
      "Nuevo apartado independiente y exclusivo para envíos directos a empresas",
      "Sincronización de métricas en tiempo real con el panel web en Vercel",
      "Algoritmo de validación de sintaxis y detección de rebotes optimizado",
      "Módulo inteligente de auto-actualizaciones con reinicio transparente",
    ],
    download_url: "https://actuariosa.com/updates/mxcorreo-2.1.0.tar.gz",
    package_size: "3.8 MB",
    sha256: "9f83a45c2b8109d7e63b0c44298fc1c149afbf4c8996fb92427ae41e4649b934",
  },
  historial_versiones: [
    {
      version: "2.1.0",
      title: "Actualización v2.1.0 — Motor Masivo & Telemetría en la Nube",
      release_date: "2026-09-21",
      mandatory: false,
      min_version: "2.0.0",
      changelog: [
        "Apartado de envío masivo a empresas",
        "Sincronización en la nube",
        "Parches en caliente",
      ],
    },
    {
      version: "2.0.0",
      title: "Versión 2.0 Inicial — Depuración Supercias y Cruce RUC",
      release_date: "2026-09-20",
      mandatory: false,
      min_version: "1.0.0",
      changelog: [
        "Depurador de bases de datos Supercias",
        "Algoritmo de cruce y verificación de empresas activas",
      ],
    },
  ],
};

// Singleton en memoria para Vercel Serverless runtime (y fallback ante desconexión)
let globalStore: TelemetriaActuariosa = { ...initialTelemetryData };

export async function getGlobalStore(): Promise<TelemetriaActuariosa> {
  const supabase = getSupabaseServerClient();
  if (!supabase) {
    return globalStore;
  }

  try {
    const [teleRes, campanasRes, leadsRes, releasesRes] = await Promise.all([
      supabase.from("actuariosa_telemetria").select("*").eq("id", "current").maybeSingle(),
      supabase.from("actuariosa_campanas").select("*").order("created_at", { ascending: false }),
      supabase.from("actuariosa_leads").select("*").order("created_at", { ascending: false }),
      supabase.from("actuariosa_releases").select("*").order("created_at", { ascending: false }),
    ]);

    if (teleRes.data) {
      const tele = teleRes.data;
      const campanas: CampanaRegistro[] = campanasRes.data
        ? campanasRes.data.map((c: any) => ({
            id: c.id,
            nombre: c.nombre,
            fecha: c.fecha,
            total: c.total,
            enviados: c.enviados,
            errores: c.errores,
            asunto: c.asunto || "",
            remitente: c.remitente || "",
          }))
        : [];

      const leads: LeadRespuesta[] = leadsRes.data
        ? leadsRes.data.map((l: any) => ({
            id: l.id,
            empresa: l.empresa,
            correo: l.correo,
            ruc: l.ruc || "",
            provincia: l.provincia || "GUAYAS",
            fecha_contacto: l.fecha_contacto,
            fecha_respuesta: l.fecha_respuesta,
            estado: l.estado,
            servicio_interes: l.servicio_interes,
            notas: l.notas || "",
          }))
        : [];

      const releases: VersionRelease[] = (releasesRes.data && releasesRes.data.length > 0)
        ? releasesRes.data.map((r: any) => ({
            version: r.version,
            title: r.title,
            release_date: r.release_date,
            mandatory: r.mandatory,
            min_version: r.min_version,
            changelog: Array.isArray(r.changelog) ? r.changelog : [],
            download_url: r.download_url,
            package_size: r.package_size,
            sha256: r.sha256,
          }))
        : globalStore.historial_versiones || [];

      globalStore = {
        fuente: tele.fuente || globalStore.fuente,
        ultima_actualizacion: tele.ultima_actualizacion || new Date().toISOString(),
        version_sistema: tele.version_sistema || globalStore.version_sistema,
        resumen_general: tele.resumen_general || globalStore.resumen_general,
        distribucion_provincias: tele.distribucion_provincias || globalStore.distribucion_provincias,
        top_dominios: tele.top_dominios || globalStore.top_dominios,
        campanas,
        leads_respuestas: leads,
        version_actual_cliente: releases[0] || globalStore.version_actual_cliente,
        historial_versiones: releases,
      };
    }
  } catch (err) {
    console.error("[DataStore] Error sincronizando con Supabase, usando memoria local:", err);
  }

  return globalStore;
}

export async function getLatestRelease(): Promise<VersionRelease> {
  const supabase = getSupabaseServerClient();
  if (supabase) {
    try {
      const { data } = await supabase
        .from("actuariosa_releases")
        .select("*")
        .order("created_at", { ascending: false })
        .limit(1)
        .maybeSingle();

      if (data) {
        return {
          version: data.version,
          title: data.title,
          release_date: data.release_date,
          mandatory: Boolean(data.mandatory),
          min_version: data.min_version,
          changelog: Array.isArray(data.changelog) ? data.changelog : [],
          download_url: data.download_url,
          package_size: data.package_size,
          sha256: data.sha256,
        };
      }
    } catch (err) {
      console.error("[DataStore] Error obteniendo latest release de Supabase:", err);
    }
  }

  return (
    globalStore.version_actual_cliente || {
      version: "2.1.0",
      title: "Actualización v2.1.0",
      release_date: new Date().toISOString().slice(0, 10),
      mandatory: false,
      min_version: "2.0.0",
      changelog: ["Mejoras generales de rendimiento y estabilidad."],
    }
  );
}

export async function publishNewRelease(rel: Partial<VersionRelease> & { version: string }): Promise<VersionRelease> {
  const newRelease: VersionRelease = {
    version: rel.version,
    title: rel.title || `Actualización v${rel.version}`,
    release_date: rel.release_date || new Date().toISOString().slice(0, 10),
    mandatory: Boolean(rel.mandatory),
    min_version: rel.min_version || "2.0.0",
    changelog: rel.changelog && rel.changelog.length > 0 ? rel.changelog : ["Optimizaciones generales del sistema."],
    download_url: rel.download_url || `https://actuariosa.com/updates/mxcorreo-${rel.version}.tar.gz`,
    package_size: rel.package_size || "4.1 MB",
    sha256: rel.sha256 || "auto-generated-checksum",
  };

  globalStore.version_actual_cliente = newRelease;
  if (!globalStore.historial_versiones) globalStore.historial_versiones = [];
  globalStore.historial_versiones.unshift(newRelease);
  globalStore.ultima_actualizacion = new Date().toISOString();

  const supabase = getSupabaseServerClient();
  if (supabase) {
    try {
      await supabase.from("actuariosa_releases").upsert({
        version: newRelease.version,
        title: newRelease.title,
        release_date: newRelease.release_date,
        mandatory: newRelease.mandatory,
        min_version: newRelease.min_version,
        changelog: newRelease.changelog,
        download_url: newRelease.download_url,
        package_size: newRelease.package_size,
        sha256: newRelease.sha256,
      });
    } catch (err) {
      console.error("[DataStore] Error guardando release en Supabase:", err);
    }
  }

  return newRelease;
}

export async function updateGlobalStore(partial: Partial<TelemetriaActuariosa>): Promise<TelemetriaActuariosa> {
  globalStore = {
    ...globalStore,
    ...partial,
    resumen_general: {
      ...globalStore.resumen_general,
      ...(partial.resumen_general || {}),
    },
    distribucion_provincias: {
      ...globalStore.distribucion_provincias,
      ...(partial.distribucion_provincias || {}),
    },
    top_dominios: {
      ...globalStore.top_dominios,
      ...(partial.top_dominios || {}),
    },
    campanas: partial.campanas
      ? [...partial.campanas, ...globalStore.campanas.filter((c) => !partial.campanas!.some((p) => p.id === c.id))]
      : globalStore.campanas,
    leads_respuestas: partial.leads_respuestas
      ? [...partial.leads_respuestas, ...globalStore.leads_respuestas.filter((l) => !partial.leads_respuestas!.some((p) => p.id === l.id))]
      : globalStore.leads_respuestas,
    ultima_actualizacion: new Date().toISOString(),
  };

  // Recalcular tasa de entrega
  const tot = globalStore.resumen_general.total_enviados_campanas;
  const err = globalStore.resumen_general.total_errores_envio;
  if (tot > 0) {
    globalStore.resumen_general.tasa_entrega = Number((((tot - err) / tot) * 100).toFixed(1));
  }

  const supabase = getSupabaseServerClient();
  if (supabase) {
    try {
      await supabase.from("actuariosa_telemetria").upsert({
        id: "current",
        fuente: globalStore.fuente,
        version_sistema: globalStore.version_sistema,
        ultima_actualizacion: globalStore.ultima_actualizacion,
        resumen_general: globalStore.resumen_general,
        distribucion_provincias: globalStore.distribucion_provincias,
        top_dominios: globalStore.top_dominios,
      });

      if (partial.campanas && partial.campanas.length > 0) {
        for (const c of partial.campanas) {
          await supabase.from("actuariosa_campanas").upsert({
            id: c.id || `CAMP-${Date.now()}`,
            nombre: c.nombre,
            fecha: c.fecha,
            total: c.total || 0,
            enviados: c.enviados || 0,
            errores: c.errores || 0,
            asunto: c.asunto || "",
            remitente: c.remitente || "",
          });
        }
      }
    } catch (err) {
      console.error("[DataStore] Error persistiendo telemetría en Supabase:", err);
    }
  }

  return globalStore;
}

export async function addLeadToStore(lead: Omit<LeadRespuesta, "id" | "fecha_respuesta">): Promise<LeadRespuesta> {
  const newLead: LeadRespuesta = {
    ...lead,
    id: `LEAD-${Date.now().toString().slice(-4)}`,
    fecha_respuesta: new Date().toISOString().slice(0, 10),
  };
  globalStore.leads_respuestas.unshift(newLead);

  const supabase = getSupabaseServerClient();
  if (supabase) {
    try {
      await supabase.from("actuariosa_leads").insert({
        id: newLead.id,
        empresa: newLead.empresa,
        correo: newLead.correo,
        ruc: newLead.ruc || "",
        provincia: newLead.provincia || "GUAYAS",
        fecha_contacto: newLead.fecha_contacto,
        fecha_respuesta: newLead.fecha_respuesta,
        estado: newLead.estado,
        servicio_interes: newLead.servicio_interes,
        notas: newLead.notas || "",
      });
    } catch (err) {
      console.error("[DataStore] Error insertando lead en Supabase:", err);
    }
  }

  return newLead;
}

export async function updateLeadStatus(id: string, nuevoEstado: LeadRespuesta["estado"], notas?: string): Promise<boolean> {
  const item = globalStore.leads_respuestas.find((l) => l.id === id);
  if (item) {
    item.estado = nuevoEstado;
    if (notas !== undefined) item.notas = notas;
  }

  const supabase = getSupabaseServerClient();
  if (supabase) {
    try {
      const updateData: Record<string, any> = { estado: nuevoEstado };
      if (notas !== undefined) updateData.notas = notas;
      const { error } = await supabase.from("actuariosa_leads").update(updateData).eq("id", id);
      if (error) {
        console.error("[DataStore] Error actualizando lead en Supabase:", error);
      }
    } catch (err) {
      console.error("[DataStore] Excepción actualizando lead en Supabase:", err);
    }
  }

  return Boolean(item);
}

