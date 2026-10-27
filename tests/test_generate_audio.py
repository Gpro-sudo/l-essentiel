"""Génération vocale de secours : tests sans service cloud et sans TTS installé."""
from __future__ import annotations
import json
import tempfile
from pathlib import Path
import unittest

from scripts.generate_audio import generate, text_for_article, text_for_finance


class AudioGenerationTests(unittest.TestCase):
    def test_article_reads_only_title_and_brief_with_caution(self):
        item = {
            "title": "Annonce provisoire",
            "displayTitle": "Le projet reste à confirmer",
            "summary": "Une seule source a publié ces informations.",
            "headlineCaution": True,
            "verification": {"status": "single-source"},
        }
        script = text_for_article(item)
        self.assertIn("Le projet reste à confirmer", script)
        self.assertIn("non recoupée", script)
        self.assertNotIn("Annonce provisoire", script)

    def test_financial_narration_keeps_context_date_and_caution(self):
        context = {
            "asOf": "2026-10-27",
            "lastOfficialSession": "2026-10-26",
            "title": "Bourse de Casablanca",
            "indexValue": "16 999,56",
            "indexChange": "−0,32 %",
            "ipo": {
                "name": "Jet Energy",
                "status": "Opération annoncée",
                "subscription": "2 au 5 novembre 2026",
                "firstListing": "16 novembre 2026",
                "price": "125 à 143 DH",
                "amount": "375 MDH",
                "detail": "Les actions sont proposées au public.",
            },
            "market": {
                "fact": "Le MASI corrige.",
                "analysis": "Les rendements obligataires augmentent.",
                "watch": "Surveiller la liquidité.",
            },
        }
        narration = text_for_finance(context)
        self.assertIn("2026-10-27", narration)
        self.assertIn("Jet Energy", narration)
        self.assertIn("conseil de placement", narration)
        self.assertIn("16 999,56", narration)

    def test_output_audio_paths_are_safe_and_manifest_is_written(self):
        items = [
            {"id": "0123456789abcdefabcd", "title": "Un titre factuel",
             "summary": "Le résumé de l'information est ici."},
            {"id": "../../malicious", "title": "Un titre invalide",
             "summary": "Ce fichier ne doit pas être créé."},
        ]
        mock_finance = {
            "asOf": "2026-10-27", "ipo": {"name": "Jet Energy"},
            "market": {"fact": "Les cours ont reculé."},
        }
        created = []
        def fake_tts(text, output):
            created.append(output.name)
            output.write_bytes(b"FAKE AUDIO")
            return True
        with tempfile.TemporaryDirectory() as directory:
            result = generate(
                {"financialBriefing": mock_finance, "categories": {"ia": items}},
                Path(directory), maker=fake_tts,
            )
            manifest = json.loads((Path(directory) / "manifest.json").read_text())
            self.assertEqual(result, manifest)
            self.assertEqual(result["finance"], "audio/finance.mp3")
            self.assertEqual(len(result["items"]), 1)
            self.assertEqual(len(created), 2)
            self.assertEqual(result["items"]["0123456789abcdefabcd"],
                             "audio/0123456789abcdefabcd.mp3")


if __name__ == "__main__":
    unittest.main()
