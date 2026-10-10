#!/usr/bin/env bash
# Anteprima locale della GitHub Page, identica a quella pubblicata dalla CI:
# export dei dati → test (schema, versioni, smoke test del sito) → server su docs/.
#   ./scripts/anteprima.sh            export + test + server sulla porta 8000
#   ./scripts/anteprima.sh --veloce   salta i test
#   PORTA=9000 ./scripts/anteprima.sh
set -euo pipefail
cd "$(dirname "$0")/.."
PORTA="${PORTA:-8000}"

echo "▶ Export dei dati"
python scripts/export_xlsx.py
python scripts/documenti.py indice

if [[ "${1:-}" != "--veloce" ]]; then
  echo "▶ Test"
  python -m unittest discover -s tests
fi

echo "▶ Versione che verrebbe pubblicata al merge: $(python scripts/versione.py prossima 2>/dev/null || echo '?')"
echo "▶ Anteprima su http://localhost:${PORTA}/  (guida: /guida/, presentazione: /presentazione/) — Ctrl+C per uscire"
exec python -c "
import sys, time; sys.path.insert(0, 'scripts')
from server_locale import servi
with servi(porta=${PORTA}, host='0.0.0.0'):
    try:
        while True: time.sleep(3600)
    except KeyboardInterrupt:
        pass
"
