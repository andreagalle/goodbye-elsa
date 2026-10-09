/* Dashboard fondi pensione aperti — vanilla JS, legge solo data/*.json generati da scripts/export_xlsx.py */
"use strict";

const STATO = {
  fondi: [], comparti: [], meta: {}, perId: new Map(),
  sort: { key: "best_rend_10a", dir: "desc" },
  filtri: { q: "", dati: false, esg: false, lc: false, online: false },
  grafico: null, evidenzia: "", includiPeriodi: false, nascosti: new Set(),
  regole: [], longevita: null, temaRegole: null, soloVaria: false, graficoLongevita: null,
  glossario: [], perTermine: new Map(), cercaGlossario: "",
  documenti: null, // indice dei documenti ufficiali (scripts/documenti.py); null se manca
  prestazioni: new Map(), soloRendita: false, // condizioni alla pensione per fondo (foglio Prestazioni)
};

// ---------------------------------------------------------------- formattazione (it-IT)
const nf = (d) => new Intl.NumberFormat("it-IT", { minimumFractionDigits: d, maximumFractionDigits: d, useGrouping: "always" });
const NF0 = nf(0), NF1 = nf(1), NF2 = nf(2);
const NA = '<span class="na" aria-label="dato mancante">—</span>';
const eur = (v) => (v == null ? NA : `${NF2.format(v)} €`);
const pct = (v, d = 2) => (v == null ? NA : `${(d === 0 ? NF0 : d === 1 ? NF1 : NF2).format(v * 100)}%`);
const pctTxt = (v, d = 2) => (v == null ? "—" : `${(d === 1 ? NF1 : NF2).format(v * 100)}%`);
const rend = (v) => (v == null ? NA : `<span class="${v < 0 ? "neg" : ""}">${pct(v)}</span>`);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const dataIt = (iso) => (iso ? new Date(iso).toLocaleDateString("it-IT", { day: "numeric", month: "long", year: "numeric" }) : "—");
const articoloData = (iso) => (/^(8|11) /.test(dataIt(iso)) ? "l'" : "il ");   // "l'8 ottobre", "il 9 ottobre"

const GRUPPI = {
  AZN: { label: "Azionari (AZN)", var: "--cat-azn", punto: "circle" },
  BIL: { label: "Bilanciati (BIL)", var: "--cat-bil", punto: "triangle" },
  OBB: { label: "Obbligazionari (OBB misto e puro)", var: "--cat-obb", punto: "rect" },
  GAR: { label: "Garantiti (GAR)", var: "--cat-gar", punto: "rectRot" },
};
const gruppo = (cat) => (cat && cat.startsWith("OBB") ? "OBB" : cat);
const sw = (cat) => `<span class="sw ${esc(gruppo(cat))}" aria-hidden="true"></span>`;
const tagCat = (cat) => `<span class="tag tag-cat"${cat ? ` data-glossario="${esc(gruppo(cat).toLowerCase())}"` : ""}>${sw(cat)}${esc(cat)}</span>`;
const css = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();

// Termine con la spiegazione del glossario al passaggio del mouse (testo già in HTML sicuro)
const termine = (id, testo) => `<span class="termine" data-glossario="${id}">${testo}</span>`;
const SPIEGA_MEDIANA = "Il valore centrale: metà dei comparti della categoria sta sotto, metà sopra. A differenza della media, non si sposta per pochi valori molto alti o molto bassi.";

const flagFondo = (k) => STATO.meta.flag?.fondi?.[k] ?? k;
const flagComparto = (k) => STATO.meta.flag?.comparti?.[k] ?? k;
const compartiDi = (id) => STATO.comparti.filter((c) => c.fondo_id === id);

// Nei fondi senza dati la nota inizia sempre con questa frase: è già detto dalla riga in grigio.
const NOTA_SENZA_SCHEDA = /^Nessuna scheda Ciao Elsa fornita\.\s*/;

function avvisiFondo(f) {
  const out = [];
  const nota = f.has_dati ? f.note : f.note?.replace(NOTA_SENZA_SCHEDA, "");
  if (nota) out.push(nota);
  for (const k of f.flag_anomalia) if (k !== "senza_dati") out.push(flagFondo(k));
  return out;
}
function badge(testi) {
  if (!testi.length) return "";
  const t = esc(testi.join(" · "));
  return `<span class="warn" role="img" data-spiega="${t}" aria-label="Attenzione: ${t}">⚠️</span>`;
}

// ---------------------------------------------------------------- caricamento
async function carica() {
  try {
    const [fondi, comparti, meta, regole, longevita, glossario, prestazioni] = await Promise.all(
      ["fondi", "comparti", "meta", "regole", "longevita", "glossario", "prestazioni"].map((n) =>
        fetch(`data/${n}.json`, { cache: "no-cache" }).then((r) => {
          if (!r.ok) throw new Error(`${n}.json: HTTP ${r.status}`);
          return r.json();
        })
      )
    );
    Object.assign(STATO, {
      fondi, comparti, meta, regole, longevita, glossario,
      perId: new Map(fondi.map((f) => [f.id, f])), perTermine: new Map(glossario.map((g) => [g.id, g])),
      prestazioni: new Map(prestazioni.map((p) => [p.fondo_id, p])),
    });
    STATO.documenti = await caricaDocumenti();
  } catch (e) {
    const el = document.getElementById("errore-caricamento");
    el.hidden = false;
    el.textContent = `Impossibile caricare i dati (${e.message}). Esegui "python scripts/export_xlsx.py" e servi la cartella docs/ con un server HTTP (es. python -m http.server -d docs).`;
    return;
  }
  renderKpi();
  initTabella();
  initGrafico();
  renderCategorie();
  initRegole();
  initLongevita();
  initPrestazioni();
  initGlossario();
  renderQualita();
  renderFooter();
  initDettaglio();
  initSuggerimenti();
}

// ---------------------------------------------------------------- KPI
function renderKpi() {
  const c = STATO.meta.conteggi;
  const kpi = (v, l) => `<div class="kpi"><div class="v">${v}</div><div class="l">${l}</div></div>`;
  document.getElementById("kpis").innerHTML =
    kpi(c.fondi, `${termine("fondo-pensione-aperto", "fondi pensione aperti")} nell'${termine("albo-covip", "elenco COVIP")}`) +
    kpi(c.fondi_con_dati, `con dati di dettaglio (${pct(c.fondi_con_dati / c.fondi, 0)})`) +
    kpi(c.comparti, `comparti, di cui ${c.comparti_10_anni} con rendimento a 10 anni`) +
    kpi(c.comparti_con_anomalie, '<a href="#qualita">comparti con anomalie o dati non confrontabili</a>');
}

// ---------------------------------------------------------------- tabella fondi
// glossario: voce mostrata al passaggio del mouse sull'intestazione; spiega: cosa mostra la colonna in questa tabella
const COLONNE = [
  { key: "nome_breve", label: "Fondo", tipo: "txt", glossario: "fondo-pensione-aperto",
    html: (f) => `<button type="button" class="fondo-btn" data-fondo="${esc(f.id)}">${esc(f.nome_breve)}</button>${badge(avvisiFondo(f))}<span class="sub">${esc(f.societa ?? "Nessuna scheda")}</span>` },
  { key: "spese_adesione", label: "Adesione", glossario: "spese-adesione", num: true, html: (f) => eur(f.spese_adesione) },
  { key: "spese_annue", label: "Spese annue", glossario: "spese-annue", num: true, html: (f) => eur(f.spese_annue) },
  { key: "costo_pct_versato", label: "% sul versato", glossario: "costo-versato", num: true, html: (f) => pct(f.costo_pct_versato, 1) },
  { key: "n_comparti", label: "Comparti", glossario: "comparto", spiega: "Qui: i comparti presenti nei dati. L'etichetta gialla indica quante linee dichiara Ciao Elsa, quando sono di più o di meno.", num: true,
    html: (f) => (f.has_dati ? `${f.n_comparti}${f.n_linee != null && f.n_linee !== f.n_comparti ? ` <span class="tag tag-warn" data-spiega="Linee dichiarate da Ciao Elsa: non coincidono con i comparti presenti nei dati.">${f.n_linee} dichiarate</span>` : ""}` : NA) },
  { key: "comm_min", label: "Commissione", glossario: "commissione-gestione", spiega: "Qui: dal comparto più economico al più caro del fondo.", num: true,
    html: (f) => (f.comm_min == null ? NA : f.comm_min === f.comm_max ? pct(f.comm_min) : `${pct(f.comm_min)} – ${pct(f.comm_max)}`) },
  { key: "max_azioni", label: "Max % azioni", glossario: "asset-allocation", spiega: "Qui: la quota di azioni del comparto più azionario del fondo, cioè il rischio più alto che puoi scegliere.", num: true,
    html: (f) => pct(f.max_azioni, 0) + (f.flag_anomalia.includes("comparti_anomali") ? badge(["Valore probabilmente falsato da un comparto con allocazione anomala"]) : "") },
  { key: "best_rend_10a", label: "Miglior rend. 10 anni", glossario: "rendimento-netto", spiega: "Qui: il rendimento a 10 anni più alto tra i comparti del fondo.", num: true, html: (f) => rend(f.best_rend_10a) },
  { key: null, label: "Caratteristiche", spiega: "Linee ESG, percorso life cycle e sottoscrizione online, secondo Ciao Elsa: passa sulle etichette per la spiegazione. Si filtrano con i pulsanti sopra la tabella.",
    html: caratteristiche },
  { key: null, label: "Fonti", glossario: "ciao-elsa", spiega: "Sito: la pagina ufficiale del fondo. Scheda: la scheda di Ciao Elsa da cui vengono i dati di dettaglio.",
    html: (f) => `<span class="links">${f.url ? `<a href="${esc(f.url)}" rel="noopener" target="_blank">Sito<span class="sr-only"> di ${esc(f.nome_breve)}</span></a>` : ""}${f.scheda_url ? `<a href="${esc(f.scheda_url)}" rel="noopener" target="_blank">Scheda<span class="sr-only"> Ciao Elsa di ${esc(f.nome_breve)}</span></a>` : ""}</span>` },
];
const attrSpiegazione = (c) => `${c.glossario ? ` data-glossario="${c.glossario}"` : ""}${c.spiega ? ` data-spiega="${esc(c.spiega)}"` : ""}`;

