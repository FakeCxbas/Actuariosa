/**
 * lib/data-store.ts
 * Estado y almacenamiento centralizado de telemetría de Actuariosa S.A.
 * Pre-poblado con los datos reales consolidados de las depuraciones 2026.
 */

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
    total_enviados_campanas: 9116,
    total_errores_envio: 84,
    tasa_entrega: 99.1,
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
  campanas: [
    {
      id: "CAMP-003",
      nombre: "Campaña Corporativa Guayas — NIC 19",
      fecha: "2026-09-20 14:30",
      total: 4500,
      enviados: 4462,
      errores: 38,
      asunto: "Actualización y Valoración Actuarial de Pasivos Laborales (NIC 19)",
      remitente: "contacto@actuariosa.com",
    },
    {
      id: "CAMP-002",
      nombre: "Prospección Jubilación Patronal y Desahucio",
      fecha: "2026-09-18 11:15",
      total: 3200,
      enviados: 3176,
      errores: 24,
      asunto: "Estudios Actuariales Obligatorios 2026 — Actuariosa S.A.",
      remitente: "gerencia@actuariosa.com",
    },
    {
      id: "CAMP-001",
      nombre: "Presentación de Servicios Actuariales B2B",
      fecha: "2026-09-15 09:40",
      total: 1500,
      enviados: 1478,
      errores: 22,
      asunto: "Propuesta de Consultoría Actuarial y Financiera — Actuariosa S.A.",
      remitente: "contacto@actuariosa.com",
    },
  ],
  leads_respuestas: [
    {
      id: "LEAD-101",
      empresa: "AGROEXPORTADORA DEL LITORAL S.A.",
      correo: "gerencia.financiera@agrolitoral.com.ec",
      ruc: "0992384912001",
      provincia: "GUAYAS",
      fecha_contacto: "2026-09-18",
      fecha_respuesta: "2026-09-19",
      estado: "Cotización Solicitada",
      servicio_interes: "Jubilación Patronal / NIC 19",
      notas: "Requieren valoración actuarial para cierre de estados financieros de 85 colaboradores.",
    },
    {
      id: "LEAD-102",
      empresa: "CONSORCIO INDUSTRIAL ECUATORIANO C.A.",
      correo: "talento.humano@ciecuador.com",
      ruc: "0991827364001",
      provincia: "GUAYAS",
      fecha_contacto: "2026-09-18",
      fecha_respuesta: "2026-09-20",
      estado: "En Negociación",
      servicio_interes: "Estudio Actuarial Completo",
      notas: "Reunión agendada para el jueves 10:00 AM vía Zoom con el Director Financiero.",
    },
    {
      id: "LEAD-103",
      empresa: "LOGÍSTICA & CARGA MARÍTIMA TRANSPORTS S.A.",
      correo: "operaciones@logistimarec.com",
      ruc: "0992918231001",
      provincia: "GUAYAS",
      fecha_contacto: "2026-09-20",
      fecha_respuesta: "2026-09-21",
      estado: "Positivo / Interesado",
      servicio_interes: "Desahucio y Pasivos Laborales",
      notas: "Respondieron solicitando el brochure corporativo y tabla referencial de honorarios.",
    },
    {
      id: "LEAD-104",
      empresa: "FARMACÉUTICA & DISTRIBUCIONES QUITO S.A.",
      correo: "administracion@farmadist.ec",
      ruc: "1792837461001",
      provincia: "PICHINCHA",
      fecha_contacto: "2026-09-15",
      fecha_respuesta: "2026-09-17",
      estado: "Cerrado / Cliente",
      servicio_interes: "Jubilación Patronal / NIC 19",
      notas: "Estudio contratado y nómina cargada en sistema. Certificación entregada.",
    },
    {
      id: "LEAD-105",
      empresa: "TEXTILES Y CONFECCIONES DEL AUSTRO CIA. LTDA.",
      correo: "contabilidad@textilesaustro.com",
      ruc: "0192837462001",
      provincia: "AZUAY",
      fecha_contacto: "2026-09-15",
      fecha_respuesta: "2026-09-16",
      estado: "Positivo / Interesado",
      servicio_interes: "Jubilación Patronal / NIC 19",
      notas: "Piden llamada de consulta sobre implicaciones de la reforma laboral.",
    },
    {
      id: "LEAD-106",
      empresa: "SERVICIOS DE CATERING Y ALIMENTACIÓN CORPORATIVA",
      correo: "info@cateringcorp.com.ec",
      ruc: "0792837461001",
      provincia: "EL ORO",
      fecha_contacto: "2026-09-20",
      fecha_respuesta: "2026-09-21",
      estado: "No Interesado",
      servicio_interes: "Consultoría Financiera",
      notas: "Indican que ya cuentan con perito actuario externo para este ejercicio.",
    },
  ],
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

// Singleton en memoria para Vercel Serverless runtime
let globalStore: TelemetriaActuariosa = { ...initialTelemetryData };

export function getGlobalStore(): TelemetriaActuariosa {
  return globalStore;
}

export function getLatestRelease(): VersionRelease {
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

export function publishNewRelease(rel: Partial<VersionRelease> & { version: string }): VersionRelease {
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

  return newRelease;
}

export function updateGlobalStore(partial: Partial<TelemetriaActuariosa>): TelemetriaActuariosa {
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

  return globalStore;
}

export function addLeadToStore(lead: Omit<LeadRespuesta, "id" | "fecha_respuesta">): LeadRespuesta {
  const newLead: LeadRespuesta = {
    ...lead,
    id: `LEAD-${Date.now().toString().slice(-4)}`,
    fecha_respuesta: new Date().toISOString().slice(0, 10),
  };
  globalStore.leads_respuestas.unshift(newLead);
  return newLead;
}

export function updateLeadStatus(id: string, nuevoEstado: LeadRespuesta["estado"], notas?: string): boolean {
  const item = globalStore.leads_respuestas.find((l) => l.id === id);
  if (item) {
    item.estado = nuevoEstado;
    if (notas !== undefined) item.notas = notas;
    return true;
  }
  return false;
}
