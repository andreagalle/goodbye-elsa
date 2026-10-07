#!/usr/bin/env bash
# Prepara l'ambiente: dipendenze Python, browser per test/screenshot e per l'MCP Playwright, primo export.
set -euo pipefail
cd "$(dirname "$0")/.."

# L'immagine base include il repository apt di Yarn con una chiave GPG scaduta, che blocca apt-get
# (e quindi `playwright install --with-deps`). Yarn non serve al progetto: si rimuove la sorgente.
sudo rm -f /etc/apt/sources.list.d/yarn.list

pip install --user --no-warn-script-location -r requirements-dev.txt
# Chromium per i test del sito e gli screenshot (versione di playwright in requirements-dev.txt)
python -m playwright install --with-deps chromium
# Chromium per l'MCP server Playwright (.mcp.json): usa la sua versione di Playwright
npx -y -p @playwright/mcp@0.0.82 playwright install chromium

python scripts/export_xlsx.py
echo "✅ Ambiente pronto. Anteprima del sito: ./scripts/anteprima.sh (oppure il task 'Anteprima GitHub Page')."
