"""Diálogos de importación. No consultan DNS ni envían mensajes."""
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
from tkinter.scrolledtext import ScrolledText

from importar_contactos import column_letter, extract_excel, extract_pasted, open_excel, read_sheet


class ImportDialog(simpledialog.Dialog):
    def buttonbox(self):
        box = ttk.Frame(self)
        box.pack(pady=10)
        ttk.Button(box, text="Importar esta lista (sin enviar)", command=self.ok).pack(side="left", padx=8)
        ttk.Button(box, text="Cancelar", command=self.cancel).pack(side="left", padx=8)
        self.bind("<Escape>", self.cancel)


class ExcelDialog(ImportDialog):
    def __init__(self, parent, path):
        self.path = Path(path)
        self.workbook = open_excel(path)
        self.table = []
        self.contacts = []
        self.result = None
        try:
            if not self.workbook.sheet_names:
                raise ValueError("El Excel no tiene hojas disponibles.")
            super().__init__(parent, "Importar Excel — elige hoja y columnas")
        finally:
            self.workbook.close()

    def body(self, master):
        ttk.Label(master, text=self.path.name, font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=8)
        ttk.Label(master, text="Solo se importan las columnas que elijas. Tu archivo original no se modifica.").pack(anchor="w")
        self.sheet = tk.StringVar(value=self.workbook.sheet_names[0])
        line = ttk.Frame(master)
        line.pack(fill="x", pady=7)
        ttk.Label(line, text="Hoja", width=22).pack(side="left")
        selector = ttk.Combobox(line, textvariable=self.sheet, values=self.workbook.sheet_names, state="readonly", width=55)
        selector.pack(side="left", fill="x", expand=True)
        selector.bind("<<ComboboxSelected>>", self.change_sheet)
        self.first = tk.StringVar(value="1")
        line = ttk.Frame(master)
        line.pack(fill="x", pady=7)
        ttk.Label(line, text="Primera fila a leer", width=22).pack(side="left")
        ttk.Spinbox(line, from_=1, to=100000, textvariable=self.first, width=8).pack(side="left")
        self.header = tk.BooleanVar(value=True)
        ttk.Checkbutton(line, text="Esta fila contiene títulos (no importar)", variable=self.header,
                        command=self.update_columns).pack(side="left", padx=8)
        ttk.Button(line, text="Actualizar", command=self.update_columns).pack(side="left")
        self.fields, self.boxes = {}, {}
        for key, title in (("correo", "Columna de correo"), ("nombre", "Nombre (opcional)"), ("empresa", "Empresa (opcional)")):
            line = ttk.Frame(master)
            line.pack(fill="x", pady=5)
            ttk.Label(line, text=title, width=22).pack(side="left")
            self.fields[key] = tk.StringVar()
            box = ttk.Combobox(line, textvariable=self.fields[key], state="readonly", width=55)
            box.pack(side="left", fill="x", expand=True)
            box.bind("<<ComboboxSelected>>", self.update_preview)
            self.boxes[key] = box
        ttk.Label(master, text="Vista previa (primeras 8 entradas; se conservan duplicados y errores para la revisión):").pack(anchor="w", pady=(12, 5))
        self.preview = ttk.Treeview(master, columns=("fila", "correo", "nombre", "empresa"), show="headings", height=8)
        for key, width in (("fila", 65), ("correo", 300), ("nombre", 150), ("empresa", 150)):
            self.preview.heading(key, text=key.capitalize())
            self.preview.column(key, width=width)
        self.preview.pack(fill="x")
        self.info = tk.StringVar()
        ttk.Label(master, textvariable=self.info, wraplength=700).pack(anchor="w", pady=8)
        ttk.Label(master, text="Se leen también las filas ocultas o filtradas. Las fórmulas usan el último valor guardado:\nsi falta o está desactualizado, recalcula y guarda el Excel, o pega valores antes de importar.", wraplength=700).pack(anchor="w", pady=5)
        self.change_sheet()
        return selector

    def change_sheet(self, _event=None):
        try:
            self.table = read_sheet(self.workbook, self.sheet.get())
            start = next((i + 1 for i, row in enumerate(self.table) if any(str(v).strip() for v in row)), 1)
            self.first.set(str(start))
            first = self.table[start - 1] if self.table else []
            self.header.set(not any("@" in str(v) for v in first))
            self.update_columns()
        except Exception as exc:
            self.table = []
            self.contacts = []
            self.info.set(str(exc))

    def update_columns(self, _event=None):
        try:
            first = int(self.first.get())
            if not 1 <= first <= len(self.table):
                raise ValueError("La fila inicial no existe o la hoja está vacía.")
            width = max(len(row) for row in self.table)
            titles = self.table[first - 1] if self.header.get() else []
            self.labels = [f"{column_letter(i)} — {str(titles[i])[:50] if i < len(titles) else '(sin título)'}" for i in range(width)]
            aliases = {"correo": {"correo", "email", "e-mail", "correo electrónico", "correoelectronico"},
                       "nombre": {"nombre", "name", "nombres"}, "empresa": {"empresa", "company"}}
            for key, box in self.boxes.items():
                box.configure(values=self.labels if key == "correo" else ["(No importar)"] + self.labels)
                found = next((i for i, title in enumerate(titles) if str(title).strip().lower() in aliases[key]), None)
                if key == "correo" and found is None and self.labels:
                    # Sugerencia visible; el usuario confirma con vista previa antes de importar.
                    found = next((i for row in self.table[first - 1:first + 8] for i, value in enumerate(row) if "@" in str(value)), 0)
                self.fields[key].set(self.labels[found] if found is not None and found < len(self.labels) else "(No importar)")
            self.update_preview()
        except Exception as exc:
            self.contacts = []
            self.info.set(str(exc))

    def selection(self):
        def index(key):
            value = self.fields[key].get()
            return self.labels.index(value) if value in self.labels else None
        return dict(first_row=int(self.first.get()), has_header=self.header.get(), email_column=index("correo"),
                    name_column=index("nombre"), company_column=index("empresa"))

    def update_preview(self, _event=None):
        for item in self.preview.get_children():
            self.preview.delete(item)
        try:
            self.contacts = extract_excel(self.table, **self.selection())
            for contact in self.contacts[:8]:
                self.preview.insert("", "end", values=(contact["fila_origen"], contact["correo"], contact["nombre"], contact["empresa"]))
            self.info.set(f"Se importarán {len(self.contacts)} entradas. Las celdas vacías de correo se omiten; las demás se conservan.")
        except Exception as exc:
            self.contacts = []
            self.info.set(str(exc))

    def validate(self):
        self.update_preview()
        if not self.contacts:
            messagebox.showwarning("Revisa la selección", "No hay entradas en esa hoja, fila y columna. Comprueba la vista previa.", parent=self)
            return False
        return True

    def apply(self):
        self.result = (self.contacts, {"tipo": "excel", "archivo": self.path.name, "hoja": self.sheet.get()})


