/* Navigazione condivisa da dashboard e guida:
   - evidenzia nella barra in alto la sezione visibile (aria-current), e su telefono la porta in vista;
   - marchio "goodbye Elsa !!" a sinistra: porta all'inizio della dashboard (se ci sei già, senza ricaricarla);
   - pulsante "Torna su" che compare dopo un po' di scorrimento. */
"use strict";

(() => {
  // ---------------------------------------------------------------- sezione attiva nel menu
  const nav = document.querySelector(".topnav .voci");
  const link = nav ? [...nav.querySelectorAll('a[href^="#"]')] : [];
  const sezioni = link.map((a) => document.getElementById(a.hash.slice(1))).filter(Boolean);

  const attiva = (id) => {
    for (const a of link) {
      const on = a.hash === `#${id}`;
      if (on) a.setAttribute("aria-current", "true");
      else a.removeAttribute("aria-current");
      // su schermi stretti la barra scorre di lato: porta in vista la voce attiva senza muovere la pagina
      if (on && nav.scrollWidth > nav.clientWidth) {
        const sx = a.offsetLeft - (nav.clientWidth - a.offsetWidth) / 2;
        nav.scrollTo({ left: Math.max(0, sx), behavior: "smooth" });
      }
    }
  };

  if (sezioni.length) {
    // una sezione è "attiva" quando attraversa una fascia appena sotto la barra fissa
    const visibili = new Set();
    const oss = new IntersectionObserver((voci) => {
      for (const v of voci) v.isIntersecting ? visibili.add(v.target) : visibili.delete(v.target);
      const prima = sezioni.find((s) => visibili.has(s));
      if (prima) attiva(prima.id);
      else if (window.scrollY < sezioni[0].offsetTop) attiva(null);
    }, { rootMargin: "-80px 0px -55% 0px" });
    sezioni.forEach((s) => oss.observe(s));
  }

  // ---------------------------------------------------------------- torna su e marchio
  const inCima = () => {
    const riduci = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    window.scrollTo({ top: 0, behavior: riduci ? "auto" : "smooth" });
    // il focus torna all'inizio della pagina per chi naviga da tastiera
    document.querySelector("h1")?.focus({ preventScroll: true });
  };

  // il nome accanto al logo lascia spazio alle voci quando il menu altrimenti non entrerebbe (solo da tablet in su:
  // su telefono il menu scorre col dito); va rimisurato al cambio di larghezza e quando arrivano i font
  const marchio = document.querySelector(".topnav .marchio");
  if (marchio && nav) {
    const adatta = () => {
      marchio.classList.remove("compatto");
      marchio.classList.toggle("compatto", nav.scrollWidth > nav.clientWidth + 1);
    };
    new ResizeObserver(adatta).observe(nav.parentElement);
    document.fonts?.ready.then(adatta);
  }

  document.querySelector(".marchio")?.addEventListener("click", (e) => {
    const a = e.currentTarget;
    // da un'altra pagina, o con Ctrl/⌘/Maiusc (nuova scheda o finestra), è un normale link
    if (a.pathname !== location.pathname || e.ctrlKey || e.metaKey || e.shiftKey || e.altKey) return;
    e.preventDefault();
    if (location.hash) history.replaceState(null, "", location.pathname + location.search);
    inCima();
  });

  const su = document.createElement("button");
  su.type = "button";
  su.className = "su";
  su.setAttribute("aria-label", "Torna su");
  su.title = "Torna su";
  su.innerHTML = '<span aria-hidden="true">↑</span>';
  document.body.append(su);

  const aggiorna = () => su.classList.toggle("visibile", window.scrollY > window.innerHeight * 0.8);
  window.addEventListener("scroll", aggiorna, { passive: true });
  aggiorna();

  su.addEventListener("click", inCima);
})();