// ESG, life cycle e online in una sola colonna di etichette: la tabella resta abbastanza stretta da non scorrere su desktop
function caratteristiche(f) {
  if (!f.has_dati) return NA;
  const tag = (testo, voce, classe = "tag-on") => `<span class="tag ${classe}" data-glossario="${voce}">${testo}</span>`;
  const out = [];
  if (f.esg === "Sì") out.push(tag("ESG", "esg"));
  if (f.life_cycle === "Sì") out.push(tag("Life cycle", "life-cycle"));
  if (f.online === "Sì (Ciao Elsa)") out.push(tag("Online", "sottoscrizione-online"));
  else if (f.online === "No (lista d'attesa)") out.push(tag("Online: lista d'attesa", "sottoscrizione-online", "tag-off"));
  return out.length ? `<span class="tags">${out.join("")}</span>` : '<span class="na">—</span>';
}

// Se la tabella è più larga del contenitore, il contenitore prende un'altezza massima: così la barra
// orizzontale resta a portata di mano (non solo in fondo alle 38 righe), con intestazione e prima colonna fisse.
function aggiornaScorrimento() {
  const box = document.querySelector("#fondi .table-scroll");
  const tab = document.getElementById("tab-fondi");
  box.classList.toggle("scorre", tab.scrollWidth > box.clientWidth + 1);
}

function initTabella() {
  const tr = document.querySelector("#tab-fondi thead tr");
  tr.innerHTML = COLONNE.map((c) =>
    `<th scope="col" class="${c.num ? "num" : ""}" ${c.key ? `data-key="${c.key}" aria-sort="none"` : ""}${attrSpiegazione(c)}>${c.key ? `<button type="button" class="sort">${c.label}</button>` : c.label}</th>`
  ).join("");
  new ResizeObserver(aggiornaScorrimento).observe(document.querySelector("#fondi .table-scroll"));
  tr.addEventListener("click", (e) => {
    const th = e.target.closest("th[data-key]");
    if (!th) return;
    const key = th.dataset.key;
    const col = COLONNE.find((c) => c.key === key);
    STATO.sort = STATO.sort.key === key
      ? { key, dir: STATO.sort.dir === "asc" ? "desc" : "asc" }
      : { key, dir: col.num && key === "best_rend_10a" ? "desc" : "asc" };
    renderTabella();
  });
  const bind = (id, k, ev = "change", prop = "checked") =>
    document.getElementById(id).addEventListener(ev, (e) => { STATO.filtri[k] = e.target[prop]; renderTabella(); });
  bind("q", "q", "input", "value");
  bind("f-dati", "dati"); bind("f-esg", "esg"); bind("f-lc", "lc"); bind("f-online", "online");
  document.querySelector("#tab-fondi tbody").addEventListener("click", (e) => {
    const b = e.target.closest("[data-fondo]");
    if (b) apriFondo(b.dataset.fondo);
  });
  renderTabella();
}

function confronta(a, b, key, dir) {
  const va = a[key], vb = b[key];
  if (va == null && vb == null) return a.nome_breve.localeCompare(b.nome_breve, "it");
  if (va == null) return 1;   // vuoti sempre in fondo
  if (vb == null) return -1;
  const r = typeof va === "string" ? va.localeCompare(vb, "it") : va - vb;
  return (dir === "asc" ? r : -r) || a.nome_breve.localeCompare(b.nome_breve, "it");
}

function renderTabella() {
  const { q, dati, esg, lc, online } = STATO.filtri;
  const ago = q.trim().toLowerCase();
  const righe = STATO.fondi.filter((f) =>
    (!dati || f.has_dati) && (!esg || f.esg === "Sì") && (!lc || f.life_cycle === "Sì") &&
    (!online || f.online === "Sì (Ciao Elsa)") &&
    (!ago || [f.nome_breve, f.denominazione, f.societa].some((s) => s && s.toLowerCase().includes(ago)))
  ).sort((a, b) => confronta(a, b, STATO.sort.key, STATO.sort.dir));

  document.querySelectorAll("#tab-fondi th[data-key]").forEach((th) => {
    th.setAttribute("aria-sort", th.dataset.key === STATO.sort.key ? (STATO.sort.dir === "asc" ? "ascending" : "descending") : "none");
  });
  document.querySelector("#tab-fondi tbody").innerHTML = righe.length
    ? righe.map((f) => `<tr class="${f.has_dati ? "" : "senza-dati"}">${COLONNE.map((c, i) =>
        i === 0 ? `<th scope="row">${c.html(f)}</th>` : `<td class="${c.num ? "num" : ""}">${c.html(f)}</td>`).join("")}</tr>`).join("")
    : `<tr><td colspan="${COLONNE.length}">Nessun fondo corrisponde ai filtri.</td></tr>`;
  document.getElementById("conteggio").textContent = `${righe.length} di ${STATO.fondi.length} fondi`;
  aggiornaScorrimento();
}

// ---------------------------------------------------------------- dettaglio fondo
function allocazione(c) {
  if (c.azioni == null && c.obbligazioni == null) return NA;
  const a = c.azioni ?? 0, o = c.obbligazioni ?? 0;
  const parti = [];
  if (a > 0) parti.push(`<span class="a" style="flex:${a}"></span>`);
  if (o > 0) parti.push(`<span class="o" style="flex:${o}"></span>`);
  return `<div class="alloc-lbl">${pct(c.azioni, 0)} azioni · ${pct(c.obbligazioni, 0)} obblig.</div>
    <div class="alloc" role="img" aria-label="${esc(pctTxt(a, 1))} azioni, ${esc(pctTxt(o, 1))} obbligazioni">${parti.join("")}</div>`;
}

function rendConPeriodo(c) {
  if (c.rendimento == null) return NA;
  const tag = c.periodo_anni === 10 ? `<span class="tag">10 anni</span>`
    : `<span class="tag tag-warn" data-spiega="Rendimento medio su ${c.periodo_anni} anni: copre un periodo di mercato diverso e non si confronta con quelli a 10 anni.">${c.periodo_anni} anni</span>`;
  return `${rend(c.rendimento)}<br>${tag}`;
}

