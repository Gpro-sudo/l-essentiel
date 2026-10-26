"""Recoupement prudent des nouvelles : RSS indépendant + recherche Google Actualités RSS.

La concordance de titres / extraits de plusieurs rédactions est une indication
de recoupement de l'événement, PAS une certification de tous ses détails.
Par défaut, aucune information n'est marquée recoupée sans deuxième rédaction.
"""
from __future__ import annotations

import concurrent.futures
import datetime as dt
import html
import re
import unicodedata
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

MAX_AGE_HOURS = 48
MAX_QUERIES = 21
GOOGLE_RSS = "https://news.google.com/rss/search"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; EssentielReader/2.0; +https://github.com/Gpro-sudo/l-essentiel)"}

STOP = frozenset("""
les des une dans pour avec sur aux est sont par ses qui que son elle lui plus mais
tout cette leur apres avant face contre fait faites avoir sans entre chez sous depuis
nouveau nouvelle nouveaux nouvelles cette ainsi encore selon suite direct video live
actualite actualites mise jour cela apres cette nous vous ils elles aurait avaient
sera sont annonce aupres entre pouvoir jeudi vendredi lundi mardi mercredi dimanche
samedi annee ans mois jours france maroc monde economie economique intelligence
artificielle high tech vers environ comment pourquoi politique etats pays grand
""".split())
# Même propriétaire / groupe éditorial, donc pas de fausse corroboration.
GROUPS = {
    "rfi": "france-medias-monde", "france 24": "france-medias-monde",
    "france24": "france-medias-monde",
    "franceinfo": "franceinfo", "france info": "franceinfo",
    "01net": "01net", "numerama": "numerama", "clubic": "clubic",
    "hespress fr": "hespress", "hespress": "hespress",
    "le courrier de l'atlas": "courrier-atlas",
}
STEPS = {
    "adoption": r"\b(adopte|adoption|approuve|approbation|vote|votee|promulgue)\b",
    "projet": r"\b(propose|proposition|envisage|projet|prevoit)\b",
    "examen": r"\b(examine|examen|discussion|debats|reexamine)\b",
    "annonce": r"\b(annonce|declare|affirme|revele|fait savoir)\b",
    "hausse": r"\b(hausse|progresse|augmentation|augmente|grimpe|monte|croissance)\b",
    "baisse": r"\b(baisse|recul|chute|diminue|baisse|degringole)\b",
    "election": r"\b(elu|elue|reelu|reelection|remporte|victoire|gagne)\b",
    "lancement": r"\b(lance|lancement|deploie|deploiement|met en service)\b",
}
ACTION_PATTERNS = {k: re.compile(v) for k, v in STEPS.items()}
BAD_STATES = frozenset({frozenset(("adoption", "projet")), frozenset(("adoption", "examen")),
                         frozenset(("hausse", "baisse"))})


def norm(text: str) -> str:
    chars = unicodedata.normalize("NFKD", html.unescape(text or "").casefold())
    result = "".join(c for c in chars if not unicodedata.combining(c))
    result = re.sub(r"\b(?:rd[ .-]*congo|republique democratique du congo)\b", "rdc", result)
    result = re.sub(r"\b(adopte|adoptee|adoptes|adoptees|adoption|adopter)\b", "adoption", result)
    result = re.sub(r"\b(reelu|reelue|reelection)\b", "reelection", result)
    return result


def keywords(text: str) -> set[str]:
    return {s for s in re.findall(r"[a-z0-9]+", norm(text)) if len(s) >= 4 and s not in STOP}


def owner(source: str) -> str:
    normalized = re.sub(r"[^a-z0-9 ]", "", norm(source))
    return GROUPS.get(normalized, normalized.strip())


def actions(text: str) -> set[str]:
    s = norm(text)
    return {k for k, p in ACTION_PATTERNS.items() if p.search(s)}


def compatible_events(a: str, b: str) -> bool:
    """Recoupement lexical conservateur ; une ressemblance thématique ne suffit pas."""
    wa, wb = keywords(a), keywords(b)
    both = wa & wb
    if len(both) < 3:
        return False
    if len(both) / max(1, min(len(wa), len(wb))) < .56:
        return False
    aa, ab = actions(a), actions(b)
    if any(x in aa and y in ab for pair in BAD_STATES for x in pair for y in pair if x != y):
        return False
    # Lorsque les deux titres précisent une étape, elles doivent être cohérentes.
    strong = {"adoption", "examen", "hausse", "baisse", "election", "lancement"}
    if aa & strong and ab & strong and not (aa & ab):
        return False
    return True


