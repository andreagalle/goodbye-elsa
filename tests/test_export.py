"""Test di schema per scripts/export_xlsx.py (python -m unittest discover -s tests)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import export_xlsx as ex  # noqa: E402

CAMPI_FONDO = {
    "id", "riga", "denominazione", "nome_breve", "url", "societa", "spese_adesione", "spese_annue",
    "costo_pct_versato", "n_linee", "n_comparti", "comm_min", "comm_max", "max_azioni", "best_rend_10a",
    "esg", "life_cycle", "online", "scheda_url", "note", "has_dati", "flag_anomalia",
}
CAMPI_COMPARTO = {
    "fondo_id", "riga", "comparto", "categoria", "azioni", "obbligazioni", "rendimento", "periodo_anni",
    "commissione", "scheda_url", "note", "flag_anomalia",
}


class TestExport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rep = ex.Report()
        cls.fondi, cls.comparti, cls.meta = ex.esporta(ex.XLSX_DEFAULT, cls.rep)
        cls.per_id = {f["id"]: f for f in cls.fondi}

    def test_nessun_errore(self):
        self.assertEqual(self.rep.errori, [])

    def test_campi(self):
        for f in self.fondi:
            self.assertEqual(set(f), CAMPI_FONDO)
        for c in self.comparti:
            self.assertEqual(set(c), CAMPI_COMPARTO)

    def test_conteggi(self):
        self.assertEqual(len(self.fondi), 38)
        self.assertEqual(len(self.comparti), 102)
        self.assertEqual(sum(f["has_dati"] for f in self.fondi), 23)

    def test_id_unici_e_riferimenti(self):
        self.assertEqual(len(self.per_id), len(self.fondi))
        for c in self.comparti:
            self.assertIn(c["fondo_id"], self.per_id)

    def test_vuoti_sono_null_non_zero(self):
        almeglio = self.fondi[2]
        self.assertFalse(almeglio["has_dati"])
        for campo in ("spese_adesione", "spese_annue", "comm_min", "best_rend_10a", "esg"):
            self.assertIsNone(almeglio[campo])
        self.assertEqual(almeglio["n_comparti"], 0)

    def test_metriche_ricalcolate(self):
        n = {}
        for c in self.comparti:
            n[c["fondo_id"]] = n.get(c["fondo_id"], 0) + 1
        for f in self.fondi:
            self.assertEqual(f["n_comparti"], n.get(f["id"], 0))
            suoi = [c for c in self.comparti if c["fondo_id"] == f["id"]]
            r10 = [c["rendimento"] for c in suoi if c["periodo_anni"] == 10 and c["rendimento"] is not None]
            self.assertEqual(f["best_rend_10a"], max(r10) if r10 else None)

    def test_percentuali_decimali(self):
        for c in self.comparti:
            for campo in ("azioni", "obbligazioni", "commissione"):
                if c[campo] is not None:
                    self.assertGreaterEqual(c[campo], 0)
                    self.assertLessEqual(c[campo], 1)

    def test_flag_anomalie_note(self):
        def flag(fondo, comparto):
            return next(c["flag_anomalia"] for c in self.comparti
                        if c["fondo_id"] == fondo and c["comparto"] == comparto)
        self.assertIn("garantito_azionario", flag("aureo", "Garantito ESG"))
        self.assertIn("garantito_azionario", flag("arti-e-mestieri", "Garanzia 1+"))
        self.assertIn("garantito_azionario", flag("cnp", "Garanzia restituzione capitale"))
        self.assertIn("periodo_non_10", flag("fondo-pensione-fideuram", "Millennials"))
        self.assertIn("rendimento_mancante", flag("programma-open", "Nuovo obbligazionario etico"))
        self.assertEqual(flag("allianz-previdenza", "Linea azionaria"), [])

    def test_flag_somma_allocazione(self):
        c = {"comparto": "X", "categoria": "BIL", "azioni": 0.5, "obbligazioni": 0.3,
             "rendimento": 0.01, "periodo_anni": 10, "commissione": 0.01}
        self.assertEqual(ex.flag_comparto(c), ["somma_allocazione"])

    def test_slug_e_nome_breve(self):
        self.assertEqual(ex.slugify("Arti & Mestieri"), "arti-e-mestieri")
        self.assertEqual(ex.nome_breve("FONDO PENSIONE APERTO TESEO"), "Teseo")


if __name__ == "__main__":
    unittest.main()
