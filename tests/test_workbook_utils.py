"""Test di scripts/workbook_utils.py: salvare con openpyxl non deve perdere il collegamento a Claude per Excel."""
import shutil
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import openpyxl  # noqa: E402

import workbook_utils as wu  # noqa: E402

XLSX = ROOT / "data" / "fondi-pensione-covip.xlsx"


class TestSalva(unittest.TestCase):
    def test_conserva_webextensions_e_formule(self):
        with zipfile.ZipFile(XLSX) as z:
            if not any(n.startswith("xl/webextensions/") for n in z.namelist()):
                self.skipTest("il workbook non ha componenti aggiuntivi")
        with tempfile.TemporaryDirectory() as d:
            copia = Path(d) / "copia.xlsx"
            shutil.copy(XLSX, copia)
            wb = openpyxl.load_workbook(copia)
            wu.salva(wb, copia)
            with zipfile.ZipFile(copia) as z:
                nomi = z.namelist()
                self.assertEqual(nomi[0], "[Content_Types].xml")
                self.assertIn("xl/webextensions/webextension1.xml", nomi)
                self.assertIn(wu.REL_TASKPANES, z.read("_rels/.rels").decode())
                ct = z.read("[Content_Types].xml").decode()
                self.assertEqual(ct.count('PartName="/xl/webextensions/taskpanes.xml"'), 1)
            wb2 = openpyxl.load_workbook(copia)
            self.assertTrue(str(wb2["Sheet1"]["H3"].value).startswith("=COUNTIF"))


if __name__ == "__main__":
    unittest.main()
