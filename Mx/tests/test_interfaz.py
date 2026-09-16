from tempfile import TemporaryDirectory
import tkinter as tk
import unittest

from mxcorreo_app import App
from verificar_correos import prepare_lines


class InterfaceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.root = tk.Tk()
        self.root.withdraw()
        self.app = App(self.root, self.tmp.name)
        self.root.withdraw()

    def tearDown(self):
        for job in self.root.tk.call('after', 'info'):
            self.root.after_cancel(job)
        self.root.destroy()
        self.tmp.cleanup()

    def test_paging_search_and_metrics(self):
        rows = prepare_lines([f'user{i}@example.com' for i in range(450)])
        rows[0]['estado'] = 'APTO_DNS'
        self.app.set_rows(rows)
        self.assertEqual(len(self.app.table.get_children()), 200)
        self.assertEqual(self.app.metrics['total'].get(), '450')
        self.app.change_page(2)
        self.assertEqual(len(self.app.table.get_children()), 50)
        self.app.category.set('Dominio apto')
        self.app.apply_filter()
        self.assertEqual(len(self.app.table.get_children()), 1)
        self.assertEqual(self.app.table.item('0', 'values')[1], 'Dominio apto')
        self.app.search.set('not-present')
        self.app.apply_filter()
        self.assertEqual(len(self.app.table.get_children()), 0)

    def test_busy_disables_actions_and_preserves_send_confirmation(self):
        self.app.set_busy(True)
        self.assertTrue(all(str(b['state']) == 'disabled' for b in self.app.action_buttons))
        self.assertTrue(all(not flag.get() for flag in self.app.approvals.values()))
        self.app.set_busy(False)
        self.assertTrue(all(str(b['state']) == 'normal' for b in self.app.action_buttons))

    def test_gmail_defaults_and_saved_configuration(self):
        from pathlib import Path
        import campana
        self.app.form['remitente'].set('empresa@example.com')
        self.app.gmail_preset()
        self.assertEqual(self.app.form['host'].get(), 'smtp.gmail.com')
        self.assertEqual(self.app.form['usuario'].get(), 'empresa@example.com')
        self.assertEqual(self.app.form['audiencia'].get(), 'Solo autorizados')
        self.app.form['baja_correo'].set('bajas@example.com')
        path = self.app.collect_config(Path(self.tmp.name), remember=True)
        cfg = campana.load_config(path)
        self.assertEqual(cfg['limites']['max_24h'], 400)
        self.assertEqual(cfg['mensaje']['baja_correo'], 'bajas@example.com')
        self.assertFalse(any(cfg['autorizacion'].values()))


if __name__ == '__main__':
    unittest.main()
