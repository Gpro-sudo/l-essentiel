"""Conserver temporairement les synthèses IA déjà validées entre deux déploiements.

Une panne de modèle gratuit ne doit pas effacer des résumés encore récents.
Ne réutilise les synthèses que si l'événement, la date, le titre et la source
sont identiques et que le recoupement est toujours positif.
"""
from __future__ import annotations

import datetime as dt
import json
import urllib.request

from scripts.ai_summarize import validate_summary

PREVIOUS_URL = "https://gpro-sudo.github.io/l-essentiel/news.json"


def restore_recent_summaries(buckets: dict, now: dt.datetime, fetch=None) -> int:
    needs = {
        a["id"]: a
        for arr in buckets.values()
        for a in arr
        if a.get("verification", {}).get("status") == "corroborated"
        and a.get("summaryType") != "ai"
    }
    if not needs:
        return 0

    if fetch is None:
        def fetch():
            req = urllib.request.Request(
                PREVIOUS_URL + "?refresh=" + str(int(now.timestamp())),
                headers={"User-Agent": "LEssentielNewsVerifier/2.0", "Cache-Control": "no-cache"},
            )
            with urllib.request.urlopen(req, timeout=7) as response:
                return json.loads(response.read(700_000))
    try:
        prior = fetch()
        prev_generated = dt.datetime.fromisoformat(prior["generatedAt"].replace("Z", "+00:00"))
        gap = (now - prev_generated).total_seconds()
        if gap < -3600 or gap > 30 * 3600:
            return 0
        published = [a for arr in prior.get("categories", {}).values() for a in arr]
        restored = 0
        for old in published:
            if old.get("summaryType") != "ai":
                continue
            current = needs.get(old.get("id"))
            if current is None:
                continue
            if any(old.get(field) != current.get(field) for field in ("id", "title", "source", "publishedAt")):
                continue
            try:
                date = dt.datetime.fromisoformat(current["publishedAt"].replace("Z", "+00:00"))
            except (TypeError, ValueError):
                continue
            if not (0 <= (now - date).total_seconds() < 24 * 3600):
                continue
            summary = validate_summary(
                old.get("summary"), current["title"],
                current.get("_sourceText") or current.get("summary", "")
            )
            if not summary:
                continue
            current["summary"] = summary
            current["summaryType"] = "ai"
            current["summaryCached"] = True
            restored += 1
        if restored:
            print(f"Synthèses IA antérieures réutilisées : {restored}.")
        return restored
    except (OSError, ValueError, TypeError, KeyError, AttributeError, json.JSONDecodeError):
        return 0
