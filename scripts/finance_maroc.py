"""Veille ciblée : économie financière marocaine, IPO, MASI et communiqués.

Un point marché documenté peut être visible en priorité, mais ses chiffres
restent DATÉS ; les articles plus récents proviennent de la collecte RSS.
Pas de cours en temps réel ni de conseils d'achat.
"""
from __future__ import annotations

import re
import urllib.parse

ECO_TERMS = re.compile(
    r"\b(?:masi(?:\s*20)?|bourse de casablanca|introduction en bourse|"
    r"\bipo\b|ammc|jet energy|jet contractors|march[eé]s? actions?|"
    r"valeurs cot[eé]es|r[eé]sultats? trimestriels?|"
    r"dividende\w*|taux obligataires?|bons? du tr[eé]sor|"
    r"rendements? obligataires?|souscriptions?|cours des actions|"
    r"bank al.maghrib|valorisation|per boursier|"
    r"\bbkgr\b|\bcfg research\b)\b", re.I
)

# Faits de contexte, vérifiés et figés au 27 octobre 2026, pas prix live.
MARKET_CONTEXT = {
    "asOf": "2026-10-27",
    "lastOfficialSession": "2026-10-26",
    "indexValue": "16 999,56",
    "indexChange": "−0,32 %",
    "title": "Bourse de Casablanca : correction du MASI et IPO de Jet Energy",
    "ipo": {
        "name": "Jet Energy",
        "status": "Prospectus visé le 21 octobre par l’AMMC",
        "price": "125 à 143 DH par action (fourchette, prix non définitif)",
        "amount": "328,1 à 375,4 MDH à lever",
        "subscription": "2 au 5 novembre 2026, 15 h 30",
        "firstListing": "16 novembre 2026 (prévue)",
        "detail": (
            "Jet Energy, filiale solaire de Jet Contractors, émet 2 625 000 "
            "actions nouvelles, représentant 20 % du capital après opération. "
            "Le prix définitif est prévu le 11 novembre. "
            "Le carnet de commandes communiqué par la direction atteint "
            "près de 1,5 milliard DH à fin juin 2026, sans garantie sur "
            "la réalisation future du chiffre d'affaires."
        ),
    },
    "market": {
        "fact": (
            "Le MASI a perdu environ 12 % entre fin août et octobre 2026, "
            "alors que les bénéfices semestriels agrégés des sociétés cotées "
            "ont augmenté de 7,4 % : la baisse des cours ne s'explique donc "
            "pas simplement par de mauvais résultats."
        ),
        "analysis": (
            "Selon CFG Research, la remontée des rendements obligataires, "
            "les tensions de liquidité et les risques d'inflation liés à "
            "l'énergie pèsent sur les valorisations. Une détente des taux "
            "pourrait aider le marché, mais une nouvelle pression sur les "
            "taux ou sur les marges pourrait prolonger la correction."
        ),
        "watch": (
            "À surveiller : taux des bons du Trésor, prix de l'énergie, "
            "publications de résultats trimestriels, multiples de "
            "valorisation des titres et calendrier des IPO. "
            "Ces scénarios ne constituent pas une prévision de cours."
        ),
    },
    "sources": [
        {"name": "AMMC · Visa Jet Energy (21 oct.)",
         "url": "https://www.ammc.ma/fr/node/55917"},
        {"name": "Bourse de Casablanca · cours et indices",
         "url": "https://www.casablanca-bourse.com/"},
        {"name": "Médias24 · Jet Energy (22 oct.)",
         "url": "https://medias24.com/2026/10/22/ipo-de-jet-energy-jusqua-3754-mdh-a-lever-les-souscriptions-du-2-au-5-novembre-1782720/"},
        {"name": "Boursenews · CFG Research (20 oct.)",
         "url": "https://boursenews.ma/article/decryptage/bourse-casablanca-quatre-facteurs-hausse-taux-longs-correction-masi"},
    ],
}


def targeted_finance_feeds() -> list[dict]:
    queries = [
        '"Jet Energy" ("introduction en bourse" OR IPO OR souscription) when:7d',
        '("MASI" OR "Bourse de Casablanca") (baisse OR hausse OR clôture) when:3d',
        '(AMMC OR "Bourse de Casablanca") (introduction OR visa OR OPA) when:7d',
        '("Bourse de Casablanca" OR MASI) (perspectives OR valorisations OR taux obligataires) when:7d',
        'site:medias24.com (MASI OR bourse OR IPO) when:7d',
        'site:boursenews.ma ("MASI" OR "Jet Energy") when:7d',
    ]
    return [{
        "category": "eco-maroc",
        "name": "Google Actualités",
        "url": "https://news.google.com/rss/search?" + urllib.parse.urlencode({
            "q": q, "hl": "fr", "gl": "MA", "ceid": "MA:fr"
        }),
        "rank": 6,
        "google_news": True,
        "finance_only": True,
    } for q in queries]


def is_maroc_market(title: str, summary: str = "") -> bool:
    return bool(ECO_TERMS.search((title or "") + " " + (summary or "")))


def finance_digest():
    # Return a shallow copy; never infer a new date or update static prices.
    return dict(MARKET_CONTEXT)
