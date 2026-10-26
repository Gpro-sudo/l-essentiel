"""Ne jamais présenter une accroche comme un fait vérifié."""
import unittest

from scripts.headline_policy import (
    sensational, neutral_title_from_excerpt, validate_headline
)


class HeadlineTests(unittest.TestCase):
    def setUp(self):
        self.original = (
            "Un « monde hors ligne » : après un nouveau dérapage, "
            "OpenAI prend une décision radicale"
        )
        self.excerpt = (
            "OpenAI a décidé d'entraîner ses futurs modèles sans connexion Internet. "
            "Ce changement concerne certains modèles expérimentaux."
        )

    def test_sensational_headline_detected(self):
        self.assertTrue(sensational(self.original))
        self.assertTrue(sensational("Une décision radicale provoque un choc mondial"))
        self.assertFalse(sensational("OpenAI restreint l'accès à Internet durant un entraînement"))

    def test_extract_only_sentence_explicit_in_source(self):
        result = neutral_title_from_excerpt(self.original, self.excerpt)
        self.assertEqual(
            result, "OpenAI a décidé d'entraîner ses futurs modèles sans connexion Internet"
        )

    def test_do_not_invent_a_number(self):
        text = "OpenAI coupe Internet pour 100 modèles expérimentaux"
        self.assertIsNone(validate_headline(text, self.original, self.excerpt))

    def test_no_misleading_merged_status(self):
        original = "Tesla et SpaceX envisagent une fusion"
        summary = "Des discussions de fusion entre Tesla et SpaceX seraient en cours."
        self.assertIsNone(validate_headline(
            "Tesla et SpaceX ont fusionné pour former une nouvelle société",
            original, summary
        ))

    def test_keep_conditional_headline(self):
        original = "Tesla et SpaceX envisagent une fusion"
        summary = "Des discussions de fusion entre Tesla et SpaceX seraient en cours."
        self.assertEqual(
            validate_headline("Tesla et SpaceX envisagent une fusion", original, summary),
            "Tesla et SpaceX envisagent une fusion"
        )

    def test_short_or_question_headline_rejected(self):
        self.assertIsNone(validate_headline("Et maintenant ?", self.original, self.excerpt))
        self.assertIsNone(neutral_title_from_excerpt(self.original, "Une annonce fracassante !"))


if __name__ == "__main__":
    unittest.main()
