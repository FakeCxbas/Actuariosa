"""Small native launcher for the Windows distribution."""
import json
import secrets
import sys
import threading
import tkinter as tk
import webbrowser
from http.server import ThreadingHTTPServer
from tkinter import messagebox
from urllib.request import urlopen

from inventory import Inventory
from server import DEFAULT_DATA, handler_for, main as server_main


def main():
    if '--no-browser' in sys.argv:
        return server_main()
    root = tk.Tk()
    root.withdraw()
    port = 8765
    url = f'http://127.0.0.1:{port}'
    try:
        inventory = Inventory(DEFAULT_DATA / 'nexo.sqlite3')
        server = ThreadingHTTPServer(('127.0.0.1', port), handler_for(inventory, secrets.token_urlsafe(32)))
    except OSError:
        try:
            with urlopen(url + '/health', timeout=2) as response:
                if json.load(response).get('app') != 'nexo-inventario':
                    raise ValueError('Puerto ocupado')
            webbrowser.open(url)
        except Exception:
            messagebox.showerror('Nexo Inventario', 'No se pudo iniciar: el puerto 8765 está ocupado por otra aplicación.')
        root.destroy()
        return
    except Exception:
        messagebox.showerror('Nexo Inventario', 'No se pudo abrir la base de datos. Verifica el acceso a la carpeta de datos.')
        root.destroy()
        return
    threading.Thread(target=server.serve_forever, daemon=True).start()
    root.title('Nexo Inventario')
    root.geometry('490x300')
    root.resizable(False, False)
    root.configure(bg='#102d27')
    tk.Label(root, text='nexo', font=('Segoe UI', 30, 'bold'), fg='#d4efb9', bg='#102d27').pack(pady=(22,0))
    tk.Label(root, text='INVENTARIO · EDICIÓN LOCAL', font=('Segoe UI', 9), fg='#a7bfb0', bg='#102d27').pack()
    tk.Label(root, text='Tu espacio está abierto y guardando en este equipo.', font=('Segoe UI', 10), fg='white', bg='#102d27').pack(pady=19)
    tk.Button(root, text='Abrir Nexo Inventario  →', command=lambda:webbrowser.open(url), bg='#d4efb9', fg='#163b2c', font=('Segoe UI',11,'bold'), relief='flat', padx=25, pady=10, cursor='hand2').pack()
    tk.Label(root, text='Mantén esta ventana abierta mientras utilizas la aplicación.\nAl cerrarla se detiene Nexo; tus datos permanecen guardados.', font=('Segoe UI',9), fg='#a7bfb0', bg='#102d27').pack(pady=17)
    def close():
        server.shutdown()
        server.server_close()
        root.destroy()
    root.protocol('WM_DELETE_WINDOW', close)
    root.deiconify()
    root.after(400, lambda:webbrowser.open(url))
    root.mainloop()


if __name__ == '__main__':
    main()