class PasteDialog(ImportDialog):
    def __init__(self, parent):
        self.result = None
        self.contacts = []
        super().__init__(parent, "Pegar correos — sin enviar mensajes")

    def body(self, master):
        ttk.Label(master, text="Pega aquí con Ctrl+V una lista o la columna de correos de Excel.", font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=8)
        ttk.Label(master, text="Puedes separar direcciones con Enter, comas, punto y coma o tabulaciones.\nTambién acepta Nombre <correo@dominio.com>. No pegues la tabla completa con otras columnas.").pack(anchor="w", pady=5)
        self.text = ScrolledText(master, width=80, height=16, wrap="word", font=("Segoe UI", 10))
        self.text.pack(fill="both", expand=True)
        self.text.bind("<<Modified>>", self.changed)
        self.info = tk.StringVar(value="Todavía no hay direcciones. No se consulta DNS ni se envían mensajes al pegarlas.")
        ttk.Label(master, textvariable=self.info, wraplength=680).pack(anchor="w", pady=8)
        return self.text

    def changed(self, _event=None):
        if not self.text.edit_modified():
            return
        self.text.edit_modified(False)
        self.update_count()

    def update_count(self):
        try:
            self.contacts = extract_pasted(self.text.get("1.0", "end-1c"))
            self.info.set(f"{len(self.contacts)} entradas para importar. Se conservarán los duplicados y posibles errores para revisarlos.")
        except ValueError as exc:
            self.contacts = []
            self.info.set(str(exc))

    def validate(self):
        self.update_count()
        if not self.contacts:
            messagebox.showwarning("Lista vacía", "Pega al menos una dirección.", parent=self)
            return False
        return True

    def apply(self):
        self.result = (self.contacts, {"tipo": "texto pegado", "archivo": "Lista pegada"})