def search_terms(title: str) -> str:
    # Privilégier les mots les plus discriminants, sans rien inventer.
    clean = re.sub(r"^(?:DIRECT|VIDEO|VIDÉO|LIVE)\s*[:.\-]\s*", "", title, flags=re.I)
    words = [w for w in re.findall(r"[A-Za-zÀ-ÿ0-9]+", clean) if len(w) > 3 and norm(w) not in STOP]
    unique = list(dict.fromkeys(words))
    return " ".join(unique[:7])


def parse_pubdate(raw: str):
    from email.utils import parsedate_to_datetime
    try:
        value = parsedate_to_datetime(raw)
        return value.astimezone(dt.timezone.utc) if value.tzinfo else value.replace(tzinfo=dt.timezone.utc)
    except (ValueError, TypeError, IndexError):
        return None


def google_search(title: str, now: dt.datetime) -> list[dict]:
    query = search_terms(title)
    if not query:
        return []
    url = GOOGLE_RSS + "?" + urllib.parse.urlencode({
        "q": query + " when:3d", "hl": "fr", "gl": "FR", "ceid": "FR:fr"
    })
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=9) as response:
        xml = response.read(600_000)
    root = ET.fromstring(xml)
    result = []
    for item in root.findall("./channel/item")[:35]:
        raw_title = item.findtext("title", "").strip()
        source_tag = item.find("source")
        source = source_tag.text.strip() if source_tag is not None and source_tag.text else ""
        title_text = raw_title
        if source and title_text.endswith(" - " + source):
            title_text = title_text[:-(len(source) + 3)]
        pub = parse_pubdate(item.findtext("pubDate", ""))
        if not pub or not (-3600 <= (now - pub).total_seconds() <= MAX_AGE_HOURS * 3600):
            continue
        link = item.findtext("link", "")
        if not link.startswith("https://"):
            continue
        if source and title_text:
            result.append({"name": source, "group": owner(source), "title": title_text, "url": link, "publishedAt": pub.isoformat()})
    return result


def create_source(article: dict) -> dict:
    return {"name": article["source"], "url": article["url"], "title": article["title"]}


def corroborate(article: dict, pool: list[dict], extra: list[dict]) -> list[dict]:
    confirmations = [create_source(article)]
    original_owner = owner(article["source"])
    selected = {original_owner}
    options = [
        {"name": a["source"], "group": owner(a["source"]), "title": a["title"], "url": a["url"]}
        for a in pool if a["id"] != article["id"]
    ] + extra
    for candidate in options:
        group = candidate.get("group") or owner(candidate.get("name", ""))
        if not group or group in selected:
            continue
        if compatible_events(article["title"], candidate.get("title", "")):
            confirmations.append({"name": candidate["name"], "url": candidate["url"], "title": candidate["title"]})
            selected.add(group)
            if len(confirmations) >= 3:
                break
    return confirmations


def enrich_verification(buckets: dict, now: dt.datetime, resolver=None) -> dict:
    """Contrôle jusqu'à trois articles prioritaires par catégorie.

    Un échec RSS / réseau ne transforme jamais un article en fait « vérifié ».
    """
    resolver = resolver or google_search
    pool = [a for arr in buckets.values() for a in arr]
    targets = []
    for arr in buckets.values():
        recent = []
        for a in arr:
            try:
                published = dt.datetime.fromisoformat(a["publishedAt"].replace("Z", "+00:00"))
                age = (now - published).total_seconds() / 3600
                if -1 <= age <= 24 and float(a.get("score", 0)) >= 5.5:
                    recent.append(a)
            except (TypeError, KeyError, ValueError):
                continue
        targets.extend(sorted(recent, key=lambda a: a.get("score", 0), reverse=True)[:3])
    targets = targets[:MAX_QUERIES]
    search_results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=7) as executor:
        futures = {executor.submit(resolver, a["title"], now): a["id"] for a in targets}
        for fut in concurrent.futures.as_completed(futures):
            try:
                search_results[futures[fut]] = fut.result()[:35]
            except Exception:
                search_results[futures[fut]] = []
    count = 0
    for arr in buckets.values():
        for a in arr:
            sources = corroborate(a, pool, search_results.get(a["id"], []))
            verified = len(sources) >= 2
            a["verification"] = {
                "status": "corroborated" if verified else "single-source",
                "sourceCount": len(sources),
                "sources": sources,
            }
            if verified:
                count += 1
    return {"corroborated": count, "total": len(pool), "checked": len(targets)}