function apriFondo(id, aggiornaHash = true) {
  const f = STATO.perId.get(id);
  if (!f) return;
  const dlg = document.getElementById("dettaglio");
  document.getElementById("d-titolo").innerHTML = `${esc(f.nome_breve)}<span class="sub">${esc(f.denominazione)}</span>`;
  const comp = compartiDi(id);
  const avvisi = avvisiFondo(f);
  const fact = (l, v, voce) => `<div class="fact"><div class="l">${voce ? termine(voce, l) : l}</div><div class="v">${v}</div></div>`;
  const link = [
    f.url && `<a href="${esc(f.url)}" rel="noopener" target="_blank">Pagina informativa del fondo ↗</a>`,
    f.scheda_url && `<a href="${esc(f.scheda_url)}" rel="noopener" target="_blank">Scheda Ciao Elsa (fonte) ↗</a>`,
  ].filter(Boolean).join(" · ");

  let html = `<p>${f.societa ? `Società: <strong>${esc(f.societa)}</strong> · ` : ""}${link}</p>`;
  if (avvisi.length) html += `<div class="note-box"><strong>⚠️ Note e anomalie</strong><ul>${avvisi.map((a) => `<li>${esc(a)}</li>`).join("")}</ul></div>`;
  if (!f.has_dati) {
    html += `<p>Per questo fondo non ci sono ancora dati di dettaglio. Consulta la Nota informativa sul sito del gestore.</p>`;
  } else {
    html += `<div class="facts">
      ${fact("Spese di adesione", eur(f.spese_adesione), "spese-adesione")}
      ${fact("Spese annue fisse", eur(f.spese_annue), "spese-annue")}
      ${fact("Costo % sul versato", pct(f.costo_pct_versato, 1), "costo-versato")}
      ${fact("ESG", esc(f.esg ?? "—"), "esg")}
      ${fact("Life cycle", esc(f.life_cycle ?? "—"), "life-cycle")}
      ${fact("Sottoscrizione online", esc(f.online ?? "—"), "sottoscrizione-online")}
    </div>
    <h3>Comparti (${comp.length}${f.n_linee != null && f.n_linee !== comp.length ? `; Ciao Elsa ne dichiara ${f.n_linee}` : ""})</h3>
    <div class="table-scroll"><table class="data">
      <caption class="sr-only">Comparti di ${esc(f.nome_breve)}</caption>
      <thead><tr><th scope="col" data-glossario="comparto">Comparto</th>
        <th scope="col" data-spiega="Categoria dichiarata da Ciao Elsa: passa sull'etichetta del comparto per la spiegazione.">Categoria</th>
        <th scope="col" data-glossario="asset-allocation">Asset allocation</th>
        <th scope="col" class="num" data-glossario="rendimento-netto">Rendimento netto<br>medio annuo</th>
        <th scope="col" class="num" data-glossario="commissione-gestione">Commissione<br>di gestione</th><th scope="col">Note</th></tr></thead>
      <tbody>${comp.map((c) => {
        const note = [...c.flag_anomalia.map((k) => `⚠️ ${esc(flagComparto(k))}`), c.note && esc(c.note)].filter(Boolean);
        return `<tr><th scope="row">${esc(c.comparto)}</th><td>${tagCat(c.categoria)}</td><td>${allocazione(c)}</td>
          <td class="num">${rendConPeriodo(c)}</td><td class="num">${pct(c.commissione)}</td>
          <td class="cell-note">${note.join("<br>") || ""}</td></tr>`;
      }).join("")}</tbody>
    </table></div>`;
  }
  html += prestazioniFondo(f) + daVerificare(f) + documentiFondo(f);
  document.getElementById("d-body").innerHTML = html;
  if (!dlg.open) dlg.showModal();
  dlg.scrollTop = 0;
  if (aggiornaHash) history.replaceState(null, "", `#fondo=${encodeURIComponent(id)}`);
}

// Cosa verificare nei documenti del singolo fondo su pensione e decesso: le voci vengono dalle regole
// che dipendono dal fondo (foglio Regole), così restano allineate all'Excel.
function daVerificare(f) {
  const voci = STATO.regole.filter((r) => ["Alla pensione", "In caso di decesso"].includes(r.tema) && r.uguale_per_tutti !== "Sì");
  if (!voci.length) return "";
  const sito = f.url ? ` sul <a href="${esc(f.url)}" rel="noopener" target="_blank">sito del fondo ↗</a>` : "";
  return `<h3 class="d-sez">Alla pensione e in caso di decesso</h3>
    <p class="hint">Le regole generali valgono per tutti i fondi (<a href="#regole">vedi Regole</a>). Per questo fondo
      verifica nel <strong>${termine("documento-rendite", "Documento sulle rendite")}</strong> e nel
      <strong>${termine("supplemento-nota", "Supplemento alla Nota informativa")}</strong>${sito}:</p>
    <ul class="verifica">${voci.map((r) => `<li><strong>${titoloConGlossario(r.titolo)}</strong>: ${esc(r.varia)}</li>`).join("")}</ul>`;
}

// Il titolo breve di una regola diventa un termine del glossario se c'è una voce con lo stesso nome (es. "Rendita vitalizia")
function titoloConGlossario(titolo) {
  const voce = STATO.glossario.find((g) => normalizza(g.termine) === normalizza(titolo));
  return voce ? termine(esc(voce.id), esc(titolo)) : esc(titolo);
}

// ---------------------------------------------------------------- documenti ufficiali
// data/documenti.json è facoltativo: se manca, la dashboard funziona lo stesso senza la sezione documenti.
async function caricaDocumenti() {
  try {
    const r = await fetch("data/documenti.json", { cache: "no-cache" });
    if (!r.ok) return null;
    const d = await r.json();
    return { ...d, tipi: new Map(d.tipi.map((t) => [t.id, t])), perFondo: new Map(d.fondi.map((x) => [x.fondo_id, x])) };
  } catch {
    return null;
  }
}

const dimensione = (b) => (b >= 1048576 ? `${NF1.format(b / 1048576)} MB` : `${NF0.format(Math.max(1, Math.round(b / 1024)))} KB`);

function coperturaDocumenti() {
  const t = STATO.documenti?.totali;
  if (!t) return "";
  return `<p class="hint">Documenti ufficiali: ${t.scaricati} PDF per ${t.fondi_con_documenti} fondi su ${t.fondi}
    (${t.scaricati_referenziati} dei ${t.referenziati} citati nelle pagine informative), nel dettaglio di ogni fondo e nell'<a
    href="https://github.com/andreagalle/goodbye-elsa/tree/master/docs/documenti" rel="noopener" target="_blank">elenco completo ↗</a>.</p>`;
}

// Copie dei PDF scaricate dal sito del gestore, con il link all'originale (fa fede quello)
function documentiFondo(f) {
  const d = STATO.documenti?.perFondo.get(f.id);
  if (!d?.documenti.length) return "";
  const date = d.documenti.map((x) => x.scaricato_il).filter(Boolean).sort();
  const quando = date.length ? ` il ${dataIt(date[date.length - 1])}` : "";
  const conteggio = d.referenziati
    ? `Scaricati ${d.scaricati_referenziati} dei ${d.referenziati} documenti citati nella pagina informativa del fondo${d.scaricati > d.scaricati_referenziati ? `, più ${d.scaricati - d.scaricati_referenziati} trovati in altre pagine del gestore` : ""}.`
    : "La pagina informativa del fondo non elenca documenti: queste copie vengono da altre pagine del gestore.";
  const voci = d.documenti.map((x) => {
    const tipo = STATO.documenti.tipi.get(x.tipo);
    const originale = x.url ? `<a href="${esc(x.url)}" rel="noopener" target="_blank" data-spiega="Il documento sul sito del gestore: se è stato aggiornato, fa fede questo.">originale ↗</a>` : "";
    if (!x.file) return `<li><span data-spiega="${esc(tipo?.descrizione ?? "")}">${esc(x.titolo)}</span> <span class="doc-meta">· non scaricato: ${esc(x.note ?? "")}${originale ? ` · ${originale}` : ""}</span></li>`;
    return `<li><a href="${esc(x.file)}" target="_blank" rel="noopener" data-spiega="${esc(tipo?.descrizione ?? "")}">${esc(x.titolo)}</a>
      <span class="doc-meta">· PDF, ${x.pagine ?? "?"} pag., ${dimensione(x.byte)} · ${originale}</span></li>`;
  }).join("");
  return `<h3 class="d-sez">Documenti ufficiali (${d.scaricati})</h3>
    <p class="hint">Copie scaricate dal sito del gestore${esc(quando)}, per consultarle anche qui. ${esc(conteggio)} Fa fede la versione
      pubblicata dal gestore (link “originale”).</p>
    <ul class="documenti">${voci}</ul>`;
}

