"""Contrôles du dossier prioritaire sans appeler de service externe."""
import unittest

from scripts.priority_gulf import gulf_relevant, spotlight, targeted_feeds, PRIORITY_CONTEXT
from scripts.update_news import CATEGORIES, FEEDS


class GulfPriorityTests(unittest.TestCase):
    def test_priority_context_is_explicitly_dated(self):
        self.assertEqual(PRIORITY_CONTEXT["asOf"], "2026-10-26")
        self.assertGreaterEqual(len(PRIORITY_CONTEXT["sources"]), 2)
        self.assertNotIn("generatedAt", PRIORITY_CONTEXT)

    def test_filters_out_golf_sport(self):
        self.assertFalse(gulf_relevant("Un golf professionnel ouvre à Dubai", "Un tournoi important"))
        self.assertFalse(gulf_relevant("Un joueur de golf affronte la chaleur du Golfe"))

    def test_finds_conflict_events(self):
        self.assertTrue(gulf_relevant("Iran : négociations sur la guerre et le détroit d'Ormuz"))
        self.assertTrue(gulf_relevant("Les Houthis revendiquent une attaque de missiles à Riyad"))
        self.assertTrue(gulf_relevant("Arabie saoudite : frappes au Yémen", "Conflit régional"))

    def test_rejects_unrelated_business(self):
        self.assertFalse(gulf_relevant("Le tourisme progresse à Casablanca"))
        self.assertFalse(gulf_relevant("Iran : festival de poésie à Téhéran"))

    def test_targeted_feeds_preserve_category_and_real_publisher_rule(self):
        feeds = targeted_feeds()
        self.assertGreaterEqual(len(feeds), 3)
        self.assertTrue(all(f["category"] == "golfe" and f["google_news"] for f in feeds))
        self.assertIn("golfe", CATEGORIES)
        self.assertGreater(len([f for f in FEEDS if f["category"] == "golfe"]), 4)

    def test_spotlight_keeps_date_with_live_item(self):
        article = {
            "title": "Discussion à Téhéran",
            "summary": "Des délégations se rencontrent à Téhéran pour tenter de désamorcer les hostilités.",
            "publishedAt": "2026-10-26T12:00:00Z",
            "verification": {"sources": [{"name": "Reuters", "url": "https://example.org"}]},
        }
        card = spotlight(article)
        self.assertEqual(card["asOf"], "2026-10-26")
        self.assertEqual(card["latest"]["title"], article["title"])
        self.assertEqual(len(card["sources"]), 3)


if __name__ == "__main__":
    unittest.main()
