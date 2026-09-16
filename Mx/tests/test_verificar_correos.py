import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

import dns.exception
import dns.resolver

from verificar_correos import DNSChecker, prepare_lines, save_report, verify


def mx(priority=10, host="mx.example.net."):
    return SimpleNamespace(preference=priority, exchange=host)


class FakeResolver:
    def __init__(self, records):
        self.records = records
        self.calls = []

    def resolve(self, name, kind, **kwargs):
        self.calls.append((name, kind, kwargs))
        value = self.records.get((name, kind), dns.resolver.NoAnswer())
        if isinstance(value, Exception):
            raise value
        return value


class DNSTests(unittest.TestCase):
    def check(self, records):
        resolver = FakeResolver(records)
        result = DNSChecker(resolver=resolver).check("example.com")
        self.assertTrue(all(c[2]["search"] is False for c in resolver.calls))
        return result

    def test_valid_mx(self):
        result = self.check({("example.com", "MX"): [mx()], ("mx.example.net.", "A"): ["192.0.2.1"]})
        self.assertEqual(result["estado"], "APTO_DNS")

    def test_ipv6_only_mx(self):
        result = self.check({("example.com", "MX"): [mx()], ("mx.example.net.", "AAAA"): ["2001:db8::1"]})
        self.assertEqual(result["estado"], "APTO_DNS")

    def test_secondary_mx_still_works(self):
        result = self.check({("example.com", "MX"): [mx(0, "broken.example.net."), mx()],
                             ("mx.example.net.", "A"): ["192.0.2.1"]})
        self.assertEqual(result["estado"], "APTO_DNS")

    def test_nxdomain(self):
        result = self.check({("example.com", "MX"): dns.resolver.NXDOMAIN()})
        self.assertEqual(result["codigo"], "DOMINIO_INEXISTENTE")

    def test_null_mx(self):
        result = self.check({("example.com", "MX"): [mx(0, ".")], ("example.com", "A"): ["192.0.2.1"]})
        self.assertEqual(result["codigo"], "NULL_MX")
        self.assertEqual(result["estado"], "INVALIDO")

    def test_mixed_null_mx(self):
        result = self.check({("example.com", "MX"): [mx(0, "."), mx()]})
        self.assertEqual(result["codigo"], "MX_INCONSISTENTE")

    def test_malformed_null_mx(self):
        result = self.check({("example.com", "MX"): [mx(10, ".")]})
        self.assertEqual(result["estado"], "REVISAR")

    def test_implicit_mx(self):
        result = self.check({("example.com", "A"): ["192.0.2.1"]})
        self.assertEqual(result["codigo"], "MX_IMPLICITO")
        self.assertEqual(result["estado"], "REVISAR")

    def test_implicit_mx_ipv6(self):
        result = self.check({("example.com", "AAAA"): ["2001:db8::1"]})
        self.assertEqual(result["codigo"], "MX_IMPLICITO")

    def test_no_route(self):
        self.assertEqual(self.check({})["codigo"], "SIN_RUTA_DNS")

    def test_mx_without_ip_does_not_use_domain_ip(self):
        result = self.check({("example.com", "MX"): [mx()], ("example.com", "A"): ["192.0.2.1"]})
        self.assertEqual(result["codigo"], "MX_SIN_IP")

    def test_timeout_is_reviewed_and_retried(self):
        resolver = FakeResolver({("example.com", "MX"): dns.exception.Timeout()})
        result = DNSChecker(resolver=resolver).check("example.com")
        self.assertEqual(result["estado"], "REVISAR")
        self.assertEqual(len(resolver.calls), 2)

    def test_servfail_is_not_invalid(self):
        self.assertEqual(self.check({("example.com", "MX"): dns.resolver.NoNameservers()})["estado"], "REVISAR")

    def test_mx_address_timeout(self):
        result = self.check({("example.com", "MX"): [mx()], ("mx.example.net.", "A"): dns.exception.Timeout()})
        self.assertEqual(result["estado"], "REVISAR")

    def test_fallback_address_timeout(self):
        result = self.check({("example.com", "A"): dns.exception.Timeout()})
        self.assertEqual(result["estado"], "REVISAR")

    def test_successful_retry(self):
        resolver = Mock()
        resolver.resolve.side_effect = [dns.exception.Timeout(), [mx()], ["192.0.2.1"]]
        self.assertEqual(DNSChecker(resolver=resolver).check("example.com")["estado"], "APTO_DNS")


class InputTests(unittest.TestCase):
    def test_duplicates_domain_case_and_whitespace(self):
        rows = prepare_lines([" user@EXAMPLE.com ", "", "user@example.com"])
        self.assertEqual(rows[0]["normalizado"], "user@example.com")
        self.assertEqual(rows[1]["duplicado_de_linea"], 1)
        self.assertEqual(rows[1]["linea"], 3)
        self.assertEqual(rows[0]["original"], " user@EXAMPLE.com ")

    def test_no_local_case_or_plus_or_dot_merging(self):
        rows = prepare_lines(["user@example.com", "User@example.com", "user+tag@example.com", "u.ser@example.com"])
        self.assertTrue(all(r["duplicado_de_linea"] is None for r in rows))

    def test_bad_syntax(self):
        rows = prepare_lines(["no-arroba", "user@", "a..b@example.com", "a b@example.com"])
        self.assertTrue(all(r["estado"] == "INVALIDO" for r in rows))

    def test_quoted_local(self):
        rows = prepare_lines(['"a b"@example.com'])
        self.assertEqual(rows[0]["dominio"], "example.com")

    def test_unicode_domain_equivalence(self):
        rows = prepare_lines(["user@bücher.de", "user@xn--bcher-kva.de"])
        self.assertEqual(rows[0]["dominio"], "xn--bcher-kva.de")
        self.assertEqual(rows[1]["duplicado_de_linea"], 1)

    def test_smtputf8(self):
        self.assertTrue(prepare_lines(["josé@example.com"])[0]["requiere_smtputf8"])

    def test_literal_reviewed(self):
        row = prepare_lines(["user@[192.0.2.1]"])[0]
        self.assertEqual(row["codigo"], "DOMINIO_LITERAL")
        self.assertEqual(row["estado"], "REVISAR")

    def test_one_check_per_domain(self):
        checker = Mock()
        checker.check.return_value = {"estado": "APTO_DNS", "codigo": "MX_RESUELVE", "motivo": "DNS", "mx": []}
        rows = verify(prepare_lines(["a@example.com", "b@example.com", "a@EXAMPLE.COM"]), checker)
        checker.check.assert_called_once_with("example.com")
        self.assertEqual(len(rows), 3)
        self.assertTrue(all(r["buzon"] == "NO_COMPROBADO" for r in rows))

    def test_report_escaping_and_no_overwrite(self):
        rows = prepare_lines(['<script>alert("bad")</script>'])
        with TemporaryDirectory() as directory:
            first, report = save_report(rows, Path(directory))
            second, _ = save_report(rows, Path(directory))
            self.assertNotEqual(first, second)
            content = (first / "informe.html").read_text(encoding="utf-8")
            self.assertNotIn('<script>', content)
            self.assertIn('&lt;script&gt;', content)
            self.assertEqual(json.loads((first / "informe.json").read_text(encoding="utf-8")), report)


if __name__ == "__main__":
    unittest.main()