function initDettaglio() {
  const dlg = document.getElementById("dettaglio");
  document.getElementById("d-chiudi").addEventListener("click", () => dlg.close());
  // un link interno (es. "vedi Regole") chiude la finestra e porta alla sezione
  dlg.addEventListener("click", (e) => { if (e.target.closest('a[href^="#"]')) dlg.close(); });
  dlg.addEventListener("click", (e) => { if (e.target === dlg) dlg.close(); });
  dlg.addEventListener("close", () => {
    if (location.hash.startsWith("#fondo=")) history.replaceState(null, "", location.pathname + location.search);
  });
  document.body.addEventListener("click", (e) => {
    const b = e.target.closest(".linkish[data-fondo]");
    if (b) apriFondo(b.dataset.fondo);
  });
  const daHash = () => {
    const m = location.hash.match(/^#fondo=(.+)$/);
    if (m) apriFondo(decodeURIComponent(m[1]), false);
  };
  window.addEventListener("hashchange", daHash);
  daHash();
}

// ---------------------------------------------------------------- grafico commissione vs rendimento
function puntiGrafico() {
  return STATO.comparti.filter((c) =>
    c.rendimento != null && c.commissione != null && (c.periodo_anni === 10 || STATO.includiPeriodi));
}

function initGrafico() {
  const sel = document.getElementById("g-fondo");
  const conDati = STATO.fondi.filter((f) => f.n_comparti > 0).sort((a, b) => a.nome_breve.localeCompare(b.nome_breve, "it"));
  sel.insertAdjacentHTML("beforeend", conDati.map((f) => `<option value="${esc(f.id)}">${esc(f.nome_breve)}</option>`).join(""));
  sel.addEventListener("change", () => { STATO.evidenzia = sel.value; STATO.grafico?.update(); });
  document.getElementById("g-periodi").addEventListener("change", (e) => { STATO.includiPeriodi = e.target.checked; disegnaGrafico(); });
  window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", disegnaGrafico);
  disegnaGrafico();
  // Ridisegna con il font definitivo (Inter) appena è caricato
  document.fonts?.ready.then(() => STATO.grafico && disegnaGrafico());
}

function legendaGrafico() {
  const el = document.getElementById("g-legend");
  el.innerHTML = Object.entries(GRUPPI).map(([k, g]) =>
    `<button type="button" data-gruppo="${k}" data-glossario="${k.toLowerCase()}" aria-pressed="${!STATO.nascosti.has(k)}">${sw(k)}${g.label}</button>`).join("") +
    (STATO.includiPeriodi ? `<span class="chk"><span class="hollow" aria-hidden="true"></span>Simbolo vuoto: rendimento a 3 o 5 anni</span>` : "");
  el.onclick = (e) => {
    const b = e.target.closest("[data-gruppo]");
    if (!b) return;
    const k = b.dataset.gruppo;
    STATO.nascosti.has(k) ? STATO.nascosti.delete(k) : STATO.nascosti.add(k);
    disegnaGrafico();
  };
}

function disegnaGrafico() {
  if (!window.Chart) {
    document.getElementById("g-nota").textContent = "Impossibile caricare la libreria dei grafici (Chart.js).";
    return;
  }
  legendaGrafico();
  const punti = puntiGrafico();
  const surface = css("--surface"), grid = css("--grid"), axis = css("--axis"), ink2 = css("--ink-2"), muted = css("--muted");
  const sbiadito = (hex) => hex + "40"; // 25% di opacità per i fondi non evidenziati

  const datasets = Object.entries(GRUPPI).map(([k, g]) => {
    const colore = css(g.var);
    const data = punti.filter((c) => gruppo(c.categoria) === k).map((c) => ({ x: c.commissione, y: c.rendimento, c }));
    const attivo = (ctx) => !STATO.evidenzia || ctx.raw?.c.fondo_id === STATO.evidenzia;
    const pieno = (ctx) => ctx.raw?.c.periodo_anni === 10;
    return {
      label: g.label, data, hidden: STATO.nascosti.has(k), pointStyle: g.punto,
      backgroundColor: (ctx) => (pieno(ctx) ? (attivo(ctx) ? colore : sbiadito(colore)) : surface),
      borderColor: (ctx) => (pieno(ctx) ? surface : attivo(ctx) ? colore : sbiadito(colore)),
      borderWidth: (ctx) => (pieno(ctx) ? 1.5 : 2),
      pointRadius: (ctx) => (STATO.evidenzia && attivo(ctx) ? 8 : 5.5),
      pointHoverRadius: 8, pointHitRadius: 8,
      order: k === "GAR" ? 0 : 1,
    };
  });

  const nonDieci = punti.filter((c) => c.periodo_anni !== 10).length;
  const esclusi = STATO.comparti.filter((c) => c.rendimento == null || c.commissione == null).length;
  document.getElementById("g-nota").textContent =
    `${punti.length} comparti nel grafico` +
    (nonDieci ? `, di cui ${nonDieci} con rendimento a 3 o 5 anni (simbolo vuoto)` : "") +
    (esclusi ? `. ${esclusi === 1 ? "1 comparto escluso" : `${esclusi} comparti esclusi`} perché manca il rendimento o la commissione.` : ".") +
    " Clicca un punto per aprire il fondo.";

  Chart.defaults.font.family = css("--font");
  STATO.grafico?.destroy();
  STATO.grafico = new Chart(document.getElementById("scatter"), {
    type: "scatter",
    data: { datasets },
    options: {
      responsive: true, maintainAspectRatio: false, animation: false,
      layout: { padding: 4 },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: css("--surface"), titleColor: css("--ink"), bodyColor: ink2,
          borderColor: axis, borderWidth: 1, padding: 10, usePointStyle: true,
          callbacks: {
            title: (items) => STATO.perId.get(items[0].raw.c.fondo_id)?.nome_breve ?? "",
            label: (item) => {
              const c = item.raw.c;
              return [
                `${c.comparto} (${c.categoria})`,
                `Commissione: ${pctTxt(c.commissione)}`,
                `Rendimento: ${pctTxt(c.rendimento)} medio annuo a ${c.periodo_anni} anni${c.periodo_anni !== 10 ? " ⚠️" : ""}`,
                ...(c.flag_anomalia.some((f) => f !== "periodo_non_10") ? ["⚠️ Dati con anomalie: vedi il dettaglio"] : []),
              ];
            },
          },
        },
      },
      scales: {
        x: {
          title: { display: true, text: "Commissione di gestione annua", color: ink2 },
          ticks: { color: muted, callback: (v) => pctTxt(v, 1) },
          grid: { color: grid }, border: { color: axis },
        },
        y: {
          title: { display: true, text: "Rendimento netto medio annuo", color: ink2 },
          ticks: { color: muted, callback: (v) => pctTxt(v, 1) },
          grid: { color: (ctx) => (ctx.tick.value === 0 ? axis : grid), lineWidth: (ctx) => (ctx.tick.value === 0 ? 1.5 : 1) },
          border: { display: false },
        },
      },
      onClick: (_e, els) => {
        if (els.length) apriFondo(datasets[els[0].datasetIndex].data[els[0].index].c.fondo_id);
      },
      onHover: (e, els) => { e.native.target.style.cursor = els.length ? "pointer" : "default"; },
    },
  });
}

// ---------------------------------------------------------------- confronto per categoria
function mediana(xs) {
  if (!xs.length) return null;
  const s = [...xs].sort((a, b) => a - b), m = s.length >> 1;
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
}

function renderCategorie() {
  const voce = (c, val) => {
    const f = STATO.perId.get(c.fondo_id);
    const warn = c.flag_anomalia.length ? badge(c.flag_anomalia.map(flagComparto)) : "";
    return `<li><button type="button" class="linkish" data-fondo="${esc(f.id)}">${esc(f.nome_breve)}</button> – ${esc(c.comparto)}: <span class="val">${val}</span>${warn}</li>`;
  };
  const lista = (titolo, arr, val) => (arr.length ? `<h4>${titolo}</h4><ol>${arr.map((c) => voce(c, val(c))).join("")}</ol>` : "");

  document.getElementById("cat-cards").innerHTML = Object.entries(GRUPPI).map(([k, g]) => {
    const tutti = STATO.comparti.filter((c) => gruppo(c.categoria) === k);
    const conComm = tutti.filter((c) => c.commissione != null);
    const dieci = tutti.filter((c) => c.periodo_anni === 10 && c.rendimento != null);
    const perComm = [...conComm].sort((a, b) => a.commissione - b.commissione);
    const perRend = [...dieci].sort((a, b) => b.rendimento - a.rendimento);
    const n = Math.min(3, Math.floor(tutti.length / 2)) || 1;
    const mostraPeggiori = tutti.length > 3;
    return `<article class="card">
      <h3>${sw(k)}${termine(k.toLowerCase(), g.label)}</h3>
      <p class="stats">${tutti.length} comparti · commissione <span class="termine" data-spiega="${SPIEGA_MEDIANA}">mediana</span> ${pctTxt(mediana(conComm.map((c) => c.commissione)))}
        · rendimento mediano a 10 anni ${pctTxt(mediana(dieci.map((c) => c.rendimento)))} (${dieci.length} comparti)</p>
      ${lista("Commissione più bassa", perComm.slice(0, n), (c) => pct(c.commissione))}
      ${mostraPeggiori ? lista("Commissione più alta", perComm.slice(-n).reverse(), (c) => pct(c.commissione)) : ""}
      ${lista("Rendimento a 10 anni più alto", perRend.slice(0, n), (c) => rend(c.rendimento))}
      ${mostraPeggiori ? lista("Rendimento a 10 anni più basso", perRend.slice(-n).reverse(), (c) => rend(c.rendimento)) : ""}
    </article>`;
  }).join("");
}

