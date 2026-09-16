"""Loopback-only application server. No third-party runtime dependencies."""
from __future__ import annotations

import argparse
import json
import mimetypes
import os
import secrets
import sys
import tempfile
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from urllib.request import urlopen

from inventory import Inventory, ValidationError, require

ASSETS = Path(getattr(sys, '_MEIPASS', Path(__file__).parent)) / 'static'
DEFAULT_DATA = Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'NexoInventario' / 'data'


def handler_for(inventory, token):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            # Request paths may contain private business data. Do not log them.
            pass

        def send(self, status, body, content_type='application/json; charset=utf-8', filename=None):
            if isinstance(body, dict):
                body = json.dumps(body, ensure_ascii=False).encode('utf-8')
            if isinstance(body, str):
                body = body.encode('utf-8')
            self.send_response(status)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Referrer-Policy', 'no-referrer')
            self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; form-action 'self'; base-uri 'none'")
            if filename:
                self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
            self.end_headers()
            self.wfile.write(body)

        def run_request(self, mutate=False):
            try:
                expected_host = f'127.0.0.1:{self.server.server_port}'
                if self.headers.get('Host') != expected_host:
                    return self.send(403, {'error': 'Acceso permitido únicamente desde este equipo.'})
                parsed = urlparse(self.path)
                path = parsed.path
                if not mutate and path == '/health':
                    return self.send(200, {'app': 'nexo-inventario', 'version': '0.1.0'})
                if not mutate and path in {'/', '/app.js', '/style.css', '/icon.svg'}:
                    file = ASSETS / ('index.html' if path == '/' else path[1:])
                    body = file.read_bytes()
                    if path == '/':
                        body = body.replace(b'__NEXO_TOKEN__', token.encode())
                    return self.send(200, body, (mimetypes.guess_type(str(file))[0] or 'application/octet-stream') + '; charset=utf-8')
                if not path.startswith('/api/'):
                    return self.send(404, {'error': 'Ruta no encontrada.'})
                if not secrets.compare_digest(self.headers.get('X-Nexo-Token', ''), token):
                    return self.send(403, {'error': 'Sesión local vencida. Recarga la página.'})
                query = parse_qs(parsed.query)
                company = int(query['company'][0]) if query.get('company') else None
                if not mutate:
                    if path == '/api/state':
                        return self.send(200, inventory.snapshot(company))
                    if path == '/api/export':
                        kind = query.get('kind', ['products'])[0]
                        return self.send(200, inventory.export_csv(company, kind), 'text/csv; charset=utf-8', f'nexo-{kind}.csv')
                    if path == '/api/backup':
                        with tempfile.TemporaryDirectory() as folder:
                            dest = Path(folder) / 'nexo-backup.sqlite3'
                            inventory.backup(dest)
                            return self.send(200, dest.read_bytes(), 'application/octet-stream', 'nexo-backup.sqlite3')
                    return self.send(404, {'error': 'Ruta no encontrada.'})
                require(self.headers.get('Content-Type', '').startswith('application/json'), 'Envía los datos como JSON.')
                size = int(self.headers.get('Content-Length', '0'))
                require(0 < size <= 3_000_000, 'Solicitud vacía o demasiado grande.')
                data = json.loads(self.rfile.read(size))
                require(isinstance(data, dict), 'Datos inválidos.')
                if path == '/api/companies':
                    result = inventory.create_company(data)
                elif path == '/api/demo':
                    result = inventory.demo()
                else:
                    require(company is not None, 'Selecciona una empresa.')
                    if path == '/api/products':
                        result = inventory.create_product(company, data)
                    elif path.startswith('/api/products/'):
                        result = inventory.update_product(company, int(path.split('/')[-1]), data)
                    elif path == '/api/warehouses':
                        result = inventory.create_warehouse(company, data)
                    elif path == '/api/suppliers':
                        result = inventory.create_supplier(company, data)
                    elif path == '/api/movements':
                        result = inventory.move(company, data)
                    elif path == '/api/orders':
                        result = inventory.create_order(company, data)
                    elif path.startswith('/api/orders/'):
                        parts = path.split('/')
                        require(len(parts) == 5, 'Acción de compra inválida.')
                        result = inventory.order_action(company, int(parts[3]), parts[4])
                    elif path == '/api/import':
                        result = inventory.import_csv(company, data.get('content'))
                    else:
                        return self.send(404, {'error': 'Ruta no encontrada.'})
                self.send(200, result)
            except (ValidationError, ValueError, TypeError, KeyError) as exc:
                self.send(400, {'error': str(exc) if isinstance(exc, ValidationError) else 'La solicitud contiene datos inválidos.'})
            except (BrokenPipeError, ConnectionResetError):
                pass
            except Exception:
                self.send(500, {'error': 'No se pudo completar la operación. No se guardaron cambios parciales. Reintenta o reinicia la aplicación.'})

        def do_GET(self):
            self.run_request()

        def do_POST(self):
            self.run_request(True)

    return Handler


def main():
    parser = argparse.ArgumentParser(description='Nexo Inventario · aplicación local')
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--data-dir', type=Path, default=DEFAULT_DATA)
    parser.add_argument('--no-browser', action='store_true')
    args = parser.parse_args()
    url = f'http://127.0.0.1:{args.port}'
    inventory = Inventory(args.data_dir / 'nexo.sqlite3')
    try:
        server = ThreadingHTTPServer(('127.0.0.1', args.port), handler_for(inventory, secrets.token_urlsafe(32)))
    except OSError:
        try:
            with urlopen(url + '/health', timeout=2) as response:
                require(json.load(response).get('app') == 'nexo-inventario', 'Puerto ocupado por otra aplicación.')
            if not args.no_browser:
                webbrowser.open(url)
            return
        except Exception:
            raise SystemExit('El puerto está ocupado. Ejecuta con --port 8766.') from None
    if not args.no_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    print(f'Nexo Inventario: {url}\nDatos: {args.data_dir}\nCtrl+C para cerrar.', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
