"""Smoke test del sito in Chromium headless (saltato se Playwright non è installato).

Controlla che dashboard, guida e presentazione si carichino senza errori JavaScript,
con i dati attesi e senza scroll orizzontale su mobile. Richiede rete (librerie da CDN)
e i JSON in docs/data/ (python scripts/export_xlsx.py).
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

try:
    from playwright.sync_api import sync_playwright
except ImportError:  # pragma: no cover
    sync_playwright = None

from server_locale import servi  # noqa: E402

# Risorse facoltative: se mancano la pagina funziona lo stesso (vedi caricaDocumenti() in app.js), quindi il loro
# 404, che il browser scrive in console come errore, non fa fallire i test. Ogni altro errore sì.
FACOLTATIVE = ("/data/documenti.json",)


@unittest.skipIf(sync_playwright is None, "Playwright non installato (pip install -r requirements-dev.txt)")
@unittest.skipUnless((ROOT / "docs" / "data" / "fondi.json").exists(), "manca docs/data: esegui l'export")
class TestSito(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._srv = servi()
        cls.base = cls._srv.__enter__()
        cls._pw = sync_playwright().start()
        try:
            cls.browser = cls._pw.chromium.launch()
        except Exception as e:  # browser non installato
            cls._pw.stop()
            cls._srv.__exit__(None, None, None)
            raise unittest.SkipTest(f"Chromium non disponibile: {e}")

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls._pw.stop()
        cls._srv.__exit__(None, None, None)

    def pagina(self, url, **kw):
        pg = self.browser.new_page(**kw)
        errori = []
        pg.on("pageerror", lambda e: errori.append(str(e)))
        pg.on("console", lambda m: errori.append(m.text)
              if m.type == "error" and not m.location.get("url", "").endswith(FACOLTATIVE) else None)
        pg.goto(self.base + url)
        return pg, errori

    def test_dashboard(self):
        pg, errori = self.pagina("", viewport={"width": 1280, "height": 900})
        pg.wait_for_selector("#tab-fondi tbody tr")
        pg.wait_for_function("() => window.Chart && Chart.getChart('scatter')")
        self.assertEqual(pg.locator("#tab-fondi tbody tr").count(), 38)
        pg.check("#f-dati")
        self.assertEqual(pg.locator("#tab-fondi tbody tr").count(), 23)
        self.assertIn("Versione", pg.inner_text("#meta-footer"))
        footer = pg.inner_text(".site-footer")
        self.assertIn("The Unlicense", footer)
        self.assertNotIn("MIT", footer)
        self.assertEqual(errori, [])

    def test_dettaglio_da_link(self):
        pg, errori = self.pagina("#fondo=aureo", viewport={"width": 1280, "height": 900})
        pg.wait_for_selector("#dettaglio[open] table")
        self.assertEqual(pg.locator("#dettaglio tbody tr").count(), 5)
        self.assertEqual(errori, [])

    def test_menu_e_torna_su(self):
        pg, errori = self.pagina("", viewport={"width": 1280, "height": 900})
        pg.wait_for_selector("#tab-fondi tbody tr")
        self.assertFalse(pg.is_visible(".su.visibile"))
        pg.evaluate("document.getElementById('categorie').scrollIntoView({behavior: 'instant'})")
        pg.wait_for_selector('.topnav a[href="#categorie"][aria-current="true"]')
        pg.wait_for_selector(".su.visibile")
        pg.click(".su")
        pg.wait_for_function("() => window.scrollY === 0")
        self.assertEqual(errori, [])

    def test_marchio_e_favicon(self):
        """Logo "goodbye Elsa !!" e favicon in tutte le pagine; il logo riporta all'inizio della dashboard."""
        for url in ("", "guida/", "presentazione/"):
            with self.subTest(pagina=url or "dashboard"):
                pg, errori = self.pagina(url, viewport={"width": 1280, "height": 900})
                pg.wait_for_function("() => document.querySelector('.marchio img')?.complete")
                self.assertGreater(pg.eval_on_selector(".marchio img", "i => i.naturalWidth"), 0)
                self.assertEqual(pg.inner_text(".marchio .scritta"), "goodbye Elsa !!")
                self.assertEqual(pg.eval_on_selector(".marchio", "a => a.href"), self.base)
                icone = pg.evaluate("""() => Promise.all([...document.querySelectorAll('link[rel~="icon"], link[rel="apple-touch-icon"]')]
                    .map((l) => fetch(l.href).then((r) => r.ok)))""")
                self.assertEqual(icone, [True, True, True])
                self.assertEqual(errori, [])
        # sulla dashboard non ricarica la pagina: torna in cima e toglie l'ancora dall'indirizzo
        pg, errori = self.pagina("#glossario", viewport={"width": 1280, "height": 900})
        pg.wait_for_selector("#tab-fondi tbody tr")
        pg.wait_for_function("() => window.scrollY > 0")
        pg.evaluate("window.ricaricata = false")
        pg.click(".marchio")
        pg.wait_for_function("() => window.scrollY === 0")
        self.assertEqual(pg.evaluate("location.hash"), "")
        self.assertIs(pg.evaluate("window.ricaricata"), False, "il clic sul logo ha ricaricato la pagina")
        self.assertEqual(errori, [])

    def test_regole_e_longevita(self):
        import json
        regole = json.loads((ROOT / "docs" / "data" / "regole.json").read_text(encoding="utf-8"))
        primo_tema = regole[0]["tema"]
        pg, errori = self.pagina("", viewport={"width": 1280, "height": 900})
        pg.wait_for_selector("#r-lista .regola")
        self.assertEqual(pg.locator("#r-lista .regola").count(), sum(r["tema"] == primo_tema for r in regole))
        pg.click('#r-temi [data-tema="Tutte"]')
        self.assertEqual(pg.locator("#r-lista .regola").count(), len(regole))
        pg.check("#r-varia")
        self.assertEqual(pg.locator("#r-lista .regola").count(), sum(r["uguale_per_tutti"] != "Sì" for r in regole))
        pg.wait_for_function("() => window.Chart && Chart.getChart('longevita')")
        self.assertEqual(pg.locator("#l-kpi .kpi").count(), 4)
        pg.goto(self.base + "#fondo=insieme")
        pg.wait_for_selector("#dettaglio[open] .verifica li")
        self.assertEqual(errori, [])

    def test_glossario_e_suggerimenti(self):
        import json
        glossario = json.loads((ROOT / "docs" / "data" / "glossario.json").read_text(encoding="utf-8"))
        # senza scroll animato: lo scroll chiude i suggerimenti, e Playwright muove il mouse mentre la pagina scorre
        pg, errori = self.pagina("", viewport={"width": 1280, "height": 900}, reduced_motion="reduce")
        pg.wait_for_selector("#gl-lista .gl-voce")
        self.assertEqual(pg.locator("#gl-lista .gl-voce").count(), len(glossario))
        # ogni termine collegato nella pagina ha una voce nel glossario
        usati = set(pg.eval_on_selector_all("[data-glossario]", "els => els.map(e => e.dataset.glossario)"))
        self.assertTrue(usati)
        self.assertEqual(usati - {g["id"] for g in glossario}, set())
        pg.fill("#gl-cerca", "sostenibil")
        self.assertIn("ESG", pg.inner_text("#gl-lista"))
        pg.fill("#gl-cerca", "")
        # mouse sul filtro ESG: compare la definizione; Esc la chiude
        tip = pg.locator("#suggerimento")
        pg.hover('label.chk[data-glossario="esg"]')
        tip.wait_for(state="visible")
        self.assertIn("Environmental", tip.inner_text())
        pg.keyboard.press("Escape")
        tip.wait_for(state="hidden")
        # tastiera: il focus sul pulsante di ordinamento mostra la spiegazione della colonna
        pg.focus('#tab-fondi th[data-key="comm_min"] button')
        pg.keyboard.press("Shift+Tab")
        pg.keyboard.press("Tab")
        tip.wait_for(state="visible")
        self.assertIn("Commissione di gestione", tip.inner_text())
        self.assertEqual(pg.evaluate("document.activeElement.getAttribute('aria-describedby')"), "suggerimento")
        # nel dettaglio fondo il suggerimento sta dentro il <dialog>, sopra la finestra
        pg.goto(self.base + "#fondo=aureo")
        pg.wait_for_selector("#dettaglio[open] table")
        pg.hover("#dettaglio .tag-cat[data-glossario]")
        tip.wait_for(state="visible")
        self.assertTrue(pg.evaluate("!!document.getElementById('suggerimento').closest('dialog')"))
        self.assertEqual(errori, [])

    def test_mobile_senza_scroll_orizzontale(self):
        pg, errori = self.pagina("", viewport={"width": 390, "height": 844}, color_scheme="dark", has_touch=True)
        pg.wait_for_selector("#tab-fondi tbody tr")
        self.assertLessEqual(pg.evaluate("document.documentElement.scrollWidth"), 390)
        # da telefono la spiegazione si apre con un tocco sul termine
        pg.locator("#kpis .termine").first.tap()
        pg.locator("#suggerimento").wait_for(state="visible")
        self.assertLessEqual(pg.evaluate("document.documentElement.scrollWidth"), 390)
        self.assertEqual(errori, [])

    def test_guida(self):
        pg, errori = self.pagina("guida/", viewport={"width": 1280, "height": 900})
        pg.wait_for_selector("#contenuto h1")
        pg.wait_for_function("() => [...document.images].every(i => i.complete)")
        immagini = pg.eval_on_selector_all("#contenuto img", "els => els.map(e => [e.getAttribute('src'), e.naturalWidth > 0])")
        self.assertTrue(immagini, "la guida non ha immagini")
        self.assertEqual([src for src, ok in immagini if not ok], [], "immagini non caricate")
        self.assertEqual(errori, [])

    def test_presentazione_2d(self):
        pg, errori = self.pagina("presentazione/", viewport={"width": 1280, "height": 800})
        pg.wait_for_function("() => window.Reveal && Reveal.isReady()")
        orizzontali = pg.evaluate("Reveal.getHorizontalSlides().length")
        verticali = pg.evaluate("Reveal.getHorizontalSlides().filter(s => s.querySelector(':scope > section')).length")
        self.assertGreaterEqual(orizzontali, 5)
        self.assertGreaterEqual(verticali, 3, "servono pile verticali per la navigazione 2D")
        pg.keyboard.press("ArrowRight")
        pg.keyboard.press("ArrowDown")
        self.assertEqual(pg.evaluate("Reveal.getIndices().v"), 1)
        self.assertEqual(errori, [])


if __name__ == "__main__":
    unittest.main()
