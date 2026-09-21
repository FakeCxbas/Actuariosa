# Actuariosa — Panel Web de Monitoreo Gerencial

Panel ejecutivo en la nube diseñado para desplegarse en **Vercel**, permitiendo a la gerencia de **Actuariosa S.A.** supervisar en tiempo real el inventario de correos, las empresas depuradas en la Superintendencia de Compañías, el rendimiento de las campañas B2B y las respuestas comerciales de los clientes.

---

## 🚀 Despliegue en Vercel en 2 Minutos

### Opción 1: Conectar Repositorio de GitHub (Recomendada)
1. Sube los cambios a tu repositorio de GitHub:
   ```bash
   git add .
   git commit -m "feat: Panel web gerencial y flujo de datos para Vercel"
   git push origin main
   ```
2. Entra a [vercel.com](https://vercel.com) e inicia sesión.
3. Haz clic en **"Add New Project"** e importa este repositorio.
4. En **Root Directory**, selecciona la carpeta: `panel-web`.
5. En **Environment Variables** (opcional pero recomendado):
   - `SYNC_API_KEY`: Tu clave secreta para sincronizar (ej: `actuariosa-telemetry-key-2026`).
6. Haz clic en **"Deploy"**. Vercel generará tu URL pública (ejemplo: `https://actuariosa-panel.vercel.app` o puedes conectar tu propio dominio como `panel.actuariosa.com`).

### Opción 2: Despliegue Directo con Vercel CLI
```bash
cd panel-web
npx -y vercel
```

---

## 🔄 Flujo de Datos de Extremo a Extremo

```
[Fuentes Locales]                   [Transmisión Segura]            [Nube Vercel]
Excel, CSV, Bases 2026               sync_telemetria.py              Endpoint Serverless
        ↓                                    ↓                                ↓
Depurador Supercias   ──(resumen)──>  POST /api/sync   ──(HTTPS)──>  Almacenamiento Cloud
        ↓                                    ↑                                ↓
MxCorreo (App Desktop) ──(bitácora)───> [☁️ Sincronizar]               Dashboard del Jefe
```

1. **Generación Local:**  
   Al ejecutar `depurar_correos_supercias.py` o al enviar correos con la aplicación desktop `MxCorreo`, se generan automáticamente los archivos de métricas y bitácoras (`Resumen_Depuracion_Supercias.json`, `bitacora_envios.csv`).
2. **Sincronización:**  
   - **Desde la app `MxCorreo`:** Haz clic en el botón **"☁️ Sincronizar con Panel Web"** en la barra lateral.
   - **Por comando de consola:** Ejecuta `python sync_telemetria.py --url https://tu-panel.vercel.app/api/sync`.
   - **Desde el propio panel web:** Haz clic en **"Cargar Reporte JSON"** y arrastra el archivo directamente al navegador.
3. **Supervisión del Jefe:**  
   El jefe puede ingresar desde su teléfono móvil, tablet o laptop a la URL de Vercel y ver las métricas consolidadas en tiempo real.

---

## 📊 Indicadores Clave del Panel (KPIs)

- **Inventario Bruto Total:** 247,997 correos recopilados a través de 69 archivos de diversas fuentes.
- **Base Activa Limpia 2026:** 136,602 correos normalizados sin duplicados básicos.
- **Empresas 100% Funcionales:** 42,648 negocios corporativos y sociedades activas en la Superintendencia de Compañías.
- **Supercias Activas con RUC:** 11,779 empresas con razón social, RUC y estado legal activo validado.
- **Correos Enviados y Tasa de Entrega:** Monitoreo del porcentaje de entrega (99.1%) y rebotes prevenidos.
- **Embudo de Conversión Comercial:** Embudo visual desde la recolección cruda hasta las respuestas de contratación actuarial (Jubilación Patronal / NIC 19).
- **CRM de Respuestas:** Registro de empresas que responden a las propuestas, clasificación por estado (`Cotización Solicitada`, `En Negociación`, `Cerrado`) y exportación a CSV.

---

## 🛠️ Ejecución Local

Para probar el panel en tu propia computadora:

```bash
cd panel-web
npm install
npm run dev
```

Abre [http://localhost:3000](http://localhost:3000) en tu navegador.
