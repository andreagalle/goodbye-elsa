#!/usr/bin/env python3
"""Rigenera gli screenshot usati dalla guida e dalla presentazione (docs/guida/img/).

Richiede requirements-dev.txt e `python -m playwright install chromium`. Esegue prima l'export,
così le immagini mostrano sempre i dati correnti. Uso: python scripts/screenshots.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from server_locale import servi  # noqa: E402

OUT = ROOT / "docs" / "guida" / "img"


def attendi(pg):
    pg.wait_for_selector("#tab-fondi tbody tr")
    pg.evaluate("document.fonts.ready.then(() => true)")
    pg.wait_for_function("() => !!document.querySelector('#scatter') && window.Chart && Chart.getChart('scatter')")
    pg.wait_for_timeout(300)


def main() -> int:
    subprocess.run([sys.executable, str(ROOT / "scripts" / "export_xlsx.py")], check=True)
    OUT.mkdir(parents=True, exist_ok=True)
    with servi() as base, sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1360, "height": 820}, color_scheme="light")
        pg.goto(base)
        attendi(pg)
        pg.screenshot(path=OUT / "dashboard.png")
        # negli screenshot delle singole sezioni la barra fissa coprirebbe il titolo
        pg.add_style_tag(content=".topnav { position: static; }")

        pg.check("#f-dati")
        pg.check("#f-esg")
        pg.click("#tab-fondi th[data-key=comm_min] button")
        pg.mouse.move(0, 0)
        pg.locator("#fondi").screenshot(path=OUT / "tabella-filtri.png")

        pg.locator("#grafico").screenshot(path=OUT / "grafico.png")
        pg.check("#g-periodi")
        pg.select_option("#g-fondo", "secondapensione")
        pg.wait_for_timeout(200)
        pg.locator("#grafico").screenshot(path=OUT / "grafico-evidenzia.png")

        pg.locator("#categorie").screenshot(path=OUT / "categorie.png")
        q = pg.locator("#qualita")
        q.scroll_into_view_if_needed()
        box = q.bounding_box()
        pg.screenshot(path=OUT / "qualita.png", full_page=True,
                      clip={"x": box["x"], "y": box["y"] + pg.evaluate("scrollY"), "width": box["width"],
                            "height": min(box["height"], 760)})

        pg = b.new_page(viewport={"width": 1360, "height": 820}, color_scheme="light")
        pg.goto(base + "#fondo=aureo")
        attendi(pg)
        pg.wait_for_selector("#dettaglio[open] table")
        pg.wait_for_timeout(200)
        pg.screenshot(path=OUT / "dettaglio.png")

        m = b.new_page(viewport={"width": 390, "height": 844}, color_scheme="dark", device_scale_factor=1)
        m.goto(base)
        attendi(m)
        m.screenshot(path=OUT / "mobile-scuro.png")
        b.close()
    print(f"Screenshot aggiornati in {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
