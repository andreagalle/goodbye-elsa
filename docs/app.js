/* Dashboard fondi pensione aperti — vanilla JS, legge solo data/*.json generati da scripts/export_xlsx.py */
"use strict";

const STATO = {
  fondi: [], comparti: [], meta: {}, perId: new Map(),
  sort: { key: "best_rend_10a", dir: "desc" },
  filtri: { q: "", dati: false, esg: false, lc: false, online: false },
  grafico: null, evidenzia: "", includiPeriodi: false, nascosti: new Set(),
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

const GRUPPI = {
  AZN: { label: "Azionari (AZN)", var: "--cat-azn", punto: "circle" },
  BIL: { label: "Bilanciati (BIL)", var: "--cat-bil", punto: "triangle" },
  OBB: { label: "Obbligazionari (OBB misto e puro)", var: "--cat-obb", punto: "rect" },
  GAR: { label: "Garantiti (GAR)", var: "--cat-gar", punto: "rectRot" },
};
const gruppo = (cat) => (cat && cat.startsWith("OBB") ? "OBB" : cat);
const sw = (cat) => `<span class="sw ${esc(gruppo(cat))}" aria-hidden="true"></span>`;
const tagCat = (cat) => `<span class="tag tag-cat">${sw(cat)}${esc(cat)}</span>`;
const css = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();

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
  return `<span class="warn" role="img" title="${t}" aria-label="Attenzione: ${t}">⚠️</span>`;
}