// ---------------------------------------------------------------- regole
const dataBreve = (iso) => new Date(iso).toLocaleDateString("it-IT");

function cardRegola(r, mostraTema) {
  const stato = r.uguale_per_tutti === "Sì"
    ? '<span class="tag">Uguale per tutti i fondi</span>'
    : `<span class="tag tag-on">${r.uguale_per_tutti === "No" ? "Dipende dal fondo" : "In parte dipende dal fondo"}</span>`;
  const vigore = r.in_vigore_dal && r.in_vigore_dal >= "2026-01-01" ? `<span class="tag">dal ${esc(dataBreve(r.in_vigore_dal))}</span>` : "";
  return `<article class="regola" id="regola-${esc(r.id)}">
    ${mostraTema ? `<p class="regola-tema">${esc(r.tema)}</p>` : ""}
    <h3>${esc(r.domanda)}</h3>
    ${r.valore ? `<p class="regola-valore">${esc(r.valore)}</p>` : ""}
    <p class="regola-testo">${esc(r.regola)}</p>
    ${r.uguale_per_tutti !== "Sì" && r.varia ? `<p class="regola-varia"><strong>Cosa cambia tra i fondi:</strong> ${esc(r.varia)}</p>` : ""}
    ${r.note ? `<p class="regola-nota">${esc(r.note)}</p>` : ""}
    <p class="regola-piede">${stato}${vigore}<a href="${esc(r.fonte_url)}" rel="noopener" target="_blank" data-spiega="Fonte: ${esc(r.fonte_nome)} (consultata il ${esc(dataBreve(r.consultata_il))})">${esc(r.riferimento)} ↗</a></p>
  </article>`;
}

function initRegole() {
  const temi = [...new Set(STATO.regole.map((r) => r.tema))];
  if (!temi.length) return;
  STATO.temaRegole = temi[0];
  const box = document.getElementById("r-temi");
  const pulsanti = [...temi, "Tutte"];
  box.innerHTML = pulsanti.map((t) => {
    const n = t === "Tutte" ? STATO.regole.length : STATO.regole.filter((r) => r.tema === t).length;
    return `<button type="button" class="pill" data-tema="${esc(t)}" aria-pressed="false">${esc(t)}<span class="n">${n}</span></button>`;
  }).join("");
  box.addEventListener("click", (e) => {
    const b = e.target.closest("[data-tema]");
    if (!b) return;
    STATO.temaRegole = b.dataset.tema;
    renderRegole();
  });
  document.getElementById("r-varia").addEventListener("change", (e) => { STATO.soloVaria = e.target.checked; renderRegole(); });
  renderRegole();
}

function renderRegole() {
  const tutte = STATO.temaRegole === "Tutte";
  const lista = STATO.regole.filter((r) =>
    (tutte || r.tema === STATO.temaRegole) && (!STATO.soloVaria || r.uguale_per_tutti !== "Sì"));
  document.querySelectorAll("#r-temi [data-tema]").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.tema === STATO.temaRegole)));
  document.getElementById("r-lista").innerHTML = lista.length
    ? lista.map((r) => cardRegola(r, tutte)).join("")
    : '<p class="hint">In questo tema tutte le regole sono uguali per tutti i fondi.</p>';
}

// ---------------------------------------------------------------- longevità (tavole ISTAT)
function initLongevita() {
  const L = STATO.longevita;
  if (!L || !L.serie) return;
  const s = L.sintesi, dd = L.durata_definita;
  const anni = (v) => NF1.format(v);
  const kpi = (v, l) => `<div class="kpi"><div class="v">${v}</div><div class="l">${l}</div></div>`;
  document.getElementById("l-kpi").innerHTML =
    kpi(`${anni(s.uomini.speranza)} · ${anni(s.donne.speranza)}`, `anni di ${termine("speranza-vita", "vita attesa")} a ${L.eta_partenza} anni (uomini · donne): è una media`) +
    kpi(`${s.uomini.eta_50_vivi} · ${s.donne.eta_50_vivi}`, `l'età che supera metà dei ${L.eta_partenza}enni (uomini · donne)`) +
    kpi(`${s.uomini.eta_10_vivi} · ${s.donne.eta_10_vivi}`, "l'età che supera uno su dieci (uomini · donne)") +
    kpi(pct(dd.vivi_a_fine.totale, 0), `è ancora vivo a ${dd.eta_fine} anni, quando finisce una ${termine("rendita-durata-definita", "rendita a durata definita")} iniziata a ${dd.eta_inizio} (${dd.anni} anni)`);
  document.getElementById("l-legend").innerHTML =
    '<span class="voce"><span class="linea" style="background:var(--cat-azn)"></span>Uomini</span>' +
    '<span class="voce"><span class="linea" style="background:var(--cat-bil)"></span>Donne</span>' +
    `<span class="voce"><span class="linea tratteggio"></span>Fine della rendita a durata definita (${dd.eta_fine} anni)</span>`;
  const f = L.fonte;
  document.getElementById("l-nota").innerHTML =
    `Fonte: <a href="${esc(f.url)}" rel="noopener" target="_blank">${esc(f.nome)}</a>, consultata il ${esc(dataBreve(f.consultata_il))}. ` +
    "Sono medie della popolazione italiana: la tua prospettiva dipende da salute e stile di vita. La durata della rendita a durata definita la fissa la tavola ISTAT usata per i coefficienti di trasformazione in vigore; qui è stimata con la tavola 2025.";
  disegnaLongevita();
  window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", disegnaLongevita);
  document.fonts?.ready.then(() => STATO.graficoLongevita && disegnaLongevita());
}

function disegnaLongevita() {
  if (!window.Chart) return;
  const L = STATO.longevita, dd = L.durata_definita;
  const grid = css("--grid"), axis = css("--axis"), ink2 = css("--ink-2"), muted = css("--muted");
  const serie = (sesso, colore, label) => ({
    label, data: L.serie[sesso].map((p) => ({ x: p.eta, y: p.vivi * 100 })),
    borderColor: colore, backgroundColor: colore, borderWidth: 2, pointRadius: 0, pointHoverRadius: 5, tension: 0.15,
  });
  // linea verticale tratteggiata alla fine della rendita a durata definita
  const fineRendita = {
    id: "fineRendita",
    afterDatasetsDraw(chart) {
      const { ctx, chartArea: a, scales: { x } } = chart;
      const px = x.getPixelForValue(dd.eta_fine);
      ctx.save();
      ctx.strokeStyle = ink2; ctx.lineWidth = 1.5; ctx.setLineDash([5, 4]);
      ctx.beginPath(); ctx.moveTo(px, a.top); ctx.lineTo(px, a.bottom); ctx.stroke();
      ctx.restore();
    },
  };
  STATO.graficoLongevita?.destroy();
  STATO.graficoLongevita = new Chart(document.getElementById("longevita"), {
    type: "line",
    data: { datasets: [serie("uomini", css("--cat-azn"), "Uomini"), serie("donne", css("--cat-bil"), "Donne")] },
    plugins: [fineRendita],
    options: {
      responsive: true, maintainAspectRatio: false, animation: false,
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: css("--surface"), titleColor: css("--ink"), bodyColor: ink2, borderColor: axis, borderWidth: 1, padding: 10,
          callbacks: {
            title: (items) => `A ${items[0].parsed.x} anni`,
            label: (item) => `${item.dataset.label}: ${NF0.format(item.parsed.y)}% ancora in vita`,
          },
        },
      },
      scales: {
        x: {
          type: "linear", min: L.eta_partenza, max: L.serie.totale.at(-1).eta,
          title: { display: true, text: "Età", color: ink2 },
          ticks: { color: muted, stepSize: 5 }, grid: { color: grid }, border: { color: axis },
        },
        y: {
          min: 0, max: 100,
          title: { display: true, text: `% dei ${L.eta_partenza}enni ancora in vita`, color: ink2 },
          ticks: { color: muted, stepSize: 25, callback: (v) => `${v}%` }, grid: { color: grid }, border: { display: false },
        },
      },
    },
  });
}

