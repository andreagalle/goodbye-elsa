"""Test dei documenti ufficiali dei fondi (scripts/documenti.py, data/documenti.csv, docs/documenti/).

Controllano che registro, file e indice siano coerenti: ogni PDF del registro esiste con il suo testo estratto
(stesso SHA-256), non ci sono file orfani, e data/documenti.json e docs/documenti/README.md sono aggiornati.
Non usano la rete.
"""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import documenti as dc  # noqa: E402

CAMPI_DOCUMENTO = {"tipo", "titolo", "url", "pagina", "referenziato", "file", "testo", "scaricato_il", "pagine",
                   "byte", "sha256", "note"}


class TestDocumenti(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.righe = dc.leggi_registro()
        cls.fondi = dc.fondi_per_id()
        cls.indice, cls.errori = dc.costruisci_indice(cls.righe, cls.fondi)

    def test_registro_e_file_coerenti(self):
        self.assertEqual(self.errori, [])

    def test_indice_aggiornato(self):
        salvato = json.loads(dc.INDICE.read_text(encoding="utf-8"))
        self.assertEqual(salvato, self.indice, "rigenera l'indice: python scripts/documenti.py indice")

    def test_readme_aggiornato(self):
        self.assertEqual(dc.README.read_text(encoding="utf-8"), dc.scrivi_readme(self.indice, self.fondi))

    def test_schema(self):
        self.assertEqual(len(self.indice["fondi"]), len(self.fondi))
        tipi = {t["id"] for t in self.indice["tipi"]}
        for f in self.indice["fondi"]:
            self.assertIn(f["fondo_id"], self.fondi)
            self.assertLessEqual(f["scaricati_referenziati"], f["referenziati"])
            for d in f["documenti"]:
                self.assertEqual(set(d), CAMPI_DOCUMENTO)
                self.assertIn(d["tipo"], tipi)
                if d["file"]:
                    self.assertTrue(d["file"].startswith(f"documenti/{f['fondo_id']}/"))
                    self.assertRegex(d["scaricato_il"], r"^\d{4}-\d{2}-\d{2}$")
                else:
                    self.assertTrue(d["note"], f"{f['fondo_id']}: documento non scaricato senza motivo")

    def test_pdf_e_testo(self):
        for f in self.indice["fondi"]:
            for d in f["documenti"]:
                if not d["file"]:
                    continue
                pdf = ROOT / "docs" / d["file"]
                self.assertEqual(pdf.read_bytes()[:5], b"%PDF-", d["file"])
                testo = (ROOT / "docs" / d["testo"]).read_text(encoding="utf-8")
                if d["url"]:  # le copie fornite a mano possono non avere un link diretto
                    self.assertIn(f"# Fonte: {d['url']}", testo)
                self.assertIn("=== pagina 1 ===", testo)
                # GitHub rifiuta i file oltre 100 MB e avvisa oltre 50 MB
                self.assertLess(d["byte"], 50 * 1024 * 1024, d["file"])

    def test_note_dei_fondi_senza_documenti(self):
        # ogni fondo senza neanche un documento scaricato spiega il perché (nota sul fondo o note dei documenti)
        for f in self.indice["fondi"]:
            if not f["scaricati"]:
                self.assertTrue(f["nota"] or any(d["note"] for d in f["documenti"]), f["fondo_id"])

    def test_smistamento_riconosce_fondo_e_tipo(self):
        # un documento vero: il fondo si riconosce dal testo anche se il nome del file non dice nulla
        ric = dc.riconosci(ROOT / "docs" / "documenti" / "aureo" / "regolamento.pdf", self.fondi)
        self.assertEqual((ric["fondo"], ric["tipo"]), ("aureo", "regolamento"))
        # la sottocartella con l'id del fondo vince sul testo
        ric = dc.riconosci(ROOT / "docs" / "documenti" / "aureo" / "regolamento.pdf", self.fondi, "teseo")
        self.assertEqual((ric["fondo"], ric["certezza"]), ("teseo", "cartella"))
        # titoli: la scheda vince sulla "Nota informativa" che la precede; il nome del file vince sul testo
        self.assertEqual(dc._tipo("", "nota informativa parte i le informazioni chiave scheda i costi"), "scheda-costi")
        self.assertEqual(dc._tipo("", "supplemento alla nota informativa le prestazioni"), "supplemento")
        self.assertEqual(dc._tipo(dc._normalizza("Documento sull’erogazione delle rendite"), ""), "documento-rendite")
        self.assertEqual(dc._tipo("scansione 1", "testo senza titoli riconoscibili"), "altro")

    def test_cassetta_ignorata_da_git(self):
        regole = (dc.CASSETTA / ".gitignore").read_text(encoding="utf-8").split()
        self.assertIn("*", regole)
        self.assertTrue((dc.CASSETTA / "README.md").exists())

    def test_valida_segnala_gli_errori(self):
        riga = {"fondo_id": "inesistente", "tipo": "boh", "titolo": "", "file": "Nome Sbagliato.PDF", "url": "",
                "pagina": "", "referenziato": "forse", "note": ""}
        errori = dc.valida([riga], self.fondi)
        self.assertEqual(len(errori), 6)  # fondo, tipo, referenziato, titolo, nome file, file senza link né nota


if __name__ == "__main__":
    unittest.main()
