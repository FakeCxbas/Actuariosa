"""Aplicación portable Windows. Interfaz local para campana.py, sin servicios externos añadidos."""
from __future__ import annotations

import argparse
from contextlib import redirect_stdout
import copy
import json
import os
import subprocess
from abrir_archivo import open_local_path
from pathlib import Path
import queue
import smtplib
import sys
import tempfile
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
from tkinter.scrolledtext import ScrolledText

import campana
from dialogos_importacion import ExcelDialog, PasteDialog, DetectionDialog
from importar_contactos import EXCEL_EXTENSIONS, load_import, save_import
from importacion_automatica import EXTENSIONS, ImportCancelled, scan_files
from resultados_interfaz import FILTERS, LABELS, export_lists, matches
from centro_campanas import import_report, OFFER_TEMPLATE


def resources():
    return Path(__file__).resolve().parent


def default_data_dir():
    base = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else resources()
    return base / "datos"


def save_json_atomic(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    # Archivos propios de la aplicación; cambio atómico para que no explote epicamente
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, prefix="config_", suffix=".tmp", delete=False) as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        temporary = Path(stream.name)
    os.replace(temporary, path)


class QueueWriter:
    def __init__(self, events):
        self.events = events

    def write(self, text):
        if text:
            self.events.put(("log", text))
        return len(text)

    def flush(self):
        pass


class ConfirmSend(simpledialog.Dialog):
    def __init__(self, parent, prompt, detail):
        self.prompt, self.detail = prompt, detail
        self.result = ""
        super().__init__(parent, "Confirmar envío REAL")

    def body(self, master):
        ttk.Label(master, text="Esto sí enviará correos. Revisa el contenido y los destinatarios.",
                  font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=8)
        text = ScrolledText(master, width=85, height=19, wrap="word")
        text.pack(fill="both", expand=True)
        text.insert("1.0", self.detail)
        text.configure(state="disabled")
        ttk.Label(master, text=self.prompt, wraplength=650).pack(anchor="w", pady=10)
        self.entry = ttk.Entry(master, width=65)
        self.entry.pack(fill="x")
        return self.entry

    def buttonbox(self):
        box = ttk.Frame(self)
        box.pack(pady=12)
        ttk.Button(box, text="Autorizar este envío", command=self.ok).pack(side="left", padx=8)
        ttk.Button(box, text="Cancelar, no enviar", command=self.cancel).pack(side="left", padx=8)
        self.bind("<Escape>", self.cancel)

    def apply(self):
        self.result = self.entry.get()


