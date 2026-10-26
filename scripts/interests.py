"""Thématiques suivies et identifiants d'histoires pour éviter les répétitions.

Les mots clés sont des heuristiques de navigation, pas des validations éditoriales.
Ne pas confondre un rapprochement envisagé avec une fusion réalisée.
"""
from __future__ import annotations
import hashlib
import re
import unicodedata
import urllib.parse

SEARCH_URL = "https://news.google.com/rss/search"


def normalized(s: str) -> str:
    s = unicodedata.normalize("NFKD", (s or "").lower())
    return "".join(c for c in s if not unicodedata.combining(c))


MERGER = re.compile(
    r"\b(?:fusion\w*|merger|merge|rapprochement|combinaison|combin\w*|"
    r"pourparlers|discut\w*|envisag\w*|rachet\w*)\b", re.I
)

ENTITY_TOPICS = [
    ("tesla", "Tesla"), ("spacex", "SpaceX"), ("starlink", "Starlink"),
    ("byd", "BYD"), ("renault", "Renault"), ("stellantis", "Stellantis"),
    ("volkswagen", "Volkswagen"), ("toyota", "Toyota"), ("audi", "Audi"),
    ("bmw", "BMW"), ("mercedes", "Mercedes-Benz"), ("volvo", "Volvo"),
    ("ford", "Ford"), ("general motors", "General Motors"),
    ("openai", "OpenAI"), ("nvidia", "Nvidia"), ("anthropic", "Anthropic"),
    ("microsoft", "Microsoft"), ("apple", "Apple"),
    ("iran", "Iran"), ("ormuz", "détroit d'Ormuz"),
]

STOP = set("les des pour avec dans vous nous une sur est sont dont avant apres tout entre"
           " vers sous sans chez plus selon cette comme leurs linfo nouveau nouvelles annonce"
           " cette lundi mardi mercredi jeudi vendredi samedi dimanche direct exclusif".split())


def classify_story(title: str, summary: str, category: str, article_id: str) -> tuple[str, str, str]:
    text = normalized(title + " " + summary)
    names = []
    for word, label in ENTITY_TOPICS:
        if re.search(r"(?<![a-z0-9])" + re.escape(word) + r"(?![a-z0-9])", text):
            names.append((word, label))

    # Une fusion envisagée reste distincte des projets communs comme Terafab.
    if {"tesla", "spacex"}.issubset({word for word, _ in names}) and MERGER.search(text):
        return "tesla-spacex-fusion", "Tesla / SpaceX — rapprochement", "tesla-spacex-fusion"
    if names:
        word, label = names[0]
        if word == "tesla" and any(w == "spacex" for w, _ in names):
            return "tesla-spacex", "Tesla + SpaceX", f"tesla-spacex-{article_id}"
        return f"topic-{word.replace(' ', '-')}", label, f"story-{article_id}"

    # Thème article-spécifique plutôt qu'un « j'aime » sur toute une rubrique.
    useful = [
        w for w in re.findall(r"[a-z0-9]+", normalized(title))
        if len(w) >= 4 and w not in STOP
    ][:5]
    key = "story-" + article_id
    label = " ".join(useful[:4]).strip().capitalize() or category
    return key, label[:64], key


def interest_feeds() -> list[dict]:
    queries = [
        'site:reuters.com/business/autos-transportation/ when:3d',
        '(Tesla SpaceX) (fusion OR rapprochement OR merger) when:3d',
        '(voitures OR constructeurs OR automobile) (BYD OR Renault OR Tesla OR Volkswagen) when:3d',
    ]
    return [
        {
            "category": "autos",
            "name": "Google Actualités",
            "url": SEARCH_URL + "?" + urllib.parse.urlencode({
                "q": query, "hl": "fr", "gl": "FR", "ceid": "FR:fr"
            }),
            "rank": 5,
            "google_news": True,
            "autos_topic_only": True,
        }
        for query in queries
    ]


def automotive_related(title: str, summary: str) -> bool:
    text = normalized(title + " " + summary)
    return bool(re.search(
        r"\b(?:tesla|spacex|voiture\w*|automobile\w*|constructeur\w*|"
        r"vehicule\w*|robotaxi\w*|transport\w*|audi|bmw|byd|renault|"
        r"stellantis|volkswagen|toyota|volvo|ford|general motors|fusion)\b", text
    )) and not bool(re.search(r"\b(?:golf professionnel|tournoi de golf)\b", text))
