"""Prépare des fichiers MP3 locaux pour les navigateurs sans API de voix.

Les fichiers sont régénérés dans dist/audio lors du déploiement GitHub Pages.
Le texte est celui du briefing, jamais l'article intégral. Aucun service cloud
de synthèse vocale ou API commerciale n'est utilisé.
"""
from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess
import sys

BASE = Path(__file__).resolve().parent.parent
NEWS = BASE / "news.json"
OUT = BASE / "dist" / "audio"
MAX_ARTICLES = 150
MAX_TEXT = 1100
ARTICLE_ID = re.compile(r"^[0-9a-f]{20}$")


def text_for_article(article: dict) -> str:
    title = str(article.get("displayTitle") or article.get("title") or "").strip()
    summary = str(article.get("summary") or "").strip()
    if not title or not summary:
        return ""
    if article.get("headlineCaution"):
        prefix = "Attention : titre du média potentiellement sensationnaliste. "
    else:
        prefix = ""
    if article.get("verification", {}).get("status") == "single-source" and not article.get("primarySource"):
        prefix += "Information provenant d'une seule rédaction, non recoupée. "
    return (prefix + title + ". " + summary)[:MAX_TEXT]


def text_for_finance(data: dict) -> str:
    if not isinstance(data, dict) or not data.get("market") or not data.get("ipo"):
        return ""
    ipo, market = data["ipo"], data["market"]
    parts = [
        "Point Bourse et IPO Maroc. Analyse historique datée du "
        + str(data.get("asOf") or "date non précisée") + ".",
        str(data.get("title", "")),
        "Le MASI clôturait à " + str(data.get("indexValue", "valeur inconnue")) +
        " points, variation " + str(data.get("indexChange", "")) + " lors de la séance du " +
        str(data.get("lastOfficialSession", "")) + ".",
        "Introduction en bourse annoncée de " + str(ipo.get("name", "")) + ".",
        str(ipo.get("status", "")) + ".",
        "Souscriptions prévues : " + str(ipo.get("subscription", "")) + ".",
        "Première cotation initialement prévue : " + str(ipo.get("firstListing", "")) + ".",
        "Prix indicatif : " + str(ipo.get("price", "")) + ".",
        "Montant de l'opération : " + str(ipo.get("amount", "")) + ".",
        str(ipo.get("detail", "")),
        "Pourquoi le MASI corrige. " + str(market.get("fact", "")),
        "Perspectives. " + str(market.get("analysis", "")),
        "Indicateurs à surveiller. " + str(market.get("watch", "")),
        "Ce point n'est pas un cours en temps réel ni un conseil de placement. "
        "Vérifiez les annonces et les cours à jour avant toute décision.",
    ]
    return " ".join(x.strip() for x in parts if x).strip()


def synthesize_mp3(text: str, target: Path) -> bool:
    """Espeak-ng et FFmpeg sont exécutés sans shell ni interpolation de commandes."""
    if not text.strip():
        return False
    try:
        wave = subprocess.run(
            ["espeak-ng", "-v", "fr", "-s", "155", "--stdin", "--stdout"],
            input=text.encode("utf-8"), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=25, check=True,
        ).stdout
        if not wave:
            return False
        encoded = subprocess.run(
            ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
             "-i", "pipe:0", "-ac", "1", "-ar", "22050",
             "-codec:a", "libmp3lame", "-b:a", "40k", str(target)],
            input=wave, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=30,
        )
        if encoded.returncode or not target.exists() or target.stat().st_size < 1000:
            target.unlink(missing_ok=True)
            return False
        return True
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        target.unlink(missing_ok=True)
        return False


def generate(news: dict, target: Path = OUT, maker=synthesize_mp3) -> dict:
    target.mkdir(parents=True, exist_ok=True)
    result = {"version": 1, "items": {}, "finance": ""}
    if news.get("financialBriefing"):
        destination = target / "finance.mp3"
        if maker(text_for_finance(news["financialBriefing"]), destination):
            result["finance"] = "audio/finance.mp3"
    seen = set()
    for articles in news.get("categories", {}).values():
        for a in articles:
            identifier = str(a.get("id") or "")
            if identifier in seen or not ARTICLE_ID.fullmatch(identifier):
                continue
            if len(seen) >= MAX_ARTICLES:
                break
            seen.add(identifier)
            destination = target / (identifier + ".mp3")
            if maker(text_for_article(a), destination):
                result["items"][identifier] = "audio/" + identifier + ".mp3"
    (target / "manifest.json").write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
    return result


def main():
    if not NEWS.exists():
        print("Erreur : news.json absent", file=sys.stderr)
        return 1
    news = json.loads(NEWS.read_text(encoding="utf-8"))
    manifest = generate(news)
    print("Audio compatible mobile :",
          len(manifest["items"]), "brèves MP3 ; point Bourse :", bool(manifest["finance"]))
    # Le fichier manifest est publié même si aucun MP3 n'est disponible :
    # le navigateur peut alors afficher un statut explicite.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
