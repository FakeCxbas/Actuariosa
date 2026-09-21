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
        ttk.Label(master, text="Esto sí enviará correos reales. Revisa el contenido y los destinatarios:",
                  font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=8)
        text = ScrolledText(master, width=88, height=18, wrap="word", font=("Consolas", 9))
        text.pack(fill="both", expand=True)
        text.insert("1.0", self.detail)
        text.configure(state="disabled")
        ttk.Label(master, text=self.prompt, wraplength=680, font=("Segoe UI", 10)).pack(anchor="w", pady=10)
        self.entry = ttk.Entry(master, width=65)
        self.entry.pack(fill="x")
        return self.entry

    def buttonbox(self):
        box = ttk.Frame(self)
        box.pack(pady=12)
        ttk.Button(box, text="Autorizar este envío", style="Primary.TButton", command=self.ok).pack(side="left", padx=8)
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
        self.step_buttons = []
        self.pending_dialog = None
        self.rows = []
        self.filtered = []
        self.page = 0
        self.search_job = None
        
        self.root.title("MxCorreo — Limpieza, Purga y Envío de Correos")
        width = min(1240, root.winfo_screenwidth() - 60)
        height = min(880, root.winfo_screenheight() - 60)
        root.geometry(f"{width}x{height}")
        root.minsize(980, 700)
        root.protocol("WM_DELETE_WINDOW", self.close)
        
        # Icono de la ventana
        icon_path = resources() / "mxcorreo.ico"
        if icon_path.exists():
            try:
                self.root.iconbitmap(str(icon_path))
            except Exception:
                pass

        # Estilo visual moderno Windows Fluent / Slate
        style = ttk.Style(root)
        style.theme_use("clam")
        
        bg_color = "#f8fafc"
        card_bg = "#ffffff"
        text_color = "#1e293b"
        
        style.configure("TFrame", background=bg_color)
        style.configure("TLabel", background=bg_color, foreground=text_color, font=("Segoe UI", 10))
        style.configure("TCheckbutton", background=bg_color, foreground=text_color, font=("Segoe UI", 10))
        
        # Botón secundario estándar
        style.configure("TButton", padding=(12, 7), font=("Segoe UI", 10), background=card_bg, foreground=text_color,
                        bordercolor="#cbd5e1", lightcolor=card_bg, darkcolor=card_bg, relief="flat")
        style.map("TButton", background=[("active", "#f1f5f9"), ("disabled", "#f8fafc")],
                  foreground=[("disabled", "#94a3b8")])
        
        # Botón primario azul
        style.configure("Primary.TButton", padding=(14, 8), font=("Segoe UI", 10, "bold"),
                        background="#2563eb", foreground="white", bordercolor="#2563eb",
                        lightcolor="#2563eb", darkcolor="#2563eb")
        style.map("Primary.TButton", background=[("active", "#1d4ed8"), ("disabled", "#93c5fd")])
        
        # Botón verde de éxito / exportación
        style.configure("Success.TButton", padding=(14, 8), font=("Segoe UI", 10, "bold"),
                        background="#16a34a", foreground="white", bordercolor="#16a34a",
                        lightcolor="#16a34a", darkcolor="#16a34a")
        style.map("Success.TButton", background=[("active", "#15803d"), ("disabled", "#86efac")])
        
        # Botón destacado de purga
        style.configure("BigPurge.TButton", padding=(18, 10), font=("Segoe UI", 11, "bold"),
                        background="#1e40af", foreground="white", bordercolor="#1e40af",
                        lightcolor="#1e40af", darkcolor="#1e40af")
        style.map("BigPurge.TButton", background=[("active", "#1e3a8a"), ("disabled", "#93c5fd")])
        
        # Botones chips / de acción rápida
        style.configure("Chip.TButton", padding=(8, 4), font=("Segoe UI", 9, "bold"),
                        background="#eff6ff", foreground="#1d4ed8", bordercolor="#bfdbfe")
        style.map("Chip.TButton", background=[("active", "#dbeafe")])
        
        # Botones del Stepper superior
        style.configure("Step.TButton", padding=(12, 6), font=("Segoe UI", 10),
                        background="#e2e8f0", foreground="#475569", bordercolor="#cbd5e1")
        style.map("Step.TButton", background=[("active", "#cbd5e1")])
        
        style.configure("ActiveStep.TButton", padding=(12, 6), font=("Segoe UI", 10, "bold"),
                        background="#2563eb", foreground="white", bordercolor="#2563eb")
        style.map("ActiveStep.TButton", background=[("active", "#1d4ed8")])

        # Tarjetas y tipografía
        style.configure("Card.TFrame", background=card_bg)
        style.configure("Card.TLabel", background=card_bg, foreground="#475569", font=("Segoe UI", 10))
        style.configure("CardHeader.TLabel", background=card_bg, foreground="#0f172a", font=("Segoe UI", 12, "bold"))
        style.configure("Section.TLabel", font=("Segoe UI", 13, "bold"), foreground="#0f172a", background=bg_color)
        style.configure("SubSection.TLabel", font=("Segoe UI", 10), foreground="#64748b", background=bg_color)
        style.configure("MetricValue.TLabel", background=card_bg, font=("Segoe UI", 22, "bold"))
        style.configure("MetricTitle.TLabel", background=card_bg, foreground="#64748b", font=("Segoe UI", 9))
        
        # Pestañas del Notebook
        style.configure("TNotebook", background=bg_color, borderwidth=0)
        style.configure("TNotebook.Tab", padding=(20, 10), font=("Segoe UI", 10, "bold"),
                        background="#e2e8f0", foreground="#475569", borderwidth=0)
        style.map("TNotebook.Tab", background=[("selected", card_bg)], foreground=[("selected", "#2563eb")])
        
        # Tabla Treeview
        style.configure("Treeview", rowheight=28, font=("Segoe UI", 9), borderwidth=0, fieldbackground="white")
        style.configure("Treeview.Heading", background="#f1f5f9", foreground="#0f172a", padding=8, font=("Segoe UI", 10, "bold"))
        style.map("Treeview", background=[("selected", "#dbeafe")], foreground=[("selected", "#1e3a8a")])
        
        # --- ENCABEZADO SUPERIOR Y STEPPER VISUAL ---
        top = ttk.Frame(root, padding=(22, 12))
        top.pack(fill="x")
        
        header_left = ttk.Frame(top)
        header_left.pack(side="left")
        ttk.Label(header_left, text="✉️ MxCorreo", font=("Segoe UI", 20, "bold"), foreground="#0f172a").pack(side="left")
        ttk.Label(header_left, text=" · Purga, Limpieza y Envío de Correos", font=("Segoe UI", 13), foreground="#64748b").pack(side="left", padx=6)
        
        # Stepper interactivo de 4 pasos
        stepper_frame = ttk.Frame(top)
        stepper_frame.pack(side="right")
        
        steps = [
            ("1. 📋 Purgar Lista", 0),
            ("2. ✍️ Redactar Mensaje", 1),
            ("3. ⚙️ Conectar Correo", 2),
            ("4. 🚀 Enviar y Resultados", 3)
        ]
        for title, idx in steps:
            btn = ttk.Button(stepper_frame, text=title, style="Step.TButton", command=lambda i=idx: self.go_to_tab(i))
            btn.pack(side="left", padx=3)
            self.step_buttons.append(btn)

        # Notebook principal
        self.book = ttk.Notebook(root)
        self.book.pack(fill="both", expand=True, padx=18, pady=(0, 6))
        self.book.bind("<<NotebookTabChanged>>", self.on_tab_changed)

        self.list_tab = self.tab("1. 📋 Purgar Lista")
        self.message_tab = self.tab("2. ✍️ Redactar Mensaje")
        self.account_tab = self.tab("3. ⚙️ Conectar Correo")
        self.send_tab = self.tab("4. 🚀 Enviar y Resultados")

        self.build_list()
        self.build_message()
        self.build_account()
        self.build_send()

        # Barra inferior de estado y progreso
        bottom = ttk.Frame(root, padding=(18, 10))
        bottom.pack(fill="x")
        
        self.status = tk.StringVar(value="Listo. Carga tus archivos de Excel, CSV o TXT en el Paso 1 para comenzar la purga.")
        status_label = ttk.Label(bottom, textvariable=self.status, wraplength=780, font=("Segoe UI", 10))
        status_label.pack(side="left", fill="x", expand=True)
        
        self.stop_button = ttk.Button(bottom, text="🛑 Detener operación", command=self.stop, state="disabled")
        self.stop_button.pack(side="right")
        
        self.progress = ttk.Progressbar(root, mode="indeterminate")
        self.progress.pack(fill="x", padx=18, pady=(0, 10))
        
        self.load_initial()
        if not (self.data_dir / "configuracion.json").exists():
            self.gmail_preset()
            
        session = self.data_dir / "sesion.json"
        if session.exists():
            try:
                saved = json.loads(session.read_text(encoding="utf-8"))
                for key in ("lista", "exclusiones", "autorizados", "audiencia"):
                    if isinstance(saved.get(key), str) and key in self.form:
                        self.form[key].set(saved[key])
                if self.form.get("lista") and self.form["lista"].get() and Path(self.form["lista"].get()).exists():
                    path = Path(self.form["lista"].get())
                    root.after(200, lambda: self.local_task("imported", lambda: (path, load_import(path, self.stop_event), "Última lista guardada"), "Recuperando contactos…"))
            except (ValueError, OSError):
                self.status.set("No se recuperó la sesión anterior. Puedes cargar tus archivos nuevamente.")
                
        self.sync_stepper(0)
        root.after(100, self.poll)

    def go_to_tab(self, index):
        self.book.select(index)

    def on_tab_changed(self, _event=None):
        try:
            current = self.book.index(self.book.select())
            self.sync_stepper(current)
        except Exception:
            pass

    def sync_stepper(self, active_index):
        for idx, btn in enumerate(self.step_buttons):
            if idx == active_index:
                btn.configure(style="ActiveStep.TButton")
            else:
                btn.configure(style="Step.TButton")

    def tab(self, title):
        outer = ttk.Frame(self.book)
        self.book.add(outer, text=title)
        canvas = tk.Canvas(outer, highlightthickness=0, background="#f8fafc")
        scroll = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        scroll.pack(side="right", fill="y")
        canvas.pack(fill="both", expand=True)
        canvas.configure(yscrollcommand=scroll.set)
        inner = ttk.Frame(canvas, padding=20)
        window = canvas.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(window, width=e.width))

        def wheel(event):
            widget = event.widget
            if isinstance(widget, (ttk.Treeview, tk.Text, tk.Listbox, ttk.Combobox)):
                return
            while widget is not None:
                if widget == outer:
                    canvas.yview_scroll(-int(event.delta / 120), "units")
                    return "break"
                widget = getattr(widget, "master", None)
        self.root.bind("<MouseWheel>", wheel, add="+")
        return inner

    def field(self, parent, key, label, value="", choices=None, browse=None, show=None):
        line = ttk.Frame(parent)
        line.pack(fill="x", pady=4)
        ttk.Label(line, text=label, width=26, font=("Segoe UI", 10)).pack(side="left")
        var = tk.StringVar(value=value)
        self.form[key] = var
        if choices:
            widget = ttk.Combobox(line, textvariable=var, values=choices, state="readonly", font=("Segoe UI", 10))
        else:
            widget = ttk.Entry(line, textvariable=var, show=show or "", font=("Segoe UI", 10))
        widget.pack(side="left", fill="x", expand=True)
        if browse:
            ttk.Button(line, text="Elegir…", command=lambda: self.choose_file(key, browse)).pack(side="left", padx=(8, 0))
        return var

    def button(self, parent, text, command, primary=False, style=None):
        btn_style = style or ("Primary.TButton" if primary else "TButton")
        item = ttk.Button(parent, text=text, command=command, style=btn_style)
        item.pack(side="left", padx=(0, 8), pady=4)
        self.action_buttons.append(item)
        return item

    def insert_tag(self, tag):
        self.body.insert("insert", tag)
        self.body.focus_set()

    # =========================================================================
    # PASO 1: PURGAR LISTA Y RESULTADOS
    # =========================================================================
    def build_list(self):
        # 1. Carga de contactos
        card_load = ttk.Frame(self.list_tab, style="Card.TFrame", padding=16)
        card_load.pack(fill="x", pady=(0, 12))
        ttk.Label(card_load, text="1. Cargar Contactos", style="CardHeader.TLabel").pack(anchor="w")
        ttk.Label(card_load, text="Selecciona tus archivos de Excel (.xlsx, .xls), CSV o TXT. El sistema extrae los correos sin alterar tus archivos originales.",
                  style="Card.TLabel").pack(anchor="w", pady=(2, 10))
        
        btn_row = ttk.Frame(card_load, style="Card.TFrame")
        btn_row.pack(fill="x", pady=2)
        self.button(btn_row, "📂 Cargar archivos (Excel, CSV, TXT)…", self.auto_files, primary=True)
        self.button(btn_row, "📁 Cargar carpeta completa…", self.auto_folder)
        self.button(btn_row, "📋 Pegar correos…", self.paste_contacts)
        self.button(btn_row, "🔍 Selección manual de Excel…", self.import_excel)
        self.button(btn_row, "📂 Abrir revisión anterior…", self.open_review)
        
        self.import_info = tk.StringVar(value="Ningún archivo cargado aún. Haz clic en «Cargar archivos» para iniciar.")
        ttk.Label(card_load, textvariable=self.import_info, font=("Segoe UI", 9, "italic"), foreground="#475569", background="white").pack(anchor="w", pady=(8, 0))

        # 2. Acción destacada de purga
        card_action = ttk.Frame(self.list_tab, style="Card.TFrame", padding=16)
        card_action.pack(fill="x", pady=(0, 12))
        
        purge_left = ttk.Frame(card_action, style="Card.TFrame")
        purge_left.pack(side="left", fill="x", expand=True)
        ttk.Label(purge_left, text="2. Análisis y Purga de Correos", style="CardHeader.TLabel").pack(anchor="w")
        ttk.Label(purge_left, text="Verifica la sintaxis, elimina duplicados y consulta en tiempo real si el servidor de cada dominio puede recibir correos.",
                  style="Card.TLabel").pack(anchor="w", pady=(2, 0))
        
        self.button(card_action, "⚡ REVISAR Y PURGAR LISTA", lambda: self.launch("revisar"), style="BigPurge.TButton")

        # 3. Métricas de purga
        cards = ttk.Frame(self.list_tab)
        cards.pack(fill="x", pady=(0, 12))
        self.metrics = {}
        metric_configs = [
            ("total", "Total de Entradas", "#1e293b"),
            ("APTO_DNS", "✅ Aptos / Válidos", "#16a34a"),
            ("INVALIDO", "⚠️ Con Problemas", "#dc2626"),
            ("pending", "⏳ Por Revisar", "#d97706"),
            ("duplicates", "🔄 Repetidas", "#7c3aed")
        ]
        for i, (key, label, color) in enumerate(metric_configs):
            cards.columnconfigure(i, weight=1, uniform="metrics")
            card = ttk.Frame(cards, style="Card.TFrame", padding=12)
            card.grid(row=0, column=i, sticky="ew", padx=(0, 8 if i < 4 else 0))
            self.metrics[key] = tk.StringVar(value="0")
            ttk.Label(card, textvariable=self.metrics[key], style="MetricValue.TLabel", foreground=color).pack(anchor="w")
            ttk.Label(card, text=label, style="MetricTitle.TLabel").pack(anchor="w")

        # 4. Exportar y acciones de resultados
        card_export = ttk.Frame(self.list_tab, style="Card.TFrame", padding=16)
        card_export.pack(fill="x", pady=(0, 12))
        
        ttk.Label(card_export, text="3. Guardar y Exportar Listas Limpias", style="CardHeader.TLabel").pack(anchor="w")
        self.summary = tk.StringVar(value="Carga tus archivos para ver el desglose y generar tus listas limpias en Excel/CSV.")
        ttk.Label(card_export, textvariable=self.summary, style="Card.TLabel").pack(anchor="w", pady=(2, 8))
        
        export_row = ttk.Frame(card_export, style="Card.TFrame")
        export_row.pack(fill="x")
        self.button(export_row, "💾 Exportar Listas Limpias (.CSV)…", self.export_csv, style="Success.TButton")
        self.button(export_row, "📊 Abrir informe visual (HTML)", lambda: self.open_result("informe.html"))
        self.button(export_row, "📂 Abrir carpeta de resultados", self.open_results)
        self.button(export_row, "👁️ Simular mensaje", lambda: self.launch("simular"))
        self.button(export_row, "💡 Probar con ejemplo", self.example)

        # 5. Explorador y filtros
        card_table = ttk.Frame(self.list_tab, style="Card.TFrame", padding=16)
        card_table.pack(fill="both", expand=True, pady=(0, 12))
        
        filter_row = ttk.Frame(card_table, style="Card.TFrame")
        filter_row.pack(fill="x", pady=(0, 8))
        ttk.Label(filter_row, text="Buscar contacto:", style="Card.TLabel", font=("Segoe UI", 10, "bold")).pack(side="left")
        self.search = tk.StringVar()
        ttk.Entry(filter_row, textvariable=self.search, width=32, font=("Segoe UI", 10)).pack(side="left", padx=8)
        ttk.Label(filter_row, text="Filtrar por:", style="Card.TLabel").pack(side="left", padx=(8, 4))
        self.category = tk.StringVar(value="Todos")
        ttk.Combobox(filter_row, textvariable=self.category, values=FILTERS, state="readonly", width=22, font=("Segoe UI", 10)).pack(side="left")
        self.search.trace_add("write", self.schedule_filter)
        self.category.trace_add("write", self.schedule_filter)

        tableframe = ttk.Frame(card_table)
        tableframe.pack(fill="both", expand=True)
        self.table = ttk.Treeview(tableframe, columns=("correo", "estado", "motivo"), show="headings", height=8)
        for key, title, width in (("correo", "Correo Electrónico", 280), ("estado", "Resultado DNS", 140), ("motivo", "Diagnóstico y Origen", 480)):
            self.table.heading(key, text=title)
            self.table.column(key, width=width, minwidth=100)
        scrollbar = ttk.Scrollbar(tableframe, orient="vertical", command=self.table.yview)
        self.table.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.table.pack(fill="both", expand=True)
        self.table.bind("<Double-1>", self.row_detail)
        
        # Colores suaves para la tabla
        self.table.tag_configure("APTO_DNS", background="#edf8f3")
        self.table.tag_configure("INVALIDO", background="#fef2f2")
        self.table.tag_configure("REVISAR", background="#fffbeb")
        self.table.tag_configure("pending", background="#ffffff")

        paging = ttk.Frame(card_table, style="Card.TFrame")
        paging.pack(fill="x", pady=(8, 0))
        self.page_info = tk.StringVar(value="Sin entradas")
        ttk.Label(paging, textvariable=self.page_info, style="Card.TLabel").pack(side="left")
        ttk.Button(paging, text="Siguiente ›", command=lambda: self.change_page(1)).pack(side="right")
        ttk.Button(paging, text="‹ Anterior", command=lambda: self.change_page(-1)).pack(side="right", padx=8)

        # Barra de navegación inferior
        nav_bottom = ttk.Frame(self.list_tab)
        nav_bottom.pack(fill="x", pady=6)
        ttk.Label(nav_bottom, text="¿Listo para enviar? Continúa al siguiente paso:").pack(side="left")
        ttk.Button(nav_bottom, text="Siguiente: Redactar Mensaje ➜", style="Primary.TButton",
                   command=lambda: self.go_to_tab(1)).pack(side="right")

        self.log = ScrolledText(self.list_tab, height=4, wrap="word", font=("Consolas", 9))
        self.log.configure(state="disabled")

        # Configuración interna de lista y columna
        self.form["lista"] = tk.StringVar()
        self.form["columna"] = tk.StringVar(value="correo")
        self.form["exclusiones"] = tk.StringVar()

    # =========================================================================
    # PASO 2: REDACTAR MENSAJE
    # =========================================================================
    def build_message(self):
        card_id = ttk.Frame(self.message_tab, style="Card.TFrame", padding=16)
        card_id.pack(fill="x", pady=(0, 12))
        ttk.Label(card_id, text="Identificación del Comunicado", style="CardHeader.TLabel").pack(anchor="w")
        ttk.Label(card_id, text="El identificador asegura que ningún destinatario reciba el mismo mensaje dos veces.",
                  style="Card.TLabel").pack(anchor="w", pady=(2, 8))
        self.field(card_id, "campana_id", "Identificador de campaña")
        self.field(card_id, "asunto", "Asunto del correo")

        card_body = ttk.Frame(self.message_tab, style="Card.TFrame", padding=16)
        card_body.pack(fill="both", expand=True, pady=(0, 12))
        
        body_top = ttk.Frame(card_body, style="Card.TFrame")
        body_top.pack(fill="x", pady=(0, 8))
        ttk.Label(body_top, text="Contenido del Mensaje", style="CardHeader.TLabel").pack(side="left")
        
        # Chips de inserción rápida
        chip_bar = ttk.Frame(body_top, style="Card.TFrame")
        chip_bar.pack(side="right")
        ttk.Label(chip_bar, text="Insertar variable:", style="Card.TLabel").pack(side="left", padx=(0, 6))
        ttk.Button(chip_bar, text="[ + Nombre ]", style="Chip.TButton", command=lambda: self.insert_tag("${nombre}")).pack(side="left", padx=2)
        ttk.Button(chip_bar, text="[ + Empresa ]", style="Chip.TButton", command=lambda: self.insert_tag("${empresa}")).pack(side="left", padx=2)
        ttk.Button(chip_bar, text="[ + Correo ]", style="Chip.TButton", command=lambda: self.insert_tag("${correo}")).pack(side="left", padx=2)
        ttk.Button(chip_bar, text="✨ Plantilla de servicios", style="TButton", command=self.offer_template).pack(side="left", padx=(8, 0))

        self.body = ScrolledText(card_body, height=12, wrap="word", font=("Segoe UI", 10))
        self.body.pack(fill="both", expand=True, pady=6)
        ttk.Label(card_body, text="Tip: Las variables ${nombre} y ${empresa} se reemplazan automáticamente con los datos del Excel/CSV de cada contacto.",
                  font=("Segoe UI", 9, "italic"), foreground="#64748b", background="white").pack(anchor="w")

        card_opts = ttk.Frame(self.message_tab, style="Card.TFrame", padding=16)
        card_opts.pack(fill="x", pady=(0, 12))
        ttk.Label(card_opts, text="Opciones Adicionales y Cumplimiento", style="CardHeader.TLabel").pack(anchor="w", pady=(0, 8))
        
        self.field(card_opts, "html", "Diseño HTML (opcional)", browse=[("HTML", "*.html *.htm")])
        self.field(card_opts, "baja_correo", "Correo para recibir bajas")
        ttk.Label(card_opts, text="Se añade automáticamente una instrucción de baja al pie de cada correo para cumplir buenas prácticas antispam.",
                  style="Card.TLabel", font=("Segoe UI", 9)).pack(anchor="w", pady=(0, 10))

        ttk.Label(card_opts, text="Archivos adjuntos (se envían a cada destinatario):", style="CardHeader.TLabel", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(4, 4))
        self.attachment_list = tk.Listbox(card_opts, height=3, font=("Segoe UI", 9), relief="solid", borderwidth=1)
        self.attachment_list.pack(fill="x", pady=4)
        
        att_bar = ttk.Frame(card_opts, style="Card.TFrame")
        att_bar.pack(fill="x", pady=4)
        self.button(att_bar, "➕ Añadir adjuntos…", self.add_attachments)
        self.button(att_bar, "➖ Quitar seleccionado", self.remove_attachment)

        # Navegación inferior
        nav_msg = ttk.Frame(self.message_tab)
        nav_msg.pack(fill="x", pady=6)
        ttk.Button(nav_msg, text="⮜ Volver a Purgar Lista", command=lambda: self.go_to_tab(0)).pack(side="left")
        ttk.Button(nav_msg, text="Siguiente: Conectar Correo ➜", style="Primary.TButton",
                   command=lambda: self.go_to_tab(2)).pack(side="right")
        self.button(nav_msg, "💾 Guardar mensaje", self.save_settings)

    # =========================================================================
    # PASO 3: CUENTA DE CORREO (SMTP)
    # =========================================================================
    def build_account(self):
        card_presets = ttk.Frame(self.account_tab, style="Card.TFrame", padding=16)
        card_presets.pack(fill="x", pady=(0, 12))
        ttk.Label(card_presets, text="Configuración Rápida de Cuenta", style="CardHeader.TLabel").pack(anchor="w")
        ttk.Label(card_presets, text="Selecciona tu proveedor para autocompletar el servidor y puerto de salida:",
                  style="Card.TLabel").pack(anchor="w", pady=(2, 10))
        
        pre_row = ttk.Frame(card_presets, style="Card.TFrame")
        pre_row.pack(fill="x")
        self.button(pre_row, "🔴 Gmail / Google Workspace", self.gmail_preset, primary=True)
        self.button(pre_row, "🔵 Outlook / Office 365", self.outlook_preset)
        self.button(pre_row, "🌐 Servidor Propio / cPanel", self.custom_preset)
        self.button(pre_row, "📂 Cargar JSON…", self.import_settings)

        # Cuadro de ayuda amigable para Gmail
        card_help = ttk.Frame(self.account_tab, style="Card.TFrame", padding=16)
        card_help.pack(fill="x", pady=(0, 12))
        ttk.Label(card_help, text="💡 ¿Cómo configurar Gmail fácilmente?", style="CardHeader.TLabel").pack(anchor="w")
        guide_text = (
            "1. En tu cuenta de Google, entra a Gestionar tu cuenta de Google > Seguridad.\n"
            "2. Activa la «Verificación en dos pasos» si no la tienes activa.\n"
            "3. En la barra de búsqueda de Seguridad escribe «Contraseñas de aplicaciones» y entra.\n"
            "4. Crea una llamada «MxCorreo» y copia las 16 letras generadas.\n"
            "5. Esa es la contraseña que la aplicación te pedirá al enviar (no tu contraseña normal)."
        )
        ttk.Label(card_help, text=guide_text, style="Card.TLabel", font=("Segoe UI", 9)).pack(anchor="w", pady=(4, 0))

        # Campos SMTP
        card_fields = ttk.Frame(self.account_tab, style="Card.TFrame", padding=16)
        card_fields.pack(fill="x", pady=(0, 12))
        ttk.Label(card_fields, text="Datos del Servidor de Envío (SMTP)", style="CardHeader.TLabel").pack(anchor="w", pady=(0, 8))
        
        self.field(card_fields, "remitente", "Correo remitente")
        self.field(card_fields, "nombre", "Nombre visible del remitente")
        self.field(card_fields, "responder_a", "Responder a (opcional)")
        self.field(card_fields, "host", "Servidor SMTP")
        self.field(card_fields, "puerto", "Puerto SMTP", "587")
        self.field(card_fields, "seguridad", "Cifrado", "starttls", choices=("starttls", "ssl"))
        self.field(card_fields, "autenticacion", "Autenticación", "password", choices=("password", "oauth2", "none"))
        self.field(card_fields, "usuario", "Usuario SMTP (suele ser tu correo)")

        # Reaseguro de seguridad
        card_sec = ttk.Frame(self.account_tab, style="Card.TFrame", padding=14)
        card_sec.pack(fill="x", pady=(0, 12))
        ttk.Label(card_sec, text="🔒 Máxima Seguridad y Privacidad:", font=("Segoe UI", 10, "bold"), foreground="#15803d", background="white").pack(anchor="w")
        ttk.Label(card_sec, text="Tu contraseña NUNCA se guarda en el disco. Solo se te solicita de forma segura y temporal al momento de autorizar un envío.",
                  style="Card.TLabel", font=("Segoe UI", 9)).pack(anchor="w")

        # Navegación inferior
        nav_acc = ttk.Frame(self.account_tab)
        nav_acc.pack(fill="x", pady=6)
        ttk.Button(nav_acc, text="⮜ Volver a Redactar Mensaje", command=lambda: self.go_to_tab(1)).pack(side="left")
        ttk.Button(nav_acc, text="Siguiente: Enviar y Resultados ➜", style="Primary.TButton",
                   command=lambda: self.go_to_tab(3)).pack(side="right")
        self.button(nav_acc, "💾 Guardar configuración", self.save_settings)

    # =========================================================================
    # PASO 4: ENVÍO AUTORIZADO Y RESULTADOS
    # =========================================================================
    def build_send(self):
        # Card 1: Prueba previa
        card_test = ttk.Frame(self.send_tab, style="Card.TFrame", padding=16)
        card_test.pack(fill="x", pady=(0, 12))
        ttk.Label(card_test, text="🧪 Modo 1: Prueba Previa en Mi Correo (Recomendado)", style="CardHeader.TLabel").pack(anchor="w")
        ttk.Label(card_test, text="Recibe un correo real en tu propia bandeja de entrada para asegurarte de que el formato, las variables y los adjuntos se vean perfectos antes de enviar a clientes.",
                  style="Card.TLabel").pack(anchor="w", pady=(2, 8))
        
        self.field(card_test, "destino_prueba", "Mi correo de prueba")
        test_bar = ttk.Frame(card_test, style="Card.TFrame")
        test_bar.pack(fill="x", pady=(8, 0))
        self.button(test_bar, "📨 Enviar correo de prueba a mi dirección", lambda: self.launch("prueba"), primary=True)

        # Card 2: Envío masivo por lotes
        card_batch = ttk.Frame(self.send_tab, style="Card.TFrame", padding=16)
        card_batch.pack(fill="x", pady=(0, 12))
        ttk.Label(card_batch, text="🚀 Modo 2: Envío Masivo por Lotes", style="CardHeader.TLabel").pack(anchor="w")
        ttk.Label(card_batch, text="El envío se realiza en lotes controlados con pausas para cuidar la reputación de tu servidor y evitar bloqueos.",
                  style="Card.TLabel").pack(anchor="w", pady=(2, 8))

        self.field(card_batch, "audiencia", "Destinatarios", "Toda la lista autorizada", choices=("Toda la lista autorizada", "Solo autorizados"))
        self.field(card_batch, "autorizados", "Archivo de autorizados (opcional)", browse=[("Texto", "*.txt")])
        self.field(card_batch, "max_por_ejecucion", "Correos por lote", "50")
        self.field(card_batch, "intervalo_segundos", "Pausa entre correos (segundos)", "2")
        self.field(card_batch, "max_24h", "Máximo permitido en 24 h", "400")

        # Lista de confirmación amigable
        ttk.Label(card_batch, text="Lista de verificación de seguridad:", style="CardHeader.TLabel", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(10, 4))
        
        self.real_config = tk.BooleanVar(value=False)
        ttk.Checkbutton(card_batch, text="He configurado mis datos reales de envío (no estoy usando ejemplos).",
                        variable=self.real_config).pack(anchor="w", pady=2)
        
        labels = {
            "remitente_autorizado": "La empresa autorizó el uso de esta cuenta de correo.",
            "envio_aprobado": "El asunto, mensaje y adjuntos están aprobados.",
            "lista_revisada": "Confirmo que la lista de destinatarios está verificada y limpia.",
            "exclusiones_revisadas": "Se aplicaron bajas o confirmo que no hay solicitudes pendientes.",
            "limites_confirmados": "Confirmo los límites y el ritmo seguro de envío.",
        }
        for key, label in labels.items():
            self.approvals[key] = tk.BooleanVar(value=False)
            ttk.Checkbutton(card_batch, text=label, variable=self.approvals[key]).pack(anchor="w", pady=2)

        batch_bar = ttk.Frame(card_batch, style="Card.TFrame")
        batch_bar.pack(fill="x", pady=(12, 0))
        self.button(batch_bar, "👁️ Simular lote (Auditoría sin enviar)", lambda: self.launch("simular"))
        self.button(batch_bar, "🚀 Iniciar Envío por Lotes…", lambda: self.launch("enviar"), primary=True)

        # Card 3: Historial y auditoría
        card_hist = ttk.Frame(self.send_tab, style="Card.TFrame", padding=16)
        card_hist.pack(fill="x", pady=(0, 12))
        ttk.Label(card_hist, text="📊 Historial y Auditoría", style="CardHeader.TLabel").pack(anchor="w", pady=(0, 8))
        
        hist_bar = ttk.Frame(card_hist, style="Card.TFrame")
        hist_bar.pack(fill="x")
        self.button(hist_bar, "📋 Consultar registro de envíos", lambda: self.launch("estado"))
        self.button(hist_bar, "📂 Abrir carpeta de resultados", self.open_results)
        self.button(hist_bar, "📖 Abrir guía de campañas", lambda: self.open_path(resources() / "Guía de campañas.txt"))

        # Navegación inferior
        nav_send = ttk.Frame(self.send_tab)
        nav_send.pack(fill="x", pady=6)
        ttk.Button(nav_send, text="⮜ Volver a Conectar Correo", command=lambda: self.go_to_tab(2)).pack(side="left")

    # =========================================================================
    # LÓGICA Y PRESETS
    # =========================================================================
    def gmail_preset(self):
        for key, value in {"host": "smtp.gmail.com", "puerto": "587", "seguridad": "starttls", "autenticacion": "password"}.items():
            if key in self.form:
                self.form[key].set(value)
        if "remitente" in self.form and "usuario" in self.form and not self.form["usuario"].get():
            self.form["usuario"].set(self.form["remitente"].get())
        self.status.set("Gmail configurado (smtp.gmail.com:587). Recuerda usar tu 'Contraseña de aplicación' de 16 letras.")

    def outlook_preset(self):
        for key, value in {"host": "smtp.office365.com", "puerto": "587", "seguridad": "starttls", "autenticacion": "password"}.items():
            if key in self.form:
                self.form[key].set(value)
        if "remitente" in self.form and "usuario" in self.form and not self.form["usuario"].get():
            self.form["usuario"].set(self.form["remitente"].get())
        self.status.set("Outlook / Office 365 configurado (smtp.office365.com:587).")

    def custom_preset(self):
        for key, value in {"puerto": "587", "seguridad": "starttls", "autenticacion": "password"}.items():
            if key in self.form:
                self.form[key].set(value)
        self.status.set("Servidor propio: completa el servidor SMTP y credenciales de tu hosting.")

    def load_initial(self):
        path = self.data_dir / "configuracion.json"
        if not path.exists():
            path = resources() / "campana.ejemplo.json"
        try:
            self.apply_config(campana.load_config(path), path.parent)
        except Exception as exc:
            messagebox.showwarning("Aviso de inicio", f"Se abrirá la plantilla base. {type(exc).__name__}", parent=self.root)
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
        self.form["max_24h"].set(str(cfg["limites"].get("max_24h", 400)))
        self.form["baja_correo"].set(cfg["mensaje"].get("baja_correo", ""))
        for flag in self.approvals.values():
            flag.set(False)
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
        cfg["mensaje"]["baja_correo"] = self.form["baja_correo"].get().strip()
        for key in ("host", "seguridad", "autenticacion", "usuario"):
            cfg["smtp"][key] = self.form[key].get().strip()
        cfg["smtp"]["puerto"] = int(self.form["puerto"].get())
        cfg["limites"]["max_por_ejecucion"] = int(self.form["max_por_ejecucion"].get())
        cfg["limites"]["max_24h"] = int(self.form["max_24h"].get())
        cfg["limites"]["intervalo_segundos"] = float(self.form["intervalo_segundos"].get())
        cfg["autorizacion"] = {key: var.get() for key, var in self.approvals.items()}
        if remember:
            cfg["autorizacion"] = {key: False for key in cfg["autorizacion"]}
        text = self.body.get("1.0", "end-1c")
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
            self.status.set("Configuración guardada de forma segura (sin contraseñas).")
            messagebox.showinfo("Guardado", "Configuración guardada correctamente.", parent=self.root)
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
        save_json_atomic(self.data_dir / "sesion.json", {key: self.form[key].get() for key in ("lista", "exclusiones", "autorizados", "audiencia") if key in self.form})

    def offer_template(self):
        if not messagebox.askyesno("Plantilla de presentación", "¿Deseas cargar una plantilla profesional de presentación de servicios?", parent=self.root):
            return
        self.body.delete("1.0", "end")
        self.body.insert("1.0", OFFER_TEMPLATE)
        self.form["asunto"].set("Presentación de nuestros servicios profesionales")
        self.form["campana_id"].set("servicios-" + campana.uuid.uuid4().hex[:10])
        self.status.set("Plantilla cargada. Completa los campos entre corchetes con los datos de tu empresa.")

    def open_review(self):
        if self.busy:
            return
        path = filedialog.askopenfilename(parent=self.root, title="Elige Detalle.json o informe.json", filetypes=[("Informe de revisión", "*.json")])
        if path:
            self.local_task("review_imported", lambda: import_report(path, self.data_dir, self.stop_event), "Integrando la revisión anterior…")

    def edit_addresses(self, key, title):
        if self.busy:
            return
        path = Path(self.form[key].get()) if self.form[key].get() else self.data_dir / (key + ".txt")
        try:
            existing = path.read_text(encoding="utf-8-sig") if path.exists() else ""
        except OSError as exc:
            messagebox.showerror(title, str(exc), parent=self.root)
            return
        dialog = tk.Toplevel(self.root)
        dialog.title(title)
        dialog.transient(self.root)
        dialog.grab_set()
        ttk.Label(dialog, text="Un correo por línea. Las bajas prevalecen sobre cualquier autorización.").pack(padx=16, pady=12)
        editor = ScrolledText(dialog, width=70, height=18, font=("Consolas", 10))
        editor.pack(padx=16, pady=8)
        editor.insert("1.0", existing)

        def save():
            try:
                values = sorted({campana.address(line).casefold() for line in editor.get("1.0", "end").splitlines() if line.strip()})
                destination = self.data_dir / (key + ".txt")
                with tempfile.NamedTemporaryFile("w", encoding="utf-8-sig", dir=self.data_dir, delete=False) as stream:
                    stream.write("\n".join(values) + ("\n" if values else ""))
                os.replace(stream.name, destination)
                self.form[key].set(str(destination))
                self.save_session()
                dialog.destroy()
                self.status.set(f"{title}: {len(values):,} direcciones guardadas.")
            except (ValueError, OSError) as exc:
                messagebox.showerror("Revisa las direcciones", str(exc), parent=dialog)
        ttk.Button(dialog, text="Guardar lista", style="Primary.TButton", command=save).pack(pady=12)

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
            button.configure(state="disabled" if value else "normal")
        for index in (1, 2, 3):
            self.book.tab(index, state="disabled" if value else "normal")
        self.stop_button.configure(state="normal" if value else "disabled")
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
                self.events.put(("local_done", (kind, result, "")))
            except Exception as exc:
                self.events.put(("local_done", (kind, None, str(exc))))
        threading.Thread(target=task, daemon=True).start()

    def auto_files(self):
        if self.busy:
            return
        paths = filedialog.askopenfilenames(parent=self.root, title="Selecciona uno o varios archivos",
                                            filetypes=[("Listas de contactos", "*.xlsx *.xls *.csv *.txt")])
        self.detect_files(paths)

    def auto_folder(self):
        if self.busy:
            return
        folder = filedialog.askdirectory(parent=self.root, title="Selecciona la carpeta con tus archivos")
        if folder:
            self.local_task("detected", lambda: scan_files(sorted(p for p in Path(folder).rglob("*")
                if p.is_file() and p.suffix.lower() in EXTENSIONS and not p.name.startswith(("~$", "._"))),
                self.stop_event, lambda message: self.events.put(("local_progress", message))), "Buscando archivos de contactos…")

    def detect_files(self, paths):
        if not paths or self.busy:
            return
        self.local_task("detected", lambda: scan_files(paths, self.stop_event,
            lambda message: self.events.put(("local_progress", message))), "Buscando columnas de correo…")

    def saved_list(self):
        if self.busy:
            return
        path = filedialog.askopenfilename(parent=self.root, title="Continuar con una lista guardada", filetypes=[("Importaciones", "*.mxlista")])
        if path:
            self.local_task("imported", lambda: (Path(path), load_import(Path(path), self.stop_event), "Lista guardada"), "Abriendo la lista…")

    def export_csv(self):
        if self.busy or not self.rows:
            if not self.busy:
                messagebox.showinfo("Primero carga una lista", "Carga tus archivos antes de exportar.", parent=self.root)
            return
        if any(not row.get("estado") for row in self.rows):
            if not messagebox.askyesno("Hay entradas sin revisar", "Hay correos sin revisar. Se exportarán en la categoría «Por revisar». ¿Continuar?", parent=self.root):
                return
        folder = filedialog.askdirectory(parent=self.root, title="Dónde guardar las listas limpias en CSV")
        if folder:
            rows = self.rows
            self.local_task("exported", lambda: export_lists(rows, folder), "Guardando listas limpias CSV…")

    def schedule_filter(self, *_):
        if self.search_job:
            self.root.after_cancel(self.search_job)
        self.search_job = self.root.after(200, self.apply_filter)

    def apply_filter(self):
        self.search_job = None
        category, search = self.category.get(), self.search.get().strip()
        self.filtered = [i for i, row in enumerate(self.rows) if matches(row, category, search)]
        self.page = 0
        self.render_page()

    def set_rows(self, rows):
        self.rows = rows
        for key in ("APTO_DNS", "INVALIDO"):
            self.metrics[key].set(f"{sum(r.get('estado') == key for r in rows):,}")
        self.metrics["total"].set(f"{len(rows):,}")
        self.metrics["pending"].set(f"{sum(r.get('estado', '') in {'', 'REVISAR'} for r in rows):,}")
        self.metrics["duplicates"].set(f"{sum(r.get('duplicado_de_linea') is not None for r in rows):,}")
        self.category.set("Todos")
        self.search.set("")
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
            reason = row.get("motivo") or "Pendiente de revisar dominios."
            origin = row.get("origen", {})
            location = " / ".join(str(v) for v in (origin.get("archivo"), origin.get("hoja"), row.get("celda_origen")) if v)
            if location:
                reason = location + " · " + reason
            if row.get("duplicado_de_linea") is not None:
                reason = f"Repetido de entrada {row['duplicado_de_linea']} · " + reason
            state = row.get("estado", "")
            self.table.insert("", "end", iid=str(i), values=(row["original"], LABELS.get(state, state), reason), tags=(state or "pending",))
        count = len(self.filtered)
        self.page_info.set(f"{start + 1 if count else 0}–{min(start + 200, count)} de {count:,} entradas · La exportación incluye toda la lista.")

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
                raise ImportCancelled("Importación cancelada.")
            path = save_import(contacts, source, self.data_dir)
            rows = load_import(path, self.stop_event, lambda number: self.events.put(("local_progress", f"Preparando {number:,} entradas…")))
            if self.stop_event.is_set():
                raise ImportCancelled("Importación cancelada. Se conserva la lista anterior.")
            return path, rows, source["archivo"]
        self.local_task("imported", prepare, "Preparando tu lista y detectando duplicados…")

    def add_attachments(self):
        for path in filedialog.askopenfilenames(parent=self.root, title="Selecciona los adjuntos"):
            if path not in self.attachments:
                self.attachments.append(path)
        self.refresh_attachments()

    def remove_attachment(self):
        for index in reversed(self.attachment_list.curselection()):
            self.attachments.pop(index)
        self.refresh_attachments()

    def refresh_attachments(self):
        self.attachment_list.delete(0, "end")
        for path in self.attachments:
            self.attachment_list.insert("end", Path(path).name + f" ({path})")

    def example(self):
        self.set_rows([])
        self.form["lista"].set(str(resources() / "ejemplo.txt"))
        self.launch("revisar")

    def launch(self, mode):
        if self.busy:
            return
        try:
            file = self.form["lista"].get().strip() if "lista" in self.form else ""
            if mode not in {"prueba", "estado"} and file and Path(file).suffix.lower() in EXCEL_EXTENSIONS:
                self.import_excel(file)
                file = self.form["lista"].get().strip()
                if Path(file).suffix.lower() in EXCEL_EXTENSIONS:
                    return
            if mode not in {"prueba", "estado"} and not file:
                raise ValueError("Carga tus archivos en el Paso 1 o pulsa «Probar con ejemplo».")
            authorized = self.form["autorizados"].get().strip() if self.form["audiencia"].get() == "Solo autorizados" else ""
            if mode in {"simular", "enviar"} and self.form["audiencia"].get() == "Solo autorizados" and not authorized:
                raise ValueError("Indica el archivo de autorizados o selecciona 'Toda la lista autorizada'.")
            if mode in {"enviar", "prueba"}:
                if not self.form["baja_correo"].get().strip():
                    raise ValueError("Completa el correo para recibir bajas en la pestaña Mensaje.")
                if any(token in self.body.get("1.0", "end") for token in ("[TU NOMBRE", "[NOMBRE DE LA EMPRESA]", "[SERVICIO]", "[TIPO DE CLIENTE]", "[NECESIDAD CONCRETA]", "[EXPLICA", "[EMPRESA")):
                    raise ValueError("Completa los campos entre corchetes de la plantilla antes de enviar.")
            config_path = resources() / "campana.ejemplo.json"
            if mode != "revisar":
                run_folder = Path(tempfile.mkdtemp(prefix="ejecucion_", dir=self.data_dir))
                config_path = self.collect_config(run_folder)
            args = argparse.Namespace(
                archivo=Path(file) if mode not in {"prueba", "estado"} else None,
                config=config_path, modo=mode, destino_prueba=self.form["destino_prueba"].get().strip() if mode == "prueba" else None,
                exclusiones=Path(self.form["exclusiones"].get().strip()) if self.form.get("exclusiones") and self.form["exclusiones"].get().strip() else None,
                autorizados=Path(authorized) if authorized and mode in {"simular", "enviar"} else None,
                columna_correo=self.form.get("columna", tk.StringVar(value="correo")).get().strip() or "correo", separador=None,
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
        if mode == "revisar":
            self.book.select(0)
        self.stop_button.configure(state="normal")
        self.progress.start(12)
        self.status.set("Trabajando en segundo plano. No cierres la ventana.")
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
            secret = "" if cfg["smtp"]["autenticacion"] == "none" else self.ask_from_worker("secret", "Introduce la contraseña o contraseña de aplicación para conectar a tu correo. No se guardará en el disco.")
            if self.stop_event.is_set():
                raise ValueError("Operación detenida.")
            return campana.connect_smtp(cfg, secret=secret)
        try:
            with redirect_stdout(QueueWriter(self.events)):
                code = campana.run(args, confirm=lambda prompt: self.ask_from_worker("confirm", prompt),
                                   connector=connector, stop_event=self.stop_event,
                                   on_output=lambda folder: self.events.put(("output", folder)))
        except (smtplib.SMTPException, OSError) as exc:
            error = f"{type(exc).__name__}: verifica la conexión a Internet y tus credenciales SMTP."
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
                elif kind == "local_progress":
                    self.status.set(payload)
                elif kind == "local_done":
                    operation, result, error = payload
                    stopped = self.stop_event.is_set()
                    self.set_busy(False)
                    if error:
                        self.status.set(error)
                        if not stopped:
                            messagebox.showerror("No se pudo completar", error, parent=self.root)
                    elif operation == "detected":
                        if stopped:
                            self.status.set("Importación cancelada.")
                            continue
                        groups, issues = result
                        if not groups:
                            messagebox.showinfo("No se encontraron columnas", "\n".join(issues) or "No hay archivos válidos.", parent=self.root)
                            self.status.set("Sin cambios. Prueba con otro archivo o carpeta.")
                            continue
                        self.status.set("Confirma las columnas a importar.")
                        dialog = DetectionDialog(self.root, groups, issues)
                        if dialog.result:
                            files = len({c["archivo_origen"] for c in dialog.result})
                            self.accept_import(dialog.result, {"tipo": "deteccion automatica", "archivo": f"{files} archivos"})
                        else:
                            self.status.set("Importación cancelada.")
                    elif operation in {"imported", "review_imported"}:
                        if stopped:
                            self.status.set("Importación cancelada.")
                            continue
                        path, rows, label = result
                        self.form["lista"].set(str(path))
                        self.save_session()
                        self.last_folder = None
                        self.set_rows(rows)
                        self.import_info.set(f"✅ {label} · {len(rows):,} contactos cargados. Archivos originales intactos.")
                        self.summary.set(f"Lista cargada ({len(rows):,} contactos). Pulsa «REVISAR Y PURGAR LISTA» para verificar los correos.")
                        self.status.set("Contactos cargados. Listo para purgar.")
                    elif operation == "exported":
                        folder, counts = result
                        self.status.set(f"Listas guardadas en: {folder}")
                        messagebox.showinfo("Listas exportadas con éxito", "\n".join(f"{name}: {count:,}" for name, count in counts.items()) + f"\n\nGuardado en:\n{folder}", parent=self.root)
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
                            payload["answer"] = simpledialog.askstring("Contraseña de correo", payload["prompt"], show="*", parent=self.root)
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
                    self.status.set("Operación terminada." if not error else f"Aviso: {error}")
                    result = self.last_folder / "envio.json" if self.last_folder else None
                    if result and result.exists():
                        delivery = json.loads(result.read_text(encoding="utf-8"))
                        self.summary.set("Resultado del envío: " + ", ".join(f"{k}: {v:,}" for k, v in delivery["lote"].items()))
                    if error:
                        messagebox.showerror("Aviso de ejecución", error, parent=self.root)
                    else:
                        if self.last_folder and (self.last_folder / "informe.json").exists():
                            messagebox.showinfo("Purga completada", "La revisión y purga de correos ha terminado. Revisa las métricas y exporta tus listas limpias.", parent=self.root)
        except queue.Empty:
            pass
        self.root.after(100, self.poll)

    def confirmation_detail(self):
        cfg = self.run_cfg
        intro = f"Servidor SMTP: {cfg['smtp']['host']}:{cfg['smtp']['puerto']}\nRemitente: {cfg['remitente']['correo']}\n\n"
        if self.last_folder:
            sample_path = self.last_folder / "vista_previa.txt"
            audit_path = self.last_folder / "seleccion.json"
            sample = sample_path.read_text(encoding="utf-8") if sample_path.exists() else ""
            recipients = []
            if audit_path.exists():
                audit = json.loads(audit_path.read_text(encoding="utf-8"))
                recipients = [item["correo"] for item in audit.get("decisiones", []) if item.get("decision") == "SELECCIONADO"]
            return intro + sample + "\nDESTINATARIOS EXACTOS DE ESTE LOTE:\n" + "\n".join(recipients)
        return intro

    def show_results(self):
        path = self.last_folder / "informe.json"
        if not path.exists():
            history = self.last_folder / "estado_envios.json"
            if history.exists():
                entries = json.loads(history.read_text(encoding="utf-8"))["envios"]
                counts = campana.Counter(row["status"] for row in entries)
                self.summary.set("Historial de envíos: " + (", ".join(f"{k}: {v:,}" for k, v in counts.items()) or "Sin envíos registrados."))
            return
        report = json.loads(path.read_text(encoding="utf-8"))
        self.set_rows(report["resultados"])
        self.summary.set(f"Purga lista · {report['total']:,} revisados · Haz clic en «Exportar Listas Limpias» para guardarlas.")

    def row_detail(self, _event=None):
        selection = self.table.selection()
        if selection:
            values = self.table.item(selection[0], "values")
            messagebox.showinfo("Detalle del contacto", "\n\n".join(values), parent=self.root)

    def open_path(self, path):
        try:
            open_local_path(path)
        except (OSError, subprocess.SubprocessError):
            messagebox.showinfo("Ruta del archivo", f"Abre la siguiente ruta en tu explorador:\n{path.resolve()}", parent=self.root)

    def open_result(self, name):
        if self.last_folder and (self.last_folder / name).exists():
            self.open_path(self.last_folder / name)
        else:
            messagebox.showinfo("Aún no generado", "Realiza la purga o simulación primero para generar este archivo.", parent=self.root)

    def open_results(self):
        folder = self.last_folder or self.data_dir
        self.open_path(folder)

    def stop(self):
        self.stop_event.set()
        self.status.set("Deteniendo de forma segura. Espera un momento…")

    def close(self):
        if self.busy:
            self.stop()
            messagebox.showinfo("Espera un momento", "Deteniendo la operación antes de cerrar…", parent=self.root)
            return
        self.root.destroy()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--datos", type=Path, default=None, help="Carpeta de datos alternativa")
    args = parser.parse_args()
    root = tk.Tk()
    try:
        App(root, args.datos or default_data_dir())
    except Exception as exc:
        root.withdraw()
        messagebox.showerror("No se pudo iniciar", f"{type(exc).__name__}: {exc}", parent=root)
        root.destroy()
        return 1
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
