"""Tests sans accès au réseau pour les synthèses réutilisées."""
import datetime as dt
import unittest

from scripts.cache_summaries import restore_recent_summaries


class CacheTests(unittest.TestCase):
    def setUp(self):
        self.now = dt.datetime(2026, 10, 26, 12, tzinfo=dt.timezone.utc)
        self.summary = "Le MASI a progressé de 0,59 % ce lundi, porté par plusieurs valeurs bancaires."
        self.current = {
            "id": "m1", "title": "La Bourse de Casablanca ouvre en hausse",
            "source": "Hespress FR", "publishedAt": "2026-10-26T09:00:00Z",
            "summary": "Le MASI a progressé de 0,59 % ce lundi, porté par plusieurs valeurs bancaires.",
            "verification": {"status": "corroborated"},
        }
        self.prev = {"generatedAt": "2026-10-26T11:00:00Z", "categories": {
            "eco-maroc": [{**self.current, "summary": self.summary, "summaryType": "ai"}]
        }}

    def test_reuse_same_verified_article(self):
        current = {"eco-maroc": [self.current]}
        count = restore_recent_summaries(current, self.now, fetch=lambda: self.prev)
        self.assertEqual(count, 1)
        self.assertEqual(self.current["summaryType"], "ai")
        self.assertTrue(self.current["summaryCached"])

    def test_never_reuse_if_not_recouped(self):
        self.current["verification"]["status"] = "single-source"
        self.assertEqual(restore_recent_summaries({"eco-maroc": [self.current]}, self.now, fetch=lambda: self.prev), 0)

    def test_never_reuse_after_title_changes(self):
        self.current["title"] = "Une autre actualité"
        self.assertEqual(restore_recent_summaries({"eco-maroc": [self.current]}, self.now, fetch=lambda: self.prev), 0)

    def test_never_reuse_old_event(self):
        self.current["publishedAt"] = "2026-10-23T09:00:00Z"
        self.assertEqual(restore_recent_summaries({"eco-maroc": [self.current]}, self.now, fetch=lambda: self.prev), 0)


if __name__ == "__main__":
    unittest.main()
