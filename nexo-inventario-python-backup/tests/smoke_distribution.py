"""End-to-end check of the actual packaged executable, on isolated temporary data."""
import json
import re
import socket
import sqlite3
import subprocess
import tempfile
import time
from pathlib import Path
from urllib.request import Request, urlopen

root = Path(__file__).resolve().parents[1]
exe = root / 'dist' / 'NexoInventario' / 'NexoInventario.exe'
with socket.socket() as sock:
    sock.bind(('127.0.0.1', 0))
    port = sock.getsockname()[1]
url = f'http://127.0.0.1:{port}'

with tempfile.TemporaryDirectory() as folder:
    data = Path(folder) / 'data'
    def launch():
        process = subprocess.Popen([str(exe), '--no-browser', '--port', str(port), '--data-dir', str(data)], creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            for _ in range(100):
                if process.poll() is not None:
                    raise AssertionError(f'Executable exited: {process.returncode}')
                try:
                    with urlopen(url, timeout=1) as response:
                        html = response.read().decode()
                    return process, re.search(r'name="nexo-token" content="([^"]+)"', html).group(1)
                except OSError:
                    time.sleep(0.1)
            raise AssertionError('Executable did not start')
        except BaseException:
            process.terminate()
            process.wait(timeout=10)
            raise

    process, token = launch()
    def request(path, body=None):
        req = Request(url + path, data=json.dumps(body).encode() if body is not None else None,
            headers={'X-Nexo-Token': token, 'Content-Type': 'application/json'})
        with urlopen(req, timeout=5) as response:
            return response.read()
    try:
        cid = json.loads(request('/api/companies', {'name': 'Prueba ejecutable'}))['id']
        state = json.loads(request(f'/api/state?company={cid}'))
        wid = state['warehouses'][0]['id']
        pid = json.loads(request(f'/api/products?company={cid}', {'sku': 'EXE-1', 'name': 'Producto ejecutable', 'cost': 2.5}))['id']
        request(f'/api/movements?company={cid}', dict(product_id=pid, warehouse_id=wid, kind='in', quantity='4.125', note='Prueba empaquetado', request_key='exe-1'))
        csv = request(f'/api/export?company={cid}&kind=products').decode('utf-8-sig')
        assert '4.125' in csv and 'EXE-1' in csv
        backup = Path(folder) / 'backup.sqlite3'
        backup.write_bytes(request('/api/backup'))
        db = sqlite3.connect(backup)
        try:
            assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
            assert db.execute('SELECT qty FROM balances').fetchone()[0] == 4125
        finally:
            db.close()
        for asset in ('/app.js', '/style.css', '/icon.svg'):
            with urlopen(url + asset) as response:
                assert response.status == 200 and len(response.read()) > 50
    finally:
        process.terminate()
        process.wait(timeout=10)
    process, token = launch()
    try:
        state = json.loads(request(f'/api/state?company={cid}'))
        assert state['products'][0]['total_qty'] == 4125
    finally:
        process.terminate()
        process.wait(timeout=10)
print('PASS: executable startup, assets, company, product, movement, CSV, backup integrity and restart persistence.')
