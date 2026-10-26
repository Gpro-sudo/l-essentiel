"""Test de non-sensationnalisme sur l'article OpenAI du 26 octobre 2026."""
import datetime as dt
import unittest

from scripts.editorial_facts import apply_primary_correction
from scripts.headline_policy import sensational, validate_headline


class PrimaryCorrectionsTests(unittest.TestCase):
    def setUp(self):
        self.article = {
            "category": "ia",
            "title": "Un « monde hors ligne » : après un nouveau dérapage de l'IA, OpenAI prend une décision radicale",
            "summary": "Des modèles d'IA OpenAI sont parvenus à s'échapper de leur prison numérique. Des agents auraient communiqué entre eux.",
            "_sourceText": "Des modèles d'IA OpenAI sont parvenus à s'échapper de leur prison numérique. Des agents auraient communiqué entre eux.",
            "source": "01net",
            "verification": {
                "status": "single-source", "sourceCount": 1,
                "sources": [{"name": "01net", "url": "https://01net.com/example"}],
            },
        }
        self.now = dt.datetime(2026, 10, 26, 16, tzinfo=dt.timezone.utc)

    def test_original_claim_is_sensational(self):
        self.assertTrue(sensational(self.article["summary"]))
        self.assertTrue(sensational(self.article["title"]))
        self.assertIsNone(validate_headline(
            "Des modèles IA OpenAI sont parvenus à s'échapper de leur prison numérique",
            self.article["title"], self.article["_sourceText"]
        ))

    def test_source_primary_replaces_scare_headline(self):
        self.assertTrue(apply_primary_correction(self.article, self.now))
        self.assertIn("isolement", self.article["displayTitle"])
        self.assertIn("faille DNS", self.article["summary"])
        self.assertLessEqual(len(self.article["summary"]), 178)
        self.assertEqual(self.article["primarySource"]["url"],
            "https://openai.com/index/securing-our-frontier-model-training-environment/")
        self.assertEqual(self.article["verification"]["status"], "single-source")
        self.assertNotIn("Recoupé", self.article["primaryNote"])
        self.assertNotIn("échapper", self.article["displayTitle"].lower())

    def test_correction_is_not_generic_for_other_openai_news(self):
        self.article["title"] = "OpenAI annonce de nouveaux modèles d'IA"
        self.article["summary"] = "OpenAI lance plusieurs produits cette semaine."
        self.article["_sourceText"] = self.article["summary"]
        self.assertFalse(apply_primary_correction(self.article, self.now))
        self.assertNotIn("primarySource", self.article)

    def test_correction_does_not_become_evergreen(self):
        self.assertFalse(apply_primary_correction(
            self.article, dt.datetime(2026, 12, 1, tzinfo=dt.timezone.utc)
        ))


if __name__ == "__main__":
    unittest.main()
