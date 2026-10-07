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
        pg.on("console", lambda m: errori.append(m.text) if m.type == "error" else None)
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

    def test_mobile_senza_scroll_orizzontale(self):
        pg, errori = self.pagina("", viewport={"width": 390, "height": 844}, color_scheme="dark")
        pg.wait_for_selector("#tab-fondi tbody tr")
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
