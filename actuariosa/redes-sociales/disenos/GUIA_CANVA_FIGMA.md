# Guía de Uso y Edición en Figma y Canva · Fliers Actuariosa

Esta guía explica cómo importar, personalizar y exportar los archivos vectoriales SVG creados para las campañas de **Actuariosa**.

---

## Archivos Disponibles en este Paquete

| Archivo | Enfoque de Venta | Dimensiones | Plataformas Recomendadas |
| :--- | :--- | :--- | :--- |
| [`flyer-servicio-jubilacion-1x1.svg`](file:///c:/Users/WinterOS/Documents/ChatGPT/actuariosa/redes-sociales/disenos/feed/flyer-servicio-jubilacion-1x1.svg) | Jubilación Patronal y Desahucio (Art. 188-218) | **1080 × 1080 px** | LinkedIn, Instagram Feed, WhatsApp |
| [`flyer-servicio-asientos-contables-1x1.svg`](file:///c:/Users/WinterOS/Documents/ChatGPT/actuariosa/redes-sociales/disenos/feed/flyer-servicio-asientos-contables-1x1.svg) | Asientos Contables, ORI y NIC 19 | **1080 × 1080 px** | LinkedIn, Contadores Generales |
| [`flyer-servicio-impuestos-diferidos-1x1.svg`](file:///c:/Users/WinterOS/Documents/ChatGPT/actuariosa/redes-sociales/disenos/feed/flyer-servicio-impuestos-diferidos-1x1.svg) | Impuestos Diferidos, LRTI y Conciliación SRI | **1080 × 1080 px** | LinkedIn, Directores Financieros |
| [`flyer-auditorias-cierre-1x1.svg`](file:///c:/Users/WinterOS/Documents/ChatGPT/actuariosa/redes-sociales/disenos/feed/flyer-auditorias-cierre-1x1.svg) | Respaldo y Acompañamiento en Auditorías | **1080 × 1080 px** | LinkedIn, Instagram Feed |
| [`flyer-auditorias-cierre-4x5.svg`](file:///c:/Users/WinterOS/Documents/ChatGPT/actuariosa/redes-sociales/disenos/feed/flyer-auditorias-cierre-4x5.svg) | Auditorías Externas (Retrato Vertical) | **1080 × 1350 px** | LinkedIn Feed Pro (Máxima visibilidad) |
| [`flyer-auditorias-cierre-9x16.svg`](file:///c:/Users/WinterOS/Documents/ChatGPT/actuariosa/redes-sociales/disenos/stories-reels/flyer-auditorias-cierre-9x16.svg) | Auditorías Externas (Stories / Estados) | **1080 × 1920 px** | Instagram Stories, WhatsApp Business |
| [`preview-studio.html`](file:///c:/Users/WinterOS/Documents/ChatGPT/actuariosa/redes-sociales/disenos/preview-studio.html) | Estudio Web Interactivo Local | N/A | Editor de texto en vivo y exportación directa PNG 2x |

---

## Paleta Oficial de Color (Brand Identity)

| Nombre de Color | Código HEX | Código RGB | Uso en el Diseño |
| :--- | :--- | :--- | :--- |
| **Midnight Navy (Fondo Base)** | `#070F1E` | `rgb(7, 15, 30)` | Fondo general oscuro y contraste |
| **Deep Corporate Blue** | `#0A1628` | `rgb(10, 22, 40)` | Tarjetas, contenedores y badges |
| **Nautical Brass / Gold** | `#D4AF37` | `rgb(212, 175, 55)` | Isotipo, números destacados, bordes premium y botón CTA |
| **Gold Light (Brillo)** | `#FDF4DC` | `rgb(253, 244, 220)` | Textos dorados luminosos y detalles |
| **Precision Cyan** | `#38BDF8` | `rgb(56, 189, 248)` | Subtítulos técnicos y enlaces |
| **Pure White** | `#FFFFFF` | `rgb(255, 255, 255)` | Titulares principales de máximo impacto |
| **Muted Slate** | `#94A3B8` | `rgb(148, 163, 184)` | Textos secundarios, descripciones y datos legales |

---

## Tipografías Corporativas (100% Gratuitas en Google Fonts)

Los diseños fueron concebidos con dos familias tipográficas modernas de libre uso comercial:

1. **Titulares e Isotipo:** [Space Grotesk](https://fonts.google.com/specimen/Space+Grotesk) (Pesos: 600 SemiBold, 700 Bold).
   * Proyecta precisión matemática, tecnología y solvencia financiera.
2. **Cuerpo de Texto y Metadatos:** [Plus Jakarta Sans](https://fonts.google.com/specimen/Plus+Jakarta+Sans) o **Inter** (Pesos: 400 Regular, 600 SemiBold, 700 Bold, 800 ExtraBold).
   * Proporciona legibilidad cristalina en pantallas de alta densidad (Retina / OLED).

---

## Cómo importar y editar en Figma

1. Abre **Figma** en tu navegador o app de escritorio.
2. Crea un nuevo archivo de diseño (`New Design File`).
3. **Arrastra y suelta (Drag & Drop)** cualquiera de los archivos `.svg` directamente sobre el lienzo de trabajo.
4. **Estructura de Capas:** Figma preserva las capas y elementos vectoriales:
   * `#capa-fotografia`
   * `#capa-encabezado`
   * `#capa-titular`
   * `#capa-pilares-editoriales`
   * `#capa-pie`
5. **Para editar:**
   * Haz doble clic en cualquier texto para modificar copy, teléfonos o correo.
   * Puedes cambiar colores usando el panel de estilos derecho de Figma.
6. **Para exportar:**
   * Selecciona el Frame del flyer.
   * En la esquina inferior derecha, ve a **Export** -> Elige **PNG** -> Escala **2x** (para obtener 2160×2160 px sin pérdida de calidad).

---

## Cómo importar y editar en Canva

1. Inicia sesión en [Canva.com](https://www.canva.com).
2. Haz clic en **"Crear un diseño"** -> **"Tamaño personalizado"** (1080 × 1080 px).
3. Sube las placas de fondo sin texto ubicadas en `disenos/canva-assets/` o importa directamente los archivos `.svg`.
4. Agrega o ajusta tus cuadros de texto usando las fuentes corporativas (**Plus Jakarta Sans**, **Montserrat**, **Inter**).
5. **Exportación desde Canva:**
   * Clic en **Compartir** -> **Descargar**.
   * Tipo de archivo: **PNG**.

---

## Exportación Instantánea sin Software Externo (`preview-studio.html`)

Si necesitas publicar de inmediato sin abrir Figma ni Canva:
1. Abre [`http://localhost:8085/preview-studio.html`](http://localhost:8085/preview-studio.html) o el archivo local en tu navegador.
2. Selecciona en la barra superior cualquiera de los servicios:
   - **Jubilación (Art. 188-218)**
   - **Asientos Contables**
   - **Impuestos Diferidos**
   - **Cierre & Auditorías**
   - **Stories (9:16)**
3. Haz clic en **"Modificar Textos"** si deseas ajustar titular, teléfonos o enlace.
4. Haz clic en **"Exportar PNG (Retina 2x)"** para descargar la imagen en alta definición (2160×2160 px).
