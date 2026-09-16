import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch
import argparse
from contextlib import redirect_stdout
from io import StringIO

import campana
from centro_campanas import import_report
from importar_contactos import load_import
from verificar_correos import prepare_lines


ROOT = Path(__file__).resolve().parents[1]


class CampaignCenterTests(unittest.TestCase):
    def test_full_campaign_mock_smtp_authorized_excluded_and_resume(self):
        with TemporaryDirectory() as tmp:
            folder = Path(tmp)
            cfg = campana.load_config(ROOT / 'campana.ejemplo.json')
            cfg['es_ejemplo'] = False
            cfg['autorizacion'] = {key: True for key in cfg['autorizacion']}
            cfg['smtp'].update(host='smtp.gmail.com', usuario='empresa@example.com')
            cfg['mensaje'].update(archivo_texto=str(ROOT / 'mensaje.ejemplo.txt'), baja_correo='bajas@example.com')
            config = folder / 'config.json'
            config.write_text(json.dumps(cfg), encoding='utf-8')
            source = folder / 'base.txt'
            source.write_text('a@example.com\nb@example.com\nc@example.com\nb@example.com', encoding='utf-8')
            allowed = folder / 'allowed.txt'
            allowed.write_text('a@example.com\nb@example.com', encoding='utf-8')
            excluded = folder / 'excluded.txt'
            excluded.write_text('a@example.com', encoding='utf-8')
            args = argparse.Namespace(modo='enviar', sin_dns=False, destino_prueba=None, archivo=source,
                                      config=config, exclusiones=excluded, autorizados=allowed,
                                      columna_correo='correo', separador=None, salida=folder / 'results',
                                      registro=folder / 'ledger.sqlite3', timeout=1, workers=1,
                                      reintentos_dns=0, reintentar_temporales=False)
            def dns(rows, *unused):
                for row in rows:
                    row.update(estado='APTO_DNS', codigo='MX_RESUELVE', motivo='Prueba local')
            client = Mock()
            client.send_message.return_value = {}
            connector = Mock(return_value=client)
            confirmation = lambda prompt: 'ENVIAR 1 ' + cfg['campana_id']
            with patch('campana.verify', side_effect=dns), redirect_stdout(StringIO()):
                self.assertEqual(campana.run(args, confirm=confirmation, connector=connector), 0)
                self.assertEqual(campana.run(args, confirm=confirmation, connector=connector), 0)
            self.assertEqual(connector.call_count, 1)
            self.assertEqual(client.send_message.call_count, 1)
            self.assertEqual(client.send_message.call_args.kwargs['to_addrs'], ['b@example.com'])

    def test_prior_report_import_and_fresh_send_input(self):
        with TemporaryDirectory() as tmp:
            source = Path(tmp) / 'Detalle.json'
            rows = prepare_lines(['ana@example.com', 'ana@example.com', 'no-es-correo'])
            rows[0].update(estado='APTO_DNS', codigo='MX_RESUELVE', motivo='Histórico')
            source.write_text(json.dumps({'correos': rows}), encoding='utf-8')
            original = source.read_bytes()
            saved, display, label = import_report(source, tmp)
            self.assertEqual(display[0]['estado'], 'APTO_DNS')
            self.assertIsNotNone(display[1]['duplicado_de_linea'])
            self.assertEqual(display[2]['estado'], 'INVALIDO')
            self.assertFalse(load_import(saved)[0]['estado'])
            self.assertEqual(source.read_bytes(), original)

    def test_permission_intersection_and_exclusion_priority(self):
        rows = prepare_lines(['a@example.com', 'b@example.com', 'c@example.com'])
        for row in rows:
            row['estado'] = 'APTO_DNS'
        selected, audit = campana.select_recipients(rows, {'a@example.com'}, {}, 50, authorized={'a@example.com', 'b@example.com'})
        self.assertEqual([r['normalizado'] for r in selected], ['b@example.com'])
        self.assertEqual([r['decision'] for r in audit], ['EXCLUIDO', 'SELECCIONADO', 'SIN_AUTORIZACION_EN_LISTA'])
        self.assertFalse(campana.select_recipients(rows, set(), {}, 50, authorized=set())[0])

    def test_quota_shared_by_campaigns_and_rollback(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / 'ledger.sqlite3'
            first = campana.Ledger(path, 'one', 'content')
            second = campana.Ledger(path, 'two', 'content')
            try:
                self.assertTrue(first.claim('a@example.com', 'id', account='gmail-user', limit=1))
                with self.assertRaises(campana.QuotaReached):
                    second.claim('b@example.com', 'id2', account='gmail-user', limit=1)
                self.assertEqual(campana.read_history(path, 'two'), {})
                self.assertFalse(first.claim('a@example.com', 'id', account='gmail-user', limit=1))
                first.db.execute('UPDATE quota_attempts SET attempted=0')
                first.db.commit()
                self.assertTrue(second.claim('b@example.com', 'id2', account='gmail-user', limit=1))
            finally:
                first.close()
                second.close()

    def test_unsubscribe_in_both_bodies_and_header(self):
        cfg = campana.load_config(ROOT / 'campana.ejemplo.json')
        cfg['mensaje']['baja_correo'] = 'bajas@example.com'
        with TemporaryDirectory() as tmp:
            folder = Path(tmp)
            (folder / 'text.txt').write_text('Oferta', encoding='utf-8')
            (folder / 'rich.html').write_text('<p>Oferta</p>', encoding='utf-8')
            cfg['mensaje'].update(archivo_texto='text.txt', archivo_html='rich.html', adjuntos=[])
            content, fingerprint = campana.load_content(cfg, folder)
            self.assertIn('bajas@example.com', content['texto'])
            self.assertIn('mailto:', content['html'])
            msg = campana.build_message(cfg, content, prepare_lines(['a@example.com'])[0], 'test')
            self.assertIn('bajas@example.com', msg['List-Unsubscribe'])
            self.assertIsNone(msg['List-Unsubscribe-Post'])
            cfg['mensaje']['baja_correo'] = 'otra@example.com'
            self.assertNotEqual(fingerprint, campana.load_content(cfg, folder)[1])

    def test_invalid_limits_rejected(self):
        cfg = campana.load_config(ROOT / 'campana.ejemplo.json')
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / 'config.json'
            for bad in (0, 2001, True, '400'):
                cfg['limites']['max_24h'] = bad
                path.write_text(json.dumps(cfg), encoding='utf-8')
                with self.assertRaises(ValueError):
                    campana.load_config(path)


if __name__ == '__main__':
    unittest.main()
