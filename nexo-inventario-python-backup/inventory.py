"""Nexo: local inventory domain. Quantities use thousandths; money uses cents."""
from __future__ import annotations

import csv
import io
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path


class ValidationError(Exception):
    pass


def require(value, message):
    if not value:
        raise ValidationError(message)


def label(value, name, limit=160, optional=False):
    require(isinstance(value, str), f"{name}: debe ser texto.")
    value = value.strip()
    require(optional or value, f"Completa {name.lower()}.")
    require(len(value) <= limit, f"{name}: máximo {limit} caracteres.")
    return value


def scaled(value, name, factor=1000, positive=False):
    try:
        n = Decimal(str(value))
        require(n.is_finite(), f"{name}: cantidad inválida.")
        require(n > 0 if positive else n >= 0, f"{name}: debe ser {'mayor que' if positive else 'como mínimo'} cero.")
        require(n <= Decimal('1000000000'), f"{name}: cantidad demasiado grande.")
        result = n * factor
        require(result == result.to_integral_value(), f"{name}: admite hasta {3 if factor == 1000 else 2} decimales.")
        return int(result)
    except (InvalidOperation, ValueError, TypeError):
        raise ValidationError(f"{name}: valor numérico inválido.") from None


def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


SCHEMA = """
CREATE TABLE IF NOT EXISTS companies (
 id INTEGER PRIMARY KEY, name TEXT NOT NULL, sector TEXT NOT NULL,
 currency TEXT NOT NULL DEFAULT 'USD', created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS warehouses (
 id INTEGER PRIMARY KEY, company_id INTEGER NOT NULL REFERENCES companies(id),
 name TEXT NOT NULL, location TEXT NOT NULL DEFAULT '', UNIQUE(company_id,name)
);
CREATE TABLE IF NOT EXISTS suppliers (
 id INTEGER PRIMARY KEY, company_id INTEGER NOT NULL REFERENCES companies(id),
 name TEXT NOT NULL, contact TEXT NOT NULL DEFAULT '', email TEXT NOT NULL DEFAULT '',
 phone TEXT NOT NULL DEFAULT '', notes TEXT NOT NULL DEFAULT '', UNIQUE(company_id,name)
);
CREATE TABLE IF NOT EXISTS products (
 id INTEGER PRIMARY KEY, company_id INTEGER NOT NULL REFERENCES companies(id),
 sku TEXT NOT NULL COLLATE NOCASE, name TEXT NOT NULL, category TEXT NOT NULL,
 unit TEXT NOT NULL, barcode TEXT NOT NULL DEFAULT '', cost_cents INTEGER NOT NULL CHECK(cost_cents>=0),
 price_cents INTEGER NOT NULL CHECK(price_cents>=0), min_qty INTEGER NOT NULL CHECK(min_qty>=0),
 notes TEXT NOT NULL DEFAULT '', active INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL,
 UNIQUE(company_id,sku)
);
CREATE UNIQUE INDEX IF NOT EXISTS product_barcode ON products(company_id,barcode) WHERE barcode<>'';
CREATE TABLE IF NOT EXISTS balances (
 product_id INTEGER NOT NULL REFERENCES products(id), warehouse_id INTEGER NOT NULL REFERENCES warehouses(id),
 qty INTEGER NOT NULL CHECK(qty>=0), PRIMARY KEY(product_id,warehouse_id)
);
CREATE TABLE IF NOT EXISTS movements (
 id INTEGER PRIMARY KEY, company_id INTEGER NOT NULL REFERENCES companies(id),
 kind TEXT NOT NULL, product_id INTEGER NOT NULL REFERENCES products(id),
 warehouse_id INTEGER NOT NULL REFERENCES warehouses(id),
 destination_id INTEGER REFERENCES warehouses(id), qty INTEGER NOT NULL CHECK(qty>0),
 delta INTEGER NOT NULL, note TEXT NOT NULL, created_at TEXT NOT NULL,
 request_key TEXT UNIQUE
);
CREATE INDEX IF NOT EXISTS movements_company ON movements(company_id,id DESC);
CREATE TABLE IF NOT EXISTS orders (
 id INTEGER PRIMARY KEY, company_id INTEGER NOT NULL REFERENCES companies(id),
 supplier_id INTEGER NOT NULL REFERENCES suppliers(id), warehouse_id INTEGER NOT NULL REFERENCES warehouses(id),
 status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','received','cancelled')),
 note TEXT NOT NULL, created_at TEXT NOT NULL, received_at TEXT, request_key TEXT UNIQUE
);
CREATE TABLE IF NOT EXISTS order_lines (
 id INTEGER PRIMARY KEY, order_id INTEGER NOT NULL REFERENCES orders(id),
 product_id INTEGER NOT NULL REFERENCES products(id), qty INTEGER NOT NULL CHECK(qty>0),
 cost_cents INTEGER NOT NULL CHECK(cost_cents>=0), UNIQUE(order_id,product_id)
);
PRAGMA user_version = 1;
"""


