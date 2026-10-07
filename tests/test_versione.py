"""Test delle regole di versionamento (scripts/versione.py)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import versione as v  # noqa: E402


def c(oggetto):
    m = v.RE_COMMIT.match(oggetto)
    return {"sha": "0" * 40, "oggetto": oggetto, "tipo": m.group("tipo").lower() if m else "altro",
            "ambito": m.group("ambito") if m else None, "testo": m.group("testo") if m else oggetto, "corpo": ""}


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


if __name__ == "__main__":
    unittest.main()