// ---------------------------------------------------------------- glossario (foglio Glossario → glossario.json)
// ---------------------------------------------------------------- alla pensione, fondo per fondo (foglio Prestazioni)
const VARIANTI = [   // [campo di prestazioni.json, etichetta, voce del glossario]
  ["reversibile", "Reversibile", "rendita-reversibile"],
  ["certa", "Certa e poi vitalizia", "rendita-certa"],
  ["controassicurata", "Controassicurata", "rendita-controassicurata"],
  ["ltc", "LTC", "ltc"],
];
const SPIEGA_RENDITA_67 = "Qui: la rendita annua iniziale, prima delle tasse, che il fondo paga a chi la chiede a 67 anni con 10.000 € di capitale (rata annuale, per chi è nato intorno al 1959 e ha aderito dopo il 2012). Con 100.000 € è dieci volte tanto. Conta il coefficiente in vigore quando chiedi la rendita.";
const SPIEGA_COSTO_RENDITA = "Caricamento: la parte che la compagnia trattiene per pagare la rendita, già compresa nel coefficiente. È quella con la rata annuale: con rate più frequenti (es. mensili) di solito è più alta.";
const SPIEGA_COSTI_OP = "Spesa fissa trattenuta dalla posizione per ogni operazione, dalla Scheda costi del fondo. «nessuna» = non prevista; — = non trovata nei documenti.";
const offerta = (v) => Boolean(v && v.startsWith("Sì"));
const costoOp = (v) => (v == null ? NA : v === 0 ? "nessuna" : eur(v));
const euroRendita = (v) => (v == null ? NA : `${NF0.format(v)} €`);

// Varianti di rendita vitalizia offerte, come etichette (solo quelle previste; il dettaglio fondo mostra anche le altre)
function variantiTag(p) {
  const note = VARIANTI.filter(([k]) => p.varianti[k] != null);
  if (!note.length) return NA;
  const si = note.filter(([k]) => offerta(p.varianti[k]));
  if (!si.length) return '<span class="na" data-spiega="Il fondo offre solo la rendita vitalizia semplice.">solo vitalizia</span>';
  return `<span class="tags">${si.map(([k, l, voce]) => `<span class="tag tag-on" data-glossario="${voce}" data-spiega="${esc(`Qui: ${p.varianti[k]}`)}">${l}</span>`).join("")}</span>`;
}

const COLONNE_PRESTAZIONI = [
  { label: "Fondo", glossario: "fondo-pensione-aperto",
    html: (f, p) => `<button type="button" class="fondo-btn" data-fondo="${esc(f.id)}">${esc(f.nome_breve)}</button><span class="sub">${esc(p.compagnia ?? "Compagnia non indicata")}</span>` },
  { label: "Rendita a 67 anni<br>ogni 10.000 €", num: true, glossario: "coefficiente-trasformazione", spiega: SPIEGA_RENDITA_67,
    html: (f, p) => euroRendita(p.rendita_67) },
  { label: "Tasso<br>tecnico", num: true, glossario: "tasso-tecnico", html: (f, p) => pct(p.tasso_tecnico, 1) },
  { label: "Costo della<br>rendita", num: true, spiega: SPIEGA_COSTO_RENDITA, html: (f, p) => pct(p.costo_rendita) },
  { label: "Opzioni oltre alla vitalizia", glossario: "rendita-vitalizia", spiega: "Qui: le varianti di rendita vitalizia che il fondo offre. Passa sulle etichette per il dettaglio.", html: (f, p) => variantiTag(p) },
  { label: "Anticipazione", num: true, glossario: "anticipazione", spiega: SPIEGA_COSTI_OP, html: (f, p) => costoOp(p.costi.anticipazione) },
  { label: "Riscatto", num: true, glossario: "riscatto", spiega: SPIEGA_COSTI_OP, html: (f, p) => costoOp(p.costi.riscatto) },
  { label: "Trasferimento", num: true, glossario: "trasferimento", spiega: SPIEGA_COSTI_OP, html: (f, p) => costoOp(p.costi.trasferimento) },
  { label: "Fonte", glossario: "documento-rendite", spiega: "Qui: il documento ufficiale da cui viene la rendita a 67 anni (o, se manca, la Scheda costi). Tutte le fonti sono nel dettaglio del fondo.",
    html: (f, p) => { const d = p.documento_rendite ?? p.scheda_costi ?? p.supplemento; return d ? `<a href="${esc(d.url)}" rel="noopener" target="_blank">${p.documento_rendite ? "Rendite" : p.scheda_costi ? "Costi" : "Supplemento"}<span class="sr-only"> di ${esc(f.nome_breve)}</span></a>` : NA; } },
];

function initPrestazioni() {
  const righe = [...STATO.prestazioni.values()].map((p) => [STATO.perId.get(p.fondo_id), p]).filter(([f]) => f);
  if (!righe.length) return;
  const conRendita = righe.filter(([, p]) => p.rendita_67 != null).sort((a, b) => a[1].rendita_67 - b[1].rendita_67);
  const kpi = (v, l) => `<div class="kpi"><div class="v">${v}</div><div class="l">${l}</div></div>`;
  const c = STATO.meta.conteggi;
  let kpiHtml = kpi(`${righe.length} su ${c.fondi}`, `fondi con i dati sulle prestazioni, presi dai ${termine("documento-rendite", "documenti ufficiali")}`);
  if (conRendita.length > 1) {
    const min = conRendita[0][1].rendita_67, max = conRendita[conRendita.length - 1][1].rendita_67;
    const nomi = (v) => conRendita.filter(([, p]) => p.rendita_67 === v).map(([f]) => esc(f.nome_breve)).join(" e ");
    kpiHtml +=
      kpi(`${euroRendita(min)} – ${euroRendita(max)}`, `la ${termine("rendita-vitalizia", "rendita")} annua a 67 anni ogni 10.000 €, da ${nomi(min)} a ${nomi(max)} (${conRendita.length} fondi confrontabili)`) +
      kpi(euroRendita((max - min) * 10), "l'anno di differenza tra il fondo che paga di più e quello che paga di meno, con 100.000 € di capitale");
  }
  document.getElementById("p-kpi").innerHTML = kpiHtml;
  document.querySelector("#tab-prestazioni thead tr").innerHTML = COLONNE_PRESTAZIONI.map((col) =>
    `<th scope="col"${col.num ? ' class="num"' : ""}${attrSpiegazione(col)}>${col.label}</th>`).join("");
  document.getElementById("p-solo-rendita").addEventListener("change", (e) => { STATO.soloRendita = e.target.checked; renderPrestazioni(); });
  document.querySelector("#tab-prestazioni tbody").addEventListener("click", (e) => {
    const b = e.target.closest("[data-fondo]");
    if (b) apriFondo(b.dataset.fondo);
  });
  const senza = STATO.fondi.filter((f) => !STATO.prestazioni.has(f.id));
  document.getElementById("p-nota").innerHTML =
    `Come leggere la rendita: un ${termine("tasso-tecnico", "tasso tecnico")} più alto dà una prima rata più alta ma rivalutazioni più basse negli anni; ` +
    "le tavole di mortalità più vecchie (IPS55) ipotizzano una vita più breve e quindi rate più alte. I coefficienti possono cambiare fino al momento in cui chiedi la rendita: " +
    "contano quelli in vigore allora, e per chi ha aderito prima del 2013 possono essere diversi. " +
    (senza.length ? `Mancano ancora ${senza.length} fondi, di cui non sono stati trovati i documenti pubblici: ${senza.map((f) => esc(f.nome_breve)).join(", ")}.` : "");
  renderPrestazioni();
}

function renderPrestazioni() {
  const righe = [...STATO.prestazioni.values()]
    .map((p) => [STATO.perId.get(p.fondo_id), p])
    .filter(([f, p]) => f && (!STATO.soloRendita || p.rendita_67 != null))
    .sort(([fa, a], [fb, b]) => (b.rendita_67 ?? -1) - (a.rendita_67 ?? -1) || fa.nome_breve.localeCompare(fb.nome_breve, "it"));
  document.querySelector("#tab-prestazioni tbody").innerHTML = righe.map(([f, p]) =>
    `<tr>${COLONNE_PRESTAZIONI.map((col, i) => (i === 0 ? `<th scope="row">${col.html(f, p)}</th>` : `<td${col.num ? ' class="num"' : ""}>${col.html(f, p)}</td>`)).join("")}</tr>`).join("");
  document.getElementById("p-conteggio").textContent = `${righe.length} fondi`;
}

