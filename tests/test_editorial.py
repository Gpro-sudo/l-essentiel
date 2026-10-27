"""Contrôles minimaux du tri éditorial, sans accès au réseau."""
import unittest

from scripts.update_news import editorial_score, informative_summary, parse_time, is_media_self_promotion


class EditorialTests(unittest.TestCase):
    def test_major_event_ranks_above_literary_review(self):
        event = editorial_score(
            "Brésil : Lula réélu président à l'issue du scrutin",
            "Le chef de l'État remporte le second tour face à Flávio Bolsonaro.",
            rank=4, age_hours=2,
        )
        soft = editorial_score(
            "Un nouveau roman littéraire : plongée dans un univers singulier",
            "Un écrivain propose une fresque au sujet d'un fonctionnaire ordinaire.",
            rank=4, age_hours=2,
        )
        self.assertGreater(event, soft + 4)

    def test_weak_summary_rejected(self):
        self.assertFalse(informative_summary(
            "La Bourse de Casablanca ouvre en hausse",
            "La Bourse de Casablanca ouvre en hausse. La Bourse de Casablanca ouvre en hausse.",
        ))

    def test_specific_summary_accepted(self):
        self.assertTrue(informative_summary(
            "La Bourse de Casablanca ouvre en hausse",
            "Le MASI a progressé de 0,59 % ce lundi, porté par plusieurs valeurs bancaires.",
        ))

    def test_bdm_alert_article_is_self_promotion(self):
        self.assertTrue(is_media_self_promotion(
            "IA, SEO, cybersécurité… Créez votre alerte BDM pour suivre vos thématiques préférées",
            "Depuis votre profil BDM, vous pouvez sélectionner des thématiques "
            "afin de recevoir une sélection quotidienne d'articles.",
            "Blog du Modérateur",
        ))

    def test_real_cybersecurity_news_is_not_promotion(self):
        self.assertFalse(is_media_self_promotion(
            "Une faille de cybersécurité touche des entreprises françaises",
            "Les experts ont révélé une vulnérabilité et détaillé les correctifs.",
            "Blog du Modérateur",
        ))

    def test_external_product_launch_is_not_self_promotion(self):
        self.assertFalse(is_media_self_promotion(
            "Google lance un outil d'alertes sur la sécurité informatique",
            "Google annonce un nouvel outil destiné aux administrateurs systèmes.",
            "Blog du Modérateur",
        ))

    def test_2026_election_is_not_marked_as_old(self):
        date = parse_time("Mon, 26 Oct 2026 09:30:00 +0000")
        self.assertEqual(date.year, 2026)


if __name__ == "__main__":
    unittest.main()
