# Guía del Repositorio Actuariosa / ChatGPT Workspace

Este repositorio se encuentra **100% subido y sincronizado** en GitHub:
🔗 **[https://github.com/FakeCxbas/Actuariosa](https://github.com/FakeCxbas/Actuariosa)**

---

## 🚀 Cómo Clonar y Trabajar en tu Otra PC

En tu otra computadora, realiza los siguientes pasos:

### 1. Clonar el repositorio
Abre una terminal (PowerShell o CMD) en la carpeta donde guardas tus proyectos (por ejemplo, `C:\Users\<TuUsuario>\Documents`) y ejecuta:

```bash
git clone https://github.com/FakeCxbas/Actuariosa.git ChatGPT
```

*(Nota: Al poner `ChatGPT` al final del comando, se creará exactamente con el nombre de carpeta `ChatGPT` que tienes en esta PC).*

### 2. Entrar a la carpeta
```bash
cd ChatGPT
```

¡Listo! Tendrás exactamente la misma estructura de carpetas y archivos lista para trabajar:
- `Mx/`: Código fuente de validación y correo masivo.
- `actuariosa/`:
  - `redes-sociales/`: Diseños, fliers y herramientas de redes.
  - `web/`: Aplicación web y plataforma Next.js.
- `actuariosa-web/`: Directorio preservado.
- `estudios-actuariales/`: Módulos de cálculo y memorias actuariales.
- `nexo-inventario/`: Aplicación moderna de inventario Next.js + SQLite.
- `nexo-inventario-python-backup/`: Versión de escritorio en Python.

---

## ⚙️ Reconstrucción de Entornos en la Otra PC

Para mantener el repositorio ultra liviano y rápido (~37 MB), los paquetes pesados (`node_modules`, `.venv`) se reconstruyen en la otra PC según lo que vayas a trabajar:

### Para proyectos Python (`Mx`, `estudios-actuariales`, `nexo-inventario-python-backup`):
```bash
cd <carpeta-del-proyecto>
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### Para proyectos Node.js / Next.js (`actuariosa/web`, `nexo-inventario`):
```bash
cd <carpeta-del-proyecto>
npm install
# o con pnpm si lo prefieres:
pnpm install
```

---

## 🔄 Enviar y Recibir Cambios entre Ambas PCs

- **Para subir cambios que hagas en cualquiera de las PCs:**
  ```bash
  git add .
  git commit -m "descripcion de tus cambios"
  git push
  ```

- **Para descargar los últimos cambios en la otra PC:**
  ```bash
  git pull
  ```
