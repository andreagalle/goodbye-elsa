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

    def test_licenza_dal_file_license(self):
        lic = self.meta["licenza"]
        testo = (ex.ROOT / "LICENSE").read_text(encoding="utf-8").lower()
        if "public domain" in testo and "unencumbered" in testo:
            self.assertEqual(lic["spdx"], "Unlicense")
        self.assertNotEqual(lic["nome"], "vedi file LICENSE", "licenza non riconosciuta")

    def test_regole(self):
        regole = self.meta["_extra"]["regole"]
        self.assertGreaterEqual(len(regole), 30)
        self.assertEqual(len({g["id"] for g in regole}), len(regole))
        for g in regole:
            self.assertIn(g["tema"], ex.TEMI_REGOLE)
            self.assertIn(g["uguale_per_tutti"], ex.UGUALE_PER_TUTTI)
            self.assertTrue(g["fonte_url"].startswith("https://"), g["id"])
            self.assertRegex(g["consultata_il"], r"^\d{4}-\d{2}-\d{2}$")
            if g["uguale_per_tutti"] != "Sì":
                self.assertTrue(g["varia"], g["id"])
        # il limite del capitale è tornato al 50% (D.L. 62/2026): un test lo protegge da modifiche distratte
        capitale = next(g for g in regole if g["domanda"].startswith("Quanto posso prendere in capitale"))
        self.assertEqual(capitale["valore"], "50%")
        self.assertIn("60%", capitale["note"])

    def test_longevita(self):
        lon = self.meta["_extra"]["longevita"]
        self.assertEqual(lon["eta_partenza"], 67)
        for sesso in ex.SESSI:
            serie = lon["serie"][sesso]
            self.assertEqual(serie[0], {"eta": 67, "vivi": 1.0})
            quote = [p["vivi"] for p in serie]
            self.assertEqual(quote, sorted(quote, reverse=True))
            sin = lon["sintesi"][sesso]
            self.assertTrue(15 < sin["speranza"] < 25, sin)
            self.assertLess(sin["eta_75_vivi"], sin["eta_50_vivi"])
            self.assertLess(sin["eta_50_vivi"], sin["eta_25_vivi"])
        dd = lon["durata_definita"]
        self.assertEqual(dd["anni"], int(lon["sintesi"]["totale"]["speranza"]))
        self.assertEqual(dd["eta_fine"], 67 + dd["anni"])
        self.assertTrue(lon["fonte"]["url"].startswith("https://"))

    def test_fonti_includono_regole(self):
        urls = {f["url"] for f in self.meta["fonti"]}
        for g in self.meta["_extra"]["regole"]:
            self.assertIn(g["fonte_url"], urls)

    def test_glossario(self):
        voci = self.meta["_extra"]["glossario"]
        self.assertGreaterEqual(len(voci), 40)
        self.assertEqual(len({v["id"] for v in voci}), len(voci))
        for v in voci:
            self.assertRegex(v["id"], ex.RE_ID_GLOSSARIO)
            self.assertIn(v["gruppo"], ex.GRUPPI_GLOSSARIO)
            self.assertTrue(v["termine"] and v["definizione"], v["id"])
            self.assertLessEqual(len(v["definizione"]), ex.DEFINIZIONE_MAX, v["id"])
            self.assertTrue(v["fonte_url"].startswith("https://"), v["id"])
            self.assertRegex(v["consultata_il"], r"^\d{4}-\d{2}-\d{2}$")
        # voci usate dalla dashboard (data-glossario in app.js e index.html)
        ids = {v["id"] for v in voci}
        for voce in ("esg", "life-cycle", "sottoscrizione-online", "azn", "bil", "obb", "gar", "commissione-gestione"):
            self.assertIn(voce, ids)
        # i numeri ripresi dal foglio Regole devono restare allineati
        regole = {g["titolo"]: g for g in self.meta["_extra"]["regole"]}
        per_id = {v["id"]: v for v in voci}
        self.assertIn(regole["Capitale"]["valore"], per_id["capitale"]["definizione"])
        self.assertIn(regole["Deducibilità"]["valore"].split(" l'anno")[0], per_id["deducibilita"]["definizione"])

    def test_glossario_nella_guida(self):
        """La tabella del glossario in GUIDA.md è generata dal foglio: se non coincide, va rifatto l'export."""
        testo = ex.GUIDA.read_text(encoding="utf-8")
        i, j = testo.find(ex.INIZIO_GLOSSARIO), testo.find(ex.FINE_GLOSSARIO)
        self.assertTrue(0 <= i < j, "mancano i marcatori del glossario in GUIDA.md")
        self.assertEqual(testo[i:j + len(ex.FINE_GLOSSARIO)], ex.glossario_md(self.meta["_extra"]["glossario"]),
                         "glossario di GUIDA.md non allineato al foglio Glossario: esegui python scripts/export_xlsx.py")

    def test_fonti_includono_glossario(self):
        urls = {f["url"] for f in self.meta["fonti"]}
        per_nome = {}
        for v in self.meta["_extra"]["glossario"]:
            per_nome.setdefault(v["fonte_nome"], []).append(v["fonte_url"])
        for nome, link in per_nome.items():
            self.assertIn(ex.url_comune(link), urls, nome)
        self.assertEqual(ex.url_comune(["https://x.it/glossario/e#esg", "https://x.it/glossario/l#life-cycle"]),
                         "https://x.it/glossario")

    def test_prestazioni(self):
        prest = self.meta["_extra"]["prestazioni"]
        self.assertGreaterEqual(len(prest), 20)
        self.assertEqual(self.meta["conteggi"]["fondi_con_prestazioni"], len(prest))
        self.assertEqual(len({p["fondo_id"] for p in prest}), len(prest))
        for p in prest:
            self.assertIn(p["fondo_id"], self.per_id)
            self.assertTrue(p["documento_rendite"] or p["scheda_costi"] or p["supplemento"], p["fondo_id"])
            for doc in (p["documento_rendite"], p["scheda_costi"], p["supplemento"]):
                if doc:
                    self.assertTrue(doc["url"].startswith("https://"), p["fondo_id"])
            self.assertRegex(p["consultata_il"], r"^\d{4}-\d{2}-\d{2}$")
            for v in p["varianti"].values():
                self.assertTrue(v is None or v.startswith(("Sì", "No")), (p["fondo_id"], v))
            # formule del foglio (H e J) ricalcolate come in Excel
            self.assertEqual(p["n_varianti"], sum(1 for v in p["varianti"].values() if v and v.startswith("Sì")))
            if p["rendita_67"] is None:
                self.assertIsNone(p["tasso_conversione_67"])
            else:
                lo, hi = ex.RENDITA_67_PLAUSIBILE
                self.assertTrue(lo <= p["rendita_67"] <= hi, p["fondo_id"])
                self.assertAlmostEqual(p["tasso_conversione_67"], p["rendita_67"] / 10000)
                self.assertIsNotNone(p["documento_rendite"], p["fondo_id"])
            # percentuali come decimali, costi in euro
            for campo in ("tasso_tecnico", "costo_rendita"):
                self.assertTrue(p[campo] is None or 0 <= p[campo] < 0.05, (p["fondo_id"], campo))
            for v in p["costi"].values():
                self.assertTrue(v is None or v >= 0)

    def test_cache_formule_piena(self):
        """Il workbook salvato (da Excel o da workbook_utils.salva) ha i valori delle formule in cache."""
        self.assertFalse([w for w in self.rep.warning if "cache" in w], self.rep.warning)

    def test_slug_e_nome_breve(self):
        self.assertEqual(ex.slugify("Arti & Mestieri"), "arti-e-mestieri")
        self.assertEqual(ex.nome_breve("FONDO PENSIONE APERTO TESEO"), "Teseo")


if __name__ == "__main__":
    unittest.main()
