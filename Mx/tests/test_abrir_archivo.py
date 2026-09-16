from pathlib import Path
import unittest
from unittest.mock import patch
from abrir_archivo import open_local_path


class OpenPathTests(unittest.TestCase):
    def test_linux_uses_argument_list(self):
        with patch('abrir_archivo.sys.platform', 'linux'), patch('abrir_archivo.subprocess.run') as run:
            open_local_path('un archivo; seguro.html')
        self.assertEqual(run.call_args.args[0], ['xdg-open', str(Path('un archivo; seguro.html').resolve())])
        self.assertNotIn('shell', run.call_args.kwargs)

    def test_windows_uses_startfile(self):
        with patch('abrir_archivo.sys.platform', 'win32'), patch('abrir_archivo.os.startfile', create=True) as start:
            open_local_path('resultado.html')
        start.assert_called_once_with(str(Path('resultado.html').resolve()))
