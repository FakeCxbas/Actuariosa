# Guía para Subir a GitHub y Trabajar en Otra PC

Este repositorio está completamente preparado y comprometido localmente como un **Monorepo** con un peso optimizado de **~37 MB**.

---

## 1. Crear el repositorio en GitHub
1. Abre tu navegador e ingresa a: **[https://github.com/new](https://github.com/new)**
2. En **Repository name**, pon el nombre que prefieras (por ejemplo: `workspace-chatgpt` o `ChatGPT`).
3. En visibilidad, selecciona **Private** (Privado) para proteger tus proyectos.
4. **IMPORTANTE:** No marques ninguna casilla ("Add a README file", "Add .gitignore", "Choose a license"). El repositorio debe crearse **completamente vacío**.
5. Haz clic en **Create repository**.

---

## 2. Vincular y Subir desde esta PC
Una vez creado el repositorio en GitHub, abre la terminal en esta carpeta (`c:\Users\WinterOS\Documents\ChatGPT`) y ejecuta:

```bash
git remote add origin https://github.com/FakeCxbas/<NOMBRE-DE-TU-REPO>.git
git push -u origin main
```

*(Por ejemplo, si le pusiste `workspace-chatgpt`:)*
```bash
git remote add origin https://github.com/FakeCxbas/workspace-chatgpt.git
git push -u origin main
```

---

## 3. Clonar y Trabajar en la Otra PC
En tu otra computadora:
1. Abre una terminal en la carpeta donde guardas tus proyectos (por ejemplo, `C:\Users\...\Documents`).
2. Ejecuta:
```bash
git clone https://github.com/FakeCxbas/<NOMBRE-DE-TU-REPO>.git ChatGPT
```
3. Entra a la carpeta:
```bash
cd ChatGPT
```

¡Tendrás de inmediato la misma estructura exacta con todos los proyectos organizados!

### Estructura disponible en la otra PC:
- `Mx/`: Código fuente de validación y correo masivo.
- `actuariosa/`: 
  - `redes-sociales/`: Diseños, fliers y herramientas de redes.
  - `web/`: Aplicación web y plataforma Next.js.
- `actuariosa-web/`: Directorio preservado.
- `estudios-actuariales/`: Módulos de cálculo y memorias actuariales.
- `nexo-inventario/`: Aplicación moderna de inventario Next.js + SQLite.
- `nexo-inventario-python-backup/`: Versión de escritorio en Python.

---

## 4. Reconstrucción rápida de dependencias en la otra PC
Como las carpetas temporales y pesadas (`node_modules`, `.venv`) se ignoraron para mantener el repositorio ultra liviano y rápido:

- **Para proyectos de Python (`Mx`, `estudios-actuariales`, etc.):**
  ```bash
  python -m venv .venv
  .venv\Scripts\activate
  pip install -r requirements.txt
  ```

- **Para proyectos Node / Next.js (`actuariosa/web`, `nexo-inventario`):**
  ```bash
  npm install
  # o si usas pnpm
  pnpm install
  ```

---

## 5. Respaldo de configuraciones previas
Tus historiales anteriores de Git de los subrepositorios (`actuariosa`, `nexo-inventario`, etc.) quedaron archivados y respaldados en la carpeta local `_subrepos_git_backup/` para máxima seguridad.
