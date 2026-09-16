import csv
import io
import json
import re
import sqlite3
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from inventory import Inventory, ValidationError
from server import handler_for


class InventoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'test.sqlite3'
        self.inv = Inventory(self.path)
        self.company = self.inv.create_company({'name': 'Negocio de prueba'})['id']
        self.warehouse = self.inv.snapshot(self.company)['warehouses'][0]['id']
        self.product = self.inv.create_product(self.company, {'sku': 'SKU-1', 'name': 'Harina', 'unit': 'kg', 'cost': '2.50', 'price': '4.20'})['id']
        self.other_warehouse = self.inv.create_warehouse(self.company, {'name': 'Sucursal'})['id']
        self.supplier = self.inv.create_supplier(self.company, {'name': 'Proveedor'})['id']
        self.sequence = 0

    def tearDown(self):
        self.tmp.cleanup()

    def move(self, kind='in', quantity=10, **kwargs):
        self.sequence += 1
        return self.inv.move(self.company, {'kind': kind, 'quantity': quantity, 'product_id': self.product,
            'warehouse_id': self.warehouse, 'note': 'Prueba', 'request_key': str(self.sequence), **kwargs})

    def stock(self, warehouse=None):
        state = self.inv.snapshot(self.company)
        if warehouse:
            return next((b['qty'] for b in state['balances'] if b['warehouse_id'] == warehouse and b['product_id'] == self.product), 0)
        return next(p['total_qty'] for p in state['products'] if p['id'] == self.product)

    def order(self, **overrides):
        return self.inv.create_order(self.company, {'supplier_id': self.supplier, 'warehouse_id': self.warehouse,
            'lines': [{'product_id': self.product, 'quantity': '2.125', 'cost': '2.40'}], 'request_key': 'order', **overrides})['id']

    def test_decimal_quantities_are_exact(self):
        self.move(quantity='0.1')
        self.move(quantity='0.2')
        self.move('out', '0.3')
        self.assertEqual(self.stock(), 0)

    def test_negative_stock_rejected_without_ledger_entry(self):
        self.move(quantity=5)
        with self.assertRaises(ValidationError):
            self.move('out', 6)
        self.assertEqual(self.stock(), 5000)
        self.assertEqual(len(self.inv.snapshot(self.company)['movements']), 1)

    def test_transfer_conserves_stock(self):
        self.move(quantity=10)
        self.move('transfer', '2.125', destination_id=self.other_warehouse)
        self.assertEqual(self.stock(), 10000)
        self.assertEqual(self.stock(self.other_warehouse), 2125)
        self.assertEqual(self.stock(self.warehouse), 7875)

    def test_failed_transfer_is_atomic(self):
        self.move(quantity=1)
        with self.assertRaises(ValidationError):
            self.move('transfer', 2, destination_id=self.other_warehouse)
        self.assertEqual(self.stock(self.other_warehouse), 0)
        self.assertEqual(self.stock(), 1000)

    def test_same_warehouse_transfer_rejected(self):
        self.move()
        with self.assertRaises(ValidationError):
            self.move('transfer', 1, destination_id=str(self.warehouse))

    def test_count_zero_and_increase(self):
        self.move()
        self.move('count', 0)
        self.assertEqual(self.stock(), 0)
        self.move('count', '3.025')
        self.assertEqual(self.stock(), 3025)
        with self.assertRaises(ValidationError):
            self.move('count', '3.025')

    def test_idempotent_movement(self):
        first = self.move(quantity=4, request_key='same')
        second = self.move(quantity=4, request_key='same')
        self.assertEqual(first['id'], second['id'])
        self.assertEqual(self.stock(), 4000)

    def test_concurrent_outflows_cannot_oversell(self):
        self.move(quantity=10)
        def consume(i):
            try:
                self.inv.move(self.company, dict(kind='out', quantity=7, product_id=self.product, warehouse_id=self.warehouse, note='Concurrente', request_key=f'concurrent-{i}'))
                return True
            except ValidationError:
                return False
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(consume, range(2)))
        self.assertEqual(sum(results), 1)
        self.assertEqual(self.stock(), 3000)

    def test_precision_and_nonfinite_rejected(self):
        for value in ['0.0001', '-1', 'NaN', 'Infinity', 'abc', None, True]:
            with self.subTest(value=value), self.assertRaises(ValidationError):
                self.move(quantity=value)

    def test_cross_company_product_and_warehouse_rejected(self):
        other = self.inv.create_company({'name': 'Otro negocio'})['id']
        wid = self.inv.snapshot(other)['warehouses'][0]['id']
        with self.assertRaises(ValidationError):
            self.move(warehouse_id=wid)
        with self.assertRaises(ValidationError):
            self.move('transfer', 1, destination_id=wid)
        with self.assertRaises(ValidationError):
            self.inv.move(other, dict(kind='in', quantity=1, product_id=self.product, warehouse_id=wid, note='Prueba', request_key='x'))
        self.assertEqual(self.inv.snapshot(other)['products'], [])

    def test_order_receipt_is_idempotent(self):
        oid = self.order()
        self.assertEqual(self.stock(), 0)
        self.inv.order_action(self.company, oid, 'receive')
        self.inv.order_action(self.company, oid, 'receive')
        self.assertEqual(self.stock(), 2125)
        self.assertEqual(self.inv.snapshot(self.company)['orders'][0]['status'], 'received')

    def test_multi_line_receipt(self):
        p2 = self.inv.create_product(self.company, {'sku': 'SKU-2', 'name': 'Sal'})['id']
        oid = self.order(lines=[{'product_id': self.product, 'quantity': '1.25', 'cost': 2}, {'product_id': p2, 'quantity': 3, 'cost': 1}])
        self.inv.order_action(self.company, oid, 'receive')
        self.assertEqual(self.stock(), 1250)
        self.assertEqual(len(self.inv.snapshot(self.company)['movements']), 2)

    def test_invalid_order_rolls_back_all_lines(self):
        with self.assertRaises(ValidationError):
            self.order(lines=[{'product_id': self.product, 'quantity': 1, 'cost': 1}, {'product_id': 999999, 'quantity': 1, 'cost': 1}])
        self.assertEqual(self.inv.snapshot(self.company)['orders'], [])

    def test_cancelled_order_cannot_be_received(self):
        oid = self.order()
        self.inv.order_action(self.company, oid, 'cancel')
        with self.assertRaises(ValidationError):
            self.inv.order_action(self.company, oid, 'receive')
        self.assertEqual(self.stock(), 0)

    def test_order_retries_dont_duplicate(self):
        self.assertEqual(self.order(), self.order())
        self.assertEqual(len(self.inv.snapshot(self.company)['orders']), 1)

    def test_duplicate_sku_case_insensitive(self):
        with self.assertRaises(ValidationError):
            self.inv.create_product(self.company, {'sku': 'sku-1', 'name': 'Otro'})

    def test_unit_change_blocked_after_movements(self):
        self.move()
        with self.assertRaises(ValidationError):
            self.inv.update_product(self.company, self.product, {'sku': 'SKU-1', 'name': 'Harina', 'unit': 'gramo'})

    def test_import_all_or_nothing(self):
        with self.assertRaises(ValidationError):
            self.inv.import_csv(self.company, 'sku,name,cost\nNEW,Nuevo,2\nBAD,Inválido,-1\n')
        self.assertEqual(len(self.inv.snapshot(self.company)['products']), 1)

    def test_import_and_duplicate_rollback(self):
        result = self.inv.import_csv(self.company, '\ufeffsku,name,unit,cost,price\nA,Arroz,kg,0.90,1.50\nB,Maíz,kg,1,2\n')
        self.assertEqual(result['count'], 2)
        with self.assertRaises(ValidationError):
            self.inv.import_csv(self.company, 'sku,name\nC,Otro\nA,Duplicado\n')
        self.assertEqual(len(self.inv.snapshot(self.company)['products']), 3)

    def test_import_does_not_silently_discard_stock(self):
        with self.assertRaises(ValidationError):
            self.inv.import_csv(self.company, 'sku,name,stock\nNEW,Nuevo,4\n')

    def test_export_protects_spreadsheet_formulas(self):
        self.inv.create_product(self.company, {'sku':'FORMULA','name':'=1+1'})
        data = list(csv.reader(io.StringIO(self.inv.export_csv(self.company, 'products').decode('utf-8-sig'))))
        self.assertTrue(any(row[1] == "'=1+1" for row in data[1:]))

    def test_backup_reopens_with_persistent_stock(self):
        self.move(quantity='3.75')
        path = Path(self.tmp.name) / 'backup.sqlite3'
        self.inv.backup(path)
        restored = Inventory(path).snapshot(self.company)
        self.assertEqual(restored['products'][0]['total_qty'], 3750)
        self.assertEqual(Inventory(self.path).snapshot(self.company)['products'][0]['total_qty'], 3750)

    def test_demo_is_separate_and_has_consistent_ledger(self):
        cid = self.inv.demo()['id']
        self.assertEqual(len(self.inv.snapshot(self.company)['products']), 1)
        demo = self.inv.snapshot(cid)
        self.assertEqual(len(demo['products']), 10)
        for p in demo['products']:
            expected = sum(m['delta'] + (m['qty'] if m['kind'] == 'transfer' else 0) for m in demo['movements'] if m['product_id'] == p['id'])
            self.assertEqual(p['total_qty'], expected)


class HttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.inv = Inventory(Path(cls.tmp.name) / 'http.sqlite3')
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), handler_for(cls.inv, 'test-token'))
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f'http://127.0.0.1:{cls.server.server_port}'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()
        cls.tmp.cleanup()

    def test_ui_loads_with_token_and_security_headers(self):
        with urlopen(self.url) as r:
            self.assertIn('test-token', r.read().decode())
            self.assertIn("frame-ancestors 'none'", r.headers['Content-Security-Policy'])

    def test_unauthorized_api_blocked(self):
        with self.assertRaises(HTTPError) as error:
            urlopen(self.url + '/api/state')
        self.assertEqual(error.exception.code, 403)

    def test_dns_rebinding_host_blocked(self):
        with self.assertRaises(HTTPError) as error:
            urlopen(Request(self.url + '/', headers={'Host': 'attacker.example'}))
        self.assertEqual(error.exception.code, 403)

    def test_authenticated_create_and_read(self):
        body = json.dumps({'name': 'HTTP Company'}).encode()
        request = Request(self.url + '/api/companies', data=body, headers={'X-Nexo-Token':'test-token', 'Content-Type':'application/json'})
        with urlopen(request) as r:
            cid = json.load(r)['id']
        with urlopen(Request(self.url + f'/api/state?company={cid}', headers={'X-Nexo-Token':'test-token'})) as r:
            self.assertEqual(json.load(r)['company']['name'], 'HTTP Company')

    def test_malformed_json_rejected(self):
        with self.assertRaises(HTTPError) as error:
            urlopen(Request(self.url + '/api/companies', data=b'{', headers={'X-Nexo-Token':'test-token','Content-Type':'application/json'}))
        self.assertEqual(error.exception.code, 400)


if __name__ == '__main__':
    unittest.main()
