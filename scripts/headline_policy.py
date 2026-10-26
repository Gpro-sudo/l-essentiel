"""Politique de titrage : neutre, prudent et traçable.

Aucun titre automatique n'est certifié exact par cet outil.
Le titre d'origine reste conservé et consultable avec le lien de source.
"""
from __future__ import annotations

import re
import unicodedata

SENSATIONAL = re.compile(
    r"\b(?:decision radicale|virage radical|depark|derapage|scandale|"
    r"coup de tonnerre|coup de theatre|choc|choc mondial|incroyable|"
    r"stup[eé]fiant|terrifiant|inquietant|panique|catastrophe|"
    r"rebondissement spectaculaire|va tout changer|va bouleverser|"
    r"nouveau seisme|personne ne s.y attendait|"
    r"vous n.allez pas croire|ce qu.il faut savoir|"
    r"le monde sous le choc|une revelation|une annonce fracassante)\b",
    re.I,
)
DRAMATIC_QUESTIONS = re.compile(
    r"\b(?:que cache|pourquoi (?:tout|personne)|faut.il avoir peur|"
    r"est.ce la fin|que se passe.t.il vraiment)\b",
    re.I,
)
STOP = frozenset(
    "pour avec dans sont sans apres avant cette leurs serait encore apres depuis "
    "face entre comme annonce decider nouveau nouvelle monde incroyable video "
    "direct source titre article selon explique decide decision radicale".split()
)
SPECULATION = re.compile(
    r"\b(?:envisag\w*|pourrai\w*|eventuel\w*|hypothes\w*|"
    r"discuss\w*|negoci\w*|rumeur\w*|projet|a l.etude|etudie\w*)\b"
)
CERTAINTY = re.compile(
    r"\b(?:fusionnent|ont fusionne|fusion definitive|fusion realisee|"
    r"rachat finalise|accord signe|loi adoptee|texte promulgue|"
    r"entre en vigueur|effectif|officialise)\b"
)


def normalize(value: str) -> str:
    s = unicodedata.normalize("NFKD", value.casefold())
    return "".join(c for c in s if not unicodedata.combining(c))


def sensational(title: str) -> bool:
    text = normalize(title)
    return bool(SENSATIONAL.search(text) or DRAMATIC_QUESTIONS.search(text)
                or (title.endswith("?!") or title.endswith("!!!")))


def _words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", normalize(text))
            if len(w) >= 4 and w not in STOP}


def _numbers(text: str) -> set[str]:
    return {x.replace(",", ".").replace(" ", "")
            for x in re.findall(r"(?<!\w)\d+(?:[.,]\d+)?\s*%?", text)}


def validate_headline(value: object, original: str, source_text: str) -> str | None:
    """Contrôles de surface, pas d'analyse sémantique ni fact-checking."""
    if not isinstance(value, str):
        return None
    title = re.sub(r"\s+", " ", value).strip().strip('"«» ')
    if not (25 <= len(title) <= 115):
        return None
    if sensational(title) or any(x in title for x in ("!", "?", "…", "http", "<", ">")):
        return None
    source = original + " " + source_text
    if not _numbers(title).issubset(_numbers(source)):
        return None
    if len(_words(title) & _words(source)) < 2:
        return None
    # Éviter d'affirmer la conclusion d'un événement encore envisagé.
    context = normalize(source)
    if SPECULATION.search(context) and CERTAINTY.search(normalize(title)):
        return None
    return title


def neutral_title_from_excerpt(original: str, description: str) -> str | None:
    """Repli extractif : reprendre UNE phrase de la source sans ajout."""
    if not sensational(original) or not description:
        return None
    clean = re.sub(r"<[^>]+>", " ", description)
    clean = re.sub(r"\s+", " ", clean).strip()
    # N'utiliser qu'une première phrase complète (pas un teaser tronqué).
    first = re.split(r"(?<=[.!?])\s+", clean, maxsplit=1)[0].strip()
    first = first.rstrip(". ")
    if first.endswith("…") or len(first) > 115:
        return None
    return validate_headline(first, original, description)