// Blocco del dettaglio fondo: condizioni alla pensione dai documenti ufficiali, con le fonti
function prestazioniFondo(f) {
  const p = STATO.prestazioni.get(f.id);
  if (!p) return "";
  const fact = (l, v, attr = "") => `<div class="fact"><div class="l"${attr}>${l}</div><div class="v">${v}</div></div>`;
  const varianti = VARIANTI.filter(([k]) => p.varianti[k] != null).map(([k, l, voce]) => {
    const v = p.varianti[k], si = offerta(v);
    const dettaglio = v.replace(/^(Sì|No)\s*/, "").replace(/^\((.*)\)$/, "$1");   // "Sì (5 o 10 anni)" → "5 o 10 anni"
    return `<li class="${si ? "si" : "no"}"><span aria-hidden="true">${si ? "✓" : "✗"}</span> ${termine(voce, l)}${si ? "" : " non prevista"}${dettaglio ? `: ${esc(dettaglio)}` : ""}</li>`;
  }).join("");
  const fonti = [["Documento sulle rendite", p.documento_rendite], ["Scheda costi", p.scheda_costi], ["Supplemento alla Nota informativa", p.supplemento]]
    .filter(([, d]) => d).map(([l, d]) => `<a href="${esc(d.url)}" rel="noopener" target="_blank" data-spiega="${esc(d.titolo)}">${l} ↗</a>`).join(" · ");
  return `<h3 class="d-sez">Alla pensione con questo fondo</h3>
    <div class="facts">
      ${fact("Rendita a 67 anni ogni 10.000 €", p.rendita_67 == null ? NA : `${NF2.format(p.rendita_67)} € l'anno`, ` data-glossario="coefficiente-trasformazione" data-spiega="${esc(SPIEGA_RENDITA_67)}"`)}
      ${fact("Tasso tecnico", pct(p.tasso_tecnico, 1), ' data-glossario="tasso-tecnico"')}
      ${fact("Costo della rendita", pct(p.costo_rendita), ` data-spiega="${esc(SPIEGA_COSTO_RENDITA)}"`)}
      ${fact("Paga la rendita", esc(p.compagnia ?? "—"))}
    </div>
    ${varianti ? `<p class="hint">Oltre alla ${termine("rendita-vitalizia", "rendita vitalizia")} semplice:</p><ul class="varianti">${varianti}</ul>` : ""}
    <div class="facts">
      ${fact(termine("anticipazione", "Anticipazione"), costoOp(p.costi.anticipazione))}
      ${fact(termine("riscatto", "Riscatto"), costoOp(p.costi.riscatto))}
      ${fact(termine("trasferimento", "Trasferimento"), costoOp(p.costi.trasferimento))}
      ${fact(termine("rita", "RITA"), costoOp(p.costi.rita))}
    </div>
    ${p.nuove_prestazioni ? `<p><strong>${termine("rendita-durata-definita", "Rendita a durata definita")} e ${termine("prelievi-liberi", "prelievi")}:</strong> ${esc(p.nuove_prestazioni)}.</p>` : ""}
    ${p.basi ? `<p class="hint">Come è calcolata la rendita: ${esc(p.basi)}.</p>` : ""}
    ${p.note ? `<div class="note-box"><strong>Note</strong><p>${esc(p.note)}</p></div>` : ""}
    <p class="hint">Fonti: ${fonti}${p.consultata_il ? ` (consultate ${articoloData(p.consultata_il)}${esc(dataIt(p.consultata_il))})` : ""}.</p>`;
}

const normalizza = (s) => String(s ?? "").normalize("NFD").replace(/\p{Diacritic}/gu, "").toLowerCase().trim();
const fonteBreve = (nome) => nome.split(" – ")[0];   // come fonte_breve() in export_xlsx.py: "COVIP – Glossario" → "COVIP"

function initGlossario() {
  if (!STATO.glossario.length) return;
  document.getElementById("gl-cerca").addEventListener("input", (e) => { STATO.cercaGlossario = e.target.value; renderGlossario(); });
  renderGlossario();
  // link diretto a una voce (…/#glossario-esg): le voci esistono solo dopo il caricamento
  if (location.hash.startsWith("#glossario-")) document.getElementById(decodeURIComponent(location.hash.slice(1)))?.scrollIntoView();
}

function voceGlossario(g) {
  const fonte = `Fonte: ${g.fonte_nome}, consultata il ${dataBreve(g.consultata_il)}`;
  return `<div class="gl-voce" id="glossario-${esc(g.id)}">
    <dt>${esc(g.termine)}${g.esteso ? ` <span class="esteso">${esc(g.esteso)}</span>` : ""}</dt>
    <dd>${esc(g.definizione)} <a class="gl-fonte" href="${esc(g.fonte_url)}" rel="noopener" target="_blank" data-spiega="${esc(fonte)}">${esc(fonteBreve(g.fonte_nome))}&nbsp;↗</a>
      ${g.note ? `<span class="gl-nota">${esc(g.note)}</span>` : ""}</dd>
  </div>`;
}

function renderGlossario() {
  const q = normalizza(STATO.cercaGlossario);
  const trovate = STATO.glossario.filter((g) => !q || normalizza(`${g.termine} ${g.esteso ?? ""} ${g.definizione}`).includes(q));
  const gruppi = [...new Set(trovate.map((g) => g.gruppo))];
  document.getElementById("gl-lista").innerHTML = trovate.length
    ? gruppi.map((gr) => `<div class="gl-gruppo"><h3>${esc(gr)}</h3>
        <dl>${trovate.filter((g) => g.gruppo === gr).map(voceGlossario).join("")}</dl></div>`).join("")
    : '<p class="hint">Nessun termine trovato: prova con un\'altra parola.</p>';
  document.getElementById("gl-conteggio").textContent =
    q ? `${trovate.length} di ${STATO.glossario.length} termini` : `${STATO.glossario.length} termini`;
}

// ---------------------------------------------------------------- suggerimenti al passaggio del mouse
// data-glossario="<id>" mostra la voce del glossario; data-spiega aggiunge (o è da sola) la spiegazione di quel punto
// della pagina. Mouse: al passaggio. Tastiera: al focus (e Esc per chiudere). Touch: un tocco su un termine che non è
// un pulsante o un link. Un solo elemento role="tooltip", spostato dentro il dettaglio fondo quando serve.
const SUGG = { el: null, bersaglio: null, inArrivo: null, descritto: null, timer: 0, puntatore: "mouse" };
const CON_SUGGERIMENTO = "[data-glossario],[data-spiega]";
const INTERATTIVO = "a, button, input, select, textarea, label, summary";

function contenutoSuggerimento(el) {
  const g = STATO.perTermine.get(el.dataset.glossario);
  const qui = el.dataset.spiega;
  const parti = [];
  if (g) parti.push(`<strong>${esc(g.termine)}${g.esteso ? ` <span class="esteso">· ${esc(g.esteso)}</span>` : ""}</strong>${esc(g.definizione)}`);
  if (qui) parti.push(g ? `<span class="qui">${esc(qui)}</span>` : esc(qui));
  return parti.join("");
}

function mostraSuggerimento(el, focusato = null) {
  const html = contenutoSuggerimento(el);
  if (!html) return;
  nascondiSuggerimento();
  const tip = SUGG.el;
  // il <dialog> aperto sta nel "top layer": il suggerimento deve stare dentro di lui per comparire sopra
  (el.closest("dialog[open]") ?? document.body).append(tip);
  tip.innerHTML = html;
  tip.hidden = false;
  const r = el.getBoundingClientRect(), t = tip.getBoundingClientRect(), m = 8;
  const top = r.top - t.height - m >= m ? r.top - t.height - m : r.bottom + m;
  const left = Math.max(m, Math.min(r.left + r.width / 2 - t.width / 2, innerWidth - t.width - m));
  tip.style.top = `${Math.round(top)}px`;
  tip.style.left = `${Math.round(left)}px`;
  SUGG.bersaglio = el;
  if (focusato) {
    focusato.setAttribute("aria-describedby", tip.id);
    SUGG.descritto = focusato;
  }
}

function nascondiSuggerimento() {
  clearTimeout(SUGG.timer);
  SUGG.inArrivo = null;
  if (!SUGG.el || SUGG.el.hidden) return;
  SUGG.el.hidden = true;
  SUGG.bersaglio = null;
  SUGG.descritto?.removeAttribute("aria-describedby");
  SUGG.descritto = null;
}

function initSuggerimenti() {
  const tip = document.createElement("div");
  Object.assign(tip, { id: "suggerimento", className: "suggerimento", hidden: true });
  tip.setAttribute("role", "tooltip");
  document.body.append(tip);
  SUGG.el = tip;

  document.addEventListener("pointerdown", (e) => { SUGG.puntatore = e.pointerType; }, true);
  // pointermove e non pointerover: se uno scroll ha chiuso il suggerimento, basta muovere un po' il mouse per riaverlo
  document.addEventListener("pointermove", (e) => {
    if (e.pointerType !== "mouse") return;
    const el = e.target.closest(CON_SUGGERIMENTO);
    if (!el || el === SUGG.bersaglio || el === SUGG.inArrivo) return;
    clearTimeout(SUGG.timer);
    SUGG.inArrivo = el;
    SUGG.timer = setTimeout(() => mostraSuggerimento(el), 120);
  }, { passive: true });
  document.addEventListener("pointerout", (e) => {
    if (e.pointerType !== "mouse") return;
    const el = e.target.closest(CON_SUGGERIMENTO);
    if (!el || el.contains(e.relatedTarget)) return;
    if (el === SUGG.inArrivo) {
      clearTimeout(SUGG.timer);
      SUGG.inArrivo = null;
    }
    if (el === SUGG.bersaglio) nascondiSuggerimento();
  });
  document.addEventListener("focusin", (e) => {
    const el = e.target.closest?.(CON_SUGGERIMENTO);
    if (el && e.target.matches(":focus-visible")) mostraSuggerimento(el, e.target);
  });
  document.addEventListener("focusout", (e) => { if (e.target === SUGG.descritto) nascondiSuggerimento(); });
  document.addEventListener("click", (e) => {
    const el = e.target.closest(CON_SUGGERIMENTO);
    const tocco = SUGG.puntatore !== "mouse";
    if (tocco && el && !e.target.closest(INTERATTIVO)) {
      if (SUGG.bersaglio === el) nascondiSuggerimento();
      else mostraSuggerimento(el);
    } else if (tocco || e.target.closest(INTERATTIVO)) {
      nascondiSuggerimento();
    }
  });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") nascondiSuggerimento(); });
  // anche lo scroll dentro la tabella o il dettaglio (lo scroll non risale il DOM, ma passa dalla fase di cattura);
  // chiude solo un suggerimento già visibile, senza annullare quello che sta per comparire sotto il mouse
  window.addEventListener("scroll", () => { if (!SUGG.el.hidden) nascondiSuggerimento(); }, { passive: true, capture: true });
  window.addEventListener("resize", nascondiSuggerimento);
  document.getElementById("dettaglio").addEventListener("close", nascondiSuggerimento);
}

// ---------------------------------------------------------------- qualità dei dati
function renderQualita() {
  const { fondi, comparti, meta } = STATO;
  const conDati = fondi.filter((f) => f.has_dati).length;
  const senza = fondi.filter((f) => !f.has_dati);
  const anomali = comparti.filter((c) => c.flag_anomalia.length);
  const fondiNote = fondi.filter((f) => f.has_dati && (f.note || f.flag_anomalia.length));

  const righeAnomalie = anomali.map((c) => {
    const f = STATO.perId.get(c.fondo_id);
    return `<tr><th scope="row"><button type="button" class="linkish" data-fondo="${esc(f.id)}">${esc(f.nome_breve)}</button></th>
      <td>${esc(c.comparto)}</td><td>${c.flag_anomalia.map((k) => esc(flagComparto(k))).join("<br>")}</td>
      <td class="cell-note">${esc(c.note ?? "")}</td></tr>`;
  }).join("");

  document.getElementById("qualita-body").innerHTML = `
    <div class="apertura">
      <h3>Copertura</h3>
      <p>${conDati} fondi su ${fondi.length} hanno dati di dettaglio (${pct(conDati / fondi.length, 0)}).</p>
      <div class="cov" role="img" aria-label="${conDati} fondi con dati su ${fondi.length}">
        <span class="si" style="flex:${conDati}"></span><span class="no" style="flex:${fondi.length - conDati}"></span></div>
      ${coperturaDocumenti()}
    </div>

    <div class="apertura">
      <h3>Anomalie aperte sui comparti (${anomali.length})</h3>
      <p class="hint">Segnalate in automatico dallo script di export. I dati sono riportati come sono nella fonte, senza correzioni: vanno verificati sulle Schede costi ufficiali.</p>
    </div>
    <div class="table-scroll"><table class="data">
      <caption class="sr-only">Comparti con anomalie</caption>
      <thead><tr><th scope="col">Fondo</th><th scope="col">Comparto</th><th scope="col">Anomalia</th><th scope="col">Nota</th></tr></thead>
      <tbody>${righeAnomalie || `<tr><td colspan="4">Nessuna anomalia rilevata.</td></tr>`}</tbody>
    </table></div>

    <div class="q-grid">
      <div>
        <h3>Fondi senza dati di dettaglio (${senza.length})</h3>
        <p class="hint">Il link apre la pagina ufficiale del fondo.</p>
        <ul class="chips">${senza.map((f) => {
          const avvisi = avvisiFondo(f);
          const nome = `${esc(f.nome_breve)}${avvisi.length ? ' <span aria-hidden="true">⚠️</span>' : ""}`;
          const t = avvisi.length ? ` data-spiega="${esc(avvisi.join(" · "))}"` : "";
          return `<li>${f.url ? `<a class="chip" href="${esc(f.url)}" rel="noopener" target="_blank"${t}>${nome}</a>` : `<span class="chip"${t}>${nome}</span>`}</li>`;
        }).join("")}</ul>
        ${senza.filter((f) => avvisiFondo(f).length).map((f) => `<p class="hint chip-nota">⚠️ <strong>${esc(f.nome_breve)}</strong>: ${esc(avvisiFondo(f).join(" · "))}</p>`).join("")}
      </div>
      <div class="q-note">
        <h3>Note sui fondi con dati (${fondiNote.length})</h3>
        <p class="hint">Clicca sul fondo per leggere la nota completa insieme ai comparti.</p>
        <ul class="note-list" id="note-fondi" data-aperto="false">${fondiNote.map((f, i) => `<li${i >= NOTE_VISIBILI ? " class=\"extra\"" : ""}>
          <button type="button" class="linkish" data-fondo="${esc(f.id)}">${esc(f.nome_breve)}</button>
          <span class="clamp" data-spiega="${esc(avvisiFondo(f).join(" · "))}">${esc(avvisiFondo(f).join(" · "))}</span></li>`).join("")}</ul>
        ${fondiNote.length > NOTE_VISIBILI ? `<button type="button" class="mostra" id="mostra-note" aria-controls="note-fondi" aria-expanded="false">Mostra tutte le ${fondiNote.length} note</button>` : ""}
      </div>
      <div>
        <h3>Fonti</h3>
        <ul>${(meta.fonti ?? []).map((s) => `<li>${s.url ? `<a href="${esc(s.url)}" rel="noopener" target="_blank">${esc(s.nome)}</a>` : esc(s.nome)} <span class="tag">${esc(s.tipo)}</span></li>`).join("")}</ul>
        ${meta.avvisi_export?.length ? `<h3 style="margin-top:12px">Avvisi dell'ultimo export</h3><ul>${meta.avvisi_export.map((a) => `<li>${esc(a)}</li>`).join("")}</ul>` : ""}
      </div>
    </div>`;
}

const NOTE_VISIBILI = 6;
document.addEventListener("click", (e) => {
  const b = e.target.closest("#mostra-note");
  if (!b) return;
  const lista = document.getElementById("note-fondi");
  const aperto = lista.dataset.aperto !== "true";
  lista.dataset.aperto = String(aperto);
  b.setAttribute("aria-expanded", String(aperto));
  b.textContent = aperto ? "Mostra meno" : `Mostra tutte le ${lista.children.length} note`;
  if (!aperto) lista.scrollIntoView({ block: "nearest" });
});

// ---------------------------------------------------------------- footer
function renderFooter() {
  const m = STATO.meta;
  const commit = m.commit ? ` · commit <code>${esc(m.commit.slice(0, 7))}</code>` : "";
  const lic = m.licenza;
  const repo = "https://github.com/andreagalle/goodbye-elsa/blob/master/";
  document.getElementById("licenza").innerHTML = lic
    ? `Codice rilasciato con licenza <a href="${repo}${esc(lic.file)}" rel="noopener">${esc(lic.nome)}</a>${lic.spdx === "Unlicense" ? " (pubblico dominio)" : ""}; i dati restano delle rispettive fonti.`
    : "";
  document.getElementById("meta-footer").innerHTML =
    `Versione <strong>${esc(m.versione ?? "—")}</strong> · Dati aggiornati al ${dataIt(m.workbook_modificato_il)} (workbook <code>${esc(m.workbook)}</code>) · export del ${dataIt(m.generato_il)}${commit}.`;
}

carica();
