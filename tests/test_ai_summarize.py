"""Tests sans réseau pour la synthèse IA et son repli RSS."""
import datetime as dt
import json
import os
import unittest
from unittest.mock import patch

from scripts.ai_summarize import (
    _numbers, parse_response, select_articles, summarize_buckets, validate_summary,
)


class MockHTTPResponse:
    def __init__(self, payload):
        self.payload = json.dumps(payload).encode("utf-8")
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def read(self, max_bytes):
        return self.payload[:max_bytes]


class SummaryTests(unittest.TestCase):
    def setUp(self):
        self.now = dt.datetime(2026, 10, 26, 12, tzinfo=dt.timezone.utc)
        self.article = {
            "id": "a1",
            "category": "eco-maroc",
            "title": "La Bourse de Casablanca ouvre en hausse",
            "summary": "Le MASI a progressé de 0,59 % ce lundi, tiré par plusieurs valeurs bancaires.",
            "_sourceText": "Le MASI a progressé de 0,59 % ce lundi, tiré par plusieurs valeurs bancaires.",
            "score": 11,
            "publishedAt": "2026-10-26T10:00:00Z",
            "verification": {
                "status": "corroborated",
                "sourceCount": 2,
                "sources": [
                    {"name": "Hespress", "title": "La Bourse de Casablanca ouvre en hausse"},
                    {"name": "Medias24", "title": "Casablanca : la Bourse ouvre en hausse"},
                ],
            },
        }
        self.buckets = {"eco-maroc": [self.article]}

    def test_select_one_article_recent(self):
        self.assertEqual(select_articles(self.buckets, self.now), [self.article])

    def test_skip_old_article(self):
        self.article["publishedAt"] = "2026-10-24T10:00:00Z"
        self.assertEqual(select_articles(self.buckets, self.now), [])

    def test_json_with_markdown_fence(self):
        response = chr(96) * 3 + 'json\n{"items":[{"id":"a1","summary":"Exemple valable."}]}\n' + chr(96) * 3
        self.assertEqual(parse_response(response)[0]["id"], "a1")

    def test_reject_invented_number(self):
        self.assertIsNone(validate_summary(
            "Le MASI bondit de 4 % alors que les investisseurs restent confiants.",
            self.article["title"], self.article["_sourceText"]
        ))

    def test_accept_grounded_summary(self):
        text = "Le MASI gagne 0,59 % à l'ouverture lundi, soutenu par plusieurs valeurs bancaires."
        self.assertEqual(validate_summary(text, self.article["title"], self.article["_sourceText"]), text)

    def test_no_key_keeps_original(self):
        old = self.article["summary"]
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": ""}):
            self.assertEqual(summarize_buckets(self.buckets, self.now), 0)
        self.assertEqual(self.article["summary"], old)
        self.assertNotIn("summaryType", self.article)

    def test_one_batched_result(self):
        text = "Le MASI gagne 0,59 % à l'ouverture lundi, soutenu par plusieurs valeurs bancaires."
        reply = {"choices": [{"message": {"content": json.dumps(
            {"items": [{"id": "a1", "summary": text}]},
            ensure_ascii=False
        )}}]}
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test_key"}), patch(
            "scripts.ai_summarize.urllib.request.urlopen",
            return_value=MockHTTPResponse(reply)
        ) as call:
            self.assertEqual(summarize_buckets(self.buckets, self.now), 1)
            self.assertEqual(call.call_count, 1)
        self.assertEqual(self.article["summaryType"], "ai")
        self.assertEqual(self.article["summary"], text)


if __name__ == "__main__":
    unittest.main()
