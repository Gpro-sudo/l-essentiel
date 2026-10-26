"""Corrections éditoriales documentées auprès de sources primaires.

Aucune correction n'est produite par IA et chaque entrée est ciblée sur un
événement donné. Le document primaire confirme des déclarations de l'organisation
et ne constitue PAS une seconde rédaction indépendante.
"""
from __future__ import annotations

import datetime as dt
import re
import unicodedata

OPENAI_PRIMARY = {
    "name": "OpenAI — publication technique du 23 octobre 2026",
    "url": "https://openai.com/index/securing-our-frontier-model-training-environment/",
    "publishedAt": "2026-10-23",
}


def norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", (text or "").casefold())
    return "".join(c for c in text if not unicodedata.combining(c))


def apply_primary_correction(article: dict, now: dt.datetime) -> bool:
    """Corriger uniquement l'histoire du 26 octobre sur la sécurité OpenAI.

    Ne pas appliquer ce texte à toutes les annonces d'OpenAI, ou à un article
    d'une autre période. Le résumé reste explicitement attribué à OpenAI.
    """
    title = norm(article.get("title", ""))
    excerpt = norm(article.get("_sourceText", "") or article.get("summary", ""))
    source = norm(article.get("source", ""))
    if article.get("category") not in {"ia", "tech"}:
        return False
    if "01net" not in source:
        return False
    if "openai" not in title:
        return False
    if not (("monde hors ligne" in title and "radicale" in title)
            or ("prison numerique" in excerpt and "openai" in excerpt)):
        return False
    if not (dt.date(2026, 10, 23) <= now.date() <= dt.date(2026, 11, 2)):
        return False

    article["displayTitle"] = "OpenAI renforce l'isolement de ses modèles pendant leur entraînement"
    article["titleType"] = "primary"
    article["summary"] = (
        "Lors de tests internes, un modèle expérimental d'OpenAI a obtenu un accès limité "
        "à Internet grâce à une faille DNS. D'autres tests ont montré des possibilités "
        "de contourner l'isolement des systèmes. OpenAI a annoncé un entraînement hors "
        "ligne pour ses modèles de pointe afin de renforcer la sécurité."
    )
    article["summaryType"] = "primary"
    article["primarySource"] = dict(OPENAI_PRIMARY)
    article["primaryNote"] = "Résumé fondé sur la publication technique d'OpenAI, pas sur un second média indépendant."
    article.pop("headlineCaution", None)
    return True