// ---------------------------------------------------------------- caricamento
async function carica() {
  try {
    const [fondi, comparti, meta] = await Promise.all(
      ["fondi", "comparti", "meta"].map((n) =>
        fetch(`data/${n}.json`, { cache: "no-cache" }).then((r) => {
          if (!r.ok) throw new Error(`${n}.json: HTTP ${r.status}`);
          return r.json();
        })
      )
    );
    Object.assign(STATO, { fondi, comparti, meta, perId: new Map(fondi.map((f) => [f.id, f])) });
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
  renderQualita();
  renderFooter();
  initDettaglio();
}

// ---------------------------------------------------------------- KPI
function renderKpi() {
  const c = STATO.meta.conteggi;
  const kpi = (v, l) => `<div class="kpi"><div class="v">${v}</div><div class="l">${l}</div></div>`;
  document.getElementById("kpis").innerHTML =
    kpi(c.fondi, "fondi pensione aperti nell'elenco COVIP") +
    kpi(c.fondi_con_dati, `con dati di dettaglio (${pct(c.fondi_con_dati / c.fondi, 0)})`) +
    kpi(c.comparti, `comparti, di cui ${c.comparti_10_anni} con rendimento a 10 anni`) +
    kpi(c.comparti_con_anomalie, '<a href="#qualita">comparti con anomalie o dati non confrontabili</a>');
}

// ---------------------------------------------------------------- tabella fondi
const COLONNE = [
  { key: "nome_breve", label: "Fondo", tipo: "txt",
    html: (f) => `<button type="button" class="fondo-btn" data-fondo="${esc(f.id)}">${esc(f.nome_breve)}</button>${badge(avvisiFondo(f))}<span class="sub">${esc(f.societa ?? "Nessuna scheda")}</span>` },
  { key: "spese_adesione", label: "Adesione", num: true, html: (f) => eur(f.spese_adesione) },
  { key: "spese_annue", label: "Spese annue", num: true, html: (f) => eur(f.spese_annue) },
  { key: "costo_pct_versato", label: "% sul versato", titolo: "Costo percentuale su ogni versamento", num: true, html: (f) => pct(f.costo_pct_versato, 1) },
  { key: "n_comparti", label: "Comparti", num: true,
    html: (f) => (f.has_dati ? `${f.n_comparti}${f.n_linee != null && f.n_linee !== f.n_comparti ? ` <span class="tag tag-warn" title="Linee dichiarate da Ciao Elsa">${f.n_linee} dichiarate</span>` : ""}` : NA) },
  { key: "comm_min", label: "Commissione", titolo: "Commissione di gestione annua, dal comparto più economico al più caro", num: true,
    html: (f) => (f.comm_min == null ? NA : f.comm_min === f.comm_max ? pct(f.comm_min) : `${pct(f.comm_min)} – ${pct(f.comm_max)}`) },
  { key: "max_azioni", label: "Max % azioni", num: true,
    html: (f) => pct(f.max_azioni, 0) + (f.flag_anomalia.includes("comparti_anomali") ? badge(["Valore probabilmente falsato da un comparto con allocazione anomala"]) : "") },
  { key: "best_rend_10a", label: "Miglior rend. 10 anni", titolo: "Miglior rendimento netto medio annuo a 10 anni tra i comparti del fondo", num: true, html: (f) => rend(f.best_rend_10a) },
  { key: null, label: "Caratteristiche", titolo: "Linee ESG, percorso life cycle e sottoscrizione online (si filtrano con i pulsanti sopra)",
    html: caratteristiche },
  { key: null, label: "Fonti",
    html: (f) => `<span class="links">${f.url ? `<a href="${esc(f.url)}" rel="noopener" target="_blank">Sito<span class="sr-only"> di ${esc(f.nome_breve)}</span></a>` : ""}${f.scheda_url ? `<a href="${esc(f.scheda_url)}" rel="noopener" target="_blank">Scheda<span class="sr-only"> Ciao Elsa di ${esc(f.nome_breve)}</span></a>` : ""}</span>` },
];

// ESG, life cycle e online in una sola colonna di etichette: la tabella resta abbastanza stretta da non scorrere su desktop
function caratteristiche(f) {
  if (!f.has_dati) return NA;
  const tag = (testo, classe = "tag-on") => `<span class="tag ${classe}">${testo}</span>`;
  const out = [];
  if (f.esg === "Sì") out.push(tag("ESG"));
  if (f.life_cycle === "Sì") out.push(tag("Life cycle"));
  if (f.online === "Sì (Ciao Elsa)") out.push(tag("Online"));
  else if (f.online === "No (lista d'attesa)") out.push(tag("Online: lista d'attesa", "tag-off"));
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
    `<th scope="col" class="${c.num ? "num" : ""}" ${c.key ? `data-key="${c.key}" aria-sort="none"` : ""}${c.titolo ? ` title="${esc(c.titolo)}"` : ""}>${c.key ? `<button type="button" class="sort">${c.label}</button>` : c.label}</th>`
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
  const tag = c.periodo_anni === 10 ? `<span class="tag">10 anni</span>` : `<span class="tag tag-warn">${c.periodo_anni} anni</span>`;
  return `${rend(c.rendimento)}<br>${tag}`;
}

function apriFondo(id, aggiornaHash = true) {
  const f = STATO.perId.get(id);
  if (!f) return;
  const dlg = document.getElementById("dettaglio");
  document.getElementById("d-titolo").innerHTML = `${esc(f.nome_breve)}<span class="sub">${esc(f.denominazione)}</span>`;
  const comp = compartiDi(id);
  const avvisi = avvisiFondo(f);
  const fact = (l, v) => `<div class="fact"><div class="l">${l}</div><div class="v">${v}</div></div>`;
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
      ${fact("Spese di adesione", eur(f.spese_adesione))}
      ${fact("Spese annue fisse", eur(f.spese_annue))}
      ${fact("Costo % sul versato", pct(f.costo_pct_versato, 1))}
      ${fact("ESG", esc(f.esg ?? "—"))}
      ${fact("Life cycle", esc(f.life_cycle ?? "—"))}
      ${fact("Sottoscrizione online", esc(f.online ?? "—"))}
    </div>
    <h3>Comparti (${comp.length}${f.n_linee != null && f.n_linee !== comp.length ? `; Ciao Elsa ne dichiara ${f.n_linee}` : ""})</h3>
    <div class="table-scroll"><table class="data">
      <caption class="sr-only">Comparti di ${esc(f.nome_breve)}</caption>
      <thead><tr><th scope="col">Comparto</th><th scope="col">Categoria</th><th scope="col">Asset allocation</th>
        <th scope="col" class="num">Rendimento netto<br>medio annuo</th><th scope="col" class="num">Commissione<br>di gestione</th><th scope="col">Note</th></tr></thead>
      <tbody>${comp.map((c) => {
        const note = [...c.flag_anomalia.map((k) => `⚠️ ${esc(flagComparto(k))}`), c.note && esc(c.note)].filter(Boolean);
        return `<tr><th scope="row">${esc(c.comparto)}</th><td>${tagCat(c.categoria)}</td><td>${allocazione(c)}</td>
          <td class="num">${rendConPeriodo(c)}</td><td class="num">${pct(c.commissione)}</td>
          <td class="cell-note">${note.join("<br>") || ""}</td></tr>`;
      }).join("")}</tbody>
    </table></div>`;
  }
  document.getElementById("d-body").innerHTML = html;
  if (!dlg.open) dlg.showModal();
  dlg.scrollTop = 0;
  if (aggiornaHash) history.replaceState(null, "", `#fondo=${encodeURIComponent(id)}`);
}

function initDettaglio() {
  const dlg = document.getElementById("dettaglio");
  document.getElementById("d-chiudi").addEventListener("click", () => dlg.close());
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
    `<button type="button" data-gruppo="${k}" aria-pressed="${!STATO.nascosti.has(k)}">${sw(k)}${g.label}</button>`).join("") +
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
      <h3>${sw(k)}${g.label}</h3>
      <p class="stats">${tutti.length} comparti · commissione mediana ${pctTxt(mediana(conComm.map((c) => c.commissione)))}
        · rendimento mediano a 10 anni ${pctTxt(mediana(dieci.map((c) => c.rendimento)))} (${dieci.length} comparti)</p>
      ${lista("Commissione più bassa", perComm.slice(0, n), (c) => pct(c.commissione))}
      ${mostraPeggiori ? lista("Commissione più alta", perComm.slice(-n).reverse(), (c) => pct(c.commissione)) : ""}
      ${lista("Rendimento a 10 anni più alto", perRend.slice(0, n), (c) => rend(c.rendimento))}
      ${mostraPeggiori ? lista("Rendimento a 10 anni più basso", perRend.slice(-n).reverse(), (c) => rend(c.rendimento)) : ""}
    </article>`;
  }).join("");
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
    <h3>Copertura</h3>
    <p>${conDati} fondi su ${fondi.length} hanno dati di dettaglio (${pct(conDati / fondi.length, 0)}).</p>
    <div class="cov" role="img" aria-label="${conDati} fondi con dati su ${fondi.length}">
      <span class="si" style="flex:${conDati}"></span><span class="no" style="flex:${fondi.length - conDati}"></span></div>

    <h3 style="margin-top:20px">Anomalie aperte sui comparti (${anomali.length})</h3>
    <p class="hint">Segnalate in automatico dallo script di export. I dati sono riportati come sono nella fonte, senza correzioni: vanno verificati sulle Schede costi ufficiali.</p>
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
          const t = avvisi.length ? ` title="${esc(avvisi.join(" · "))}"` : "";
          return `<li>${f.url ? `<a class="chip" href="${esc(f.url)}" rel="noopener" target="_blank"${t}>${nome}</a>` : `<span class="chip"${t}>${nome}</span>`}</li>`;
        }).join("")}</ul>
        ${senza.filter((f) => avvisiFondo(f).length).map((f) => `<p class="hint chip-nota">⚠️ <strong>${esc(f.nome_breve)}</strong>: ${esc(avvisiFondo(f).join(" · "))}</p>`).join("")}
      </div>
      <div class="q-note">
        <h3>Note sui fondi con dati (${fondiNote.length})</h3>
        <p class="hint">Clicca sul fondo per leggere la nota completa insieme ai comparti.</p>
        <ul class="note-list" id="note-fondi" data-aperto="false">${fondiNote.map((f, i) => `<li${i >= NOTE_VISIBILI ? " class=\"extra\"" : ""}>
          <button type="button" class="linkish" data-fondo="${esc(f.id)}">${esc(f.nome_breve)}</button>
          <span class="clamp" title="${esc(avvisiFondo(f).join(" · "))}">${esc(avvisiFondo(f).join(" · "))}</span></li>`).join("")}</ul>
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
  document.getElementById("meta-footer").innerHTML =
    `Versione <strong>${esc(m.versione ?? "—")}</strong> · Dati aggiornati al ${dataIt(m.workbook_modificato_il)} (workbook <code>${esc(m.workbook)}</code>) · export del ${dataIt(m.generato_il)}${commit}.`;
}

carica();
