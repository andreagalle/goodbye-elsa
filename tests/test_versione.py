"""Test delle regole di versionamento (scripts/versione.py)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import versione as v  # noqa: E402


def c(oggetto, corpo=""):
    return v.analizza("0" * 40, oggetto, corpo)


# corpo di un commit che ne riunisce altri tre (come a538964): i titoli a inizio riga, i dettagli in elenco
CORPO_UNITO = """La scritta resta a 1,45 rem.

Co-Authored-By: Claude <noreply@anthropic.com>

sito: documenti ufficiali dei fondi scaricabili

- dati: registro data/documenti.csv e 532 PDF
- script: documenti.py con scarica e smista
- Fonti: pagine informative dei fondi
Fonte: COVIP, consultata il 2026-10-10

dati: prestazioni di altri 6 fondi
  dati: riga di continuazione rientrata, non è un titolo

Co-Authored-By: Claude <noreply@anthropic.com>"""


class TestVersione(unittest.TestCase):
    def test_patch_per_dati_e_docs(self):
        self.assertEqual(v.tipo_incremento([c("dati: aggiorna Aureo"), c("docs: guida")]), "patch")

    def test_minor_per_sito_script_feat(self):
        for o in ("sito: simulatore", "script(export): nuovo flag", "feat: qualcosa"):
            self.assertEqual(v.tipo_incremento([c("docs: x"), c(o)]), "minor", o)

    def test_major_mai_automatica(self):
        self.assertEqual(v.tipo_incremento([c("sito!: cambia tutto"), c("BREAKING CHANGE: x")]), "minor")
        self.assertEqual(v.tipo_incremento([c("docs: x")], "major"), "major")

    def test_incrementa(self):
        self.assertEqual(v.incrementa(None, "minor"), "v0.1.0")
        self.assertEqual(v.incrementa(None, "patch"), "v0.0.1")
        self.assertEqual(v.incrementa("v0.3.2", "patch"), "v0.3.3")
        self.assertEqual(v.incrementa("v0.3.2", "minor"), "v0.4.0")
        self.assertEqual(v.incrementa("v0.3.2", "major"), "v1.0.0")

    def test_note(self):
        note = v.note_rilascio("v0.2.0", "v0.1.0", [c("sito: tabella"), c("dati: Aureo"), c("varie")], "minor",
                               repo="utente/repo", pr_numero="7", pr_titolo="Nuova tabella")
        self.assertIn("## v0.2.0", note)
        self.assertIn("[#7](https://github.com/utente/repo/pull/7)", note)
        self.assertIn("### 🖥️ Sito e dashboard", note)
        self.assertIn("- tabella", note)
        self.assertIn("### 🔧 Altro", note)
        self.assertIn("compare/v0.1.0...v0.2.0", note)
        self.assertLess(note.index("Sito e dashboard"), note.index("📊 Dati"))

    def test_commit_uniti_nel_corpo(self):
        # solo le righe "tipo: testo" a inizio riga: niente elenchi, Fonte:, Co-Authored-By: o righe rientrate
        lavori = v.voci([c("sito: logo più grande", CORPO_UNITO)])
        self.assertEqual([(x["tipo"], x["testo"]) for x in lavori], [
            ("sito", "logo più grande"),
            ("sito", "documenti ufficiali dei fondi scaricabili"),
            ("dati", "prestazioni di altri 6 fondi"),
        ])
        self.assertEqual({x["sha"] for x in lavori}, {"0" * 40})
        # un titolo ripetuto nel corpo non si duplica
        self.assertEqual(len(v.voci([c("dati: Aureo", "dati: Aureo")])), 1)

    def test_commit_uniti_contano_per_versione_e_note(self):
        self.assertEqual(v.tipo_incremento([c("docs: guida", "sito: simulatore")]), "minor")
        self.assertEqual(v.tipo_incremento([c("docs: guida", "- sito: dettaglio in elenco")]), "patch")
        note = v.note_rilascio("v0.3.0", "v0.2.0", [c("sito: logo più grande", CORPO_UNITO)], "minor")
        for voce in ("- logo più grande", "- documenti ufficiali dei fondi scaricabili", "- prestazioni di altri 6 fondi"):
            self.assertIn(voce, note)
        self.assertNotIn("registro data/documenti.csv", note)
        self.assertNotIn("### 🔧 Altro", note)


if __name__ == "__main__":
    unittest.main()
