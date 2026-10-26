"""Tests sans Internet du recoupement et de ses limites."""
import datetime as dt
import unittest

from scripts.verify_news import (
    compatible_events, corroborate, enrich_verification, owner, search_terms,
)


def article(uid, source, title):
    return {
        "id": uid, "title": title,
        "source": source, "url": "https://example.org/" + uid,
        "summary": "Le vote est intervenu après les observations de la Cour constitutionnelle.",
        "publishedAt": "2026-10-26T11:00:00Z", "score": 10,
        "category": "monde",
    }


class VerificationTests(unittest.TestCase):
    def setUp(self):
        self.now = dt.datetime(2026, 10, 26, 12, tzinfo=dt.timezone.utc)
        self.a = article("a", "France 24", "RD Congo : la loi sur les conditions du référendum adoptée")
        self.b = article("b", "ACP", "RDC : l'Assemblée nationale adopte la loi sur le référendum")

    def test_rdc_variants_refer_to_same_event(self):
        self.assertTrue(compatible_events(self.a["title"], self.b["title"]))

    def test_adoption_is_not_only_an_examination(self):
        self.assertFalse(compatible_events(
            self.a["title"], "RDC : l'Assemblée nationale examine la loi sur le référendum"
        ))

    def test_same_editorial_group_cannot_corroborate(self):
        self.assertEqual(owner("RFI"), owner("France 24"))
        second = article("c", "RFI", self.a["title"])
        self.assertEqual(len(corroborate(self.a, [self.a, second], [])), 1)

    def test_two_distinct_outlets_can_corroborate(self):
        matches = corroborate(self.a, [self.a, self.b], [])
        self.assertEqual(len(matches), 2)

    def test_search_terms_are_short(self):
        self.assertLessEqual(len(search_terms(self.a["title"]).split()), 7)

    def test_single_source_not_confirmed(self):
        buckets = {"monde": [self.a]}
        stats = enrich_verification(buckets, self.now, resolver=lambda title, now: [])
        self.assertEqual(stats["corroborated"], 0)
        self.assertEqual(self.a["verification"]["status"], "single-source")

    def test_source_from_search_is_valid(self):
        other = {
            "name": "ACP",
            "group": "acp",
            "title": self.b["title"],
            "url": "https://news.google.com/articles/example",
            "publishedAt": "2026-10-26T11:30:00Z",
        }
        buckets = {"monde": [self.a]}
        stats = enrich_verification(buckets, self.now, resolver=lambda title, now: [other])
        self.assertEqual(stats["corroborated"], 1)
        self.assertEqual(self.a["verification"]["sourceCount"], 2)

    def test_not_correlated_when_action_conflicts(self):
        other = {
            "name": "ACP",
            "group": "acp",
            "title": "RDC : l'Assemblée nationale examine la loi sur le référendum",
            "url": "https://news.google.com/articles/example",
            "publishedAt": "2026-10-26T11:30:00Z",
        }
        buckets = {"monde": [self.a]}
        stats = enrich_verification(buckets, self.now, resolver=lambda title, now: [other])
        self.assertEqual(stats["corroborated"], 0)


if __name__ == "__main__":
    unittest.main()
