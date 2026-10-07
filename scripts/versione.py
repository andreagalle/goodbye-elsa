#!/usr/bin/env python3
"""Calcola la prossima versione (SemVer, tag `vX.Y.Z`) e le note di rilascio a partire dai commit.

Regole (vedi CLAUDE.md §9):
  - minor  se almeno un commit è `feat:`, `sito:` o `script:` (nuove funzionalità del sito o dello script);
  - patch  per tutto il resto (`dati:`, `docs:`, `fix:`, `ci:`, `test:`, `chore:`, …);
  - major  MAI in automatico: solo con `--bump major` (input manuale del workflow o label `release:major`),
           su richiesta esplicita del responsabile del progetto. `BREAKING CHANGE` e `!` valgono come minor.

Uso:
  python scripts/versione.py prossima [--bump auto|patch|minor|major]   → stampa es. v0.2.0
  python scripts/versione.py note --versione v0.2.0 [--pr-numero N --pr-titolo T] [--repo owner/nome]
  python scripts/versione.py corrente                                    → ultimo tag (o v0.0.0)
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RE_TAG = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")
RE_COMMIT = re.compile(r"^(?P<tipo>[a-zA-Z]+)(?:\((?P<ambito>[^)]+)\))?(?P<rotto>!)?:\s*(?P<testo>.+)$")
TIPI_MINOR = {"feat", "sito", "script"}

# Sezioni delle note di rilascio, nell'ordine in cui compaiono.
SEZIONI = [
    ("sito", "🖥️ Sito e dashboard"),
    ("feat", "✨ Nuove funzionalità"),
    ("dati", "📊 Dati"),
    ("script", "⚙️ Script di export"),
    ("fix", "🐛 Correzioni"),
    ("docs", "📖 Documentazione"),
    ("ci", "🔁 CI e release"),
    ("test", "🧪 Test"),
    ("altro", "🔧 Altro"),
]


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()


def ultimo_tag() -> str | None:
    try:
        tags = git("tag", "--list", "v*", "--sort=-v:refname").splitlines()
    except subprocess.CalledProcessError:
        return None
    return next((t for t in tags if RE_TAG.match(t)), None)


def commit_dal(tag: str | None) -> list[dict]:
    intervallo = f"{tag}..HEAD" if tag else "HEAD"
    sep, fine = "\x1f", "\x1e"
    out = git("log", intervallo, "--no-merges", f"--format=%H{sep}%s{sep}%b{fine}")
    commits = []
    for blocco in filter(None, (b.strip() for b in out.split(fine))):
        sha, oggetto, corpo = (blocco.split(sep) + ["", ""])[:3]
        m = RE_COMMIT.match(oggetto)
        commits.append({
            "sha": sha,
            "oggetto": oggetto,
            "tipo": m.group("tipo").lower() if m else "altro",
            "ambito": m.group("ambito") if m else None,
            "testo": m.group("testo") if m else oggetto,
            "corpo": corpo.strip(),
        })
    return commits


def tipo_incremento(commits: list[dict], richiesto: str = "auto") -> str:
    if richiesto in ("patch", "minor", "major"):
        return richiesto
    return "minor" if any(c["tipo"] in TIPI_MINOR for c in commits) else "patch"


def incrementa(tag: str | None, bump: str) -> str:
    major, minor, patch = map(int, RE_TAG.match(tag).groups()) if tag else (0, 0, 0)
    if bump == "major":
        return f"v{major + 1}.0.0"
    if bump == "minor":
        return f"v{major}.{minor + 1}.0"
    return f"v{major}.{minor}.{patch + 1}"


def note_rilascio(versione: str, precedente: str | None, commits: list[dict], bump: str,
                  repo: str | None = None, pr_numero: str | None = None, pr_titolo: str | None = None,
                  meta_path: Path = ROOT / "data" / "meta.json") -> str:
    url_repo = f"https://github.com/{repo}" if repo else None
    righe = [f"## {versione}", ""]
    if pr_numero:
        pr = f"[#{pr_numero}]({url_repo}/pull/{pr_numero})" if url_repo else f"#{pr_numero}"
        righe += [f"Pull request {pr}: **{pr_titolo or ''}**", ""]
    righe += [f"Incremento: `{bump}` (da {precedente or 'nessuna versione precedente'}).", ""]

    gruppi: dict[str, list[dict]] = {}
    for c in commits:
        chiave = c["tipo"] if c["tipo"] in dict(SEZIONI) else "altro"
        gruppi.setdefault(chiave, []).append(c)
    if not commits:
        righe += ["Nessuna modifica rispetto alla versione precedente.", ""]
    for chiave, titolo in SEZIONI:
        if chiave not in gruppi:
            continue
        righe += [f"### {titolo}", ""]
        for c in gruppi[chiave]:
            sha = c["sha"][:7]
            link = f"[`{sha}`]({url_repo}/commit/{c['sha']})" if url_repo else f"`{sha}`"
            ambito = f"**{c['ambito']}**: " if c["ambito"] else ""
            righe.append(f"- {ambito}{c['testo']} ({link})")
        righe.append("")

    if meta_path.exists():
        m = json.loads(meta_path.read_text(encoding="utf-8"))
        c = m.get("conteggi", {})
        righe += [
            "### 📦 Dati pubblicati", "",
            f"- {c.get('fondi')} fondi, di cui {c.get('fondi_con_dati')} con dati di dettaglio",
            f"- {c.get('comparti')} comparti ({c.get('comparti_10_anni')} con rendimento a 10 anni), "
            f"{c.get('comparti_con_anomalie')} con anomalie segnalate",
            "",
        ]
    if url_repo:
        owner, nome = repo.split("/", 1)
        righe.append(f"🔗 Dashboard: https://{owner.lower()}.github.io/{nome}/ · "
                     f"[Guida](https://{owner.lower()}.github.io/{nome}/guida/) · "
                     f"[Presentazione](https://{owner.lower()}.github.io/{nome}/presentazione/)")
        if precedente:
            righe.append(f"\n**Confronto completo:** {url_repo}/compare/{precedente}...{versione}")
    return "\n".join(righe).rstrip() + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("prossima")
    p.add_argument("--bump", choices=["auto", "patch", "minor", "major"], default="auto")
    p.add_argument("--json", action="store_true", help="stampa versione, incremento e n. commit in JSON")
    n = sub.add_parser("note")
    n.add_argument("--versione", required=True)
    n.add_argument("--bump", choices=["auto", "patch", "minor", "major"], default="auto")
    n.add_argument("--repo")
    n.add_argument("--pr-numero")
    n.add_argument("--pr-titolo")
    sub.add_parser("corrente")
    args = ap.parse_args(argv)

    tag = ultimo_tag()
    if args.cmd == "corrente":
        print(tag or "v0.0.0")
        return 0
    commits = commit_dal(tag)
    bump = tipo_incremento(commits, args.bump)
    if args.cmd == "prossima":
        # Nessun commit nuovo (es. workflow rilanciato): la versione resta quella dell'ultimo tag.
        if tag and not commits:
            versione, bump = tag, "nessuno"
        else:
            versione = incrementa(tag, bump)
        if args.json:
            print(json.dumps({"versione": versione, "precedente": tag, "incremento": bump, "commit": len(commits)}))
        else:
            print(versione)
        return 0
    sys.stdout.write(note_rilascio(args.versione, tag, commits, bump, args.repo, args.pr_numero, args.pr_titolo))
    return 0


if __name__ == "__main__":
    sys.exit(main())
