#!/usr/bin/env python3
"""Rigenera logo e favicon del sito (docs/img/) dall'immagine originale assets/elsa.png.

L'originale (2048 px, 2,5 MB) resta fuori da docs/, così il sito pubblica solo le versioni leggere:
  elsa.png              512 px  README e guida
  elsa-192.png          192 px  pulsante "goodbye Elsa !!" in alto a sinistra, icona per Android
  apple-touch-icon.png  180 px  icona su iPhone/iPad (sfondo pieno: iOS riempie di nero la trasparenza)
  favicon-32.png         32 px  icona nella scheda del browser
Richiede Pillow (requirements-dev.txt). Uso: python scripts/icone.py
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
ORIGINALE = ROOT / "assets" / "elsa.png"
OUT = ROOT / "docs" / "img"
SFONDO_IOS = (247, 247, 244, 255)  # --page di docs/style.css (tema chiaro)


def quadrato(im: Image.Image, margine: float = 0.0) -> Image.Image:
    """Ritaglia i bordi trasparenti e centra il disegno in un quadrato, con un margine (frazione del lato)."""
    im = im.crop(im.getchannel("A").getbbox())
    lato = round(max(im.size) * (1 + 2 * margine))
    tela = Image.new("RGBA", (lato, lato), (0, 0, 0, 0))
    tela.alpha_composite(im, ((lato - im.width) // 2, (lato - im.height) // 2))
    return tela


def salva(im: Image.Image, nome: str, lato: int) -> None:
    # disegno a tinte piatte: con 256 colori non cambia a occhio e il file pesa circa un decimo
    im = im.resize((lato, lato), Image.Resampling.LANCZOS)
    im.quantize(256, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE).save(OUT / nome, optimize=True)
    print(f"  {nome:22} {lato:>4} px  {(OUT / nome).stat().st_size // 1024:>4} KB")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    elsa = Image.open(ORIGINALE).convert("RGBA")
    print(f"Icone da {ORIGINALE.relative_to(ROOT)} in {OUT.relative_to(ROOT)}:")
    pieno = quadrato(elsa)  # nelle icone piccole conta ogni pixel: niente margine
    salva(quadrato(elsa, 0.02), "elsa.png", 512)
    salva(pieno, "elsa-192.png", 192)
    salva(pieno, "favicon-32.png", 32)
    ios = Image.new("RGBA", pieno.size, SFONDO_IOS)
    ios.alpha_composite(quadrato(elsa, 0.08).resize(pieno.size, Image.Resampling.LANCZOS))
    salva(ios.convert("RGB"), "apple-touch-icon.png", 180)
    return 0


if __name__ == "__main__":
    sys.exit(main())
