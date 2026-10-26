"""Dossier prioritaire sur le conflit du Golfe : sources publiques et requêtes ciblées.

Le contexte éditorial est explicitement daté : il n'est pas une mise à jour en direct.
Les dernières dépêches sont récupérées séparément et leur recoupement reste nécessaire.
"""
from __future__ import annotations

import re
import urllib.parse

AS_OF = "2026-10-26"

# Relevé vérifié manuellement le 26 octobre 2026 : ne jamais le redater
# automatiquement ou lui attribuer une heure de publication inventée.
PRIORITY_CONTEXT = {
    "id": "conflit-golfe",
    "category": "golfe",
    "asOf": AS_OF,
    "title": "Guerre dans le Golfe : conflit régional et détroit d'Ormuz",
    "summary": (
        "La guerre entre l'Iran, Israël et les États-Unis reste sans accord durable. "
        "Les attaques contre les navires perturbent le détroit d'Ormuz et les prix de l'énergie. "
        "Le 26 octobre, une réunion diplomatique à Téhéran cherche à éviter une nouvelle escalade."
    ),
    "note": "Contexte vérifié le 26 octobre 2026, pas un fil d'actualité en direct.",
    "sources": [
        {
            "name": "Council on Foreign Relations (23 oct.)",
            "url": "https://www.cfr.org/global-conflict-tracker/conflict/confrontation-between-united-states-and-iran",
        },
        {
            "name": "Ministère français de l'Économie (23 oct.)",
            "url": "https://www.tresor.economie.gouv.fr/Articles/2026/10/23/bilan-de-la-tournee-regionale-du-president-de-la-republique-19-21-octobre-2026",
        },
        {
            "name": "Reuters (26 oct.)",
            "url": "https://www.reuters.com/world/asia-pacific/top-officials-mecca-pact-countries-meet-iranian-officials-tehran-monday-two-2026-10-26/",
        },
        {
            "name": "Associated Press (26 oct.)",
            "url": "https://apnews.com/article/36486edb61b3bf4e0df67e8a17123e44",
        },
    ],
}

GULF_CONTEXT = re.compile(
    r"\b(?:iran|iranien\w*|teheran|téhéran|ormuz|hormuz|golfe persique|"
    r"golfe d.oman|houthis?|houthi|yemen|yémen|riyad|saoudi\w*|"
    r"bab.el.mandeb|detroit d.ormuz|détroit d.ormuz)\b", re.I
)
CONFLICT_CONTEXT = re.compile(
    r"\b(?:guerre|conflit|frappe\w*|attaque\w*|bombardement\w*|missile\w*|"
    r"drone\w*|navire\w*|pétrolier\w*|petrolier\w*|cessez.le.feu|"
    r"blocus|menace\w*|tension\w*|escala\w*|militaire\w*|négocia\w*|"
    r"negocia\w*|médiation\w*|mediation\w*|sécurité\w*|securite\w*|"
    r"sanction\w*|ports?|shipping|otan|hormuz|ormuz|mer rouge|"
    r"detroit|détroit|troupes?|diplomatie|petrole|pétrole|"
    r"gaz|énergie|energie|coalition)\b", re.I
)
# Assurer que "golfe" seul ne récupère pas le sport "golf".
SPORT_GOLF = re.compile(r"\b(?:golfeur|golfeuse|golf|pga tour|ryder cup)\b", re.I)


def gulf_relevant(title: str, summary: str = "") -> bool:
    text = f"{title} {summary}"
    return (not SPORT_GOLF.search(title) and bool(GULF_CONTEXT.search(text))
            and bool(CONFLICT_CONTEXT.search(text)))


def targeted_feeds() -> list[dict]:
    terms = [
        '"Iran" "Ormuz" (guerre OR attaques OR négociations) when:3d',
        '"Arabie saoudite" "Houthis" (guerre OR frappes OR médiation) when:3d',
        '"Iran" "États-Unis" "Israël" (conflit OR guerre OR négociations) when:3d',
        '"détroit d’Ormuz" (navires OR pétroliers OR blocus) when:3d',
    ]
    feeds = []
    for term in terms:
        url = "https://news.google.com/rss/search?" + urllib.parse.urlencode({
            "q": term, "hl": "fr", "gl": "FR", "ceid": "FR:fr"
        })
        feeds.append({
            "category": "golfe",
            "name": "Google Actualités",
            "url": url,
            "rank": 6,
            "google_news": True,
            "gulf_only": True,
        })
    return feeds


def spotlight(latest: dict | None = None) -> dict:
    """Un fait de contexte daté +, éventuellement, un nouvel article recoupé."""
    result = {**PRIORITY_CONTEXT}
    if latest:
        result["latest"] = {
            "title": latest["title"],
            "summary": latest["summary"],
            "publishedAt": latest["publishedAt"],
            "sources": latest["verification"]["sources"],
        }
    return result