class DetectionDialog(ImportDialog):
    """Confirm the detected columns, not hundreds of thousands of table rows."""
    def __init__(self, parent, groups, issues):
        self.groups, self.issues = groups, issues
        self.result = None
        super().__init__(parent, 'Confirma los correos encontrados')

    def body(self, master):
        ttk.Label(master, text='Encontramos estas columnas', style='Section.TLabel').pack(anchor='w', pady=8)
        ttk.Label(master, text='Selecciona las columnas que quieras reunir. Ctrl + clic permite quitar o añadir una.').pack(anchor='w')
        area = ttk.Frame(master)
        area.pack(fill='both', expand=True, pady=10)
        self.detected = ttk.Treeview(area, columns=('archivo', 'hoja', 'columna', 'cantidad'), show='headings', height=10, selectmode='extended')
        for key, title, width in [('archivo', 'Archivo', 330), ('hoja', 'Hoja', 210), ('columna', 'Columna', 110), ('cantidad', 'Entradas', 90)]:
            self.detected.heading(key, text=title)
            self.detected.column(key, width=width)
        scroll = ttk.Scrollbar(area, command=self.detected.yview)
        scroll.pack(side='right', fill='y')
        self.detected.configure(yscrollcommand=scroll.set)
        self.detected.pack(fill='both', expand=True)
        for i, group in enumerate(self.groups):
            self.detected.insert('', 'end', iid=str(i), values=(group['archivo'], group['hoja'], group['columna'], f"{len(group['contacts']):,}"))
        controls = ttk.Frame(master)
        controls.pack(fill='x')
        ttk.Button(controls, text='Seleccionar todas', command=lambda: self.detected.selection_set(self.detected.get_children())).pack(side='left')
        ttk.Button(controls, text='Quitar selección', command=lambda: self.detected.selection_remove(self.detected.selection())).pack(side='left', padx=8)
        self.info = tk.StringVar()
        ttk.Label(master, textvariable=self.info).pack(anchor='w', pady=8)
        self.sample = ScrolledText(master, height=6, width=94, font=('Segoe UI', 10), wrap='word')
        self.sample.pack(fill='x')
        self.detected.bind('<<TreeviewSelect>>', self.update_selection)
        self.detected.selection_set(self.detected.get_children())
        ttk.Label(master, text='Incluye filas ocultas y filtradas. Las fórmulas usan su último valor guardado.\nSe conservan duplicados y posibles errores para revisarlos después.', wraplength=740).pack(anchor='w', pady=8)
        if self.issues:
            ttk.Label(master, text=f'{len(self.issues)} archivos necesitan atención. No se importaron sus datos.', foreground='#9a5416').pack(anchor='w')
            notices = ScrolledText(master, height=4, width=94, wrap='word')
            notices.pack(fill='x', pady=5)
            notices.insert('1.0', '\n'.join(self.issues))
            notices.configure(state='disabled')
        self.update_selection()
        return self.detected

    def update_selection(self, _event=None):
        selected = [self.groups[int(i)] for i in self.detected.selection()]
        self.info.set(f"{len(selected)} columnas seleccionadas · {sum(len(g['contacts']) for g in selected):,} entradas")
        self.sample.configure(state='normal')
        self.sample.delete('1.0', 'end')
        focus = self.detected.focus()
        group = self.groups[int(focus)] if focus else (selected[0] if selected else None)
        if group:
            self.sample.insert('1.0', f"Vista previa: {group['archivo']} / {group['hoja']} / {group['columna']}\n" + '\n'.join(c['correo'] for c in group['contacts'][:5]))
        self.sample.configure(state='disabled')

    def validate(self):
        if not self.detected.selection():
            messagebox.showwarning('Selecciona una columna', 'Selecciona al menos una columna con entradas.', parent=self)
            return False
        return True

    def apply(self):
        self.result = [c for i in self.detected.selection() for c in self.groups[int(i)]['contacts']]
