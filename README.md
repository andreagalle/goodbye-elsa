<p align="center"><img src="docs/img/elsa.png" alt="Logo goodbye Elsa !!: Elsa, una nonna arrabbiata che agita il bastone" width="160"></p>

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
| `data/fondi.json`, `data/comparti.json`, `data/regole.json`, `data/longevita.json`, `data/glossario.json`, `data/prestazioni.json`, `data/meta.json` | Dati esportati dal workbook (generati, non modificarli a mano) |
| `scripts/export_xlsx.py` | Converte il workbook in JSON, con validazione dello schema e anomalie |
| `data/documenti.csv`, `docs/documenti/` | Registro e copie dei **documenti ufficiali dei fondi** (PDF + testo estratto per pagina), [elenco](docs/documenti/README.md) |
| `scripts/documenti.py` | Scarica i documenti del registro (o smista quelli aggiunti a mano), ne estrae il testo e genera `data/documenti.json` e l'elenco |
| `documenti-da-smistare/` | Cartella dove mettere i PDF scaricati dal browser per i siti che bloccano gli script ([istruzioni](documenti-da-smistare/README.md)) |
| `scripts/versione.py` | Calcola la prossima versione e le note di rilascio dai commit |
| `scripts/workbook_utils.py` | Salva il workbook da Python calcolando le formule (cache piena, come Excel) e senza perdere il collegamento a Claude per Excel |
| `scripts/anteprima.sh` | Anteprima locale della GitHub Page (export + test + server) |
| `scripts/screenshots.py` | Rigenera gli screenshot della guida e della presentazione |
| `scripts/icone.py` | Rigenera logo e favicon (`docs/img/`) dall'immagine originale `assets/elsa.png` |
| `docs/` | Sito statico GitHub Pages: dashboard, `guida/`, `presentazione/`, `img/` (logo e favicon) |
| `assets/elsa.png` | Logo *goodbye Elsa !!* originale (2048 px), fuori dal sito pubblicato |
| `tests/` | Test di schema, versioni, documenti e smoke test del sito (Playwright) |
| `.github/workflows/` | `ci.yml` (PR) e `pages.yml` (deploy + tag + release al merge) |
| `.devcontainer/`, `.mcp.json` | Ambiente di sviluppo e MCP server Playwright |
| `CLAUDE.md` | Contesto, regole e istruzioni per lo sviluppo assistito da Claude |

## Dati

- **38 fondi pensione aperti** dall'[elenco dei fondi iscritti all'Albo COVIP](https://www.covip.it/la-covip-e-la-sua-attivita/albo-fondi-pensione/elenco-fondi-albo)
  (filtro *Tipologia: Sezione II – Fondi pensione aperti*), di cui **23** con dati dettagliati presi dalle schede di [Ciao Elsa](https://www.ciaoelsa.com).
- **102 comparti**, con categoria, % azioni/obbligazioni, rendimento netto medio annuo, orizzonte del rendimento e commissione di gestione.
- Le metriche per fondo (n. comparti, commissione min/max, % azioni max, miglior rendimento a 10 anni) sono **calcolate con formule** a partire dal foglio `Comparti`.
- **32 regole generali** (TFR, tasse, anticipazioni, opzioni alla pensione, decesso) aggiornate alla Legge di Bilancio 2026,
  ognuna con riferimento normativo e link alla fonte ufficiale (foglio `Regole`), e la **tavola di mortalità ISTAT 2025**
  per ragionare sulla durata della pensione (foglio `Longevita`).
- **Glossario di 49 termini** (foglio `Glossario`), soprattutto dal [glossario COVIP](https://www.covip.it/per-il-cittadino/educazione-previdenziale/glossario):
  nella dashboard le definizioni compaiono passando il mouse su termini, intestazioni, filtri ed etichette, e sono
  raccolte nella sezione *Glossario*; l'export rigenera anche la tabella del glossario nella guida.
- **Condizioni alla pensione di 32 fondi** (foglio `Prestazioni`), dai documenti ufficiali dei gestori (Documento sulle
  rendite, Scheda costi, Supplemento alla Nota informativa): rendita annua a 67 anni ogni 10.000 € (confrontabile per 24
  fondi), varianti di rendita offerte, costo della rendita, costi di anticipazione, riscatto, trasferimento e RITA.
- **Documenti ufficiali dei fondi**: oltre 500 PDF per 31 fondi (Nota informativa e schede, Supplemento, Regolamento,
  Documento sulle rendite, anticipazioni, regime fiscale, politica di investimento, rendiconto…), scaricati dalle pagine
  dei gestori con il testo estratto pagina per pagina, scaricabili dal dettaglio di ogni fondo. Fa fede la versione del
  gestore; i documenti che non è stato possibile scaricare sono elencati con il motivo in
  [`docs/documenti/README.md`](docs/documenti/README.md).

> ⚠️ I dati vengono da fonti secondarie (Ciao Elsa) e contengono anomalie note (vedi `CLAUDE.md` → *Problemi noti nei dati*).
> Prima di prendere qualsiasi decisione, verificali sulla **Nota informativa / Scheda costi** ufficiale del fondo.
> Questo progetto non è una consulenza finanziaria.

> ℹ️ **Progetto personale**, nato per uso privato e pubblicato su GitHub a puro scopo dimostrativo: non è un servizio rivolto al pubblico. L'autore non è affiliato a COVIP, ai gestori dei fondi o a Ciao Elsa.

## Sviluppo

Il modo più semplice è aprire il repository in **Codespaces** o nel **devcontainer** di VS Code: viene installato tutto
(Python, Playwright, estensioni, MCP) e la porta dell'anteprima viene inoltrata in automatico.

```bash
# 1. Modifica data/fondi-pensione-covip.xlsx in Excel e salva (da Python: workbook_utils.salva(), che calcola le formule)
# 2. Prova il sito in locale, identico a quello che verrà pubblicato
./scripts/anteprima.sh            # export + test + http://localhost:8000
# 3. Se hai cambiato la dashboard, aggiorna gli screenshot di guida e presentazione
python scripts/screenshots.py
# Documenti ufficiali: registro in data/documenti.csv, poi
python scripts/documenti.py scarica   # PDF mancanti + testo (riprova: quelli non scaricati, da un'altra rete)
python scripts/documenti.py indice    # data/documenti.json e docs/documenti/README.md
# 4. Commit (convenzionali, in italiano) su un branch e pull request verso master
```

Al merge della PR su `master`, GitHub Actions pubblica il sito e crea il tag e la release `vX.Y.Z`:
**minor** per i commit `sito:`/`script:`/`feat:`, **patch** per il resto, **major** solo su richiesta esplicita
(label `release:major` o avvio manuale). Una volta sola: *Settings → Pages → Source: GitHub Actions*.
JSON, workbook e zip del sito (senza i PDF dei documenti, che restano nel repository) sono allegati alla release ([Releases](https://github.com/andreagalle/goodbye-elsa/releases/latest)),
non nella sezione *Packages*, che è il registro di GitHub per npm, container e simili.

## Requisiti
Python 3.11+ e `pip install -r requirements-dev.txt` (solo per l'export basta `requirements.txt`),
poi `python -m playwright install chromium` per test e screenshot.

## Licenza e fonti
Dati: COVIP, siti ufficiali dei gestori, Ciao Elsa (vedi `CLAUDE.md` per l'elenco completo). Codice: [The Unlicense](LICENSE) (pubblico dominio); i dati restano delle rispettive fonti.
