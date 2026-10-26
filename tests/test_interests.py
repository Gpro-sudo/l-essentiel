"""Tests de regroupement par sujet et recherche automobile sans réseau."""
import unittest

from scripts.interests import classify_story, interest_feeds, automotive_related
from scripts.update_news import CATEGORIES, FEEDS


class InterestTests(unittest.TestCase):
    def test_merger_is_proposal_not_completed_merger(self):
        key, label, story = classify_story(
            "Tesla et SpaceX envisagent une fusion",
            "Elon Musk discute d'un rapprochement, aucun accord final",
            "autos", "id1"
        )
        self.assertEqual(key, "tesla-spacex-fusion")
        self.assertEqual(story, "tesla-spacex-fusion")
        self.assertIn("rapprochement", label)

    def test_articles_same_merger_group(self):
        a = classify_story("Tesla SpaceX merger discussions", "No deal signed", "autos", "one")
        b = classify_story("Fusion SpaceX-Tesla à l'étude", "Les discussions continuent", "autos", "two")
        self.assertEqual(a[2], b[2])

    def test_joint_venture_not_mistaken_for_merger(self):
        a = classify_story("Tesla SpaceX Terafab : nouvelle usine", "Usine commune de puces", "autos", "someid")
        b = classify_story("Tesla et SpaceX envisagent une fusion", "Projet discuté", "autos", "anotherid")
        self.assertNotEqual(a[2], b[2])

    def test_tesla_only_followed_as_tesla(self):
        key, label, story = classify_story("Tesla vise des robotaxis", "Nouvelles ambitions", "autos", "t")
        self.assertEqual(key, "topic-tesla")
        self.assertEqual(label, "Tesla")

    def test_automotive_search_is_through_google_news_metadata(self):
        self.assertIn("autos", CATEGORIES)
        feeds = interest_feeds()
        self.assertGreaterEqual(len(feeds), 2)
        self.assertTrue(all(f["google_news"] and "news.google.com/rss/search" in f["url"] for f in feeds))
        self.assertTrue(any(f.get("autos_topic_only") for f in FEEDS))

    def test_auto_filter(self):
        self.assertTrue(automotive_related("Tesla et SpaceX discutent d'une fusion", ""))
        self.assertTrue(automotive_related("Volkswagen annonce une nouvelle voiture électrique", ""))
        self.assertFalse(automotive_related("Une enquête sur une réforme des retraites", ""))


if __name__ == "__main__":
    unittest.main()
