# Actuariosa

Sitio web de presentación para una consultora actuarial ecuatoriana, desarrollado por Sebastián Zambrano con React y TypeScript.

## Qué resuelve

Presenta los servicios de jubilación patronal, desahucio, asientos contables e impuestos diferidos. El visitante puede consultar preguntas frecuentes y preparar una solicitud de cotización para enviarla por WhatsApp o correo.

## Implementación

- Diseño adaptable a móviles y escritorio.
- Formulario de cotización con validación y mensaje revisable antes de enviarlo.
- Componentes reutilizables, navegación por secciones y preguntas frecuentes.
- Animaciones que respetan la preferencia de movimiento reducido.
- Metadatos para compartir enlaces y exportación estática para Vercel.

Tecnologías: React 19, TypeScript, Vinext, Vite, CSS y componentes de interfaz con Tailwind CSS.

## Ejecutar localmente

Requiere Node.js 22.13 o superior y pnpm.

```sh
pnpm install --frozen-lockfile
pnpm dev
```

Para generar la versión estática:

```sh
pnpm build:vercel
```

La salida se genera en `dist/client`. `vercel.json` contiene la configuración de publicación. Este repositorio no incluye credenciales ni identificadores de las cuentas de despliegue.

## Alcance y privacidad

El sitio está publicado en Vercel; su contenido lo identifica como una propuesta de demostración. No procesa cálculos actuariales ni guarda los datos del formulario en una base de datos. WhatsApp y correo se abren por acción del visitante.

Se publica únicamente el código y los recursos de la web. No se incluyen informes actuariales, documentos internos, listas de contactos ni datos de clientes.

## Créditos

Desarrollo: [Sebastián Zambrano](https://github.com/FakeCxbas).

La identidad de Actuariosa pertenece a su titular. Las imágenes ilustrativas generadas no representan al personal ni las instalaciones reales de la empresa. Fotografía de arquitectura: Unsplash, `photo-1486406146926-c627a92ad1ab`. Referencias de contenido y diseño: Actuaria e Iceberg Actuarial, sin atribuir sus clientes, certificaciones o resultados a este proyecto.
