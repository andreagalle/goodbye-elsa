# Confronto Fondi Pensione Aperti (COVIP)

Analisi comparativa dei **fondi pensione aperti** iscritti all'Albo COVIP: costi, comparti,
asset allocation, rendimenti e commissioni, con una dashboard pubblicata su GitHub Pages.

🔗 **Dashboard:** https://<utente>.github.io/<repo>/

## Contenuto

| Percorso | Descrizione |
|---|---|
| `data/fondi-pensione-covip.xlsx` | Workbook sorgente (fonte di verità, modificato a mano in Excel) |
| `data/fondi.json`, `data/comparti.json` | Dati esportati dal workbook (generati, non modificarli a mano) |
| `scripts/export_xlsx.py` | Converte il workbook in JSON |
| `docs/` | Sito statico GitHub Pages (HTML/CSS/JS) |
| `.github/workflows/` | CI: export dei dati + deploy del sito |
| `CLAUDE.md` | Contesto e istruzioni per lo sviluppo assistito da Claude |

## Dati

- **38 fondi pensione aperti** (dall'elenco COVIP), di cui **23** con dati dettagliati presi dalle schede di [Ciao Elsa](https://www.ciaoelsa.com).
- **102 comparti**, con categoria, % azioni/obbligazioni, rendimento netto medio annuo, orizzonte del rendimento e commissione di gestione.
- Le metriche per fondo (n. comparti, commissione min/max, % azioni max, miglior rendimento a 10 anni) sono **calcolate con formule** a partire dal foglio `Comparti`.

> ⚠️ I dati vengono da fonti secondarie (Ciao Elsa) e contengono anomalie note (vedi `CLAUDE.md` → *Problemi noti nei dati*).
> Prima di prendere qualsiasi decisione, verificali sulla **Nota informativa / Scheda costi** ufficiale del fondo.
> Questo progetto non è una consulenza finanziaria.

## Workflow

```bash
# 1. Modifica data/fondi-pensione-covip.xlsx in Excel e salva (così i valori delle formule restano in cache)
# 2. Rigenera i JSON
python scripts/export_xlsx.py
# 3. Anteprima del sito in locale
python -m http.server -d docs 8000
# 4. Commit e push: la GitHub Action pubblica la dashboard
```

## Requisiti
Python 3.11+, `openpyxl` (`pip install -r requirements.txt`).

## Licenza e fonti
Dati: COVIP, siti ufficiali dei gestori, Ciao Elsa (vedi `CLAUDE.md` per l'elenco completo). Codice: MIT.