"""Veille IPO/MASI : sélection ciblée et conservation des dates de contexte."""
import unittest
from scripts.finance_maroc import targeted_finance_feeds, is_maroc_market, finance_digest
from scripts.update_news import FEEDS


class FinanceMarocTests(unittest.TestCase):
    def test_ipos_and_masi_are_included(self):
        self.assertTrue(is_maroc_market("JET ENERGY : lancement de l'introduction en bourse"))
        self.assertTrue(is_maroc_market("Le MASI recule à la Bourse de Casablanca"))
        self.assertTrue(is_maroc_market("L'AMMC vise un nouveau prospectus d'introduction en Bourse"))
        self.assertTrue(is_maroc_market("Les rendements obligataires affectent les valorisations"))

    def test_unrelated_news_not_mislabeled(self):
        self.assertFalse(is_maroc_market("Les élections en Amérique latine avancent"))
        self.assertFalse(is_maroc_market("Un festival de cinéma a lieu à Rabat"))

    def test_feeds_are_moroccan_finance_only(self):
        feeds=targeted_finance_feeds()
        self.assertGreaterEqual(len(feeds), 4)
        self.assertTrue(all(f.get("google_news") and f.get("finance_only") for f in feeds))
        self.assertTrue(all(f["category"]=="eco-maroc" for f in feeds))
        self.assertGreaterEqual(len([f for f in FEEDS if f.get("finance_only")]), 4)

    def test_context_is_never_passed_off_as_live_quote(self):
        news=finance_digest()
        self.assertEqual(news["asOf"], "2026-10-27")
        self.assertEqual(news["lastOfficialSession"], "2026-10-26")
        self.assertEqual(news["ipo"]["firstListing"], "16 novembre 2026 (prévue)")
        self.assertIn("Selon CFG Research",news["market"]["analysis"])
        self.assertGreaterEqual(len(news["sources"]), 3)


if __name__=="__main__":
    unittest.main()
