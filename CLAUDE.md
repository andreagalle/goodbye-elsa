# CLAUDE.md — Progetto "Confronto Fondi Pensione Aperti (COVIP)"

## 1. Obiettivo del progetto
1. Mantenere e versionare un dataset dei **fondi pensione aperti italiani** (elenco COVIP), arricchito con costi,
   comparti, asset allocation, rendimenti e commissioni.
2. Pubblicare una **dashboard su GitHub Pages** (`docs/`), aggiornata a ogni push, che renda i dati il più
   utili e fruibili possibile per chi deve scegliere un fondo.
3. Il workbook Excel `data/fondi-pensione-covip.xlsx` è la **fonte di verità**. Il sito legge solo i JSON generati.

Lingua: **italiano** per UI, testi, commenti nei dati, commit message e documentazione. Numeri in formato italiano
nella UI (virgola decimale, `€` dopo l'importo, es. `25,00 €`, `1,45%`).

## 2. Istruzioni originali dell'utente
- Il file nasce da un "Elenco dei fondi pensione COVIP" (fondi pensione aperti) fornito dall'utente con l'URL
  della pagina informativa di ogni fondo, più le **schede Ciao Elsa** dei singoli fondi come fonte dei dati di dettaglio.
- Regole seguite finora (da mantenere):
  - Valori derivati **sempre con formule** in Excel (COUNTIF/MINIFS/MAXIFS sul foglio `Comparti`), mai numeri calcolati e incollati.
  - Ogni dato ha una **fonte tracciabile** (colonna "Scheda Ciao Elsa (fonte)" con hyperlink, oppure una nota).
  - Le **incoerenze delle fonti non vengono corrette in silenzio**: si riporta il dato così com'è e lo si segnala nella colonna `Note`.
  - Dati finanziari solo da **fonti ufficiali/primarie** (COVIP, sito/IR del gestore, Nota informativa, Scheda costi)
    oppure Ciao Elsa, citata esplicitamente come fonte secondaria. Niente blog, forum, aggregatori non citati.
- Istruzioni successive (sviluppo del sito, ottobre 2026):
  - A ogni PR su `master` (al merge): deploy della GitHub Page, tag e release con le note delle ultime modifiche e
    versione incrementale. **Claude incrementa solo minor o patch; la major solo quando l'utente lo chiede esplicitamente**
    (vedi §8).
  - Devcontainer con tutto l'occorrente, comprese le estensioni in uso e un visualizzatore Excel affidabile (§9).
  - MCP server Playwright per gli screenshot della guida (§9).
  - Guida dettagliata + presentazione interattiva reveal.js 2D sulla GitHub Page, **sempre aggiornate e allineate**
    con il codice e con questo file (§10).
  - Possibilità di provare la GitHub Page in locale prima del push (§10.3).
- <!-- TODO: aggiungi qui eventuali altre istruzioni della conversazione originale che non risultano dal file -->

## 3. Struttura del workbook

### Foglio `Sheet1` (fondi) — intestazioni alla riga 2, dati nelle righe 3–40 (38 fondi). Righe 1–2 e colonna A bloccate.
| Col | Campo | Tipo | Note |
|---|---|---|---|
| A | Denominazione | testo | Nome ufficiale COVIP. È la **chiave** usata dal foglio Comparti |
| B | Pagina informativa (URL) | URL/hyperlink | Sito del gestore |
| C | Società (Ciao Elsa) | testo | |
| D | Spese di adesione (€) | numero, `#,##0.00 "€"` | input |
| E | Spese annue fisse (€) | numero, `#,##0.00 "€"` | input |
| F | Costo % sul versato | %, `0.0%` | input (solo Il Melograno = 0,5%) |
| G | N. linee (dichiarate Ciao Elsa) | intero | input |
| H | N. comparti nel foglio Comparti | formula | `=COUNTIF(Comparti!$A:$A,$A3)` |
| I | Comm. gestione min | formula | `=IF($H3=0,"",MINIFS(Comparti!$H:$H,Comparti!$A:$A,$A3))` |
| J | Comm. gestione max | formula | idem con `MAXIFS` |
| K | Max % azioni tra i comparti | formula | `MAXIFS(Comparti!$D:$D,…)` |
| L | Miglior rendimento 10 anni | formula | `MAXIFS(Comparti!$F:$F,…,Comparti!$G:$G,10)`, vuoto se nessun comparto ha dati a 10 anni |
| M | Linee sostenibili (ESG) | Sì/No | |
| N | Life cycle | Sì/No | |
| O | Sottoscrizione online | "Sì (Ciao Elsa)" / "No" / "No (lista d'attesa)" | |
| P | Scheda Ciao Elsa (fonte) | testo + hyperlink | vuoto se non c'è la scheda |
| Q | Note | testo | anomalie, incoerenze, contesto |

### Foglio `Comparti` — intestazioni alla riga 1, dati nelle righe 2–103 (102 comparti). Riga 1 bloccata.
| Col | Campo | Note |
|---|---|---|
| A | Fondo | **formula** `=Sheet1!$A$n` (link alla denominazione) |
| B | Comparto | nome della linea |
| C | Categoria (Ciao Elsa) | `AZN`, `BIL`, `OBB MISTO`, `OBB PURO`, `GAR` |
| D | % Azioni | `0.00%` |
| E | % Obbligazioni | `0.00%` |
| F | Rendimento netto medio annuo | `0.00%`, può essere negativo o vuoto |
| G | Periodo rendimento (anni) | 10, 5 o 3 |
| H | Commissione di gestione annua | `0.00%` |
| I | Scheda Ciao Elsa (fonte) | hyperlink alla scheda del fondo |
| J | Note | |

**Attenzione all'export:** `openpyxl` non calcola le formule. Con `data_only=True` legge i valori **messi in cache
dall'ultimo salvataggio in Excel**: se il file viene modificato fuori da Excel, la cache è vuota. Per questo lo script
di export deve **risolvere da solo** `Comparti!A` (`=Sheet1!$A$n` → valore di A n) e **ricalcolare** H–L di Sheet1 in
Python, confrontandoli con i valori in cache (warning se diversi). Gli hyperlink vanno letti da `cell.hyperlink.target`.

## 4. Fonti

### 4.1 Fonti primarie / istituzionali
- **COVIP** – Elenco dei fondi iscritti all'Albo: https://www.covip.it/la-covip-e-la-sua-attivita/albo-fondi-pensione/elenco-fondi-albo
  con il filtro **Tipologia = "Sezione II – Fondi pensione aperti"**. È l'elenco da cui è partito il progetto
  (denominazioni di Sheet1 col. A).
- **Note informative e Schede costi ufficiali** dei singoli fondi (da usare per verificare le anomalie).
- generali.it – fonte della notizia della confluenza di Almeglio in Generali Global dal 1/1/2027.

### 4.2 Pagine informative dei fondi (Sheet1 col. B) e schede Ciao Elsa (col. P)
| Riga | Fondo | Pagina informativa | Scheda Ciao Elsa |
|---|---|---|---|
| 3 | Allianz Previdenza | https://www.allianz.it/le-soluzioni-per-te/previdenza/fondi-pensione/allianz-previdenza.html | https://www.ciaoelsa.com/schede-fondo/fondi-pensione-aperti/allianz/allianz-previdenza/ |
| 4 | Previdenza per Te (AXA MPS) | https://www.axa-mps.it/fondo-pensione-aperto | https://www.ciaoelsa.com/schede-fondo/fondi-pensione-aperti/axa/axa-previdenza-per-te/ |
| 5 | Almeglio (Alleanza) | https://www.alleanza.it/previdenza-complementare/almeglio/ | — |
| 6 | Fondo Pensione Fideuram | https://www.fideuram.it/prodotti-e-soluzioni-personalizzate/assicurazione-e-previdenza/previdenza/fondo-pensione-fideuram/ | https://www.ciaoelsa.com/schede-fondo/fondi-pensione-aperti/fideuram/fideuram/ |
| 7 | Generali Global | https://www.generali.it/previdenza/generali-global-fondo-pensione-aperto/ | https://www.ciaoelsa.com/schede-fondo/fondi-pensione-aperti/generali/generali-global/ |
| 8 | Previdsystem | https://www.intesasanpaoloassicurazioni.com/it/prodotti-e-rendimenti/pensione-integrativa/previdsystem.html | — |
| 9 | Teseo (Reale Mutua) | https://www.realemutua.it/risparmio/previdenza/fondo-pensione-teseo | https://www.ciaoelsa.com/schede-fondo/fondi-pensione-aperti/reale-mutua/reale-mutua-teseo/ |
| 10 | Destinazione Futuro (Credemvita) | https://www.credem.it/content/credem/it/privati-e-famiglie/assicurazione-e-previdenza/previdenza/fondo-pensione.html | https://www.ciaoelsa.com/schede-fondo/fondi-pensione-aperti/credem/credemprevidenza/ |
| 11 | Vittoria Formula Lavoro | https://www.vittoriaassicurazioni.com/performances/fondo-pensione/ | https://www.ciaoelsa.com/schede-fondo/fondi-pensione-aperti/vittoria-assicurazioni/vittoria-formula-lavoro/ |
| 12 | Arca Previdenza | https://www.arcafondi.it/s/previdenza | — |
| 13 | Unipol Previdenza FPA | https://www.unipol.it/aziende/risparmio-previdenza/fondo-pensione-aperto | — |
| 14 | Vera Vita | https://www.bancobpmvita.it/prodotti/previdenza/fondo-pensione-aperto-vera-vita/ | — |
| 15 | UniCredit FPA | https://www.unicreditallianzvita.it/le-soluzioni-per-te/archivio-prodotti/previdenza.html | — |
| 16 | Previgest Fund Mediolanum | https://www.mediolanumgestionefondi.it/fondi-pensione | https://www.ciaoelsa.com/schede-fondo/fondi-pensione-aperti/mediolanum/mediolanum-previgest/ |
| 17 | Zurich Contribution | https://www.zurich.it/persone/risparmio-e-investimento/previdenza/zurich-contribution | https://www.ciaoelsa.com/schede-fondo/fondi-pensione-aperti/zurich/zurich-contribution/ |
| 18 | ZED Omnifund | https://www.zurich.it/gruppo-zurich/zurich-italia/partner/banks-and-ifa/zed-omnifund | https://www.ciaoelsa.com/schede-fondo/fondi-pensione-aperti/zurich/zurich-zed-omnifund/ |
| 19 | Plurifonds (ITAS Vita) | https://www.gruppoitas.it/it/prodotti/fondo-pensione-plurifonds | https://www.ciaoelsa.com/schede-fondo/fondi-pensione-aperti/itas/itas-plurifonds/ |
| 20 | Eurorisparmio (Sella) | https://www.sella.it/banca-on-line/privati/consulenza-e-investimenti/prodotti-di-investimento/fondi-pensione | https://www.ciaoelsa.com/schede-fondo/fondi-pensione-aperti/sella/sella-eurorisparmio/ |
| 21 | Aureo (BCC) | https://www.bccrisparmioeprevidenza.it/it-IT/pagine/prodotti/fondo-pensione.aspx | https://www.ciaoelsa.com/schede-fondo/fondi-pensione-aperti/bcc/bcc-aureo/ |
| 22 | Crédit Agricole Vita | https://www.credit-agricole.it/privati/investimenti/previdenza-e-fondi-pensione/fondo-pensione-aperto | https://www.ciaoelsa.com/schede-fondo/fondi-pensione-aperti/credit-agricole/credit-agricole-vita/ |
| 23 | Arti & Mestieri (Anima) | https://www.animasgr.it/IT/investitore-privato/prodotti/Pagine/fondopensione.aspx | https://www.ciaoelsa.com/schede-fondo/fondi-pensione-aperti/anima/anima-arti-e-mestieri/ |
| 24 | Secondapensione (Amundi) | https://www.secondapensione.it | https://www.ciaoelsa.com/schede-fondo/fondi-pensione-aperti/amundi/amundi-secondapensione/ |
| 25 | Giustiniano | https://www.intesasanpaoloassicurazioni.com/it/prodotti-e-rendimenti/pensione-integrativa/giustiniano.html | — |
| 26 | Programma Open (Groupama) | https://www.groupama.it/previdenza-integrativa/programma-open/ | https://www.ciaoelsa.com/schede-fondo/fondi-pensione-aperti/groupama/groupama-programma-open/ |
| 27 | Il Mio Domani | https://www.intesasanpaolo.com/it/persone-e-famiglie/prodotti/piani-previdenza-complementare-pensione-integrativa/fondo-pensione-aperto-il-mio-domani-adesioni-individuali.html | — |
| 28 | Azimut Previdenza | https://www.azimutwm.it/web/azimut.it/prodotti/previdenza | https://www.ciaoelsa.com/schede-fondo/fondi-pensione-aperti/azimut/azimut-previdenza/ |
| 29 | Azione di Previdenza (HDI) | https://www.hdiassicurazioni.it/it/privati/previdenza/fondo-pensione-aperto | https://www.ciaoelsa.com/schede-fondo/fondi-pensione-aperti/hdi/hdi-azione-di-previdenza/ |
| 30 | FPA CNP | https://gruppocnp.it/prodotti/fondo-pensione-aperto/fondo-pensione-aperto-cnp | https://www.ciaoelsa.com/schede-fondo/fondi-pensione-aperti/cnp-unicredit/cnp/ |
| 31 | Insieme (Allianz) | https://www.allianz.it/le-soluzioni-per-te/previdenza/fondi-pensione/insieme.html | https://www.ciaoelsa.com/schede-fondo/fondi-pensione-aperti/allianz/allianz-insieme/ |
| 32 | BIM Vita | https://www.unipol.it/risparmio-previdenza/pensione-integrativa-fondi-pensione/fondo-pensione-aperto-bv | https://www.ciaoelsa.com/schede-fondo/fondi-pensione-aperti/bim-vita/bim-vita/ |
| 33 | PensPlan Profi | https://www.fondopensioneprofi.com/ | — |
| 34 | Raiffeisen FPA | https://www.raiffeisenpensionsfonds.it/it/il-raiffeisen-fondo-pensione/chi-siamo.html | — |
| 35 | Il Melograno (Assimoco) | https://www.assimoco.it/assimoco/offerta/protezione-persona-casa-famiglia/previdenza/il-melograno.html | https://www.ciaoelsa.com/schede-fondo/fondi-pensione-aperti/assimoco/assimoco-il-melograno/ |
| 36 | UBI Previdenza | https://www.intesasanpaoloassicurazioni.com/it/prodotti-e-rendimenti/pensione-integrativa/fondo-pensione-aperto-ubi-previdenza.html | — |
| 37 | Soluzione Previdente (Helvetia) | https://www.helvetia.com/it/web/it/prodotti-e-servizi/prodotti-dedicati-alla-previdenza-complementare/previdenza_complementare/fpa-soluzione-previdente.html | — |
| 38 | BAP Pensione 2007 | https://www.intesasanpaoloassicurazioni.com/it/prodotti-e-rendimenti/pensione-integrativa/bappensione-2007.html | — |
| 39 | Core Pension | https://www.corepension.it | — |
| 40 | Azimut Sustainable Future | https://www.azimutwm.it/web/azimut.it/prodotti/previdenza | — |

Nell'elenco originale alcuni link comparivano due volte (Fideuram, ZED Omnifund, Eurorisparmio, Insieme). Azimut Previdenza
e Azimut Sustainable Future condividono lo stesso URL.

## 5. Problemi noti nei dati (da verificare sulle fonti ufficiali)
**Probabili inversioni azioni/obbligazioni (Comparti):**
- Aureo: *Garantito ESG* e *Prudente ESG* risultano al 100% azioni.
- Arti & Mestieri: *Garanzia 1+* al 100% azioni.
- CNP: *Garanzia restituzione capitale* al 95% azioni (atteso circa 5%).
- Programma Open: le % di *Bilanciato etico* (56%) e *Prevalentemente azionario etico* (30%) sembrano scambiate.
  ⇒ Queste anomalie falsano `Max % azioni` (Sheet1 col. K) di Aureo, Arti & Mestieri e CNP.

**Incoerenze nelle schede Ciao Elsa:**
- Allianz Previdenza: il testo dice 6 linee, la scheda ne riporta 5. Life cycle a 30 €/anno, non incluso nelle spese annue.
- Insieme: 6 linee, ma il testo dice "sette". Anche qui life cycle a 30 €/anno. Coperture assicurative opzionali (50/100/150 €).
- Generali Global e Teseo: life cycle = No, ma il testo descrive dei percorsi life cycle.
- Destinazione Futuro: Ciao Elsa usa il vecchio nome *Credemprevidenza* (cambiato dal 1/12/2025, con comparti rinominati).
- Aureo: spese 2 €/12 € secondo Ciao Elsa, mentre altre fonti indicavano 10 €/30 €.
- Arti & Mestieri: 6 comparti su Ciao Elsa, ma la Scheda costi delle adesioni collettive cita anche *Sviluppo 15+*.
- BIM Vita: oggi è venduto come "Unipol Fondo Pensione Aperto BV", quindi i costi potrebbero essere cambiati.
- Programma Open: per *Nuovo obbligazionario etico* mancano rendimento e commissione.

**Rendimenti non a 10 anni** (col. G ≠ 10): Fideuram *Millennials* (5), Generali *Real return* e *Obbl. breve* (5),
Vittoria *Bilanciato internazionale* (3), Aureo *Prudente ESG* (3), Insieme *Obbl. breve* (5). **Non confrontarli** con i rendimenti a 10 anni.

**Stato dei fondi:** Almeglio è chiuso a nuove adesioni e dal 1/1/2027 confluisce in Generali Global.
Fideuram si sottoscrive solo tramite Private Banker.

**Copertura:** 15 fondi su 38 non hanno ancora una scheda né dati di dettaglio (righe 5, 8, 12–15, 25, 27, 33, 34, 36–40).

## 6. Regole di sviluppo
- **Excel**: non sovrascrivere le formule con valori fissi. I nuovi comparti vanno aggiunti al foglio `Comparti` con
  `A = =Sheet1!$A$n`: le metriche di Sheet1 si aggiornano da sole. Ogni dato nuovo deve avere una fonte (hyperlink o nota).
  Ogni incoerenza va in `Note`, non va corretta in silenzio. Le correzioni verificate vanno riportate in nota con la fonte
  ufficiale e la data.
- **Dati generati** (`data/*.json`): non modificarli mai a mano, vanno rigenerati con lo script.
- **Schema JSON** (proposta):
  - `fondi.json`: `{ id (slug), riga, denominazione, url, societa, spese_adesione, spese_annue, costo_pct_versato,
    n_linee, n_comparti, comm_min, comm_max, max_azioni, best_rend_10a, esg, life_cycle, online, scheda_url, note,
    has_dati }`
  - `comparti.json`: `{ fondo_id, comparto, categoria, azioni, obbligazioni, rendimento, periodo_anni, commissione,
    scheda_url, note, flag_anomalia }`
  - `meta.json`: data di export, hash del commit, conteggi, elenco delle fonti.
  - Le percentuali sono decimali (0.0145), formattate solo nella UI. Celle vuote → `null`, mai 0.
  - Implementato: in più rispetto alla proposta, `fondi.json` ha `nome_breve` (denominazione senza "Fondo pensione aperto"
    ecc., usata dalla UI e per lo slug) e `flag_anomalia`; entrambi i file hanno `riga` (riga del workbook).
    `flag_anomalia` è una lista di codici, descritti in `meta.json` → `flag`.
- **Flag di anomalia**: lo script segnala in automatico `azioni+obbligazioni ≠ 1`, comparto "garantito/prudente" con
  azioni > 50%, `periodo_anni ≠ 10`, rendimento o commissione mancanti, `n_linee ≠ n_comparti`, e la categoria incoerente
  con le % di azioni (AZN < 50% oppure OBB/GAR > 50%; intercetta il caso di Programma Open).
- **Commit**: in italiano, convenzionali (`dati:`, `sito:`, `script:`, `docs:`). Ogni modifica ai dati va citata con la fonte nel messaggio.

## 7. GitHub Page — requisiti della dashboard
Sito statico in `docs/`, senza build obbligatoria (vanilla JS + una libreria per i grafici, es. Chart.js o Plotly via CDN),
responsive, accessibile, in italiano.
1. **Tabella dei fondi** ordinabile e filtrabile (ESG, life cycle, online, solo con dati), con ricerca testuale, link alla
   pagina del fondo e alla scheda fonte, e badge ⚠️ dove ci sono note o anomalie.
2. **Dettaglio fondo**: comparti, asset allocation (barra azioni/obbligazioni), rendimento con periodo esplicito, commissione e note.
3. **Grafico a dispersione commissione vs rendimento** per comparto, colorato per categoria, solo comparti a 10 anni
   (con un toggle per includere quelli a 3 o 5 anni, ben segnalati).
4. **Simulatore dei costi**: versamento annuo + orizzonte + comparto → costo totale stimato (adesione + spese fisse +
   % sul versato + commissione di gestione sul patrimonio) e montante netto. Confronto tra 2 e 4 comparti.
5. **Confronto per categoria** (AZN/BIL/OBB/GAR): migliori e peggiori per costo e rendimento.
6. Sezione **"Qualità dei dati"**: copertura, anomalie aperte e fonti.
7. **Disclaimer** sempre visibili: avviso "progetto personale" sotto l'intestazione e nel footer (testo canonico:
   *"Progetto personale, nato per uso privato e pubblicato su GitHub a puro scopo dimostrativo: non è un servizio rivolto
   al pubblico né una consulenza finanziaria."*, più la non affiliazione a COVIP, gestori e Ciao Elsa), ripetuto in
   guida, presentazione e README. Footer con "non è consulenza finanziaria", versione e data di aggiornamento da
   `meta.json` e licenza.
8. **CI**: `.github/workflows/ci.yml` su ogni PR verso `master` (export, test, smoke test del sito, anteprima della
   versione); `.github/workflows/pages.yml` al merge su `master` (export, test, deploy di `docs/` con i JSON copiati in
   `docs/data/`, poi tag e release). Dettagli nella §8.
9. Pagine collegate dal menu: **Guida** (`docs/guida/`) e **Presentazione** (`docs/presentazione/`), vedi §10.
10. **Stile**: semplice e poco distraente. Font Inter (Google Fonts, fallback di sistema), intestazione con leggera
   sfumatura, navigazione fissa a pillole, card con ombre morbide, filtri a pillola. Colori come token CSS in
   `docs/style.css` (chiaro/scuro); i colori delle categorie del grafico sono validati e non vanno cambiati a occhio.

## 8. Versioni e release
- Branch principale: **`master`**. Si lavora su branch (es. `dev`) e si apre una PR verso `master`.
- **SemVer** con tag `vX.Y.Z`; la prima release sarà `v0.1.0`. Logica in `scripts/versione.py` (testata in `tests/test_versione.py`):
  - **minor** se tra i commit dall'ultimo tag c'è almeno un `sito:`, `script:` o `feat:`;
  - **patch** per tutto il resto (`dati:`, `docs:`, `fix:`, `ci:`, `test:`, `chore:`…);
  - **major MAI in automatico**: `!` e `BREAKING CHANGE` contano come minor. La major si fa solo con la label
    `release:major` sulla PR, o avviando a mano *Deploy GitHub Page e release* con `bump = major`.
    ⚠️ **Claude non deve mai usare la major (né aggiungere la label `release:major`) senza una richiesta esplicita dell'utente.**
  - Le label `release:minor` / `release:patch` sulla PR forzano il tipo di incremento.
- **`ci.yml`** (PR verso `master`, push sugli altri branch): export, test (schema, versioni, smoke test Playwright del sito)
  e, sulle PR, la versione e le note che verranno pubblicate nel *Job summary*.
- **`pages.yml`** (push su `master`, cioè il merge di una PR, oppure avvio manuale):
  1. `build`: trova la PR di origine, calcola la versione, `APP_VERSION=vX.Y.Z python scripts/export_xlsx.py`
     (la versione finisce in `meta.json` e nel footer), test, note di rilascio, artifact di Pages;
  2. `deploy`: GitHub Pages (ambiente `github-pages`);
  3. `release`: `gh release create vX.Y.Z` con le note (sezioni per tipo di commit, link alla PR, numeri dei dati,
     link a dashboard/guida/presentazione e confronto con il tag precedente). Viene saltata se non ci sono commit nuovi.
  Si usa `push` e non `pull_request: closed` perché l'ambiente `github-pages` accetta deploy solo dal branch di default.
- Requisito su GitHub: *Settings → Pages → Source: GitHub Actions*.
- Commit: i prefissi decidono il tipo di versione, quindi vanno scelti con cura (`sito:` per le funzionalità della dashboard,
  `fix:` per le correzioni).

## 9. Ambiente di sviluppo
- **Devcontainer** (`.devcontainer/`): Python 3.12, Node 22, GitHub CLI, Claude Code. `post-create.sh` installa
  `requirements-dev.txt`, Chromium per i test e per l'MCP, e fa il primo export. La porta 8000 (anteprima) viene inoltrata.
- **Estensioni** (devcontainer + `.vscode/extensions.json`): Claude Code, GitHub Pull Requests, GitHub Actions,
  GitHub Theme, Codespaces, Python, **Git Graph** (`mhutchie.git-graph`, grafico dei branch e dei tag di release) e **Spreadsheet Viewer** (`grapecity.gc-excelviewer`) per aprire `.xlsx` in VS Code.
  È stato scelto perché è di un editore verificato (GrapeCity/MESCIUS), ha più di 6,8 milioni di installazioni, il sorgente è
  pubblico (github.com/wijmo/gc-excelviewer) ed è un **visualizzatore**. Il workbook va comunque **modificato in Excel**, per
  mantenere la cache delle formule (§3).
- **MCP** (`.mcp.json`, server di progetto per Claude Code): `@playwright/mcp@0.0.82` in Chromium headless e isolato, con
  viewport 1360×820 e output in `.playwright-mcp/` (ignorato da git). Serve a navigare il sito e a fare screenshot ad hoc;
  gli screenshot della guida si rigenerano invece con lo script riproducibile `scripts/screenshots.py`.
- Versioni fissate: `playwright==1.63.0` (Python), `@playwright/mcp@0.0.82`, Chart.js 4.4.1, reveal.js 6.0.2,
  marked 18.0.13, DOMPurify 3.4.15. Quando si aggiorna una versione, aggiornarla qui.
- `.vscode/tasks.json`: *Anteprima GitHub Page*, *Anteprima veloce*, *Export dati*, *Test*, *Rigenera screenshot*, *Prossima versione*.

## 10. Documentazione per gli utenti
### 10.1 Guida (`docs/guida/`)
- Il testo sta in `docs/guida/GUIDA.md` (si legge anche su GitHub); `docs/guida/index.html` lo mostra sul sito con
  marked + DOMPurify. Le ancore sono compatibili con GitHub.
- Screenshot in `docs/guida/img/`, generati da `python scripts/screenshots.py` (fa prima l'export): `dashboard`,
  `tabella-filtri`, `dettaglio`, `grafico`, `grafico-evidenzia`, `categorie`, `qualita`, `mobile-scuro`.
### 10.2 Presentazione (`docs/presentazione/`)
- reveal.js con navigazione **2D**: in orizzontale gli argomenti (titolo, perché, dati, dashboard, come scegliere,
  manutenzione, fine), in verticale gli approfondimenti. Riusa gli screenshot della guida e legge i numeri dal vivo da
  `data/meta.json`. Tema chiaro/scuro automatico.
### 10.3 Anteprima locale prima del push
- `./scripts/anteprima.sh` (export + test + server su http://localhost:8000, con le stesse pagine che verranno pubblicate),
  `--veloce` per saltare i test, `PORTA=9000` per cambiare porta. È disponibile anche come task di VS Code.
- `tests/test_sito.py` controlla dashboard, dettaglio, mobile, guida (immagini caricate) e presentazione (pile verticali,
  navigazione ↓) senza errori JavaScript. Usa `scripts/server_locale.py`.
### 10.4 Regola di allineamento (obbligatoria)
Ogni modifica che cambia ciò che l'utente vede o fa (dashboard, dati mostrati, flusso di rilascio, comandi) va
accompagnata **nello stesso commit/PR** da:
1. aggiornamento di `docs/guida/GUIDA.md`;
2. aggiornamento della presentazione, se tocca uno degli argomenti;
3. `python scripts/screenshots.py`, se cambia l'aspetto;
4. aggiornamento di questo `CLAUDE.md` (struttura, schema, versioni, roadmap) e del `README.md`;
5. test verdi (`python -m unittest discover -s tests`).

## 11. Roadmap / TODO
- [x] Script `scripts/export_xlsx.py` + `requirements.txt` + test di schema (`tests/test_export.py`)
- [x] Prima versione della dashboard (tabella, dettaglio, scatter, confronto per categoria, qualità dei dati) + CI `pages.yml`
- [x] CI su PR, deploy + tag + release al merge, versionamento automatico (minor/patch)
- [x] Devcontainer, MCP Playwright, guida con screenshot, presentazione reveal.js 2D, anteprima locale
- [ ] Simulatore dei costi (poi aggiornare guida, presentazione e screenshot)
- [ ] Verificare le anomalie della §5 sulle Schede costi ufficiali
- [ ] Completare i 15 fondi senza dati
- [ ] Aggiungere l'**ISC (Indicatore Sintetico dei Costi)** COVIP a 2/5/10/35 anni: è la metrica di costo ufficiale e confrontabile
- [ ] Valutare di rinominare `Sheet1` in `Fondi` (le formule di Excel si aggiornano da sole; aggiornare lo script)
- [x] Confermare l'URL esatto dell'elenco COVIP nella §4.1