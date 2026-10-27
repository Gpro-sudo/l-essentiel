"""Prépare les MP3 locaux et, sur activation explicite, les voix Google Cloud.

Google Cloud TTS est utilisé uniquement lorsque la clé de service sécurisée
est configurée dans GitHub Actions. Réutilise les MP3 par hachage du texte et
s'arrête au budget logiciel indiqué ; n'effectue aucun appel non authentifié.
"""
from __future__ import annotations

import base64
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request

BASE = Path(__file__).resolve().parent.parent
NEWS = BASE / "news.json"
OUT = BASE / "dist" / "audio"
MAX_ARTICLES = 150
MAX_TEXT = 1100
ARTICLE_ID = re.compile(r"^[0-9a-f]{20}$")
GOOGLE_VOICE = os.environ.get("GOOGLE_TTS_VOICE", "fr-FR-Chirp3-HD-Aoede")
GOOGLE_MAX_NEW_PER_BUILD = 6
GOOGLE_MAX_NEW_CHARS_PER_BUILD = 1850
GOOGLE_MONTHLY_SOFT_CAP_CHARS = 650000
CACHE = BASE / ".tts-cache" / "google"
VOICE_ALLOWED = re.compile(r"^fr-FR-(?:Chirp3-HD-[A-Za-z]+|Neural2-[A-Z]|Wavenet-[A-Z])$")


def google_credentials():
    """Le secret n'est lu que côté workflow et n'est jamais écrit dans dist."""
    raw = os.environ.get("GOOGLE_TTS_SERVICE_ACCOUNT_JSON", "").strip()
    if not raw:
        return None
    try:
        from google.oauth2 import service_account
        from google.auth.transport.requests import Request
        info = json.loads(raw)
        cred = service_account.Credentials.from_service_account_info(
            info, scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        cred.refresh(Request())
        return cred.token
    except (ImportError, ValueError, KeyError, TypeError) as exc:
        print(f"Google Cloud TTS non initialisé ({type(exc).__name__}).", file=sys.stderr)
        return None
    except Exception as exc:
        # Never output credentials or the full exception body.
        print(f"Google Cloud TTS : échec de l'authentification ({type(exc).__name__}).", file=sys.stderr)
        return None


def google_synthesize(text: str, target: Path, token: str, voice: str = GOOGLE_VOICE) -> bool:
    """Google Cloud TTS REST, MP3. Aucun secret dans les URLs ou le dépôt."""
    if not token or not VOICE_ALLOWED.fullmatch(voice) or not text or len(text.encode("utf-8")) > 4600:
        return False
    body = json.dumps({
        "input": {"text": text},
        "voice": {"languageCode": "fr-FR", "name": voice},
        "audioConfig": {"audioEncoding": "MP3"},
    }, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        "https://texttospeech.googleapis.com/v1/text:synthesize",
        data=body,
        headers={
            "Authorization": "Bearer " + token,
            "Content-Type": "application/json; charset=utf-8",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            content = json.loads(response.read(2_000_000))
        mp3 = base64.b64decode(content["audioContent"], validate=True)
        if len(mp3) < 1000 or len(mp3) > 1_500_000:
            return False
        target.write_bytes(mp3)
        return True
    except (OSError, ValueError, KeyError, TypeError, urllib.error.HTTPError) as exc:
        target.unlink(missing_ok=True)
        print(f"Google TTS : génération indisponible ({type(exc).__name__}).", file=sys.stderr)
        return False


class GoogleAudio:
    """Gestion des quotas logiciels sur CE dépôt, pas un plafond Google Cloud."""
    def __init__(self, cache: Path = CACHE, token: str | None = None,
                 voice: str = GOOGLE_VOICE, writer=google_synthesize):
        self.token = token
        self.voice = voice if VOICE_ALLOWED.fullmatch(voice) else "fr-FR-Chirp3-HD-Aoede"
        self.cache = cache
        self.writer = writer
        self.new_count = 0
        self.new_chars = 0
        self.disabled = not bool(token)
        self.month = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m")
        self.ledger = cache / ("usage-" + self.month + ".json")
        try:
            self.month_chars = max(0, int(json.loads(self.ledger.read_text()).get("chars", 0)))
        except (ValueError, OSError, KeyError, TypeError, AttributeError):
            self.month_chars = 0

    def create(self, text: str, destination: Path) -> bool:
        if self.disabled or not text:
            return False
        digest = hashlib.sha256((self.voice + "\n" + text).encode("utf-8")).hexdigest()
        cached = self.cache / (digest + ".mp3")
        if cached.exists() and cached.stat().st_size > 1000:
            shutil.copyfile(cached, destination)
            return True
        chars = len(text)
        if (self.new_count >= GOOGLE_MAX_NEW_PER_BUILD or
                self.new_chars + chars > GOOGLE_MAX_NEW_CHARS_PER_BUILD or
                self.month_chars + chars > GOOGLE_MONTHLY_SOFT_CAP_CHARS):
            return False
        if not self.writer(text, destination, self.token, self.voice):
            self.disabled = True  # ne pas insister sur les erreurs d'API
            return False
        self.cache.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(destination, cached)
        self.new_count += 1
        self.new_chars += chars
        self.month_chars += chars
        self.ledger.write_text(json.dumps({"chars": self.month_chars, "month": self.month}))
        return True



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


def generate(news: dict, target: Path = OUT, maker=synthesize_mp3, google=None) -> dict:
    target.mkdir(parents=True, exist_ok=True)
    result = {"version": 1, "items": {}, "finance": "",
              "google": {"items": {}, "finance": "", "voice": ""}}
    if news.get("financialBriefing"):
        destination = target / "finance.mp3"
        finance_text = text_for_finance(news["financialBriefing"])
        if maker(finance_text, destination):
            result["finance"] = "audio/finance.mp3"
        if google and google.create(finance_text, target / "finance-google.mp3"):
            result["google"]["finance"] = "audio/finance-google.mp3"
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
            script = text_for_article(a)
            if maker(script, destination):
                result["items"][identifier] = "audio/" + identifier + ".mp3"
            if google and google.create(script, target / (identifier + "-google.mp3")):
                result["google"]["items"][identifier] = "audio/" + identifier + "-google.mp3"
    if google and not google.disabled or result["google"]["finance"] or result["google"]["items"]:
        result["google"]["voice"] = google.voice
    (target / "manifest.json").write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
    return result


def main():
    if not NEWS.exists():
        print("Erreur : news.json absent", file=sys.stderr)
        return 1
    news = json.loads(NEWS.read_text(encoding="utf-8"))
    token = google_credentials()
    google = GoogleAudio(token=token) if token else None
    manifest = generate(news, google=google)
    if google:
        print("Google TTS :", len(manifest["google"]["items"]),
              "brèves HD ; nouveau budget de ce lancement :", google.new_chars,
              "caractères ; cumul estimé du mois :", google.month_chars)
    print("Audio compatible mobile :",
          len(manifest["items"]), "brèves MP3 ; point Bourse :", bool(manifest["finance"]))
    # Le fichier manifest est publié même si aucun MP3 n'est disponible :
    # le navigateur peut alors afficher un statut explicite.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
