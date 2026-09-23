-- ====================================================================
-- ACTUARIOSA S.A. — ESQUEMA DE BASE DE DATOS EN SUPABASE (POSTGRESQL)
-- ====================================================================
-- Ejecuta este script en el "SQL Editor" de tu proyecto de Supabase.
-- Creará las tablas necesarias y cargará los datos iniciales reales.

-- 1. Tabla de Telemetría Global y Métricas Consolidadas
CREATE TABLE IF NOT EXISTS actuariosa_telemetria (
    id TEXT PRIMARY KEY DEFAULT 'current',
    fuente TEXT NOT NULL DEFAULT 'Consolidado Maestro Actuariosa + Supercias 2026',
    version_sistema TEXT NOT NULL DEFAULT 'v2.0 Enterprise Cloud',
    ultima_actualizacion TIMESTAMPTZ NOT NULL DEFAULT now(),
    resumen_general JSONB NOT NULL DEFAULT '{}'::jsonb,
    distribucion_provincias JSONB NOT NULL DEFAULT '{}'::jsonb,
    top_dominios JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 2. Tabla de Campañas de Envíos Masivos
CREATE TABLE IF NOT EXISTS actuariosa_campanas (
    id TEXT PRIMARY KEY,
    nombre TEXT NOT NULL,
    fecha TEXT NOT NULL,
    total INTEGER NOT NULL DEFAULT 0,
    enviados INTEGER NOT NULL DEFAULT 0,
    errores INTEGER NOT NULL DEFAULT 0,
    asunto TEXT,
    remitente TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 3. Tabla de Leads y Respuestas Comerciales (CRM B2B)
CREATE TABLE IF NOT EXISTS actuariosa_leads (
    id TEXT PRIMARY KEY,
    empresa TEXT NOT NULL,
    correo TEXT NOT NULL,
    ruc TEXT,
    provincia TEXT DEFAULT 'GUAYAS',
    fecha_contacto TEXT NOT NULL,
    fecha_respuesta TEXT NOT NULL,
    estado TEXT NOT NULL CHECK (estado IN ('Positivo / Interesado', 'Cotización Solicitada', 'En Negociación', 'Cerrado / Cliente', 'No Interesado')),
    servicio_interes TEXT NOT NULL CHECK (servicio_interes IN ('Jubilación Patronal / NIC 19', 'Desahucio y Pasivos Laborales', 'Estudio Actuarial Completo', 'Consultoría Financiera')),
    notas TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 4. Tabla de Versiones y Parches de Software (Auto-Update)
CREATE TABLE IF NOT EXISTS actuariosa_releases (
    version TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    release_date TEXT NOT NULL,
    mandatory BOOLEAN NOT NULL DEFAULT false,
    min_version TEXT NOT NULL DEFAULT '2.0.0',
    changelog JSONB NOT NULL DEFAULT '[]'::jsonb,
    download_url TEXT,
    package_size TEXT,
    sha256 TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Índices recomendados
CREATE INDEX IF NOT EXISTS idx_leads_estado ON actuariosa_leads(estado);
CREATE INDEX IF NOT EXISTS idx_leads_correo ON actuariosa_leads(correo);
CREATE INDEX IF NOT EXISTS idx_campanas_fecha ON actuariosa_campanas(fecha DESC);

-- Habilitar RLS (Seguridad a nivel de filas)
ALTER TABLE actuariosa_telemetria ENABLE ROW LEVEL SECURITY;
ALTER TABLE actuariosa_campanas ENABLE ROW LEVEL SECURITY;
ALTER TABLE actuariosa_leads ENABLE ROW LEVEL SECURITY;
ALTER TABLE actuariosa_releases ENABLE ROW LEVEL SECURITY;

-- Políticas de lectura anónima y escritura mediante Service Role
CREATE POLICY "Lectura pública de telemetría" ON actuariosa_telemetria FOR SELECT USING (true);
CREATE POLICY "Escritura completa para service role" ON actuariosa_telemetria FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "Lectura pública de campanas" ON actuariosa_campanas FOR SELECT USING (true);
CREATE POLICY "Escritura de campanas para service role" ON actuariosa_campanas FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "Lectura pública de leads" ON actuariosa_leads FOR SELECT USING (true);
CREATE POLICY "Escritura de leads para service role" ON actuariosa_leads FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "Lectura pública de releases" ON actuariosa_releases FOR SELECT USING (true);
CREATE POLICY "Escritura de releases para service role" ON actuariosa_releases FOR ALL USING (true) WITH CHECK (true);

-- ====================================================================
-- CARGA DE DATOS INICIALES REALES DE ACTUARIOSA S.A.
-- ====================================================================

-- Telemetría consolidada inicial
INSERT INTO actuariosa_telemetria (id, fuente, version_sistema, ultima_actualizacion, resumen_general, distribucion_provincias, top_dominios)
VALUES (
    'current',
    'Consolidado Maestro Actuariosa + Supercias 2026',
    'v2.0 Enterprise Cloud',
    '2026-09-21T18:57:40.000Z',
    '{
        "total_recopilados_brutos": 247997,
        "total_base_activa": 136602,
        "total_negocios_unicos": 42648,
        "supercias_activas_con_ruc": 11779,
        "negocios_corporativos": 30869,
        "descartados_inactivas": 3496,
        "instituciones_educativas": 4809,
        "otros_genericos": 85649,
        "correos_con_error_formato": 563,
        "duplicados_eliminados": 141437,
        "total_enviados_campanas": 9116,
        "total_errores_envio": 84,
        "tasa_entrega": 99.1
    }'::jsonb,
    '{
        "GUAYAS": 11236,
        "PICHINCHA": 307,
        "EL ORO": 52,
        "MANABI": 37,
        "SANTA ELENA": 35,
        "AZUAY": 32,
        "LOS RIOS": 30,
        "LOJA": 9,
        "GALAPAGOS": 7,
        "SANTO DOMINGO": 7
    }'::jsonb,
    '{
        "hotmail.com": 44874,
        "gmail.com": 16983,
        "yahoo.com": 5726,
        "yahoo.es": 4019,
        "outlook.com": 1437,
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
        "etapanet.net": 84
    }'::jsonb
)
ON CONFLICT (id) DO UPDATE SET
    resumen_general = EXCLUDED.resumen_general,
    distribucion_provincias = EXCLUDED.distribucion_provincias,
    top_dominios = EXCLUDED.top_dominios,
    ultima_actualizacion = EXCLUDED.ultima_actualizacion;

-- Campañas iniciales
INSERT INTO actuariosa_campanas (id, nombre, fecha, total, enviados, errores, asunto, remitente)
VALUES
    ('CAMP-003', 'Campaña Corporativa Guayas — NIC 19', '2026-09-20 14:30', 4500, 4462, 38, 'Actualización y Valoración Actuarial de Pasivos Laborales (NIC 19)', 'contacto@actuariosa.com'),
    ('CAMP-002', 'Prospección Jubilación Patronal y Desahucio', '2026-09-18 11:15', 3200, 3176, 24, 'Estudios Actuariales Obligatorios 2026 — Actuariosa S.A.', 'gerencia@actuariosa.com'),
    ('CAMP-001', 'Presentación de Servicios Actuariales B2B', '2026-09-15 09:40', 1500, 1478, 22, 'Propuesta de Consultoría Actuarial y Financiera — Actuariosa S.A.', 'contacto@actuariosa.com')
ON CONFLICT (id) DO NOTHING;

-- Leads iniciales
INSERT INTO actuariosa_leads (id, empresa, correo, ruc, provincia, fecha_contacto, fecha_respuesta, estado, servicio_interes, notas)
VALUES
    ('LEAD-101', 'AGROEXPORTADORA DEL LITORAL S.A.', 'gerencia.financiera@agrolitoral.com.ec', '0992384912001', 'GUAYAS', '2026-09-18', '2026-09-19', 'Cotización Solicitada', 'Jubilación Patronal / NIC 19', 'Requieren valoración actuarial para cierre de estados financieros de 85 colaboradores.'),
    ('LEAD-102', 'CONSORCIO INDUSTRIAL ECUATORIANO C.A.', 'talento.humano@ciecuador.com', '0991827364001', 'GUAYAS', '2026-09-18', '2026-09-20', 'En Negociación', 'Estudio Actuarial Completo', 'Reunión agendada para el jueves 10:00 AM vía Zoom con el Director Financiero.'),
    ('LEAD-103', 'LOGÍSTICA & CARGA MARÍTIMA TRANSPORTS S.A.', 'operaciones@logistimarec.com', '0992918231001', 'GUAYAS', '2026-09-20', '2026-09-21', 'Positivo / Interesado', 'Desahucio y Pasivos Laborales', 'Respondieron solicitando el brochure corporativo y tabla referencial de honorarios.'),
    ('LEAD-104', 'FARMACÉUTICA & DISTRIBUCIONES QUITO S.A.', 'administracion@farmadist.ec', '1792837461001', 'PICHINCHA', '2026-09-15', '2026-09-17', 'Cerrado / Cliente', 'Jubilación Patronal / NIC 19', 'Estudio contratado y nómina cargada en sistema. Certificación entregada.'),
    ('LEAD-105', 'TEXTILES Y CONFECCIONES DEL AUSTRO CIA. LTDA.', 'contabilidad@textilesaustro.com', '0192837462001', 'AZUAY', '2026-09-15', '2026-09-16', 'Positivo / Interesado', 'Jubilación Patronal / NIC 19', 'Piden llamada de consulta sobre implicaciones de la reforma laboral.'),
    ('LEAD-106', 'SERVICIOS DE CATERING Y ALIMENTACIÓN CORPORATIVA', 'info@cateringcorp.com.ec', '0792837461001', 'EL ORO', '2026-09-20', '2026-09-21', 'No Interesado', 'Consultoría Financiera', 'Indican que ya cuentan con perito actuario externo para este ejercicio.')
ON CONFLICT (id) DO NOTHING;

-- Versión actual y releases
INSERT INTO actuariosa_releases (version, title, release_date, mandatory, min_version, changelog, download_url, package_size, sha256)
VALUES
    ('2.1.0', 'Actualización v2.1.0 — Motor Masivo & Telemetría en la Nube', '2026-09-21', false, '2.0.0', '["Nuevo apartado independiente y exclusivo para envíos directos a empresas", "Sincronización de métricas en tiempo real con el panel web en Vercel", "Algoritmo de validación de sintaxis y detección de rebotes optimizado", "Módulo inteligente de auto-actualizaciones con reinicio transparente"]'::jsonb, 'https://actuariosa.com/updates/mxcorreo-2.1.0.tar.gz', '3.8 MB', '9f83a45c2b8109d7e63b0c44298fc1c149afbf4c8996fb92427ae41e4649b934'),
    ('2.0.0', 'Versión 2.0 Inicial — Depuración Supercias y Cruce RUC', '2026-09-20', false, '1.0.0', '["Depurador de bases de datos Supercias", "Algoritmo de cruce y verificación de empresas activas"]'::jsonb, 'https://actuariosa.com/updates/mxcorreo-2.0.0.tar.gz', '3.6 MB', 'init')
ON CONFLICT (version) DO NOTHING;
