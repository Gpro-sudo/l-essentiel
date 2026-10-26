"""Lecture accessible et extraction testées sans trafic réseau."""
import datetime as dt
import unittest

from scripts.article_content import (
    publisher_host, extract_text, hydrate_articles, MAX_FETCH,
)


class ReaderTests(unittest.TestCase):
    def setUp(self):
        self.now = dt.datetime(2026, 10, 26, 16, tzinfo=dt.timezone.utc)
        self.long_text = (
            "Le gouvernement a présenté un calendrier précis et plusieurs mesures nouvelles. "
            "La décision intervient après des consultations menées pendant plusieurs mois. "
            "Les responsables ont indiqué que les entreprises concernées devront adapter leurs pratiques. "
            "Le texte contient des éléments sur les délais, les coûts et les exceptions prévues. "
            "Les autorités ont aussi détaillé les étapes administratives et les conditions de mise en œuvre. "
            "Ces renseignements permettent de comprendre le fait sans se contenter du titre. "
        )

    def test_html_article_extraction_skips_ad_and_nav(self):
        page = (
            "<html><nav><p>Ne pas extraire la publicité de navigation du site.</p></nav>"
            "<article><div class='newsletter'><p>Inscrivez-vous à nos offres commerciales.</p></div>"
            "<p>" + self.long_text + "</p><p>" + self.long_text + "</p>"
            "</article><footer><p>Contenu de bas de page indésirable.</p></footer></html>"
        )
        result = extract_text(page)
        self.assertIn("calendrier précis", result)
        self.assertNotIn("commerciales", result)
        self.assertNotIn("bas de page", result)

    def test_article_extraction_ignores_short_teaser(self):
        self.assertEqual(extract_text("<article><p>Lire la suite de cet article.</p></article>"), "")

    def test_allow_only_known_public_https_publishers(self):
        self.assertEqual(publisher_host("https://www.01net.com/actualites/sujet.html"), "www.01net.com")
        self.assertIsNone(publisher_host("http://www.01net.com/actualites/sujet.html"))
        self.assertIsNone(publisher_host("https://127.0.0.1/admin"))
        self.assertIsNone(publisher_host("https://localhost/admin"))
        self.assertIsNone(publisher_host("https://random-site.net/article"))

    def test_hydrate_uses_rss_full_body_without_network(self):
        article = {
            "id": "a", "publishedAt": "2026-10-26T13:00:00Z",
            "score": 8, "_embeddedArticle": self.long_text * 3,
        }
        count = hydrate_articles({"ia": [article]}, self.now, fetcher=lambda a: self.fail("No network should be used"))
        self.assertEqual(count, 1)
        self.assertEqual(article["articleRead"], "rss-full")

    def test_fetch_is_bounded_and_is_optional(self):
        items = [{
            "id": str(i), "publishedAt": "2026-10-26T13:00:00Z",
            "score": 8, "url": "https://www.01net.com/news/" + str(i),
        } for i in range(20)]
        count = hydrate_articles({"ia": items}, self.now, fetcher=lambda a: self.long_text * 3)
        self.assertLessEqual(count, MAX_FETCH)
        self.assertEqual(items[0]["articleRead"], "public-html")


if __name__ == "__main__":
    unittest.main()