class App:
    def __init__(self, root, data_dir):
        self.root, self.data_dir = root, Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.events = queue.Queue()
        self.stop_event = threading.Event()
        self.busy = False
        self.last_folder = None
        self.form = {}
        self.approvals = {}
        self.attachments = []
        self.action_buttons = []
        self.pending_dialog = None
        self.rows = []
        self.filtered = []
        self.page = 0
        self.search_job = None
        self.root.title("MxCorreo — Centro de correos")
        width = min(1200, root.winfo_screenwidth() - 80)
        height = min(850, root.winfo_screenheight() - 80)
        root.geometry(f"{width}x{height}")
        root.minsize(960, 680)
        root.protocol("WM_DELETE_WINDOW", self.close)
        style = ttk.Style(root)
        style.theme_use("clam")
        style.configure("TFrame", background="#f5f7fa")
        style.configure("TLabel", background="#f5f7fa", foreground="#253348", font=("Segoe UI", 10))
        style.configure("TButton", padding=(12, 7), font=("Segoe UI", 10), background='white', foreground='#253348',
                        bordercolor='#d7e1ec', lightcolor='white', darkcolor='white', relief='flat')
        style.map('TButton', background=[('active', '#e8f0fb'), ('disabled', '#eef1f5')], foreground=[('disabled', '#8796a8')])
        style.configure("TNotebook.Tab", padding=(14, 9), font=("Segoe UI", 10))
        style.configure("Primary.TButton", background="#1459ad", foreground="white", bordercolor='#1459ad', lightcolor='#1459ad', darkcolor='#1459ad')
        style.map("Primary.TButton", background=[("active", "#104889"), ("disabled", "#8b9aaf")])
        style.configure("Treeview", rowheight=27, font=("Segoe UI", 9), borderwidth=0, fieldbackground='white')
        style.configure('TNotebook', background='#f5f7fa', borderwidth=0)
        style.configure('TNotebook.Tab', padding=(24, 12), background='#e5ebf2', foreground='#43566c', lightcolor='#e5ebf2', darkcolor='#e5ebf2', borderwidth=0)
        style.map('TNotebook.Tab', background=[('selected', '#ffffff')], foreground=[('selected', '#1459ad')])
        style.configure('Card.TFrame', background='white')
        style.configure('Card.TLabel', background='white', foreground='#52647a')
        style.configure('Section.TLabel', font=('Segoe UI', 15, 'bold'), foreground='#172d48')
        style.configure('Metric.TLabel', background='white', foreground='#172d48', font=('Segoe UI', 24, 'bold'))
        style.configure('Treeview.Heading', background='#e5edf7', foreground='#172d48', padding=8, font=('Segoe UI', 10, 'bold'))
        style.map('Treeview', background=[('selected', '#d9eaff')], foreground=[('selected', '#143554')])
        top = ttk.Frame(root, padding=(22, 14))
        top.pack(fill="x")
        ttk.Label(top, text="Envío Automático de Correos", font=("Segoe UI", 23, "bold")).pack(side="left")
        ttk.Label(top, text="Contactos · Campañas · Envíos", foreground="#52647a").pack(side="right")
        self.book = ttk.Notebook(root)
        self.book.pack(fill="both", expand=True, padx=18)
        self.list_tab = self.tab("Listas y resultados")
        self.message_tab = self.tab("Mensaje")
        self.account_tab = self.tab("Cuenta de correo")
        self.send_tab = self.tab("Envío autorizado")
        self.build_list()
        self.build_message()
        self.build_account()
        self.build_send()
        bottom = ttk.Frame(root, padding=(18, 10))
        bottom.pack(fill="x")
        self.status = tk.StringVar(value="Carga tus archivos para empezar. No necesitas configurar una cuenta para filtrar correos.")
        ttk.Label(bottom, textvariable=self.status, wraplength=700).pack(side="left", fill="x", expand=True)
        self.stop_button = ttk.Button(bottom, text="Detener", command=self.stop, state="disabled")
        self.stop_button.pack(side="right")
        self.progress = ttk.Progressbar(root, mode="indeterminate")
        self.progress.pack(fill="x", padx=18, pady=(0, 12))
        self.load_initial()
        if not (self.data_dir / 'configuracion.json').exists():
            self.gmail_preset()
        session = self.data_dir / 'sesion.json'
        if session.exists():
            try:
                saved = json.loads(session.read_text(encoding='utf-8'))
                for key in ('lista', 'exclusiones', 'autorizados', 'audiencia'):
                    if isinstance(saved.get(key), str):
                        self.form[key].set(saved[key])
                if self.form['lista'].get() and Path(self.form['lista'].get()).exists():
                    path = Path(self.form['lista'].get())
                    root.after(200, lambda: self.local_task('imported', lambda: (path, load_import(path, self.stop_event), 'Última lista guardada'), 'Recuperando tus contactos…'))
            except (ValueError, OSError):
                self.status.set('No se recuperó la sesión. Puedes volver a cargar tus archivos.')
        root.after(100, self.poll)

    def tab(self, title):
        outer = ttk.Frame(self.book)
        self.book.add(outer, text=title)
        canvas = tk.Canvas(outer, highlightthickness=0, background="#f5f7fa")
        scroll = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        scroll.pack(side="right", fill="y")
        canvas.pack(fill="both", expand=True)
        canvas.configure(yscrollcommand=scroll.set)
        inner = ttk.Frame(canvas, padding=18)
        window = canvas.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(window, width=e.width))
        def wheel(event):
            widget = event.widget
            if isinstance(widget, (ttk.Treeview, tk.Text, tk.Listbox, ttk.Combobox)):
                return
            while widget is not None:
                if widget == outer:
                    canvas.yview_scroll(-int(event.delta / 120), 'units')
                    return 'break'
                widget = getattr(widget, 'master', None)
        self.root.bind('<MouseWheel>', wheel, add='+')
        return inner

    def field(self, parent, key, label, value="", choices=None, browse=None, show=None):
        line = ttk.Frame(parent)
        line.pack(fill="x", pady=4)
        ttk.Label(line, text=label, width=25).pack(side="left")
        var = tk.StringVar(value=value)
        self.form[key] = var
        if choices:
            widget = ttk.Combobox(line, textvariable=var, values=choices, state="readonly")
        else:
            widget = ttk.Entry(line, textvariable=var, show=show or "")
        widget.pack(side="left", fill="x", expand=True)
        if browse:
            ttk.Button(line, text="Elegir…", command=lambda: self.choose_file(key, browse)).pack(side="left", padx=(8, 0))
        return var

    def button(self, parent, text, command, primary=False):
        item = ttk.Button(parent, text=text, command=command, style="Primary.TButton" if primary else "TButton")
        item.pack(side="left", padx=(0, 8), pady=8)
        self.action_buttons.append(item)
        return item

    def build_list(self):
        ttk.Label(self.list_tab, text="Tus listas, en un solo lugar", style='Section.TLabel').pack(anchor="w")
        ttk.Label(self.list_tab, text="Carga Excel, CSV o TXT. Encontramos las columnas de correo y tú confirmas qué importar.").pack(anchor='w', pady=(4, 10))
        imports = ttk.Frame(self.list_tab)
        imports.pack(fill="x")
        self.button(imports, "Cargar archivos…", self.auto_files, True)
        self.button(imports, "Cargar carpeta…", self.auto_folder)
        self.button(imports, "Pegar correos…", self.paste_contacts)
        self.button(imports, 'Selección manual de Excel…', self.import_excel)
        self.import_info = tk.StringVar(value="Puedes seleccionar varios archivos a la vez. Los originales no se modifican.")
        ttk.Label(self.list_tab, textvariable=self.import_info, wraplength=900).pack(anchor="w", pady=3)
        continuation = ttk.Frame(self.list_tab)
        continuation.pack(fill='x')
        self.button(continuation, 'Importar revisión anterior…', self.open_review)
        self.button(continuation, 'Preparar mi oferta →', lambda: self.book.select(1))
        self.form['lista'] = tk.StringVar()
        self.form['columna'] = tk.StringVar(value='correo')
        advanced = ttk.Frame(self.list_tab)
        self.button(imports, 'Opciones', lambda: advanced.pack_forget() if advanced.winfo_manager() else advanced.pack(fill='x', before=buttons))
        self.field(advanced, "exclusiones", "Bajas / exclusiones", browse=[("Texto", "*.txt")])
        ttk.Button(advanced, text='Abrir una lista guardada…', command=self.saved_list).pack(anchor='w', pady=4)
        cards = ttk.Frame(self.list_tab)
        cards.pack(fill='x', pady=12)
        self.metrics = {}
        for i, (key, label, color) in enumerate([('total', 'Entradas', '#172d48'), ('APTO_DNS', 'Dominio apto', '#187757'), ('INVALIDO', 'Con problemas', '#b23b40'), ('pending', 'Por revisar', '#9a6516'), ('duplicates', 'Repetidas', '#6354a3')]):
            cards.columnconfigure(i, weight=1, uniform='metrics')
            card = ttk.Frame(cards, style='Card.TFrame', padding=12)
            card.grid(row=0, column=i, sticky='ew', padx=(0, 8 if i < 4 else 0))
            self.metrics[key] = tk.StringVar(value='0')
            ttk.Label(card, textvariable=self.metrics[key], style='Metric.TLabel', foreground=color).pack(anchor='w')
            ttk.Label(card, text=label, style='Card.TLabel').pack(anchor='w')
        buttons = ttk.Frame(self.list_tab)
        buttons.pack(fill="x")
        self.button(buttons, "Revisar dominios", lambda: self.launch("revisar"), True)
        self.button(buttons, 'Exportar listas CSV…', self.export_csv)
        self.button(buttons, "Simular mensaje", lambda: self.launch("simular"))
        self.button(buttons, "Ver un ejemplo", self.example)
        self.summary = tk.StringVar(value="1. Carga tus archivos    2. Revisa los dominios    3. Exporta las listas")
        ttk.Label(self.list_tab, textvariable=self.summary, wraplength=920).pack(anchor="w", pady=(6, 10))
        filters = ttk.Frame(self.list_tab)
        filters.pack(fill='x', pady=(0, 8))
        ttk.Label(filters, text='Buscar').pack(side='left')
        self.search = tk.StringVar()
        ttk.Entry(filters, textvariable=self.search, width=32).pack(side='left', padx=8)
        self.category = tk.StringVar(value='Todos')
        ttk.Combobox(filters, textvariable=self.category, values=FILTERS, state='readonly', width=20).pack(side='left')
        self.search.trace_add('write', self.schedule_filter)
        self.category.trace_add('write', self.schedule_filter)
        tableframe = ttk.Frame(self.list_tab)
        tableframe.pack(fill="both", expand=True)
        self.table = ttk.Treeview(tableframe, columns=("correo", "estado", "motivo"), show="headings", height=6)
        for key, title, width in (("correo", "Correo", 270), ("estado", "Resultado DNS", 135), ("motivo", "Explicación", 460)):
            self.table.heading(key, text=title)
            self.table.column(key, width=width, minwidth=80)
        scrollbar = ttk.Scrollbar(tableframe, orient="vertical", command=self.table.yview)
        self.table.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.table.pack(fill="both", expand=True)
        self.table.bind("<Double-1>", self.row_detail)
        for state, color in [('', '#ffffff'), ('APTO_DNS', '#edf8f3'), ('INVALIDO', '#fff0f0'), ('REVISAR', '#fff7e7')]:
            self.table.tag_configure(state or 'pending', background=color)
        paging = ttk.Frame(self.list_tab)
        paging.pack(fill='x', pady=6)
        self.page_info = tk.StringVar(value='Sin entradas')
        ttk.Label(paging, textvariable=self.page_info).pack(side='left')
        ttk.Button(paging, text='Siguiente ›', command=lambda: self.change_page(1)).pack(side='right')
        ttk.Button(paging, text='‹ Anterior', command=lambda: self.change_page(-1)).pack(side='right', padx=8)
        ttk.Label(self.list_tab, text="Dominio apto no confirma que exista el buzón. Importar, revisar y exportar no envían mensajes.").pack(anchor="w", pady=6)
        results = ttk.Frame(self.list_tab)
        results.pack(fill="x")
        ttk.Button(results, text="Abrir informe", command=lambda: self.open_result("informe.html")).pack(side="left", padx=(0, 8))
        ttk.Button(results, text="Ver muestra del mensaje", command=lambda: self.open_result("vista_previa.txt")).pack(side="left", padx=(0, 8))
        ttk.Button(results, text="Abrir carpeta de resultados", command=self.open_results).pack(side="left")
        self.log = ScrolledText(self.list_tab, height=4, wrap="word", font=("Consolas", 9))
        ttk.Button(results, text='Detalles técnicos', command=lambda: self.log.pack_forget() if self.log.winfo_manager() else self.log.pack(fill='x', pady=8)).pack(side='right')
        self.log.configure(state="disabled")

    def build_message(self):
        ttk.Label(self.message_tab, text="Prepara el contenido que apruebe la empresa.", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(0, 10))
        self.field(self.message_tab, "campana_id", "Identificador del comunicado")
        ttk.Label(self.message_tab, text="Mantén el mismo identificador para continuar un envío. Uno nuevo puede volver a escribir a todos.", wraplength=880).pack(anchor="w", pady=5)
        self.field(self.message_tab, "asunto", "Asunto")
        ttk.Label(self.message_tab, text="Mensaje de texto:").pack(anchor="w", pady=(10, 5))
        self.body = ScrolledText(self.message_tab, height=10, wrap="word", font=("Segoe UI", 10))
        self.body.pack(fill="both", expand=True)
        ttk.Label(self.message_tab, text="Opcional: ${nombre}, ${correo} y ${empresa}. Nombre y empresa se toman del CSV o de las columnas elegidas al importar Excel.", wraplength=880).pack(anchor="w", pady=6)
        self.field(self.message_tab, "html", "Archivo HTML (opcional)", browse=[("HTML", "*.html *.htm")])
        ttk.Label(self.message_tab, text="Adjuntos (se enviarán completos a cada destinatario):").pack(anchor="w", pady=(8, 4))
        self.attachment_list = tk.Listbox(self.message_tab, height=3, font=("Segoe UI", 9))
        self.attachment_list.pack(fill="x")
        buttons = ttk.Frame(self.message_tab)
        buttons.pack(fill="x")
        self.button(buttons, "Añadir adjuntos", self.add_attachments)
        self.button(buttons, "Quitar de la lista", self.remove_attachment)
        self.button(buttons, "Guardar configuración", self.save_settings)
        self.button(buttons, 'Plantilla de servicios', self.offer_template)
        self.field(self.message_tab, 'baja_correo', 'Correo para recibir bajas')
        ttk.Label(self.message_tab, text='Se añade una instrucción de baja al texto y al HTML. Las solicitudes se atienden manualmente en «Bajas».', wraplength=850).pack(anchor='w', pady=6)

    def build_account(self):
        ttk.Label(self.account_tab, text="Estos datos debe confirmarlos el administrador del correo.", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(0, 10))
        ttk.Label(self.account_tab, text="Puedes revisar listas sin completar esta pestaña. El dominio propio no indica por sí solo el servidor de envío.", wraplength=880).pack(anchor="w", pady=(0, 10))
        self.field(self.account_tab, "remitente", "Correo remitente")
        self.field(self.account_tab, "nombre", "Nombre de la empresa")
        self.field(self.account_tab, "responder_a", "Responder a (opcional)")
        self.field(self.account_tab, "host", "Servidor SMTP")
        self.field(self.account_tab, "puerto", "Puerto", "587")
        self.field(self.account_tab, "seguridad", "Cifrado", "starttls", choices=("starttls", "ssl"))
        self.field(self.account_tab, "autenticacion", "Autenticación", "password", choices=("password", "oauth2", "none"))
        self.field(self.account_tab, "usuario", "Usuario SMTP")
        ttk.Label(self.account_tab, text="La contraseña o token se pedirá en una ventana solo después de confirmar un envío. No se guarda.", wraplength=880, foreground="#1459ad").pack(anchor="w", pady=10)
        ttk.Label(self.account_tab, text="password: credencial SMTP autorizada. oauth2: token ya emitido (sin renovación automática).\nnone: solo relay expresamente autorizado. Siempre se exige TLS.", wraplength=880).pack(anchor="w", pady=5)
        actions = ttk.Frame(self.account_tab)
        actions.pack(fill="x")
        self.button(actions, "Guardar configuración", self.save_settings)
        self.button(actions, "Cargar configuración JSON…", self.import_settings)
        self.button(actions, 'Configurar Gmail', self.gmail_preset)
        ttk.Label(self.account_tab, text='Gmail: usa una contraseña de aplicación, si el administrador la permite; no tu contraseña habitual.\nOAuth2 admite un token emitido por el administrador, sin inicio de sesión Google ni renovación automática.\nLos límites de Google incluyen también lo enviado fuera de esta aplicación. No hay envío ilimitado.', wraplength=850).pack(anchor='w', pady=8)
        ttk.Label(self.account_tab, text="La copia portable no trae cuentas reales ni contraseñas. No desactives medidas de seguridad de la empresa.", wraplength=880).pack(anchor="w", pady=10)

    def build_send(self):
        ttk.Label(self.send_tab, text="Solo después de revisar la lista y aprobar el mensaje.", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(0, 10))
        self.field(self.send_tab, 'audiencia', 'Destinatarios', 'Solo autorizados', choices=('Solo autorizados', 'Toda la lista autorizada'))
        self.field(self.send_tab, 'autorizados', 'Archivo de autorizados', browse=[('Texto: un correo por línea', '*.txt')])
        tools = ttk.Frame(self.send_tab)
        tools.pack(fill='x')
        self.button(tools, 'Editar autorizados', lambda: self.edit_addresses('autorizados', 'Destinatarios autorizados'))
        self.button(tools, 'Bajas / no contactar', lambda: self.edit_addresses('exclusiones', 'Bajas y exclusiones'))
        ttk.Label(self.send_tab, text='Una base recopilada no acredita permiso para recibir ofertas. Usa «Solo autorizados» para cruzarla con los contactos que sí lo tienen.', wraplength=860).pack(anchor='w', pady=6)
        self.field(self.send_tab, "max_por_ejecucion", "Mensajes por lote", "50")
        self.field(self.send_tab, 'max_24h', 'Máximo local en 24 h', '400')
        ttk.Label(self.send_tab, text='El máximo cuenta intentos de todas las campañas en esta copia. No conoce los envíos desde Gmail, otras aplicaciones ni registros anteriores a esta versión.', wraplength=860).pack(anchor='w', pady=4)
        self.field(self.send_tab, "intervalo_segundos", "Segundos entre mensajes", "2")
        self.field(self.send_tab, "destino_prueba", "Mi dirección de prueba")
        self.real_config = tk.BooleanVar(value=False)
        ttk.Checkbutton(self.send_tab, text="Ya completé los datos reales; no estoy usando la configuración de ejemplo.", variable=self.real_config).pack(anchor="w", pady=8)
        labels = {
            "remitente_autorizado": "La empresa autorizó esta cuenta remitente.",
            "envio_aprobado": "La empresa aprobó el asunto, texto y adjuntos.",
            "lista_revisada": "Confirmé que los destinatarios seleccionados aceptaron recibir estas ofertas.",
            "exclusiones_revisadas": "Apliqué el archivo de bajas/exclusiones o confirmé que no hay ninguna.",
            "limites_confirmados": "El administrador confirmó los límites y el ritmo de envío.",
        }
        for key, label in labels.items():
            self.approvals[key] = tk.BooleanVar(value=False)
            ttk.Checkbutton(self.send_tab, text=label, variable=self.approvals[key]).pack(anchor="w", pady=3)
        ttk.Label(self.send_tab, text="Una prueba real exige autorización del remitente y límites confirmados. El lote exige todas las casillas.\nSe pedirá una segunda confirmación con la lista exacta antes de conectarse al correo.", wraplength=870).pack(anchor="w", pady=12)
        actions = ttk.Frame(self.send_tab)
        actions.pack(fill="x")
        self.button(actions, "Enviar a mi dirección de prueba", lambda: self.launch("prueba"))
        self.button(actions, "Preparar envío del lote…", lambda: self.launch("enviar"))
        self.button(actions, "Consultar registro", lambda: self.launch("estado"))
        ttk.Label(self.send_tab, text="Conserva la carpeta «datos» al mover la aplicación: contiene el registro para no repetir envíos.\nNo ejecutes copias simultáneas en distintas computadoras para la misma campaña.", wraplength=870, foreground="#8a4b10").pack(anchor="w", pady=14)
        ttk.Button(self.send_tab, text="Abrir guía de campañas", command=lambda: self.open_path(resources() / "Guía de campañas.txt")).pack(anchor="w")

    def load_initial(self):
        path = self.data_dir / "configuracion.json"
        if not path.exists():
            path = resources() / "campana.ejemplo.json"
        try:
            self.apply_config(campana.load_config(path), path.parent)
        except Exception as exc:
            messagebox.showwarning("No se cargó la configuración", f"Se abrirá el ejemplo. {type(exc).__name__}", parent=self.root)
            self.apply_config(campana.load_config(resources() / "campana.ejemplo.json"), resources())

    def apply_config(self, cfg, base):
        self.cfg = copy.deepcopy(cfg)
        values = {"campana_id": cfg["campana_id"], "asunto": cfg["mensaje"]["asunto"],
                  "remitente": cfg["remitente"]["correo"], "nombre": cfg["remitente"]["nombre"],
                  "responder_a": cfg["remitente"]["responder_a"], **cfg["smtp"], **cfg["limites"]}
        for key, value in values.items():
            if key in self.form:
                self.form[key].set(str(value))
        self.real_config.set(not cfg["es_ejemplo"])
        self.form['max_24h'].set(str(cfg['limites'].get('max_24h', 400)))
        self.form['baja_correo'].set(cfg['mensaje'].get('baja_correo', ''))
        for flag in self.approvals.values():
            flag.set(False)  # Reconfirmación, esto mas que todo por que poner dos veces los correos literalmente buguea esto, y para evitarlo pues se me ocurrió
        self.body.delete("1.0", "end")
        self.body.insert("1.0", (base / cfg["mensaje"]["archivo_texto"]).read_text(encoding="utf-8-sig"))
        self.form["html"].set(str((base / cfg["mensaje"]["archivo_html"]).resolve()) if cfg["mensaje"]["archivo_html"] else "")
        self.attachments = [str((base / item).resolve()) for item in cfg["mensaje"]["adjuntos"]]
        self.refresh_attachments()

    def collect_config(self, folder, *, remember=False):
        folder.mkdir(parents=True, exist_ok=True)
        cfg = copy.deepcopy(self.cfg)
        cfg["campana_id"] = self.form["campana_id"].get().strip()
        cfg["es_ejemplo"] = not self.real_config.get()
        cfg["remitente"] = {"correo": self.form["remitente"].get().strip(), "nombre": self.form["nombre"].get(), "responder_a": self.form["responder_a"].get().strip()}
        cfg["mensaje"] = {"asunto": self.form["asunto"].get(), "archivo_texto": "mensaje.txt", "archivo_html": self.form["html"].get().strip(), "adjuntos": list(self.attachments)}
        cfg['mensaje']['baja_correo'] = self.form['baja_correo'].get().strip()
        for key in ("host", "seguridad", "autenticacion", "usuario"):
            cfg["smtp"][key] = self.form[key].get().strip()
        cfg["smtp"]["puerto"] = int(self.form["puerto"].get())
        cfg["limites"]["max_por_ejecucion"] = int(self.form["max_por_ejecucion"].get())
        cfg['limites']['max_24h'] = int(self.form['max_24h'].get())
        cfg["limites"]["intervalo_segundos"] = float(self.form["intervalo_segundos"].get())
        cfg["autorizacion"] = {key: var.get() for key, var in self.approvals.items()}
        if remember:
            cfg["autorizacion"] = {key: False for key in cfg["autorizacion"]}
        text = self.body.get("1.0", "end-1c")
        # El mensaje se nombra por contenido para no alterar la versión previa si falla el guardado, que si bien no ha pasado, no se sabe
        # Esto por que ya tengo un prescendente de cuando lo hice allá en 1ro
        name = "mensaje_" + campana.hashlib.sha256(text.encode()).hexdigest()[:16] + ".txt"
        cfg["mensaje"]["archivo_texto"] = name
        message_path = folder / name
        if not message_path.exists():
            message_path.write_text(text, encoding="utf-8")
        path = folder / "configuracion.json"
        candidate = folder / ("validar_" + campana.uuid.uuid4().hex + ".json")
        save_json_atomic(candidate, cfg)
        validated = campana.load_config(candidate)
        campana.load_content(validated, folder)
        os.replace(candidate, path)
        return path

    def save_settings(self):
        if self.busy:
            return
        try:
            self.collect_config(self.data_dir, remember=True)
            self.save_session()
            self.status.set("Configuración guardada sin contraseñas. Las autorizaciones se reconfirman al abrir.")
        except Exception as exc:
            messagebox.showerror("Revisa la configuración", str(exc), parent=self.root)

    def import_settings(self):
        path = filedialog.askopenfilename(parent=self.root, filetypes=[("Configuración", "*.json")])
        if path:
            try:
                self.apply_config(campana.load_config(Path(path)), Path(path).parent)
            except Exception as exc:
                messagebox.showerror("No se pudo cargar", str(exc), parent=self.root)

    def save_session(self):
        save_json_atomic(self.data_dir / 'sesion.json', {key: self.form[key].get() for key in ('lista', 'exclusiones', 'autorizados', 'audiencia')})

    def gmail_preset(self):
        for key, value in {'host': 'smtp.gmail.com', 'puerto': '587', 'seguridad': 'starttls', 'autenticacion': 'password', 'usuario': self.form['remitente'].get()}.items():
            self.form[key].set(value)
        self.status.set('Gmail preparado. Completa tu remitente y usuario. La credencial solo se pide al confirmar una prueba o un lote.')

    def offer_template(self):
        if not messagebox.askyesno('Plantilla de servicios', '¿Reemplazar el texto actual por una plantilla editable? No modifica los adjuntos.', parent=self.root):
            return
        self.body.delete('1.0', 'end')
        self.body.insert('1.0', OFFER_TEMPLATE)
        self.form['asunto'].set('Presentación de nuestros servicios')
        self.form['campana_id'].set('servicios-' + campana.uuid.uuid4().hex[:12])
        self.status.set('Completa todos los campos entre corchetes antes de enviar. Revisa también el HTML si tienes uno.')

    def open_review(self):
        if self.busy:
            return
        path = filedialog.askopenfilename(parent=self.root, title='Elige Detalle.json o informe.json', filetypes=[('Informe de revisión', '*.json')])
        if path:
            self.local_task('review_imported', lambda: import_report(path, self.data_dir, self.stop_event), 'Integrando la revisión anterior…')

    def edit_addresses(self, key, title):
        if self.busy:
            return
        path = Path(self.form[key].get()) if self.form[key].get() else self.data_dir / (key + '.txt')
        try:
            existing = path.read_text(encoding='utf-8-sig') if path.exists() else ''
        except OSError as exc:
            messagebox.showerror(title, str(exc), parent=self.root)
            return
        dialog = tk.Toplevel(self.root)
        dialog.title(title)
        dialog.transient(self.root)
        dialog.grab_set()
        ttk.Label(dialog, text='Un correo por línea. Las bajas prevalecen sobre cualquier autorización.').pack(padx=16, pady=12)
        editor = ScrolledText(dialog, width=70, height=18)
        editor.pack(padx=16, pady=8)
        editor.insert('1.0', existing)
        def save():
            try:
                values = sorted({campana.address(line).casefold() for line in editor.get('1.0', 'end').splitlines() if line.strip()})
                # Guardar una copia propia: nunca sobrescribir la lista original elegida.
                destination = self.data_dir / (key + '.txt')
                with tempfile.NamedTemporaryFile('w', encoding='utf-8-sig', dir=self.data_dir, delete=False) as stream:
                    stream.write('\n'.join(values) + ('\n' if values else ''))
                os.replace(stream.name, destination)
                self.form[key].set(str(destination))
                self.save_session()
                dialog.destroy()
                self.status.set(f'{title}: {len(values):,} direcciones guardadas. No se enviaron mensajes.')
            except (ValueError, OSError) as exc:
                messagebox.showerror('Revisa las direcciones', str(exc), parent=dialog)
        ttk.Button(dialog, text='Guardar lista', command=save).pack(pady=12)

    def choose_file(self, key, filters):
        if self.busy:
            return
        path = filedialog.askopenfilename(parent=self.root, filetypes=filters)
        if path:
            if key == "lista" and Path(path).suffix.lower() in EXCEL_EXTENSIONS:
                self.import_excel(path)
            else:
                self.form[key].set(path)

    def set_busy(self, value):
        self.busy = value
        for button in self.action_buttons:
            button.configure(state='disabled' if value else 'normal')
        for index in (1, 2, 3):
            self.book.tab(index, state='disabled' if value else 'normal')
        self.stop_button.configure(state='normal' if value else 'disabled')
        if value:
            self.stop_event.clear()
            self.progress.start(12)
        else:
            self.progress.stop()

    def local_task(self, kind, function, message):
        if self.busy:
            return
        self.set_busy(True)
        self.status.set(message)
        def task():
            try:
                result = function()
                self.events.put(('local_done', (kind, result, '')))
            except Exception as exc:
                self.events.put(('local_done', (kind, None, str(exc))))
        threading.Thread(target=task, daemon=True).start()

    def auto_files(self):
        if self.busy:
            return
        paths = filedialog.askopenfilenames(parent=self.root, title='Selecciona uno o varios archivos',
            filetypes=[('Listas de contactos', '*.xlsx *.xls *.csv *.txt')])
        self.detect_files(paths)

    def auto_folder(self):
        if self.busy:
            return
        folder = filedialog.askdirectory(parent=self.root, title='Selecciona la carpeta de bases')
        if folder:
            self.local_task('detected', lambda: scan_files(sorted(p for p in Path(folder).rglob('*')
                if p.is_file() and p.suffix.lower() in EXTENSIONS and not p.name.startswith(('~$', '._'))),
                self.stop_event, lambda message: self.events.put(('local_progress', message))), 'Buscando archivos de contactos…')

    def detect_files(self, paths):
        if not paths or self.busy:
            return
        self.local_task('detected', lambda: scan_files(paths, self.stop_event,
            lambda message: self.events.put(('local_progress', message))), 'Buscando columnas de correo…')

    def saved_list(self):
        if self.busy:
            return
        path = filedialog.askopenfilename(parent=self.root, title='Continuar con una lista guardada', filetypes=[('Importaciones', '*.mxlista')])
        if path:
            self.local_task('imported', lambda: (Path(path), load_import(Path(path), self.stop_event), 'Lista guardada'), 'Abriendo la lista…')

    def export_csv(self):
        if self.busy or not self.rows:
            if not self.busy:
                messagebox.showinfo('Primero carga una lista', 'Carga tus archivos para poder exportarlos.', parent=self.root)
            return
        if any(not row.get('estado') for row in self.rows):
            if not messagebox.askyesno('Hay entradas sin revisar', 'La lista completa se puede exportar ahora, pero los correos sin revisar irán también a «Por revisar». ¿Continuar?', parent=self.root):
                return
        folder = filedialog.askdirectory(parent=self.root, title='Dónde guardar las listas CSV')
        if folder:
            rows = self.rows
            self.local_task('exported', lambda: export_lists(rows, folder), 'Guardando listas CSV…')

    def schedule_filter(self, *_):
        if self.search_job:
            self.root.after_cancel(self.search_job)
        self.search_job = self.root.after(250, self.apply_filter)

    def apply_filter(self):
        self.search_job = None
        category, search = self.category.get(), self.search.get().strip()
        self.filtered = [i for i, row in enumerate(self.rows) if matches(row, category, search)]
        self.page = 0
        self.render_page()

    def set_rows(self, rows):
        self.rows = rows
        for key in ('APTO_DNS', 'INVALIDO'):
            self.metrics[key].set(f"{sum(r.get('estado') == key for r in rows):,}")
        self.metrics['total'].set(f'{len(rows):,}')
        self.metrics['pending'].set(f"{sum(r.get('estado', '') in {'', 'REVISAR'} for r in rows):,}")
        self.metrics['duplicates'].set(f"{sum(r.get('duplicado_de_linea') is not None for r in rows):,}")
        self.category.set('Todos')
        self.search.set('')
        self.apply_filter()

    def change_page(self, delta):
        last = max(0, (len(self.filtered) - 1) // 200)
        self.page = max(0, min(last, self.page + delta))
        self.render_page()

    def render_page(self):
        self.table.delete(*self.table.get_children())
        start = self.page * 200
        for i in self.filtered[start:start + 200]:
            row = self.rows[i]
            reason = row.get('motivo') or 'Importado; pendiente de revisar dominios.'
            origin = row.get('origen', {})
            location = ' / '.join(str(v) for v in (origin.get('archivo'), origin.get('hoja'), row.get('celda_origen')) if v)
            if location:
                reason = location + ' · ' + reason
            if row.get('duplicado_de_linea') is not None:
                reason = f"Repetido de entrada {row['duplicado_de_linea']} · " + reason
            state = row.get('estado', '')
            self.table.insert('', 'end', iid=str(i), values=(row['original'], LABELS.get(state, state), reason), tags=(state or 'pending',))
        count = len(self.filtered)
        self.page_info.set(f'{start + 1 if count else 0}–{min(start + 200, count)} de {count:,} entradas · La exportación incluye toda la lista, no solo esta página.')

    def import_excel(self, path=None):
        if self.busy:
            return
        path = path or filedialog.askopenfilename(parent=self.root, title="Selecciona el Excel de contactos", filetypes=[("Excel", "*.xlsx *.xls")])
        if not path:
            return
        try:
            self.root.configure(cursor="watch")
            self.root.update_idletasks()
            dialog = ExcelDialog(self.root, Path(path))
            if dialog.result:
                self.accept_import(*dialog.result)
        except Exception as exc:
            messagebox.showerror("No se pudo importar el Excel", str(exc), parent=self.root)
        finally:
            self.root.configure(cursor="")

    def paste_contacts(self):
        if self.busy:
            return
        dialog = PasteDialog(self.root)
        if dialog.result:
            try:
                self.accept_import(*dialog.result)
            except Exception as exc:
                messagebox.showerror("No se pudo guardar la lista", str(exc), parent=self.root)

    def accept_import(self, contacts, source):
        def prepare():
            if self.stop_event.is_set():
                raise ImportCancelled('Importación cancelada.')
            path = save_import(contacts, source, self.data_dir)
            rows = load_import(path, self.stop_event, lambda number: self.events.put(('local_progress', f'Preparando {number:,} entradas…')))
            if self.stop_event.is_set():
                raise ImportCancelled('Importación cancelada. Se conserva la lista anterior.')
            return path, rows, source['archivo']
        self.local_task('imported', prepare, 'Preparando tu lista y detectando duplicados…')

    def add_attachments(self):
        for path in filedialog.askopenfilenames(parent=self.root, title="Selecciona los adjuntos aprobados"):
            if path not in self.attachments:
                self.attachments.append(path)
        self.refresh_attachments()

    def remove_attachment(self):
        for index in reversed(self.attachment_list.curselection()):
            self.attachments.pop(index)  # Solo quita la referencia, no borra ningún archivo | NO CAMBIAR POR NADA DEL MUNDO
        self.refresh_attachments()

    def refresh_attachments(self):
        self.attachment_list.delete(0, "end")
        for path in self.attachments:
            self.attachment_list.insert("end", path)

    def example(self):
        self.set_rows([])
        self.form["lista"].set(str(resources() / "ejemplo.txt"))
        self.launch("revisar")

    def launch(self, mode):
        if self.busy:
            return
        try:
            file = self.form["lista"].get().strip()
            if mode not in {"prueba", "estado"} and file and Path(file).suffix.lower() in EXCEL_EXTENSIONS:
                self.import_excel(file)
                file = self.form["lista"].get().strip()
                if Path(file).suffix.lower() in EXCEL_EXTENSIONS:
                    return
            if mode not in {"prueba", "estado"} and not file:
                raise ValueError("Elige tu archivo de correos o pulsa «Probar lista de ejemplo».")
            authorized = self.form['autorizados'].get().strip() if self.form['audiencia'].get() == 'Solo autorizados' else ''
            if mode in {'simular', 'enviar'} and self.form['audiencia'].get() == 'Solo autorizados' and not authorized:
                raise ValueError('Añade los destinatarios en «Editar autorizados» o confirma que toda la lista tiene autorización en la pestaña de envío.')
            if mode in {'enviar', 'prueba'}:
                if not self.form['baja_correo'].get().strip():
                    raise ValueError('Completa el correo para recibir bajas en la pestaña Mensaje.')
                if any(token in self.body.get('1.0', 'end') for token in ('[TU NOMBRE', '[NOMBRE DE LA EMPRESA]', '[SERVICIO]', '[TIPO DE CLIENTE]', '[NECESIDAD CONCRETA]', '[EXPLICA', '[EMPRESA')):
                    raise ValueError('Completa los campos entre corchetes de la plantilla antes de enviar.')
            config_path = resources() / "campana.ejemplo.json"
            if mode != "revisar":
                run_folder = Path(tempfile.mkdtemp(prefix="ejecucion_", dir=self.data_dir))
                config_path = self.collect_config(run_folder)
            args = argparse.Namespace(archivo=Path(file) if mode not in {"prueba", "estado"} else None,
                config=config_path, modo=mode, destino_prueba=self.form["destino_prueba"].get().strip() if mode == "prueba" else None,
                exclusiones=Path(self.form["exclusiones"].get().strip()) if self.form["exclusiones"].get().strip() else None,
                autorizados=Path(authorized) if authorized and mode in {'simular', 'enviar'} else None,
                columna_correo=self.form["columna"].get().strip() or "correo", separador=None,
                salida=self.data_dir / "resultados", registro=self.data_dir / "envios.sqlite3",
                sin_dns=False, reintentar_temporales=False, workers=8, timeout=4, reintentos_dns=1)
            self.run_cfg = campana.load_config(config_path) if mode != "revisar" else None
        except Exception as exc:
            messagebox.showerror("Falta completar un dato", str(exc), parent=self.root)
            return
        self.busy = True
        self.stop_event.clear()
        self.last_folder = None
        for button in self.action_buttons:
            button.configure(state="disabled")
        for index in (1, 2, 3):
            self.book.tab(index, state="disabled")
        self.book.select(0)
        self.stop_button.configure(state="normal")
        self.progress.start(12)
        self.status.set("Trabajando. No cierres la aplicación ni retires la USB.")
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")
        threading.Thread(target=self.worker, args=(args,), daemon=True).start()

    def ask_from_worker(self, kind, prompt):
        request = {"event": threading.Event(), "answer": "", "prompt": prompt}
        self.events.put((kind, request))
        while not request["event"].wait(0.2):
            if self.stop_event.is_set():
                return ""
        return request["answer"] or ""

    def worker(self, args):
        code, error = 1, ""
        def connector(cfg):
            secret = "" if cfg["smtp"]["autenticacion"] == "none" else self.ask_from_worker("secret", "Introduce la credencial SMTP o access token autorizado. No se guardará.")
            if self.stop_event.is_set():
                raise ValueError("Operación detenida antes de conectar a SMTP.")
            return campana.connect_smtp(cfg, secret=secret)
        try:
            with redirect_stdout(QueueWriter(self.events)):
                code = campana.run(args, confirm=lambda prompt: self.ask_from_worker("confirm", prompt),
                    connector=connector, stop_event=self.stop_event,
                    on_output=lambda folder: self.events.put(("output", folder)))
        except (smtplib.SMTPException, OSError) as exc:
            error = f"{type(exc).__name__}: comprueba los archivos, la conexión y los datos SMTP con el administrador. Si hubo envío, consulta el registro antes de repetir."
        except Exception as exc:
            error = str(exc)
        finally:
            self.events.put(("done", (code, error)))

    def poll(self):
        try:
            while True:
                kind, payload = self.events.get_nowait()
                if kind == "log":
                    self.log.configure(state="normal")
                    self.log.insert("end", payload)
                    self.log.see("end")
                    self.log.configure(state="disabled")
                elif kind == 'local_progress':
                    self.status.set(payload)
                elif kind == 'local_done':
                    operation, result, error = payload
                    stopped = self.stop_event.is_set()
                    self.set_busy(False)
                    if error:
                        self.status.set(error)
                        if not stopped:
                            messagebox.showerror('No se pudo completar', error, parent=self.root)
                    elif operation == 'detected':
                        if stopped:
                            self.status.set('Importación cancelada. Se conserva la lista anterior.')
                            continue
                        groups, issues = result
                        if not groups:
                            messagebox.showinfo('No se encontraron columnas', '\n'.join(issues) or 'No hay archivos admitidos en esa carpeta.', parent=self.root)
                            self.status.set('Sin cambios. Prueba otra carpeta o la selección manual de Excel.')
                            continue
                        self.status.set('Confirma qué columnas quieres importar.')
                        dialog = DetectionDialog(self.root, groups, issues)
                        if dialog.result:
                            files = len({c['archivo_origen'] for c in dialog.result})
                            self.accept_import(dialog.result, {'tipo': 'deteccion automatica', 'archivo': f'{files} archivos'})
                        else:
                            self.status.set('Importación cancelada. Se conserva la lista anterior.')
                    elif operation in {'imported', 'review_imported'}:
                        if stopped:
                            self.status.set('Importación cancelada. Se conserva la lista anterior.')
                            continue
                        path, rows, label = result
                        self.form['lista'].set(str(path))
                        self.save_session()
                        self.last_folder = None
                        self.set_rows(rows)
                        self.import_info.set(f'{label} · {len(rows):,} entradas importadas. Originales intactos.')
                        self.summary.set('Lista preparada. Pulsa «Revisar dominios» para comprobar su configuración de correo.')
                        self.status.set('Importación terminada. Aún no se ha consultado DNS ni enviado mensajes.')
                        if operation == 'review_imported':
                            self.summary.set('Resultados históricos importados. Antes de preparar cada lote se vuelve a consultar DNS.')
                            self.status.set('Revisión integrada. No se enviaron mensajes; el estado anterior no acredita permiso ni existencia del buzón.')
                    elif operation == 'exported':
                        folder, counts = result
                        self.status.set(f'CSV guardados en {folder}')
                        messagebox.showinfo('Listas exportadas', '\n'.join(f'{name}: {count:,}' for name, count in counts.items()) + f'\n\n{folder}\n\nDominio apto no confirma que el buzón exista.', parent=self.root)
                elif kind == "output":
                    self.last_folder = payload
                    self.show_results()
                elif kind in {"confirm", "secret"}:
                    if not self.stop_event.is_set():
                        if kind == "confirm":
                            detail = self.confirmation_detail()
                            dialog = ConfirmSend(self.root, payload["prompt"], detail)
                            payload["answer"] = dialog.result
                        else:
                            payload["answer"] = simpledialog.askstring("Credencial de envío", payload["prompt"], show="*", parent=self.root)
                    payload["event"].set()
                elif kind == "done":
                    code, error = payload
                    self.busy = False
                    self.progress.stop()
                    self.stop_button.configure(state="disabled")
                    for button in self.action_buttons:
                        button.configure(state="normal")
                    for index in (1, 2, 3):
                        self.book.tab(index, state="normal")
                    self.status.set("Revisa el aviso: la operación no terminó." if error else "Operación detenida; revisa el registro." if code in {2, 130} else "Terminado. Los detalles aparecen abajo y en la carpeta de resultados.")
                    result = self.last_folder / 'envio.json' if self.last_folder else None
                    if result and result.exists():
                        delivery = json.loads(result.read_text(encoding='utf-8'))
                        self.summary.set('Resultado del lote: ' + ', '.join(f'{key}: {value:,}' for key, value in delivery['lote'].items()) + '. Aceptado por SMTP no significa entregado.')
                        if delivery['lote'].get('LIMITE_LOCAL_24H'):
                            self.status.set('Lote detenido por el máximo local de 24 horas. Conserva la campaña para continuar cuando haya cupo; comprueba también los límites de Google.')
                    if error:
                        messagebox.showerror("No se pudo completar", error, parent=self.root)
        except queue.Empty:
            pass
        self.root.after(100, self.poll)

    def confirmation_detail(self):
        cfg = self.run_cfg
        intro = f"Servidor: {cfg['smtp']['host']}:{cfg['smtp']['puerto']}\nRemitente: {cfg['remitente']['correo']}\n\n"
        if self.last_folder:
            sample = (self.last_folder / "vista_previa.txt").read_text(encoding="utf-8")
            audit = json.loads((self.last_folder / "seleccion.json").read_text(encoding="utf-8"))
            recipients = [item["correo"] for item in audit["decisiones"] if item["decision"] == "SELECCIONADO"]
            return intro + sample + "\nDESTINATARIOS EXACTOS DE ESTE LOTE:\n" + "\n".join(recipients)
        return intro

    def show_results(self):
        path = self.last_folder / "informe.json"
        if not path.exists():
            history = self.last_folder / 'estado_envios.json'
            if history.exists():
                entries = json.loads(history.read_text(encoding='utf-8'))['envios']
                counts = campana.Counter(row['status'] for row in entries)
                self.summary.set('Registro: ' + (', '.join(f'{key}: {value:,}' for key, value in counts.items()) or 'Todavía no hay envíos.') + ' · CSV disponible en la carpeta de resultados.')
            return
        report = json.loads(path.read_text(encoding="utf-8"))
        self.set_rows(report['resultados'])
        self.summary.set(f"Revisión disponible · {report['total']:,} entradas · Exporta los grupos a CSV para Excel.")

    def row_detail(self, _event=None):
        selection = self.table.selection()
        if selection:
            values = self.table.item(selection[0], "values")
            messagebox.showinfo("Detalle de revisión", "\n\n".join(values), parent=self.root)

    def open_path(self, path):
        try:
            open_local_path(path)
        except (OSError, subprocess.SubprocessError):
            messagebox.showinfo("Abrir archivo", f"Abre esta ruta con el Explorador o un editor de texto:\n{path.resolve()}", parent=self.root)

    def open_result(self, name):
        if self.last_folder and (self.last_folder / name).exists():
            self.open_path(self.last_folder / name)
        else:
            messagebox.showinfo("Todavía no está disponible", "Primero revisa la lista. Para ver un mensaje, ejecuta «Simular el mensaje» con destinatarios aptos.", parent=self.root)

    def open_results(self):
        folder = self.last_folder or self.data_dir
        self.open_path(folder)

    def stop(self):
        self.stop_event.set()
        self.status.set("Deteniendo de forma segura. Espera a que termine la consulta o mensaje actual.")

    def close(self):
        if self.busy:
            self.stop()
            messagebox.showinfo("Espera un momento", "Solicité detener la operación. Espera a que termine antes de cerrar o retirar la USB.", parent=self.root)
            return
        self.root.destroy()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--datos", type=Path, default=None, help="Carpeta de datos alternativa, para pruebas o uso administrado")
    args = parser.parse_args()
    root = tk.Tk()
    try:
        App(root, args.datos or default_data_dir())
    except Exception as exc:
        root.withdraw()
        messagebox.showerror("MxCorreo no pudo abrirse", f"{type(exc).__name__}: copia la carpeta completa a una ubicación donde puedas guardar archivos, como Documentos. No la abras dentro del ZIP.", parent=root)
        root.destroy()
        return 1
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
