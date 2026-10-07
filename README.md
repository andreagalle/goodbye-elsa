# Confronto Fondi Pensione Aperti (COVIP)

Analisi comparativa dei **fondi pensione aperti** iscritti all'Albo COVIP: costi, comparti,
asset allocation, rendimenti e commissioni, con una dashboard pubblicata su GitHub Pages.

- 📊 **Dashboard:** https://andreagalle.github.io/goodbye-elsa/
- 📖 **Guida all'uso:** https://andreagalle.github.io/goodbye-elsa/guida/ (sorgente: [`docs/guida/GUIDA.md`](docs/guida/GUIDA.md))
- 🎞️ **Presentazione interattiva:** https://andreagalle.github.io/goodbye-elsa/presentazione/ (← → argomenti, ↑ ↓ dettagli)

## Contenuto

| Percorso | Descrizione |
|---|---|
| `data/fondi-pensione-covip.xlsx` | Workbook sorgente (fonte di verità, modificato a mano in Excel) |
| `data/fondi.json`, `data/comparti.json`, `data/meta.json` | Dati esportati dal workbook (generati, non modificarli a mano) |
| `scripts/export_xlsx.py` | Converte il workbook in JSON, con validazione dello schema e anomalie |
| `scripts/versione.py` | Calcola la prossima versione e le note di rilascio dai commit |
| `scripts/anteprima.sh` | Anteprima locale della GitHub Page (export + test + server) |
| `scripts/screenshots.py` | Rigenera gli screenshot della guida e della presentazione |
| `docs/` | Sito statico GitHub Pages: dashboard, `guida/`, `presentazione/` |
| `tests/` | Test di schema, versioni e smoke test del sito (Playwright) |
| `.github/workflows/` | `ci.yml` (PR) e `pages.yml` (deploy + tag + release al merge) |
| `.devcontainer/`, `.mcp.json` | Ambiente di sviluppo e MCP server Playwright |
| `CLAUDE.md` | Contesto, regole e istruzioni per lo sviluppo assistito da Claude |

## Dati

- **38 fondi pensione aperti** dall'[elenco dei fondi iscritti all'Albo COVIP](https://www.covip.it/la-covip-e-la-sua-attivita/albo-fondi-pensione/elenco-fondi-albo)
  (filtro *Tipologia: Sezione II – Fondi pensione aperti*), di cui **23** con dati dettagliati presi dalle schede di [Ciao Elsa](https://www.ciaoelsa.com).
- **102 comparti**, con categoria, % azioni/obbligazioni, rendimento netto medio annuo, orizzonte del rendimento e commissione di gestione.
- Le metriche per fondo (n. comparti, commissione min/max, % azioni max, miglior rendimento a 10 anni) sono **calcolate con formule** a partire dal foglio `Comparti`.

> ⚠️ I dati vengono da fonti secondarie (Ciao Elsa) e contengono anomalie note (vedi `CLAUDE.md` → *Problemi noti nei dati*).
> Prima di prendere qualsiasi decisione, verificali sulla **Nota informativa / Scheda costi** ufficiale del fondo.
> Questo progetto non è una consulenza finanziaria.

> ℹ️ **Progetto personale**, nato per uso privato e pubblicato su GitHub a puro scopo dimostrativo: non è un servizio rivolto al pubblico. L'autore non è affiliato a COVIP, ai gestori dei fondi o a Ciao Elsa.

## Sviluppo

Il modo più semplice è aprire il repository in **Codespaces** o nel **devcontainer** di VS Code: viene installato tutto
(Python, Playwright, estensioni, MCP) e la porta dell'anteprima viene inoltrata in automatico.

```bash
# 1. Modifica data/fondi-pensione-covip.xlsx in Excel e salva (così i valori delle formule restano in cache)
# 2. Prova il sito in locale, identico a quello che verrà pubblicato
./scripts/anteprima.sh            # export + test + http://localhost:8000
# 3. Se hai cambiato la dashboard, aggiorna gli screenshot di guida e presentazione
python scripts/screenshots.py
# 4. Commit (convenzionali, in italiano) su un branch e pull request verso master
```

Al merge della PR su `master`, GitHub Actions pubblica il sito e crea il tag e la release `vX.Y.Z`:
**minor** per i commit `sito:`/`script:`/`feat:`, **patch** per il resto, **major** solo su richiesta esplicita
(label `release:major` o avvio manuale). Una volta sola: *Settings → Pages → Source: GitHub Actions*.

## Requisiti
Python 3.11+ e `pip install -r requirements-dev.txt` (solo per l'export basta `requirements.txt`),
poi `python -m playwright install chromium` per test e screenshot.

## Licenza e fonti
Dati: COVIP, siti ufficiali dei gestori, Ciao Elsa (vedi `CLAUDE.md` per l'elenco completo). Codice: MIT.
