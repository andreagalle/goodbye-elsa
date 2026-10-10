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
- Istruzioni permanenti sull'uso della piattaforma (da ottobre 2026): l'utente usa la dashboard e chiede ciò che non
  capisce. Per ogni domanda Claude **spiega in chat e rende la spiegazione chiara anche nella piattaforma**; se servono
  dati nuovi o approfondimenti, **cerca online, arricchisce prima l'Excel e poi a cascata tutto il resto**, citando le
  fonti senza appesantire la grafica. Procedura nella §11.
- Richiesta del 10/10/2026: piano per passare da GitHub Pages a Cloudflare con un accesso leggero (authn/authz) e rendere
  privato il repository. È nella §13 ed è **da eseguire solo quando l'utente lo chiede**; fino ad allora valgono §7–§8.
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

### Foglio `Regole` — regole generali della previdenza complementare (intestazioni alla riga 1, una regola per riga)
Fonte di verità per la sezione *Regole* della dashboard, la guida e la presentazione. Una riga = una regola verificata.
| Col | Campo | Note |
|---|---|---|
| A | ID | `R01`, `R02`, … (univoco) |
| B | Tema | `Come funziona`, `Adesione e TFR`, `Tasse e deduzioni`, `Prima della pensione`, `Alla pensione`, `In caso di decesso` |
| C | Titolo breve | etichetta per gli elenchi compatti (es. "Rendita vitalizia") |
| D | Domanda | come la porrebbe un utente |
| E | Regola | spiegazione in italiano semplice |
| F | Valore chiave | es. `50%`, `5.300 € l'anno` (testo) |
| G | Uguale per tutti i fondi? | `Sì` / `In parte` / `No` |
| H | Cosa varia da fondo a fondo | obbligatorio se G ≠ `Sì`: è la checklist dell'approfondimento per fondo |
| I | Riferimento normativo | es. `D.Lgs. 252/2005, art. 11 c. 3` |
| J | Fonte | nome della fonte + **hyperlink** |
| K | Consultata il | data |
| L | In vigore dal | data, solo per le regole nuove |
| M | Note | incoerenze tra fonti, chiarimenti (mai correzioni silenziose) |

### Foglio `Longevita` — tavola di mortalità ISTAT (Italia), età 60–110
A Età · B–D Sopravviventi (uomini, donne, uomini e donne, su 100.000 nati) · E–G Speranza di vita residua ·
H–J **% vivi tra i 67enni (formule** `=B9/B$9`…). Celle L1:M4: fonte, link, data di consultazione, note.
Oggi: *Tavole di mortalità della popolazione residente 2025 (stima)*, scaricate da demo.istat.it
(`datiripartizionecompleti2025.zip`, righe "Italia").