class Inventory:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        db = self.connect()
        try:
            db.executescript(SCHEMA)
        finally:
            db.close()

    def connect(self):
        db = sqlite3.connect(self.path, timeout=20)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        db.execute('PRAGMA journal_mode=WAL')
        return db

    @contextmanager
    def transaction(self):
        db = self.connect()
        try:
            db.execute('BEGIN IMMEDIATE')
            yield db
            db.commit()
        except sqlite3.IntegrityError as exc:
            db.rollback()
            raise ValidationError('Ya existe ese código, código de barras o nombre. Revisa los datos.') from exc
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def own(self, db, table, row_id, company):
        require(table in {'products', 'warehouses', 'suppliers', 'orders'}, 'Entidad inválida.')
        row = db.execute(f'SELECT * FROM {table} WHERE id=? AND company_id=?', (row_id, company)).fetchone()
        require(row, 'El registro no existe en esta empresa.')
        return row

    def company(self, db, company):
        row = db.execute('SELECT * FROM companies WHERE id=?', (company,)).fetchone()
        require(row, 'Selecciona una empresa válida.')
        return row

    def create_company(self, data):
        name = label(data.get('name'), 'Nombre de empresa')
        sector = label(data.get('sector', 'General'), 'Sector')
        currency = data.get('currency', 'USD')
        require(currency in {'USD', 'EUR', 'MXN', 'COP', 'PEN', 'CLP', 'ARS', 'GBP'}, 'Moneda no admitida.')
        with self.transaction() as db:
            cid = db.execute('INSERT INTO companies(name,sector,currency,created_at) VALUES(?,?,?,?)', (name, sector, currency, now())).lastrowid
            db.execute('INSERT INTO warehouses(company_id,name,location) VALUES(?,?,?)', (cid, 'Bodega principal', ''))
            return {'id': cid}

    def create_warehouse(self, company, data):
        with self.transaction() as db:
            self.company(db, company)
            wid = db.execute('INSERT INTO warehouses(company_id,name,location) VALUES(?,?,?)',
                             (company, label(data.get('name'), 'Nombre'), label(data.get('location', ''), 'Ubicación', 240, True))).lastrowid
            return {'id': wid}

    def create_supplier(self, company, data):
        values = [label(data.get('name'), 'Nombre')]
        values += [label(data.get(k, ''), k, 500, True) for k in ('contact', 'email', 'phone', 'notes')]
        with self.transaction() as db:
            self.company(db, company)
            sid = db.execute('INSERT INTO suppliers(company_id,name,contact,email,phone,notes) VALUES(?,?,?,?,?,?)', [company] + values).lastrowid
            return {'id': sid}

    def product_values(self, data):
        return (label(data.get('sku'), 'SKU', 64).upper(), label(data.get('name'), 'Nombre'),
                label(data.get('category', 'General'), 'Categoría', 80), label(data.get('unit', 'unidad'), 'Unidad', 30),
                label(data.get('barcode', ''), 'Código de barras', 80, True), scaled(data.get('cost', 0), 'Costo', 100),
                scaled(data.get('price', 0), 'Precio', 100), scaled(data.get('min_stock', 0), 'Stock mínimo'),
                label(data.get('notes', ''), 'Notas', 1000, True))

    def create_product(self, company, data):
        values = self.product_values(data)
        with self.transaction() as db:
            self.company(db, company)
            pid = db.execute('INSERT INTO products(company_id,sku,name,category,unit,barcode,cost_cents,price_cents,min_qty,notes,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)', (company, *values, now())).lastrowid
            return {'id': pid}

    def update_product(self, company, pid, data):
        values = self.product_values(data)
        with self.transaction() as db:
            previous = self.own(db, 'products', pid, company)
            if previous['unit'] != values[3]:
                used = db.execute('SELECT 1 FROM movements WHERE product_id=? UNION ALL SELECT 1 FROM order_lines WHERE product_id=? LIMIT 1', (pid, pid)).fetchone()
                require(not used, 'No puedes cambiar la unidad de un producto con movimientos o compras. Crea otro SKU.')
            db.execute('UPDATE products SET sku=?,name=?,category=?,unit=?,barcode=?,cost_cents=?,price_cents=?,min_qty=?,notes=? WHERE id=?', (*values, pid))
            return {'id': pid}

    def balance(self, db, pid, wid):
        row = db.execute('SELECT qty FROM balances WHERE product_id=? AND warehouse_id=?', (pid, wid)).fetchone()
        return row['qty'] if row else 0

    def change(self, db, pid, wid, delta):
        balance = self.balance(db, pid, wid)
        require(balance + delta >= 0, 'Stock insuficiente en la bodega seleccionada. No se guardó ningún cambio.')
        db.execute('INSERT INTO balances(product_id,warehouse_id,qty) VALUES(?,?,?) ON CONFLICT(product_id,warehouse_id) DO UPDATE SET qty=excluded.qty', (pid, wid, balance + delta))

    def _movement(self, db, company, data, key=None):
        pid, wid = data.get('product_id'), data.get('warehouse_id')
        self.own(db, 'products', pid, company)
        self.own(db, 'warehouses', wid, company)
        kind = data.get('kind')
        require(kind in {'in', 'out', 'transfer', 'count'}, 'Tipo de movimiento inválido.')
        note = label(data.get('note'), 'Motivo o referencia', 500)
        qty = scaled(data.get('quantity'), 'Cantidad', positive=kind != 'count')
        destination = None
        if kind == 'count':
            delta = qty - self.balance(db, pid, wid)
            require(delta != 0, 'El conteo coincide con el stock actual; no necesita ajuste.')
            qty = abs(delta)
        else:
            delta = qty if kind == 'in' else -qty
        if kind == 'transfer':
            destination = data.get('destination_id')
            self.own(db, 'warehouses', destination, company)
            require(str(destination) != str(wid), 'Selecciona una bodega de destino diferente.')
        self.change(db, pid, wid, delta)
        if destination:
            self.change(db, pid, destination, qty)
        mid = db.execute('INSERT INTO movements(company_id,kind,product_id,warehouse_id,destination_id,qty,delta,note,created_at,request_key) VALUES(?,?,?,?,?,?,?,?,?,?)', (company, kind, pid, wid, destination, qty, delta, note, now(), key)).lastrowid
        return {'id': mid}

    def move(self, company, data):
        key = label(data.get('request_key'), 'Identificador de operación', 100)
        key = f'{company}:movement:{key}'
        with self.transaction() as db:
            row = db.execute('SELECT id FROM movements WHERE request_key=?', (key,)).fetchone()
            if row:
                return {'id': row['id'], 'replayed': True}
            return self._movement(db, company, data, key)

    def create_order(self, company, data):
        lines = data.get('lines')
        require(isinstance(lines, list) and 0 < len(lines) <= 200, 'Agrega entre 1 y 200 productos.')
        key = f"{company}:order:{label(data.get('request_key'), 'Identificador', 100)}"
        with self.transaction() as db:
            existing = db.execute('SELECT id FROM orders WHERE request_key=?', (key,)).fetchone()
            if existing:
                return {'id': existing['id'], 'replayed': True}
            self.own(db, 'suppliers', data.get('supplier_id'), company)
            self.own(db, 'warehouses', data.get('warehouse_id'), company)
            oid = db.execute('INSERT INTO orders(company_id,supplier_id,warehouse_id,note,created_at,request_key) VALUES(?,?,?,?,?,?)',
                             (company, data['supplier_id'], data['warehouse_id'], label(data.get('note', ''), 'Referencia', 500, True), now(), key)).lastrowid
            seen = set()
            for line in lines:
                require(isinstance(line, dict), 'Línea de compra inválida.')
                product = self.own(db, 'products', line.get('product_id'), company)
                require(product['id'] not in seen, 'Un producto aparece repetido. Agrupa su cantidad en una sola línea.')
                seen.add(product['id'])
                db.execute('INSERT INTO order_lines(order_id,product_id,qty,cost_cents) VALUES(?,?,?,?)',
                           (oid, product['id'], scaled(line.get('quantity'), 'Cantidad', positive=True), scaled(line.get('cost'), 'Costo', 100)))
            return {'id': oid}

    def order_action(self, company, oid, action):
        require(action in {'receive', 'cancel'}, 'Acción inválida.')
        with self.transaction() as db:
            order = self.own(db, 'orders', oid, company)
            if action == 'receive' and order['status'] == 'received':
                return {'id': oid, 'replayed': True}
            require(order['status'] == 'pending', 'La orden ya está cerrada.')
            if action == 'receive':
                lines = db.execute('SELECT * FROM order_lines WHERE order_id=?', (oid,)).fetchall()
                for line in lines:
                    self._movement(db, company, {'product_id': line['product_id'], 'warehouse_id': order['warehouse_id'],
                        'kind': 'in', 'quantity': str(Decimal(line['qty']) / 1000), 'note': f'Recepción de compra OC-{oid:04d}'}, f'order:{oid}:{line["id"]}')
                db.execute("UPDATE orders SET status='received',received_at=? WHERE id=?", (now(), oid))
            else:
                db.execute("UPDATE orders SET status='cancelled' WHERE id=?", (oid,))
            return {'id': oid}

    def snapshot(self, company=None):
        db = self.connect()
        try:
            db.execute('BEGIN')
            companies = [dict(r) for r in db.execute('SELECT * FROM companies ORDER BY id')]
            result = {'companies': companies, 'company': None, 'products': [], 'warehouses': [], 'suppliers': [], 'movements': [], 'orders': [], 'balances': []}
            if not companies:
                return result
            company = company or companies[0]['id']
            result['company'] = dict(self.company(db, company))
            for table in ('warehouses', 'suppliers'):
                result[table] = [dict(r) for r in db.execute(f'SELECT * FROM {table} WHERE company_id=? ORDER BY name', (company,))]
            result['products'] = [dict(r) for r in db.execute('SELECT p.*,COALESCE(SUM(b.qty),0) AS total_qty FROM products p LEFT JOIN balances b ON p.id=b.product_id WHERE p.company_id=? GROUP BY p.id ORDER BY p.name', (company,))]
            result['balances'] = [dict(r) for r in db.execute('SELECT b.* FROM balances b JOIN products p ON p.id=b.product_id WHERE p.company_id=?', (company,))]
            result['movements'] = [dict(r) for r in db.execute('SELECT m.*,p.name AS product_name,p.sku,p.unit,w.name AS warehouse_name,d.name AS destination_name FROM movements m JOIN products p ON p.id=m.product_id JOIN warehouses w ON w.id=m.warehouse_id LEFT JOIN warehouses d ON d.id=m.destination_id WHERE m.company_id=? ORDER BY m.id DESC LIMIT 500', (company,))]
            result['movement_count'] = db.execute('SELECT COUNT(*) FROM movements WHERE company_id=?', (company,)).fetchone()[0]
            orders = [dict(r) for r in db.execute('SELECT o.*,s.name AS supplier_name,w.name AS warehouse_name FROM orders o JOIN suppliers s ON s.id=o.supplier_id JOIN warehouses w ON w.id=o.warehouse_id WHERE o.company_id=? ORDER BY o.id DESC', (company,))]
            for order in orders:
                order['lines'] = [dict(r) for r in db.execute('SELECT l.*,p.name AS product_name,p.unit FROM order_lines l JOIN products p ON p.id=l.product_id WHERE l.order_id=?', (order['id'],))]
            result['orders'] = orders
            return result
        finally:
            db.close()

    def export_csv(self, company, kind):
        require(kind in {'products', 'movements'}, 'Exportación inválida.')
        stream = io.StringIO(newline='')
        writer = csv.writer(stream)
        def safe(v):
            if isinstance(v, str) and v.lstrip().startswith(('=', '+', '-', '@')):
                return "'" + v
            return v
        db = self.connect()
        try:
            self.company(db, company)
            if kind == 'products':
                writer.writerow(['sku', 'name', 'category', 'unit', 'barcode', 'cost', 'price', 'min_stock', 'stock', 'notes'])
                rows = db.execute('SELECT p.*,COALESCE(SUM(b.qty),0) AS total_qty FROM products p LEFT JOIN balances b ON b.product_id=p.id WHERE company_id=? GROUP BY p.id ORDER BY p.name', (company,))
                for r in rows:
                    writer.writerow([safe(v) for v in [r['sku'], r['name'], r['category'], r['unit'], r['barcode'], Decimal(r['cost_cents']) / 100, Decimal(r['price_cents']) / 100, Decimal(r['min_qty']) / 1000, Decimal(r['total_qty']) / 1000, r['notes']]])
            else:
                writer.writerow(['id', 'fecha_utc', 'tipo', 'sku', 'producto', 'bodega', 'destino', 'cantidad', 'variacion_origen', 'motivo'])
                rows = db.execute('SELECT m.*,p.sku,p.name,w.name AS warehouse,d.name AS destination FROM movements m JOIN products p ON p.id=m.product_id JOIN warehouses w ON w.id=m.warehouse_id LEFT JOIN warehouses d ON d.id=m.destination_id WHERE m.company_id=? ORDER BY m.id', (company,))
                for r in rows:
                    writer.writerow([safe(v) for v in [r['id'], r['created_at'], r['kind'], r['sku'], r['name'], r['warehouse'], r['destination'] or '', Decimal(r['qty']) / 1000, Decimal(r['delta']) / 1000, r['note']]])
            return ('\ufeff' + stream.getvalue()).encode('utf-8')
        finally:
            db.close()

    def import_csv(self, company, content):
        require(isinstance(content, str) and len(content) <= 2_000_000, 'El CSV supera 2 MB.')
        reader = csv.DictReader(io.StringIO(content.lstrip('\ufeff')))
        require(reader.fieldnames and {'sku', 'name'} <= set(reader.fieldnames), 'El CSV necesita encabezados sku y name. Usa la plantilla.')
        rows = list(reader)
        require(0 < len(rows) <= 5000, 'El archivo debe contener entre 1 y 5000 productos.')
        # Validate all rows before committing. Stock is intentionally moved through the ledger.
        with self.transaction() as db:
            self.company(db, company)
            for index, row in enumerate(rows, 2):
                try:
                    if row.get('stock', '').strip():
                        require(scaled(row['stock'], 'Stock') == 0, 'Importa el catálogo sin existencias. Registra el stock inicial mediante una entrada o conteo.')
                    values = self.product_values({k: v for k, v in row.items() if v not in ('', None)})
                    db.execute('INSERT INTO products(company_id,sku,name,category,unit,barcode,cost_cents,price_cents,min_qty,notes,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)', (company, *values, now()))
                except (ValidationError, sqlite3.IntegrityError) as exc:
                    message = str(exc) if isinstance(exc, ValidationError) else 'SKU o código de barras duplicado.'
                    raise ValidationError(f'Fila {index}: {message} No se importó ningún producto.') from None
        return {'count': len(rows)}

    def backup(self, destination):
        source = self.connect()
        target = sqlite3.connect(destination)
        try:
            source.backup(target)
        finally:
            target.close()
            source.close()

    def demo(self):
        # An independent company: never seeds the user's real inventory.
        with self.transaction() as db:
            cid = db.execute('INSERT INTO companies(name,sector,currency,created_at) VALUES(?,?,?,?)', ('Comercial Horizonte · Demo', 'Comercio y distribución', 'USD', now())).lastrowid
            w1 = db.execute('INSERT INTO warehouses(company_id,name,location) VALUES(?,?,?)', (cid, 'Bodega central', 'Centro de distribución')).lastrowid
            w2 = db.execute('INSERT INTO warehouses(company_id,name,location) VALUES(?,?,?)', (cid, 'Local comercial', 'Punto de venta')).lastrowid
            sid = db.execute('INSERT INTO suppliers(company_id,name,contact,email,phone) VALUES(?,?,?,?,?)', (cid, 'Distribuciones Andina', 'Contacto de ejemplo', 'compras@example.com', '')).lastrowid
            items = [
                ('AL-001','Café de origen · 250 g','Alimentos','unidad',4.50,7.90,20,84),
                ('AL-002','Aceite de oliva · 500 ml','Alimentos','unidad',6.20,9.80,15,12),
                ('HO-001','Jabón líquido · 1 L','Hogar','unidad',2.40,4.90,20,65),
                ('FE-001','Tornillo galvanizado 1/4','Ferretería','unidad',0.12,0.30,100,450),
                ('TE-001','Cable USB-C · 1 m','Tecnología','unidad',3.50,8.00,12,8),
                ('TE-002','Cargador rápido · 20 W','Tecnología','unidad',8.00,16.50,10,0),
                ('IN-001','Tela de algodón crudo','Insumos','metro',2.80,5.40,25,126.5),
                ('AL-003','Arroz a granel','Alimentos','kg',0.85,1.40,30,210.75),
                ('HO-002','Vaso de vidrio · 350 ml','Hogar','unidad',1.20,2.80,24,96),
                ('FE-002','Pintura blanca · 1 gal','Ferretería','unidad',12.00,19.90,8,18),
            ]
            pids = []
            for sku, name, category, unit, cost, price, minimum, stock in items:
                values = self.product_values(dict(sku=sku, name=name, category=category, unit=unit, cost=cost, price=price, min_stock=minimum))
                pid = db.execute('INSERT INTO products(company_id,sku,name,category,unit,barcode,cost_cents,price_cents,min_qty,notes,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)', (cid, *values, now())).lastrowid
                pids.append(pid)
                if stock:
                    self._movement(db, cid, dict(product_id=pid, warehouse_id=w1, kind='in', quantity=stock, note='Existencias iniciales de demostración'))
            self._movement(db, cid, dict(product_id=pids[0], warehouse_id=w1, destination_id=w2, kind='transfer', quantity=24, note='Reposición del local · Demo'))
            self._movement(db, cid, dict(product_id=pids[2], warehouse_id=w1, kind='out', quantity=5, note='Venta de demostración'))
            oid = db.execute('INSERT INTO orders(company_id,supplier_id,warehouse_id,note,created_at) VALUES(?,?,?,?,?)', (cid, sid, w1, 'Reposición de productos · Demo', now())).lastrowid
            db.execute('INSERT INTO order_lines(order_id,product_id,qty,cost_cents) VALUES(?,?,?,?)', (oid, pids[5], 30000, 800))
            return {'id': cid}