### Foglio `Glossario` — termini spiegati nella dashboard e nella guida (intestazioni alla riga 1, una voce per riga)
Fonte di verità per i **suggerimenti al passaggio del mouse**, la sezione *Glossario* della dashboard e la tabella del
capitolo *Glossario* della guida (generata dall'export). Oggi 49 voci, in gran parte dal glossario COVIP.
| Col | Campo | Note |
|---|---|---|
| A | ID | slug univoco (`esg`, `life-cycle`…): è il valore di `data-glossario` nella UI, **non cambiarlo** senza aggiornare `app.js`/`index.html` |
| B | Gruppo | `Fondi e documenti`, `Investimento`, `Costi e rendimenti`, `Versamenti e uscite anticipate`, `Alla pensione`, `Longevità e decesso` |
| C | Termine | come compare nella UI (es. "Comparto (linea di investimento)") |
| D | Per esteso | sigla sciolta o nome ufficiale (es. "Environmental, Social, Governance"), facoltativo |
| E | Definizione | italiano semplice, al massimo 400 caratteri (l'export avvisa oltre): è il testo del suggerimento |
| F | Fonte | nome + **hyperlink** (per il glossario COVIP il link punta alla lettera e alla voce, es. `…/glossario/e#esg`) |
| G | Consultata il | data |
| H | Note | come il termine è usato nella dashboard, altre fonti, **incoerenze tra fonti** (mai correzioni silenziose) |
I numeri ripresi dal foglio `Regole` (capitale 50%, deducibilità 5.300 €) devono coincidere: lo controlla `test_export.py`.

### Foglio `Prestazioni` — condizioni alla pensione fondo per fondo (intestazioni alla riga 1, righe 2–39 = Sheet1 3–40)
Fonte di verità per la sezione *Alla pensione, fondo per fondo* e per il blocco *Alla pensione con questo fondo* del
dettaglio. Una riga per fondo (anche senza dati); i dati vengono dai documenti ufficiali del gestore. Righe 1 e colonna A bloccate.
| Col | Campo | Note |
|---|---|---|
| A | Fondo | **formula** `=Sheet1!$A$n` |
| B | Documento sulle rendite (fonte) | titolo con edizione + **hyperlink** |
| C | Compagnia che paga la rendita | |
| D–G | Rendita reversibile / certa e poi vitalizia / controassicurata / con LTC | `Sì…` o `No…`, con il dettaglio tra parentesi (es. `Sì (5 o 10 anni)`); vuoto = non verificato |
| H | N. varianti oltre alla vitalizia | **formula** `=COUNTIF(Dn:Gn,"Sì*")` |
| I | Rendita annua a 67 anni ogni 10.000 € | `#,##0.00 "€"`. **Solo se confrontabile**: coefficiente per età 67, nato nel 1959, adesione dopo il 21/12/2012 (unisex), rata **annuale**; se il coefficiente è per 1 € di rendita si inverte (10.000/x). Altrimenti vuoto e motivo in `Note` |
| J | Tasso di conversione a 67 anni | **formula** `=IF(In="","",In/10000)` |
| K | Tasso tecnico | `0.0%` |
| L | Basi del coefficiente | tavola, correzione d'età, tasso tecnico, dove sono i coefficienti |
| M | Costo della rendita (rata annuale) | caricamento `0.00%` |
| N–Q | Costo anticipazione / riscatto / trasferimento / RITA (€) | 0 = non previsto, vuoto = non trovato; RITA "a rata" va spiegato in `Note` |
| R | Scheda costi (fonte) | hyperlink |
| S | Nuove prestazioni (durata definita e prelievi) | periodicità, minimi, comparto predefinito, costi |
| T | Supplemento alla Nota informativa (fonte) | hyperlink |
| U | Consultata il | data |
| V | Note | incoerenze, limiti del confronto, documenti datati |

### Registro dei documenti ufficiali — `data/documenti.csv` (fuori dal workbook)
Fonte di verità per le **copie dei documenti dei fondi** in `docs/documenti/<fondo-id>/` (PDF + testo `.txt`), per il
blocco *Documenti ufficiali* del dettaglio fondo e per l'elenco `docs/documenti/README.md`. Sta in un CSV, non nel
workbook, perché descrive file (pagine, peso e SHA-256 li calcola lo script) e perché lo aggiorna anche lo script
(`documenti.py riprova`). Una riga per documento, nell'ordine fondo → tipo:
| Colonna | Note |
|---|---|
| `fondo_id` | id di `fondi.json` |
| `tipo` | uno dei tipi di `TIPI` in `scripts/documenti.py` (`nota-informativa`, `scheda-presentazione`, `scheda-costi`, `scheda-destinatari`, `opzioni-investimento`, `soggetti-coinvolti`, `informativa-sostenibilita`, `supplemento`, `regolamento`, `documento-rendite`, `documento-anticipazioni`, `documento-regime-fiscale`, `documento-politica-investimento`, `documento-sistema-governo`, `rendiconto`, `modulo-adesione`, `metodologia-proiezioni`, `altro`), oppure `nota-fondo`: riga che contiene solo una nota sul fondo intero (testo in `titolo`) |
| `titolo` | come compare sul sito del gestore (non corretto: es. "Circolare COVID" di Teseo resta così) |
| `file` | nome del PDF nella cartella del fondo (il tipo, con `-2`, `-3`… se ripetuto); vuoto = non scaricato |
| `url` | link di download (vuoto se il sito non ne espone uno, es. Teseo e Arca) |
| `pagina` | pagina che cita il documento; vuota = la pagina informativa del fondo (Sheet1 col. B) |
| `referenziato` | `Sì` se citato dalla pagina informativa ufficiale o dalle pagine "Documentazione" a cui rimanda; `No` se trovato altrove sul sito dello stesso gestore |
| `note` | **obbligatoria** se `file` è vuoto: il motivo (403, solo JavaScript, sito non raggiungibile…) |
**Perimetro** (deciso con l'utente il 9/10/2026, a partire dai documenti "specifici per fondo" su cui si basa il foglio
`Prestazioni`): tutti i documenti informativi del fondo citati nella sua pagina — Nota informativa intera e per schede,
Appendice sulla sostenibilità (anche per comparto), Supplemento, Regolamento e allegati, Documento sulle rendite, sulle
anticipazioni, sul regime fiscale, sulla politica di investimento, sul sistema di governo, **ultimo** rendiconto, modulo
di adesione, metodologia delle proiezioni, organismo di rappresentanza, informative sulle nuove prestazioni, FAQ e
politica di impegno del fondo. **Esclusi**: modulistica operativa, privacy, materiale promozionale (brochure, schede
marketing per comparto), politiche e informative di gruppo non specifiche del fondo (PAI, remunerazione, linee guida),
informative periodiche SFDR e versioni precedenti. Ogni `.txt` ha un'intestazione (`# Fondo`, `# Documento`, `# Fonte`,
`# Citato in`, `# Scaricato il`, `# SHA-256 del PDF`, `# Pagine`, eventuale `# Attenzione: …`) e poi `=== pagina N ===`
per ogni pagina: è il testo da **consultare nei prossimi lavori** (es. `grep -n -i "coefficient" docs/documenti/*/documento-rendite.txt`)
e da citare con file e pagina; per i numeri fa fede il PDF. I PDF non si modificano mai a mano.

**Componente aggiuntivo:** il workbook contiene il collegamento a **Claude per Excel** (`xl/webextensions/*`), che openpyxl
scarta al salvataggio. Per salvarlo da Python usare sempre `scripts/workbook_utils.py` → `salva(wb, percorso)`, che lo
reinserisce (test in `tests/test_workbook_utils.py`).

**Cache dei valori delle formule:** Excel salva ogni formula insieme al suo ultimo risultato; openpyxl non sa calcolare e,
salvando, lascia il risultato vuoto. Chi legge il file senza ricalcolare (export con `data_only=True`, Spreadsheet Viewer,
anteprime, l'xlsx allegato alle release) vedrebbe celle vuote. Per questo `salva()` **calcola le formule in Python**
(`Calcolatore` in `workbook_utils.py`: riferimenti anche tra fogli e a colonne intere, aritmetica, confronti, `&`, e le
funzioni in `FUNZIONI` = IF, COUNTIF, COUNTIFS, MINIFS, MAXIFS) e ne scrive i risultati in cache come Excel; restituisce
le celle non calcolabili (oggi nessuna). Excel le ricalcola comunque all'apertura (`fullCalcOnLoad`). **Una formula con
una funzione nuova va aggiunta al calcolatore, con un test.** `test_workbook_reale` verifica che i valori calcolati
coincidano con quelli messi in cache da Excel e con il ricalcolo dell'export.

**Attenzione all'export:** lo script non si fida della cache: **risolve da solo** `Comparti!A` e `Prestazioni!A`
(`=Sheet1!$A$n` → valore di A n), **ricalcola** H–L di Sheet1 (e H, J di `Prestazioni`) in Python e li confronta con i valori
in cache (warning se diversi o assenti). Gli hyperlink vanno letti da `cell.hyperlink.target`.

## 4. Fonti

### 4.1 Fonti primarie / istituzionali
- **COVIP** – Elenco dei fondi iscritti all'Albo: https://www.covip.it/la-covip-e-la-sua-attivita/albo-fondi-pensione/elenco-fondi-albo
  con il filtro **Tipologia = "Sezione II – Fondi pensione aperti"**. È l'elenco da cui è partito il progetto
  (denominazioni di Sheet1 col. A).
- **Note informative e Schede costi ufficiali** dei singoli fondi (da usare per verificare le anomalie).
- generali.it – fonte della notizia della confluenza di Almeglio in Generali Global dal 1/1/2027.

### 4.1-bis Fonti normative e statistiche (foglio `Regole` e `Longevita`, consultate l'8/10/2026)
- D.Lgs. 252/2005, **testo COVIP aggiornato alla L. 199/2025** (con le note sulle modifiche successive):
  https://www.covip.it/sites/default/files/legislazione_fondi/decreto_legislativo_5_dicembre_2005_n_252.pdf — è la fonte
  più affidabile sul testo vigente (es. nota 129: capitale tornato al 50%).
- Legge 30 dicembre 2025, n. 199 (estratto COVIP): https://www.covip.it/sites/default/files/legislazione_fondi/legge_bilancio_2026.pdf
- COVIP, Istruzioni sulle prestazioni (deliberazione 25/6/2026): https://www.covip.it/sites/default/files/provvedimenti/istruzioni_prestazioni_25_06_2026.pdf
- COVIP, Esempio di supplemento alla Nota informativa per i fondi aperti (28/7/2026): https://www.covip.it/sites/default/files/notizie/esempio_supplementoni_fpa.pdf
- COVIP, FAQ (prestazioni, TFR, fisco), risposte a quesito (premorienza 10/2009; riscatto art. 14 c. 5 02/2021), Guida
  introduttiva (2018); DM 4/9/2026 Modulo TFR3.
- ISTAT, Tavole di mortalità 2025: https://demo.istat.it/app/?i=TVM&l=it
- Nota tecnica: le pagine HTML di covip.it rispondono 403 ai fetch automatici; si scaricano con un User-Agent da browser
  (curl) e i PDF si estraggono in locale (pypdf).

### 4.1-ter Fonti del glossario (foglio `Glossario`, consultate l'8/10/2026)
- **COVIP – Glossario** (aggiornato alla Legge di Bilancio 2026): https://www.covip.it/per-il-cittadino/educazione-previdenziale/glossario
  — una pagina per lettera (`…/glossario/e`), ogni voce ha un'ancora (`#esg`). In `meta.json → fonti` compare una sola volta.
- COVIP – Guida introduttiva (2018), D.Lgs. 252/2005 (artt. 14 c. 3 e 23 c. 7), Istruzioni sulle prestazioni ed Esempio di
  supplemento (2026): le stesse fonti del foglio `Regole`.
- Ciao Elsa (fonte secondaria): home page "Ma chi è Ciao Elsa?" https://www.ciaoelsa.com/ e
  https://www.ciaoelsa.com/sottoscrizione-fondi-pensione-su-ciao-elsa (adesione online con Ciao Elsa come broker).

### 4.1-quater Fonti delle prestazioni (foglio `Prestazioni`, consultate l'8–9/10/2026)
- Per ogni fondo: **Documento sulle rendite** (o allegato al Regolamento con i coefficienti), **Scheda "I costi"** della Nota
  informativa e **Supplemento alla Nota informativa** sulle nuove prestazioni (luglio 2026, modello COVIP), con hyperlink
  nelle colonne B, R e T. In `meta.json → fonti` compaiono come una sola voce (i link sono in `prestazioni.json`).
- Note tecniche: allianz.it e unicreditallianzvita.it rispondono 403 a curl (si scaricano con Chromium/Playwright);
  i PDF di unipol.it arrivano compressi in gzip e cifrati AES (servono `gunzip` e il pacchetto `cryptography` per pypdf);
  i siti Intesa Sanpaolo Assicurazioni usano `…/bin/openAssetInline?path=…/regolamento-e-nota-informativa/<codice prodotto>/…`.

### 4.1-quinquies Documenti ufficiali dei fondi (`data/documenti.csv`, scaricati l'8–10/10/2026)
- Fonte: le **pagine informative dei fondi** (§4.2) e le pagine "Documentazione" a cui rimandano; per Azimut, Crédit
  Agricole Vita, Destinazione Futuro e Il Mio Domani la pagina dell'elenco non li collega e vengono dal sito del gestore
  (`referenziato = No`): azimut.it (`/prodotti-previdenziali/…`, file in `/archives/…`), ca-vita.it, credemvita.it,
  intesasanpaoloassicurazioni.com (`…/pensione-integrativa/il-mio-domani.html`).
- Note tecniche per scaricarli (`scripts/documenti.py`): alcuni siti funzionano solo con curl e non con urllib (Aureo,
  per il quale serve anche una pausa: blocca dopo 2–3 richieste ravvicinate, `riprova --pausa 25`); unipol.it manda i PDF
  compressi gzip anche senza richiesta; alcuni PDF sono cifrati senza password (pypdf richiede `cryptography`); URL con
  caratteri non ASCII (Vera Vita) vanno codificati; Zurich espone i link nel JSON della pagina
  (`/api/archiviodigitale/download?guid=…&filename=…`); Amundi (Secondapensione, Core Pension) ha i titoli nel testo
  vicino al link (`files/nuxeo/dl/<uuid>`). Da questo ambiente (Codespaces) allianz.it e unicreditallianzvita.it
  rispondono **403 anche a Chromium** (il 9–10/10/2026): l'elenco dei loro documenti viene dalla pagina letta con un
  fetcher esterno.

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

**Regole: fonti non allineate (verificato l'8/10/2026)**
- Capitale alla pensione: la L. 199/2025 lo portava al **60%** dal 1/7/2026, ma il D.L. 62/2026 (conv. L. 112/2026, in vigore
  dal 28/6/2026) ha ripristinato il **50%** prima che si applicasse. Molte fonti secondarie (e alcune sintesi) riportano 60%.
- Le FAQ COVIP su TFR (6 mesi, silenzio-assenso) e fisco (deducibilità 5.164,57 €) non sono aggiornate alla riforma.
- La durata della rendita a durata definita a 67 anni (≈ 19 anni) è stimata con la tavola ISTAT 2025: per legge conta la
  tavola usata per i coefficienti di trasformazione INPS in vigore.

**Categorie Ciao Elsa e classificazione COVIP (verificato l'8/10/2026):** per la COVIP (glossario, voce *Multicomparto*)
un comparto è obbligazionario puro senza azioni, misto con azioni ≤ 30%, azionario con azioni ≥ 50%, bilanciato negli altri
casi. Le categorie di Ciao Elsa non sempre lo rispettano: 28 comparti su 102 hanno una % di azioni fuori soglia per la loro
categoria (es. 10 BIL con il 50% di azioni o più, 6 BIL con il 30% o meno, OBB PURO con il 2–4% di azioni, OBB MISTO allo
0%), e molti comparti con garanzia sono classificati OBB invece di GAR. Il dato resta quello della fonte: le note delle voci
`bil`, `obb` e `gar` del glossario lo spiegano. Il flag `categoria_incoerente` usa soglie più larghe e segnala solo i casi
evidenti.

**Glossario: fonti non allineate:** "vecchio iscritto" — il glossario COVIP (voce *Iscritti*) parla di iscrizione alla
previdenza obbligatoria prima del 29/4/1993 e alla complementare prima dell'entrata in vigore della L. 421/1992; il D.Lgs.
252/2005 (art. 23 c. 7) e la Guida COVIP (p. 26) di assunti prima del 29/4/1993 iscritti entro quella data a un fondo già
istituito al 15/11/1992. La voce segue il decreto e segnala la differenza in nota.

**Cache delle formule:** risolto il 9/10/2026: `workbook_utils.salva()` calcola le formule e le mette in cache, quindi dopo
un salvataggio da Python non serve più riaprire il file in Excel (§3).

**Prestazioni: dati incompleti o non confrontabili (verificato l'8–9/10/2026)**
- Dati per **32 fondi su 38**; rendita a 67 anni confrontabile per 24 (aggiornato il 10/10/2026 con i documenti trovati
  dalla sessione dei documenti ufficiali, `data/documenti.csv`). Mancano: Fideuram (documenti non pubblicati), Vittoria
  Formula Lavoro (il sito risponde 502), Arca Previdenza (documento solo dall'app del sito), Eurorisparmio (il link non
  restituisce il PDF), Il Melograno (sito non raggiungibile) e Azimut Sustainable Future (la sua pagina su azimut.it
  pubblica i documenti di Azimut Previdenza: da chiarire prima di riportarli). Per Teseo ci sono solo costi e basi tecniche.
- Coefficienti non pubblicati: Previgest Mediolanum, CNP, PensPlan Profi (sono nella convenzione con la compagnia).
  Raiffeisen pubblica solo un esempio con rate mensili (422,10 € ogni 10.000 €; coincide con il coefficiente mensile di
  Aureo, stessa compagnia e stesse basi). UniCredit usa coefficienti **distinti per sesso** (RG48, tasso tecnico 2%):
  684,6 € uomini, 575,5 € donne prima della correzione d'età; anche Azimut Previdenza pubblica coefficienti per sesso
  (A62D, 0%): 457,44 € uomini, 395,65 € donne. Non sono confrontabili con quelli unisex.
- Coefficienti in comune: Unipol Previdenza, BIM Vita, Vera Vita e Arti & Mestieri (A62I 40/60, 0%) danno tutti 408,18 €;
  Core Pension e Secondapensione 443,46 € (Crédit Agricole Vita); Zurich Contribution e ZED 421,60 € (tavola e tasso
  tecnico non indicati nel Regolamento).
  Almeglio ha coefficienti diversi per data di adesione ed è chiuso.
- Documenti datati: Plurifonds (2021), Crédit Agricole Vita (2022), Vera Vita (2023) e Unipol Previdenza (2025), precedenti
  alle nuove prestazioni o alla loro versione definitiva; Arti & Mestieri ha
  la convenzione per le rendite in scadenza il 31/12/2026.
- I coefficienti non sono del tutto omogenei: tassi tecnici diversi (0%, 0,5%), tavole diverse (A62, AZPS62, IPS55),
  Secondapensione con rate anticipate. La dashboard lo spiega sotto la tabella.

**Documenti ufficiali non scaricati (verificato il 9–10/10/2026)** — il motivo è anche in `data/documenti.csv`:
- **Allianz Previdenza, Insieme, UniCredit**: 403 ai download automatici da questo ambiente; da riprovare da un'altra rete
  (`python scripts/documenti.py riprova --fondo allianz-previdenza insieme unicredit`) oppure dal browser con `smista`.
- **Teseo**: la pagina di Reale Mutua elenca 24 documenti ma li apre con JavaScript, senza link (ci sono solo i 3
  dell'area pubblica fondoteseo.com). **Arca Previdenza**: 21 documenti nella scheda "Documentazione Fondo Pensione",
  consegnati dall'app Salesforce del sito senza link diretti.
- **Fondo Pensione Fideuram**: il sito pubblico ha solo una brochure. **Il Melograno**: assimoco.it non risponde da qui.
  **Vittoria Formula Lavoro**: la pagina dell'elenco (rendimenti) non ha documenti e i vecchi link (Nota informativa del
  2021) rispondono 502. **Eurorisparmio**: i link "SSRDisplayer" della pagina Sella non restituiscono il PDF (scaricati 4
  su 11 da sellasgr.it). **Arti & Mestieri**: 31 su 32; manca la *Scheda sintetica per adesioni collettive*, il cui link
  sulla pagina di animasgr.it risponde 404.
- In tutto **10 fondi** con documenti da recuperare: sono le righe della tabella *Documenti da recuperare* della dashboard.
- Quando l'utente fornisce i PDF (in `documenti-da-smistare/`), si smistano con `documenti.py smista` (anteprima, poi
  `--applica`), si controllano i titoli dei documenti nuovi nel registro e si rigenera l'indice.
- **Azimut Sustainable Future**: la sua pagina su azimut.it pubblica gli stessi file di Azimut Previdenza; l'URL
  azimutwm.it dell'elenco (§4.2, righe 28 e 40) non esiste più.
- Documenti datati segnalati anche in `Prestazioni`: Vera Vita (Documento sulle rendite 12/2023), Crédit Agricole Vita
  (2022), Plurifonds.

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
  - `regole.json`: `[{ id, tema, titolo, domanda, regola, valore, uguale_per_tutti, varia, riferimento, fonte_nome,
    fonte_url, consultata_il, in_vigore_dal, note }]` (date ISO).
  - `longevita.json`: `{ fonte, eta_partenza: 67, sintesi: {uomini|donne|totale: {speranza, eta_75_vivi, eta_50_vivi,
    eta_25_vivi, eta_10_vivi}}, durata_definita: {eta_inizio, anni, eta_fine, vivi_a_fine}, serie: {sesso: [{eta, vivi}]} }`
    (le quote si ricalcolano in Python dai sopravviventi).
  - `glossario.json`: `[{ id, gruppo, termine, esteso, definizione, fonte_nome, fonte_url, consultata_il, note }]`
    nell'ordine del foglio. L'export rigenera anche la tabella del glossario in `docs/guida/GUIDA.md`, **solo** tra
    `<!-- glossario:inizio … -->` e `<!-- glossario:fine -->` (`glossario_md()`; `test_glossario_nella_guida` verifica
    che sia allineata).
  - `prestazioni.json`: solo le righe di `Prestazioni` con dati: `[{ fondo_id, riga, documento_rendite: {titolo, url},
    compagnia, varianti: {reversibile, certa, controassicurata, ltc}, n_varianti, rendita_67, tasso_conversione_67,
    tasso_tecnico, basi, costo_rendita, costi: {anticipazione, riscatto, trasferimento, rita}, scheda_costi: {titolo, url},
    nuove_prestazioni, supplemento: {titolo, url}, consultata_il, note }]`. `n_varianti` e `tasso_conversione_67` sono
    ricalcolati dall'export (come le formule H e J); costi a 0 = non previsti, `null` = non trovati.
  - `documenti.json` (generato da `scripts/documenti.py indice`, non dall'export): `{ aggiornato_il, tipi: [{id, nome,
    descrizione}], totali: {fondi, fondi_con_documenti, referenziati, scaricati_referenziati, scaricati, pagine, byte},
    fondi: [{ fondo_id, referenziati, scaricati_referenziati, scaricati, nota, documenti: [{ tipo, titolo, url, pagina,
    referenziato, file, testo, scaricato_il, pagine, byte, sha256, note }] }] }` in ordine di riga, con `file`/`testo`
    relativi a `docs/` (es. `documenti/aureo/regolamento.pdf`). È **facoltativo** per il sito (`caricaDocumenti()`).
  - `meta.json`: versione, data di export, hash del commit, licenza (da `LICENSE`), conteggi (anche `regole`,
    `glossario`, `fondi_con_prestazioni`, `prestazioni_con_rendita_67`), flag, elenco delle fonti (quelle dei fogli `Regole` e `Glossario` e della tavola ISTAT vi si aggiungono
    **in automatico**, senza duplicati; le voci del glossario COVIP diventano una sola fonte, con `url_comune()`).
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
   pagina del fondo e alla scheda fonte, e badge ⚠️ dove ci sono note o anomalie. ESG/life cycle/online in un'unica
   colonna "Caratteristiche" a etichette, così su desktop (≥ 1280 px) la tabella entra senza scroll orizzontale; se non
   entra, il contenitore prende un'altezza massima (classe `scorre`, gestita da `aggiornaScorrimento()` in `app.js`) con
   intestazione e colonna "Fondo" fisse, perché la barra orizzontale non resti solo in fondo alle 38 righe.
2. **Dettaglio fondo**: comparti, asset allocation (barra azioni/obbligazioni), rendimento con periodo esplicito, commissione e note.
   In fondo, **Documenti ufficiali** (`documentiFondo()` in `app.js`, da `documenti.json`): copie scaricabili in due
   colonne (titolo del gestore, pagine, peso, link "originale"), conteggio "scaricati X dei Y citati" e, sotto, i documenti
   non scaricati con il motivo; la nota sul fondo se c'è. In *Qualità dei dati → Copertura* una riga con i totali
   (`coperturaDocumenti()`) e, dopo le anomalie, la tabella **Documenti da recuperare** (`documentiDaRecuperare()`:
   fondo, quanti mancano, perché), richiesta dall'utente per poter fornire lui i PDF che non si scaricano.
3. **Grafico a dispersione commissione vs rendimento** per comparto, colorato per categoria, solo comparti a 10 anni
   (con un toggle per includere quelli a 3 o 5 anni, ben segnalati).
4. **Simulatore dei costi**: versamento annuo + orizzonte + comparto → costo totale stimato (adesione + spese fisse +
   % sul versato + commissione di gestione sul patrimonio) e montante netto. Confronto tra 2 e 4 comparti.
5. **Confronto per categoria** (AZN/BIL/OBB/GAR): migliori e peggiori per costo e rendimento.
6. Sezione **"Qualità dei dati"**: copertura, anomalie aperte e fonti. Niente blocchi `<details>` "tutto o niente":
   i fondi senza dati sono etichette sempre visibili; le note mostrano le prime 6 (due righe ciascuna) con
   "Mostra tutte / Mostra meno".
7. **Disclaimer** sempre visibili: avviso "progetto personale" sotto l'intestazione e nel footer (testo canonico:
   *"Progetto personale, nato per uso privato e pubblicato su GitHub a puro scopo dimostrativo: non è un servizio rivolto
   al pubblico né una consulenza finanziaria."*, più la non affiliazione a COVIP, gestori e Ciao Elsa), ripetuto in
   guida, presentazione e README. Footer (centrato) con "non è consulenza finanziaria", versione e data di
   aggiornamento da `meta.json` e licenza. **La licenza non si scrive mai a mano**: `export_xlsx.py` la riconosce dal
   file `LICENSE` del repository (`meta.json → licenza`, oggi **The Unlicense**, pubblico dominio) e il footer la legge
   da lì; il testo precisa che i dati restano delle rispettive fonti.
8. **CI**: `.github/workflows/ci.yml` su ogni PR verso `master` (export, test, smoke test del sito, anteprima della
   versione); `.github/workflows/pages.yml` al merge su `master` (export, test, deploy di `docs/` con i JSON copiati in
   `docs/data/`, poi tag e release). Dettagli nella §8.
9. Pagine collegate dal menu: **Guida** (`docs/guida/`) e **Presentazione** (`docs/presentazione/`), vedi §10.
   **Navigazione** (`docs/navigazione.js`, condiviso da dashboard e guida): la barra fissa evidenzia la sezione visibile
   (`aria-current`, IntersectionObserver) e su telefono scorre fino alla voce attiva; pulsante rotondo **"Torna su"**
   in basso a destra, visibile dopo circa uno schermo di scorrimento. Spaziatura verticale ampia tra le sezioni (96 px,
   72 su telefono).
   **Marchio "goodbye Elsa !!"** (richiesta dell'utente): logo di Elsa (`docs/img/elsa-192.png`) + scritta nel font
   **Chewy** (Google Fonts) e nell'arancione del suo golfino (`--elsa: #f03e3a`, uguale nei due temi), come pulsante in
   alto a sinistra in **tutte le pagine**, che riporta sempre all'inizio della dashboard (`<a class="marchio">`; sulla
   dashboard `navigazione.js` scorre in cima senza ricaricare e toglie l'ancora). Nella barra `.topnav .wrap` è una
   griglia a tre colonne: marchio, voci (`.topnav .voci`, centrate nella pagina) e una colonna vuota che bilancia.
   Da 641 px in su, se il menu non entra, `navigazione.js` aggiunge `.compatto` e la scritta si nasconde (resta per i
   lettori di schermo); su telefono resta, più piccola, e il menu scorre. Nella presentazione è fisso in alto a sinistra.
   **Favicon** in tutte le pagine: `img/favicon-32.png`, `img/elsa-192.png`, `img/apple-touch-icon.png` (sfondo pieno).
   L'originale è `assets/elsa.png` (2048 px, fuori da `docs/`); le versioni del sito si rigenerano con
   `python scripts/icone.py` (Pillow, PNG a 256 colori).
9-bis. **Regole** (sezione `#regole`, dopo *Per categoria*): schede lette da `regole.json`, filtro per tema a pillole
   (default: il primo tema) e interruttore *Solo ciò che cambia da fondo a fondo*; ogni scheda ha valore chiave, stato
   (uguale per tutti / dipende dal fondo), data di entrata in vigore se nuova e riferimento normativo con link alla fonte.
   Sotto, **Per quanto tempo servirà il capitale?**: 4 numeri chiave e la curva ISTAT dei 67enni ancora in vita (Chart.js,
   uomini/donne, linea tratteggiata alla fine della rendita a durata definita). Nel **dettaglio fondo**, l'elenco
   "Alla pensione e in caso di decesso" da verificare nei documenti del fondo, generato dalle regole con G ≠ `Sì`.
9-ter. **Glossario e suggerimenti** (sezione `#glossario`, tra *Regole* e *Qualità dei dati*, voce nel menu): le voci di
   `glossario.json` per gruppo, su più colonne in un unico riquadro, con ricerca (`#gl-cerca`, ignora maiuscole e accenti),
   link alla fonte e note; ancore `#glossario-<id>`. **Suggerimenti** (sezione "suggerimenti" di `app.js`, un solo
   `#suggerimento` con `role="tooltip"`): ogni elemento con `data-glossario="<id>"` mostra la voce, `data-spiega="…"` aggiunge
   (o da solo dà) la spiegazione di quel punto della pagina ("Qui: …"). Mouse: al passaggio (120 ms); tastiera: al focus
   visibile, con `aria-describedby`, ed **Esc** per chiudere; touch: un tocco sui termini che non sono pulsanti o link. Nel
   dettaglio fondo il suggerimento viene spostato dentro il `<dialog>` (top layer); lo scroll chiude quello visibile.
   I termini nel testo sono `<span class="termine">` (sottolineatura a puntini, helper `termine()` in `app.js`); intestazioni
   di colonna (`glossario`/`spiega` in `COLONNE`), filtri, etichette, legenda del grafico e badge ⚠️ usano gli stessi
   attributi: **non si usa più l'attributo `title`** per le spiegazioni.
9-quater. **Alla pensione, fondo per fondo** (sezione `#prestazioni`, tra *Regole* e *Glossario*, voce "Alla pensione" nel
   menu): 3 numeri chiave (fondi con dati, intervallo della rendita a 67 anni ogni 10.000 €, differenza annua su 100.000 €),
   filtro *Solo con la rendita a 67 anni* e tabella ordinata dalla rendita più alta (rendita, tasso tecnico, costo della
   rendita, varianti a etichette, costi di anticipazione/riscatto/trasferimento, link alla fonte). Sotto, come leggere i
   numeri e l'elenco dei fondi mancanti. Nel **dettaglio fondo**, prima della lista da verificare, il blocco *Alla pensione
   con questo fondo* (`prestazioniFondo()` in `app.js`) con fonti e data di consultazione.
10. **Stile**: semplice e poco distraente. Font Inter (Google Fonts, fallback di sistema), intestazione con leggera
   sfumatura, **intestazione, navigazione e "aperture" delle sezioni centrate** (titolo `h2` + prima riga `.hint`,
   avviso "progetto personale", sotto-aperture `.apertura` come Copertura e Anomalie in Qualità dei dati, footer);
   centrate anche le **didascalie sotto le immagini a tutta larghezza** (`.chart-box + .hint` sotto i grafici di
   commissione/rendimento e longevità, `img.shot + .piccolo` nella presentazione, figure della guida);
   tabelle, grafico, card, note e filtri allineati a sinistra, navigazione fissa a
   pillole, card con ombre morbide, filtri a pillola. `text-wrap: balance` sui titoli e `pretty` sui paragrafi, per
   evitare parole isolate a fine riga. Colori come token CSS in
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
  - **Commit che ne riuniscono altri** (messaggi concatenati o squash, es. `a538964`): `voci()` legge anche le righe
    `tipo: testo` **a inizio riga** nel corpo, con un tipo di `TIPI_NEL_CORPO` in minuscolo, e le tratta come lavori a sé
    (note di rilascio e tipo di incremento). Le voci di elenco (`- dati: …`), le righe rientrate, `Fonte:` e
    `Co-Authored-By:` restano fuori. Quindi in un messaggio unito i titoli vanno a inizio riga e i dettagli in elenco.
- **`ci.yml`** (solo PR verso `master` e avvio manuale; niente `push`, per non far girare due volte lo stesso job): export, test (schema, versioni, smoke test Playwright del sito)
  e, sulle PR, la versione e le note che verranno pubblicate nel *Job summary*.
- **`pages.yml`** (push su `master`, cioè il merge di una PR, oppure avvio manuale):
  1. `build`: trova la PR di origine, calcola la versione, `APP_VERSION=vX.Y.Z python scripts/export_xlsx.py`
     (la versione finisce in `meta.json` e nel footer), test, note di rilascio, artifact di Pages;
  2. `deploy`: GitHub Pages (ambiente `github-pages`);
  3. `release`: `gh release create vX.Y.Z` con le note (sezioni per tipo di commit, link alla PR, numeri dei dati,
     link a dashboard/guida/presentazione e confronto con il tag precedente). Viene saltata se non ci sono commit nuovi.
     **Allegati** (preparati nel job `build`, passati con l'artifact `rilascio`): `fondi.json`, `comparti.json`,
     `meta.json` e `documenti.json` della versione, `fondi-pensione-covip-vX.Y.Z.xlsx`, `sito-vX.Y.Z.zip` (il contenuto
     di `docs/` così come pubblicato, **senza `docs/documenti/`**: oltre 400 MB di PDF, che restano nel repository e sul
     sito) e `SHA256SUMS.txt`. GitHub aggiunge da solo gli archivi del codice sorgente.
     Gli allegati stanno solo nella pagina *Releases*: la sezione *Packages* (GitHub Packages: npm, Maven, ghcr.io…)
     è un servizio diverso e resta vuota, per scelta (vedi guida).
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
  pubblico (github.com/wijmo/gc-excelviewer) ed è un **visualizzatore**. Il workbook si modifica in Excel, oppure da Python
  salvando con `workbook_utils.salva()`, che calcola le formule e ne mantiene la cache (§3).
- **MCP** (`.mcp.json`, server di progetto per Claude Code): `@playwright/mcp@0.0.82` in Chromium headless e isolato, con
  viewport 1360×820 e output in `.playwright-mcp/` (ignorato da git). Serve a navigare il sito e a fare screenshot ad hoc;
  gli screenshot della guida si rigenerano invece con lo script riproducibile `scripts/screenshots.py`.
- Versioni fissate: `playwright==1.63.0`, `pillow==12.3.0`, `pypdf==6.19.0` e `cryptography==50.0.1` (Python), `@playwright/mcp@0.0.82`, Chart.js 4.4.1,
  reveal.js 6.0.2, marked 18.0.13, DOMPurify 3.4.15. Quando si aggiorna una versione, aggiornarla qui.
- `.vscode/tasks.json`: *Anteprima GitHub Page*, *Anteprima veloce*, *Export dati* (export + indice dei documenti),
  *Documenti: riprova i download mancanti*, *Documenti: smista i PDF aggiunti a mano (anteprima)*, *Test*,
  *Rigenera screenshot*, *Prossima versione*.
- **Documenti ufficiali** (`scripts/documenti.py`): `scarica` (PDF mancanti del registro + testo), `riprova` (documenti
  senza file: urllib → curl → `--browser`, con `--pausa`; aggiorna il registro), `smista` (PDF messi a mano
  dall'utente in **`documenti-da-smistare/`**, cartella ignorata da git tranne README: fondo dalla sottocartella
  `<fondo-id>/` o da nome del file e prime pagine con `CHIAVI_FONDO`, tipo dal titolo con `TITOLI_TIPO`, abbinamento al
  documento mancante più simile del registro; senza `--applica` mostra solo l'anteprima; con `--applica` sposta, estrae
  il testo con `# Provenienza: copia fornita a mano` e scrive nel registro la nota "Copia fornita a mano il …"; i PDF
  con fondo dubbio restano in cartella), `indice` (senza rete: `documenti.json`
  in `data/` e `docs/data/`, `docs/documenti/README.md`, e controlla registro, file orfani e SHA-256). `indice` gira in
  CI dopo l'export, in `anteprima.sh`, `screenshots.py` e `post-create.sh`; i test sono in `tests/test_documenti.py`.

## 10. Documentazione per gli utenti
### 10.1 Guida (`docs/guida/`)
- Il testo sta in `docs/guida/GUIDA.md` (si legge anche su GitHub); `docs/guida/index.html` lo mostra sul sito con
  marked + DOMPurify. Le ancore sono compatibili con GitHub.
- Screenshot in `docs/guida/img/`, generati da `python scripts/screenshots.py` (fa prima l'export): `dashboard`,
  `tabella-filtri`, `suggerimento` (mouse sul filtro ESG), `dettaglio`, `grafico`, `grafico-evidenzia`, `categorie`,
  `regole`, `longevita`, `prestazioni`, `glossario`, `qualita`, `dettaglio-pensione` (blocco "Alla pensione con questo
  fondo" di Generali Global), `documenti` (documenti ufficiali in fondo al dettaglio di Generali Global), `mobile-scuro`. I blocchi alti si portano in cima alla finestra prima dello
  scatto (Chromium non disegna oltre il bordo); il pulsante "Torna su" è nascosto negli scatti delle sezioni.
- Capitolo **"Glossario"**: introduzione scritta a mano, poi la tabella **generata dall'export** dal foglio `Glossario`
  (tra i marcatori `glossario:inizio`/`glossario:fine`, da non modificare a mano).
- **Immagini centrate con didascalia** (richiesta dell'utente): nel Markdown un'immagine sta da sola nel suo paragrafo
  (`![Didascalia](img/x.png)`); `index.html` la trasforma in `<figure>` con il testo alternativo come `<figcaption>`, e
  immagine e didascalia sono centrate, anche quelle più strette della pagina (es. `mobile-scuro`). Il testo
  alternativo va quindi scritto come una didascalia leggibile.
- Capitolo **"Come funziona un fondo pensione"**: risposte alle domande dell'utente (funzionamento, TFR e uscite anticipate,
  opzioni alla pensione e cosa dipende dal fondo, decesso ed eredi, strategie con i dati ISTAT), con le fonti in fondo.
  I numeri devono coincidere con il foglio `Regole`.
- Capitolo **"Alla pensione, fondo per fondo"**: come leggere la tabella e il blocco del dettaglio, e i limiti del confronto
  (tasso tecnico, tavole, coefficienti che cambiano, fondi mancanti).
- Capitolo **"Documenti ufficiali dei fondi"**: cosa c'è, come si conta "scaricati X dei Y citati", cosa è escluso e perché
  alcuni mancano; in *Per chi mantiene il progetto* i comandi di `scripts/documenti.py`.
### 10.2 Presentazione (`docs/presentazione/`)
- reveal.js con navigazione **2D**: in orizzontale gli argomenti (titolo, perché, dati, dashboard, **come funziona**, come
  scegliere, manutenzione, fine), in verticale gli approfondimenti. I valori chiave delle regole (`data-regola="<titolo
  breve>"`) e la frase sulla longevità si leggono dal vivo da `regole.json` e `longevita.json`; la slide *Quanto paga la
  rendita? Dipende dal fondo* legge l'intervallo della rendita a 67 anni da `prestazioni.json`; la slide *I documenti
  ufficiali dei fondi* (pila "dati") legge i totali da `documenti.json`. Riusa gli screenshot della guida e legge i numeri dal vivo da
  `data/meta.json`. Tema chiaro/scuro automatico.
### 10.3 Anteprima locale prima del push
- `./scripts/anteprima.sh` (export + test + server su http://localhost:8000, con le stesse pagine che verranno pubblicate),
  `--veloce` per saltare i test, `PORTA=9000` per cambiare porta. È disponibile anche come task di VS Code.
- `tests/test_sito.py` controlla dashboard, dettaglio, mobile, guida (immagini caricate) e presentazione (pile verticali,
  navigazione ↓) senza errori JavaScript, più marchio e favicon in tutte le pagine (`test_marchio_e_favicon`: il logo
  riporta alla dashboard, che non si ricarica) e i documenti nel dettaglio (`test_documenti_nel_dettaglio`: il link serve
  davvero un PDF). Usa `scripts/server_locale.py`. `tests/test_documenti.py` controlla registro, PDF, testi e indice.
### 10.4 Regola di allineamento (obbligatoria)
Ogni modifica che cambia ciò che l'utente vede o fa (dashboard, dati mostrati, flusso di rilascio, comandi) va
accompagnata **nello stesso commit/PR** da:
1. aggiornamento di `docs/guida/GUIDA.md`;
2. aggiornamento della presentazione, se tocca uno degli argomenti;
3. `python scripts/screenshots.py`, se cambia l'aspetto;
4. aggiornamento di questo `CLAUDE.md` (struttura, schema, versioni, roadmap) e del `README.md`;
5. test verdi (`python -m unittest discover -s tests`).

## 11. Come gestire le domande dell'utente (procedura permanente)
1. **Spiegare in chat**, in modo semplice, con esempi presi dai dati del progetto.
2. **Rendere chiaro anche nella piattaforma** ciò che ha generato il dubbio, nel modo più leggero possibile, in quest'ordine:
   - testo vicino all'elemento: riga `.hint` sotto il titolo, **suggerimento** al passaggio del mouse (`data-spiega` sul
     punto della pagina, oppure `glossario`/`spiega` in `COLONNE` di `app.js` per le intestazioni), etichette più parlanti;
   - voce nel **Glossario**: una riga nel foglio `Glossario` (con fonte), poi `data-glossario="<id>"` sui punti della UI
     dove compare il termine; l'export aggiorna dashboard e tabella della guida. Oppure la sezione giusta di
     `docs/guida/GUIDA.md`;
   - una slide (verticale) nella presentazione, solo se l'argomento è centrale.
   Niente box, icone o colori nuovi senza motivo: la pagina deve restare semplice e poco distraente (§7.10).
3. **Se servono dati nuovi o da verificare**, cercarli online solo su fonti ammesse (§2: COVIP, siti/documenti ufficiali
   dei gestori, Nota informativa, Scheda costi; Ciao Elsa come fonte secondaria) e aggiornare **a cascata**:
   1. **Excel** (fonte di verità): valore nella cella, fonte come hyperlink o in `Note` nel formato
      `Fonte: <nome> <URL> (consultata il AAAA-MM-GG)`; incoerenze segnalate, mai corrette in silenzio; formule intatte;
      nuove colonne o fogli solo se servono, documentati nella §3;
   2. `scripts/export_xlsx.py` (schema, validazioni, flag), `tests/`, poi `python scripts/export_xlsx.py`;
   3. dashboard (`docs/`), guida, presentazione, `python scripts/screenshots.py`;
   4. `CLAUDE.md` (§3 struttura, §4 fonti, §5 problemi noti, roadmap) e `README.md`.
   Se Claude modifica l'Excel con openpyxl, deve preservare formule, formati e hyperlink e salvare con
   `scripts/workbook_utils.salva()` (conserva il collegamento a Claude per Excel e calcola le formule, così la cache resta
   piena e **non serve chiedere all'utente di riaprire il file in Excel**). Se `salva()` restituisce celle non calcolate,
   la formula usa una funzione da aggiungere al calcolatore (§3). Se altre sessioni lavorano sul workbook, ricaricarlo
   dal disco subito prima di salvare e avvisarle.
4. **Citare le fonti**: in chat con i link consultati; nella piattaforma solo attraverso i canali esistenti (link
   *Sito/Scheda*, note del fondo/comparto, sezione *Fonti* alimentata da `meta.json → fonti` nella lista di
   `export_xlsx.py`). Ogni nuova fonte va aggiunta lì e nella §4.
5. **Chiudere ogni richiesta** con: export, test verdi, screenshot se è cambiato l'aspetto, controllo della regola di
   allineamento (§10.4) e **messaggio di commit pronto** (convenzionale, in italiano, con le fonti dei dati).
   Commit e push li fa l'utente.

## 12. Roadmap / TODO
- [x] Script `scripts/export_xlsx.py` + `requirements.txt` + test di schema (`tests/test_export.py`)
- [x] Prima versione della dashboard (tabella, dettaglio, scatter, confronto per categoria, qualità dei dati) + CI `pages.yml`
- [x] CI su PR, deploy + tag + release al merge, versionamento automatico (minor/patch)
- [x] Devcontainer, MCP Playwright, guida con screenshot, presentazione reveal.js 2D, anteprima locale
- [x] Regole generali con fonti (foglio `Regole`), tavola ISTAT di longevità, sezione *Regole* e capitolo della guida
- [x] Glossario con fonti (foglio `Glossario`, 49 voci dal glossario COVIP e da altre fonti ufficiali), sezione *Glossario*
  e suggerimenti al passaggio del mouse su termini, intestazioni, filtri ed etichette
- [ ] Valutare un flag per le categorie Ciao Elsa fuori dalle soglie COVIP (§5), da decidere con l'utente
- [x] **Approfondimento verticale per fondo sulle prestazioni**: foglio `Prestazioni` (32 fondi su 38, rendita a 67 anni
  confrontabile per 24), sezione *Alla pensione, fondo per fondo*, blocco nel dettaglio, capitolo della guida e slide
- [x] Cache delle formule calcolata da `workbook_utils.salva()`: niente più "apri e salva in Excel" dopo le modifiche da Python
- [ ] Completare `Prestazioni` per i 6 fondi senza documenti (§5) e cercare i coefficienti non pubblicati (Mediolanum,
  CNP, PensPlan Profi, Raiffeisen con rata annuale, Azimut e UniCredit unisex); aggiornare Plurifonds e Crédit Agricole Vita se escono documenti nuovi
- [ ] Valutare colonne per rivalutazione (rendimento trattenuto), durata maggiore e conversione del residuo nelle nuove forme
- [x] **Documenti ufficiali dei fondi** scaricati nel repository (`docs/documenti/`, registro `data/documenti.csv`, testo
  per pagina da consultare), scaricabili dal dettaglio fondo: 532 documenti per 31 fondi, 438 dei 538 citati (10/10/2026);
  tabella *Documenti da recuperare* in Qualità dei dati e cartella `documenti-da-smistare/` con `documenti.py smista`
- [ ] Recuperare i documenti mancanti dei 10 fondi (§5): l'utente li fornirà in `documenti-da-smistare/` (Teseo, Arca,
  Allianz, Insieme, UniCredit, Eurorisparmio, Fideuram, Il Melograno, Vittoria, Arti & Mestieri); in alternativa
  `documenti.py riprova` da un'altra rete
- [ ] Usare i testi dei documenti per completare `Prestazioni` e verificare le anomalie della §5 (Scheda costi)
- [ ] Simulatore dei costi (poi aggiornare guida, presentazione e screenshot)
- [ ] Verificare le anomalie della §5 sulle Schede costi ufficiali
- [ ] Completare i 15 fondi senza dati
- [ ] Aggiungere l'**ISC (Indicatore Sintetico dei Costi)** COVIP a 2/5/10/35 anni: è la metrica di costo ufficiale e confrontabile
- [ ] Valutare di rinominare `Sheet1` in `Fondi` (le formule di Excel si aggiornano da sole; aggiornare lo script)
- [x] Confermare l'URL esatto dell'elenco COVIP nella §4.1
- [ ] **Migrazione a Cloudflare** (Workers static assets + Access con One-time PIN) e repository privato: piano nella §13,
  da approvare con l'utente (Access in un account dedicato o password unica della §13.8, testo del disclaimer, licenza)

## 13. Piano: da GitHub Pages a Cloudflare, con accesso riservato e repository privato (proposta del 10/10/2026)
**Stato: proposta da approvare, non eseguita.** Finché non viene eseguita valgono le §7–§8 (GitHub Pages). Prezzi,
limiti e comandi verificati il 10/10/2026 sulle fonti della §13.10: prima di partire ricontrollare versioni e prezzi.

### 13.1 Scelte consigliate
| Tema | Scelta | Perché |
|---|---|---|
| Hosting | **Cloudflare Workers con static assets**: un Worker senza codice che serve `docs/` (variante Pages nella §13.9) | Pages resta supportato, ma le novità arrivano su Workers (Access a un clic, anteprime delle PR); costi e limiti uguali |
| Build e deploy | tutto resta in **GitHub Actions** (export, test, versione, release): cambia solo il passo di deploy, `wrangler deploy` | export Python e test Playwright restano dove sono; niente build su Cloudflare; l'anteprima locale (§10.3) non cambia |
| Autenticazione | **Cloudflare Access** con **One-time PIN** (si scrive la propria email e arriva un codice), in un **account Cloudflare dedicato** a goodbye-elsa, con la sua organizzazione Zero Trust Free; alternativa senza Zero Trust: utente e password unici (§13.8) | l'utente non vuole condividere Zero Trust con l'altro progetto (10/10/2026); nessuna password da custodire, nessun codice nel sito |
| Autorizzazione | una policy *Allow* con l'**elenco delle email** ammesse (all'inizio solo l'utente) | si aggiunge o si toglie una persona dal pannello Zero Trust, senza deploy |
| Indirizzo | **deciso con l'utente il 10/10/2026**: quello di default, `https://goodbye-elsa.<sottodominio>.workers.dev`, senza dominio proprio | sito per uso personale: gratuito e senza DNS da gestire |
| IaC | **niente Terraform all'inizio**: `wrangler.jsonc` versionato + la checklist della §13.2; Terraform solo se serve (§13.7) | sono 4–5 oggetti: state, token e import costerebbero più di quanto fanno risparmiare |
| Repository | privato su **GitHub Free** | 0 €, ma si perdono alcune funzioni (§13.5, punto 5) |

### 13.2 Lato Cloudflare (una tantum, a mano)
1. **Account dedicato a goodbye-elsa** (l'utente non vuole condividere Zero Trust con l'altro progetto, 10/10/2026):
   con lo stesso login, *Accounts › Create Account* (fino a 5 account Free in più; serve un utente attivo da almeno 7
   giorni e Super Administrator di un account esistente). Annotare l'**Account ID** e scegliere il sottodominio
   `workers.dev` del nuovo account. Worker, Zero Trust e token stanno tutti qui: nome del team, pagina di login, metodi
   di login e posti non hanno niente in comune con l'altro progetto.
2. **Zero Trust del nuovo account**: nome del team (es. `goodbye-elsa` → `goodbye-elsa.cloudflareaccess.com`, se
   libero), piano **Free** (chiede un metodo di pagamento, senza addebiti) e metodo di login **One-time PIN**, da
   aggiungere in *Integrations › Identity providers* (da giugno 2026 le organizzazioni nuove partono con il solo login
   Cloudflare). Facoltativo il logo di Elsa nella pagina di login. I 50 posti sono tutti per goodbye-elsa: un posto si
   occupa al primo accesso e si libera togliendo la persona da *Team & Resources › Users*.
3. **Worker segnaposto**: *Workers & Pages › Create*, modello *Hello World*, nome `goodbye-elsa` (una pagina innocua:
   permette di attivare Access prima che arrivino i dati, e il token del punto 5 può aggiornare solo un Worker che
   esiste già). Poi *goodbye-elsa › Domains* (prima *Settings › Domains & Routes*) → **Enable Cloudflare Access** su
   `workers.dev` e, in *Manage Cloudflare Access*, la policy `goodbye-elsa - Production`: regola *Include* con le
   **email** ammesse (o un gruppo Access), mai *Everyone* né il solo metodo di login (con il One-time PIN chiunque abbia
   un indirizzo email riceverebbe il codice); come metodo di login dell'app solo One-time PIN; sessione di 1 settimana.
4. **Verifica**: in una finestra anonima compare il login di Access;
   `curl -sI https://goodbye-elsa.<sottodominio>.workers.dev/` risponde con un redirect a `<team>.cloudflareaccess.com`,
   mai `200`.
5. **API token per la CI**, nel nuovo account e limitato al solo Worker: *Manage Account › Account API Tokens*, ambito
   *Specified Workers* → `goodbye-elsa`, ruolo **Editor** (pubblica ma non cancella). Con scadenza (es. 12 mesi, da
   segnare: scaduto il token, la CI non pubblica). I permessi per singolo Worker esistono dal 15/9/2026: se
   `wrangler deploy` fallisce con questo token, va bene anche un token di account con il ruolo Workers Admin, perché
   l'account è dedicato.
6. Facoltativo: **service token** `ci-goodbye-elsa` e una regola *Service Auth* nella policy di goodbye-elsa, per il
   controllo dopo il deploy (§13.4, punto 3).

### 13.3 Lato GitHub: secrets e variabili
- **Un solo secret di repository**, `CLOUDFLARE_API_TOKEN`: i secret di repository funzionano anche con il repository
  privato su GitHub Free. Non funzionano solo quelli d'ambiente (environments), che il piano non usa.
- **Variabili** (non sono segrete): `CLOUDFLARE_ACCOUNT_ID` e `SITO_URL`.
- Si impostano dal browser, in *Settings › Secrets and variables › Actions* (schede *Secrets* e *Variables*): dal
  Codespace il token automatico non ha il permesso (la lettura dei secret risponde 403). In alternativa `gh auth login`
  con il proprio account, poi `gh secret set` e `gh variable set`. Possono essere creati prima o dopo il passaggio a
  privato: restano.
- Facoltativi: `CF_ACCESS_CLIENT_ID` e `CF_ACCESS_CLIENT_SECRET` (service token della §13.2, punto 6).
- Con l'alternativa della §13.8, al posto del service token: il secret `SITO_PASSWORD` e la variabile `SITO_UTENTE`.
- `GITHUB_TOKEN` resta quello automatico per tag e release. **Nessun secret per Terraform** finché gira in locale (§13.7).
- Senza nessun secret si potrebbe solo collegare il repository a Cloudflare (Workers Builds), che farebbe la build sui suoi
  server, separata da test e release in GitHub Actions: scartato.

### 13.4 Modifiche al repository (una PR da `dev`)
1. **`wrangler.jsonc`** alla radice:
   ```jsonc
   { "name": "goodbye-elsa", "compatibility_date": "2026-10-01", "assets": { "directory": "./docs" },
     "workers_dev": true, "preview_urls": false }
   ```
   Anteprime spente: basta l'anteprima locale (§10.3). Facoltativi `docs/404.html` (con
   `"not_found_handling": "404-page"`) e `docs/_headers` (`X-Robots-Tag: noindex`).
   Provato il 10/10/2026 con `wrangler deploy --dry-run`, che non chiede credenziali: legge tutto `docs/` (circa 1.100
   file) e **blocca i file oltre 25 MiB** ("Asset too large").
2. **`pages.yml` → `deploy.yml`** (*Deploy su Cloudflare e release*): nel job `build`, dopo export e test,
   `cloudflare/wrangler-action@v4` (≥ 4.1.2: la 4.1.0 e la 4.1.1 sono rotte) con `apiToken`, `accountId`,
   `wranglerVersion: "4.149.0"` e `command: deploy --tag <versione> --message "<titolo della PR>"`, al posto di
   `upload-pages-artifact`. Il job `deploy` (environment `github-pages`, permessi `pages` e `id-token`) sparisce e
   `release` dipende solo da `build`. Artifact `rilascio` con `retention-days: 1`: su un repository privato gli artifact
   consumano i 500 MB inclusi. Il primo deploy carica tutti i ~450 MB, i successivi solo i file cambiati.
3. **Controllo dopo il deploy**, nello stesso job: `curl` senza credenziali su `SITO_URL` e `SITO_URL/data/meta.json`
   deve dare il redirect al login (se dà `200` il sito è pubblico e il job fallisce); con il service token, `meta.json`
   deve riportare la versione appena pubblicata. Cloudflare consiglia anche di verificare il JWT di Access
   (`Cf-Access-Jwt-Assertion`) nel Worker: servirebbe un Worker con codice, che conta nelle 100.000 richieste al giorno
   del piano Free; per un sito statico raggiungibile solo dagli indirizzi protetti basta questo controllo.
4. **`ci.yml`**: `wrangler deploy --dry-run` (senza secret), così un PDF troppo grande si scopre nella PR e non al merge.
   Se un giorno servono le anteprime delle PR: `wrangler preview` (in open beta a ottobre 2026), protette dalla policy
   *Cloudflare Workers Preview URLs* dell'account (dedicato, quindi solo goodbye-elsa), con il link nel *Job summary*.
5. **Link e testi**: `versione.py note` prende l'indirizzo da `--sito` (`SITO_URL`) invece di costruire quello di
   `github.io` (aggiornare `tests/test_versione.py`). I link a github.com nel sito diventano 404 per chi non è
   collaboratore: `app.js` (licenza nel footer, "elenco completo" dei documenti), `guida/index.html` ("Sorgente su
   GitHub"), presentazione ("💻 GitHub"), `GUIDA.md` (elenco dei documenti, Releases): puntarli a copie sul sito o
   toglierli. README con il nuovo indirizzo; "GitHub Page" → "sito" in `.vscode/tasks.json`,
   `.devcontainer/devcontainer.json`, `anteprima.sh` e `server_locale.py`.
6. **Disclaimer** (§7.7: dashboard ×2, guida, presentazione ×2, README, questo file): "pubblicato su GitHub a puro scopo
   dimostrativo" non sarà più vero. Proposta, da confermare con l'utente: *"Progetto personale, nato per uso privato e
   consultabile solo su invito: non è un servizio rivolto al pubblico né una consulenza finanziaria."*
7. **Licenza**: con il repository privato The Unlicense non serve più a nessuno; decidere se tenerla o togliere `LICENSE`
   (l'export regge l'assenza del file: avviso e footer senza licenza).
8. **Allineamento** (§10.4): guida (indirizzo, come si entra con il codice via email, deploy e release), slide di
   manutenzione della presentazione, screenshot se cambia il footer, questo file (§1, §2, §7.8, §8, §9 con le versioni di
   wrangler e della action, §10.3) e README.

### 13.5 Ordine di esecuzione (su Cloudflare il sito non è mai pubblico)
1. §13.2 punti 1–5 (Access attivo e verificato sul segnaposto, token della CI creato) e §13.3.
2. PR da `dev` con la §13.4 e CI verde; al merge il primo deploy su Cloudflare e la release.
3. Prova completa da autenticati (tabella, dettaglio, PDF, guida, presentazione) e da anonimi (solo il login).
4. **Spegnere GitHub Pages** (*Settings › Pages › Unpublish site*; con GitHub Free succede comunque da solo al punto 5)
   e cancellare l'environment `github-pages`. Fino ad allora `andreagalle.github.io/goodbye-elsa/` resta pubblico; le
   copie già in cache (motori di ricerca, Wayback Machine) non dipendono da noi.
5. **Repository privato**: *Settings › General › Danger Zone › Change visibility*. Con GitHub Free: Pages spento, stelle e
   watcher cancellati (oggi nessuna stella), fork pubblici staccati (oggi nessuno), environments e secret d'ambiente
   ignorati, protezione dei branch non applicata (resta la convenzione PR → `master`).
6. Controllare la prima esecuzione delle Actions da privato e i minuti consumati (*Settings › Billing and licensing*).
7. **Tornare indietro**: Cloudflare conserva le versioni precedenti (`wrangler rollback` o *Deployments*); il repository
   può tornare pubblico (environments e secret d'ambiente si riattivano) e `pages.yml` resta nella storia di git.

### 13.6 Costi (ottobre 2026)
| Voce | Piano | Costo | Limiti che contano per noi |
|---|---|---|---|
| Hosting (Workers static assets) | Free | 0 € | richieste ai file statici gratuite e illimitate; 20.000 file per versione, 25 MiB per file (oggi ~1.100 file, il più grande 20 MiB: `documenti/plurifonds-itas-vita/rendiconto.pdf`) |
| Access (Zero Trust) | Free, nell'account dedicato | 0 € | 50 posti solo per goodbye-elsa; chiede un metodo di pagamento, senza addebiti; oltre 50, il piano a pagamento vale per tutti (~7 $ a utente al mese, da fonti secondarie) |
| oppure: password unica (§13.8) | Workers Free | 0 € | niente Zero Trust né metodo di pagamento; ogni richiesta esegue il Worker: 100.000 al giorno, poi `429` |
| GitHub, repository privato | Free | 0 € | 2.000 minuti di Actions al mese (oggi una PR ne usa circa 5 tra CI, deploy e release), 500 MB di artifact (condivisi con Packages) |
| GitHub Pro | facoltativo | ~4 $ al mese | riporta protezione dei branch ed environments sul repository privato |
| Terraform | facoltativo | 0 € | state su R2 (piano gratuito da 10 GB) |

**Totale: 0 € al mese.** Niente dominio proprio (deciso il 10/10/2026): il `.it` non si comprerebbe nemmeno su Cloudflare.

### 13.7 Terraform (solo se serve)
- Serve se si vuole ricreare tutto in modo riproducibile o gestire più ambienti e persone. Il contenuto del sito resta
  pubblicato da wrangler: Terraform gestirebbe solo Access, compresa l'organizzazione Zero Trust dell'account dedicato
  (che non tocca l'altro progetto).
- `infra/` con Terraform 1.16 e provider `cloudflare/cloudflare` 5.27 (versioni fissate). Risorse:
  `cloudflare_zero_trust_access_identity_provider` (One-time PIN), `cloudflare_zero_trust_access_group` (email),
  `cloudflare_zero_trust_access_policy`, `cloudflare_zero_trust_access_application` (hostname `workers.dev`),
  facoltativo `cloudflare_zero_trust_access_service_token`.
- **O "a un clic" o Terraform**, non entrambi: le app create dal pannello vanno importate (`terraform import`) o ricreate.
- State su **R2** con il backend `s3` (endpoint `https://<account_id>.r2.cloudflarestorage.com`, `region = "auto"`,
  `use_path_style = true`, `skip_credentials_validation`, `skip_region_validation`, `skip_requesting_account_id`,
  `skip_metadata_api_check`, `skip_s3_checksum`), bucket privato e token R2 *Object Read & Write* solo su quel bucket.
  **Mai lo state in git** (`.gitignore`: `.terraform/`, `*.tfstate*`).
- Esecuzione **in locale** dal devcontainer (feature Terraform ed estensione `hashicorp.terraform`, §9) con i **secrets di
  Codespaces**: un token Cloudflare separato da quello della CI (*Access: Apps and Policies* e *Access: Organizations,
  Identity Providers, and Groups* in Edit) e le chiavi R2. Gli stessi valori come secrets di GitHub servirebbero solo per
  `plan` nelle PR e `apply` al merge.

### 13.8 Alternativa: utente e password unici, senza Zero Trust
Per chi non vuole un secondo account né Zero Trust (scelta dell'utente ancora aperta il 10/10/2026). **Nessun
database**: utente e password sono due secret del Worker, e con l'HTTP Basic il browser li ricorda e li rimanda a ogni
richiesta.
- **Worker** `worker/accesso.js` (~25 righe, provato il 10/10/2026 con `wrangler dev`): senza credenziali o con quelle
  sbagliate risponde `401` con `WWW-Authenticate: Basic realm="goodbye Elsa", charset="UTF-8"` (il browser apre la sua
  finestra di accesso); con quelle giuste passa la richiesta a `env.ASSETS.fetch(request)`. Confronto con
  `crypto.subtle.timingSafeEqual` tra gli SHA-256 di `utente:password` ricevuti e attesi (stessa lunghezza, tempo
  costante). **Se un secret manca deve rispondere sempre `401`**: altrimenti `undefined:undefined` aprirebbe il sito.
- **`wrangler.jsonc`**: in più `"main": "worker/accesso.js"` e, dentro `assets`, `"binding": "ASSETS"` e
  `"run_worker_first": true`, così il Worker controlla anche PDF e JSON.
- **Secret**: `SITO_PASSWORD` come secret di GitHub e `SITO_UTENTE` come variabile (es. `elsa`); la action li copia nel
  Worker a ogni deploy (input `secrets`, con i valori in `env`; il ruolo Editor del token lo permette). Si possono
  tenere anche solo su Cloudflare (*Settings › Variables and Secrets*), ma allora il controllo dopo il deploy non può
  provare il login. In locale `.dev.vars` (in `.gitignore`).
- **Password lunga e casuale** (almeno 20 caratteri, solo ASCII): con un'unica password e nessun limite ai tentativi è
  l'unica difesa contro chi prova a indovinarla.
- **Costi e limiti**: 0 €, nessun metodo di pagamento. Ogni richiesta (anche file statici e PDF) esegue il Worker e conta
  nelle 100.000 al giorno del piano Free (una visita fa qualche decina di richieste: migliaia di visite al giorno);
  oltre, risposta `429`. Va bene anche nell'account dell'altro progetto, con il token limitato al solo Worker (serve
  comunque il segnaposto della §13.2, punto 3, perché il token aggiorna solo un Worker che esiste già).
- **Rispetto ad Access**: una password per tutti (per escludere una persona la si cambia a tutti), niente "esci" (si
  chiude il browser), finestra di accesso del browser invece di una pagina del sito. Se servono una pagina di accesso
  nostra e "esci": modulo e cookie firmato (HMAC con un terzo secret), sempre senza database, ~100 righe.
- **Test**: lo stesso giro del 10/10/2026 (`wrangler dev` con `.dev.vars` e `curl`: `401` senza credenziali, con
  password sbagliata o con un'intestazione non valida, `200` e `meta.json` con quelle giuste) e, dopo ogni deploy, lo
  stesso controllo sul sito pubblicato (§13.4, punto 3).

### 13.9 Variante: Cloudflare Pages
Stessi costi e limiti. `wrangler pages project create goodbye-elsa --production-branch master` crea il progetto senza
contenuti (Access si configura prima del primo deploy); deploy con `wrangler pages deploy docs --project-name
goodbye-elsa --branch master` (con `--branch dev` l'anteprima `dev.goodbye-elsa.pages.dev`); token *Account › Cloudflare
Pages › Edit*. Differenza principale: *Settings › Enable access policy* protegge solo le anteprime; per proteggere anche
`goodbye-elsa.pages.dev` serve la procedura dei *Known issues* di Pages (togliere il `*` dal sottodominio dell'app
Access creata, poi riattivare la policy delle anteprime).

### 13.10 Fonti (consultate il 10/10/2026)
- Cloudflare: limiti di [Workers](https://developers.cloudflare.com/workers/platform/limits/) e
  [Pages](https://developers.cloudflare.com/pages/platform/limits/),
  [costi degli static assets](https://developers.cloudflare.com/workers/static-assets/billing-and-limitations/),
  [migrazione da Pages](https://developers.cloudflare.com/workers/static-assets/migration-guides/migrate-from-pages/),
  [Access a un clic](https://developers.cloudflare.com/changelog/post/2025-10-03-one-click-access-for-workers/) e
  [policy riutilizzabili](https://developers.cloudflare.com/changelog/post/2025-12-03-reusable-access-policies/),
  [Worker Previews](https://developers.cloudflare.com/workers/previews/),
  [setup di Zero Trust](https://developers.cloudflare.com/cloudflare-one/setup/),
  [posti di Zero Trust](https://developers.cloudflare.com/cloudflare-one/identity/users/seat-management/),
  [One-time PIN](https://developers.cloudflare.com/cloudflare-one/integrations/identity-providers/one-time-pin/),
  [token per singolo Worker](https://developers.cloudflare.com/changelog/post/2026-09-15-granular-worker-permissions/)
  e [ruoli dei Worker](https://developers.cloudflare.com/workers/authorization/workers/),
  [account Free in più](https://developers.cloudflare.com/fundamentals/account/create-account/),
  [Worker davanti agli static assets](https://developers.cloudflare.com/workers/static-assets/binding/),
  [wrangler-action (input `secrets`)](https://github.com/cloudflare/wrangler-action), Pages
  ([anteprime](https://developers.cloudflare.com/pages/configuration/preview-deployments/),
  [known issues](https://developers.cloudflare.com/pages/platform/known-issues/),
  [Direct Upload in CI](https://developers.cloudflare.com/pages/how-to/use-direct-upload-with-continuous-integration/)),
  [state Terraform su R2](https://developers.cloudflare.com/terraform/advanced-topics/remote-backend/),
  [TLD del Registrar](https://www.cloudflare.com/tld-policies/).
- GitHub: [piani](https://docs.github.com/en/get-started/learning-about-github/githubs-plans),
  [costi di Actions](https://docs.github.com/billing/managing-billing-for-github-actions/about-billing-for-github-actions),
  [environments](https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments),
  [visibilità del repository](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/managing-repository-settings/setting-repository-visibility).
- Versioni del 10/10/2026: wrangler 4.149.0, `cloudflare/wrangler-action` v4.1.3, provider `cloudflare/cloudflare`
  5.27.0, Terraform 1.16.5.