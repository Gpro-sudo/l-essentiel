#!/usr/bin/env python3
"""Récupération RSS -> news.json (Python standard uniquement)."""
from __future__ import annotations

import concurrent.futures
import datetime as dt
import email.utils
import hashlib
import html
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

from scripts.ai_summarize import summarize_buckets
from scripts.cache_summaries import restore_recent_summaries
from scripts.verify_news import enrich_verification
from scripts.priority_gulf import targeted_feeds, gulf_relevant, spotlight
from scripts.interests import interest_feeds, classify_story, automotive_related
from scripts.headline_policy import sensational, neutral_title_from_excerpt
from scripts.editorial_facts import apply_primary_correction

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / 'news.json'
NOW = dt.datetime.now(dt.timezone.utc)
MAX_AGE_DAYS = 7
MAX_ITEMS_PER_CATEGORY = 18
CATEGORIES = ['golfe', 'monde', 'france', 'maroc', 'eco-maroc', 'eco-monde', 'autos', 'ia', 'tech']

# Sources choisies pour disposer de titres ET descriptions (RSS natifs des éditeurs).
# Les URL fonctionnelles relevées auprès d'annuaires de flux en octobre 2026.
FEEDS = [
    {'category': 'monde', 'name': 'RFI', 'url': 'https://www.rfi.fr/fr/monde/rss', 'rank': 4},
    {'category': 'golfe', 'name': 'RFI', 'url': 'https://www.rfi.fr/fr/moyen-orient/rss', 'rank': 6, 'gulf_only': True},
    {'category': 'golfe', 'name': 'France 24', 'url': 'https://www.france24.com/fr/moyen-orient/rss', 'rank': 5, 'gulf_only': True},
    {'category': 'monde', 'name': 'France 24', 'url': 'https://www.france24.com/fr/rss', 'rank': 3},
    {'category': 'monde', 'name': 'franceinfo', 'url': 'https://www.franceinfo.fr/monde.rss', 'rank': 3},
    {'category': 'france', 'name': 'franceinfo', 'url': 'https://www.franceinfo.fr/france.rss', 'rank': 4},
    {'category': 'france', 'name': 'RFI', 'url': 'https://www.rfi.fr/fr/france/rss', 'rank': 3},
    {'category': 'france', 'name': 'franceinfo', 'url': 'https://www.franceinfo.fr/politique.rss', 'rank': 3},
    {'category': 'maroc', 'name': 'Hespress FR', 'url': 'https://fr.hespress.com/feed', 'rank': 4, 'split_economy': True},
    {'category': 'maroc', 'name': 'Le Courrier de l’Atlas', 'url': 'https://www.lecourrierdelatlas.com/category/maroc/feed/', 'rank': 2, 'split_economy': True},
    # Deux flux d'économie riches en résumés ; le filtre exclut les sujets franco-français.
    {'category': 'eco-monde', 'name': 'RFI', 'url': 'https://www.rfi.fr/fr/rss', 'rank': 3, 'econ_only': True},
    {'category': 'eco-monde', 'name': 'France 24', 'url': 'https://www.france24.com/fr/rss', 'rank': 3, 'econ_only': True},
    {'category': 'ia', 'name': '01net', 'url': 'https://www.01net.com/rss/actus.xml', 'rank': 3, 'ai_only': True},
    {'category': 'ia', 'name': 'Numerama', 'url': 'https://www.numerama.com/tech/feed/', 'rank': 3, 'ai_only': True},
    {'category': 'ia', 'name': 'Blog du Modérateur', 'url': 'https://www.blogdumoderateur.com/feed/', 'rank': 3, 'ai_only': True},
    {'category': 'tech', 'name': '01net', 'url': 'https://www.01net.com/rss/actus.xml', 'rank': 3, 'non_ai': True},
    {'category': 'tech', 'name': 'Numerama', 'url': 'https://www.numerama.com/tech/feed/', 'rank': 3, 'non_ai': True},
    {'category': 'tech', 'name': 'Clubic', 'url': 'https://www.clubic.com/xml/news.rss', 'rank': 2, 'non_ai': True},
] + targeted_feeds() + interest_feeds()

MAROC_CONTEXT = re.compile(r'\b(?:maroc\w*|royaume|rabat|casablanca|tanger|fès|fes|marrakech|agadir|kénitra|kenitra|oujda|meknès|tetouan|tétouan|safi|laâyoune|dakhla|nador|berkane|salé|sale|bouskoura|bank al.maghrib|oncf|ocp|rni|pam|akhannouch|el mansouri|dirham\w*|makhzen)\b', re.I)
ECON_MA = re.compile(r'\b(?:économi\w*|finance\w*|financi\w*|investissement\w*|banque\w*|bank al.maghrib|dirham|inflation|bourse|casablanca finance|taux directeur|budget|fiscal\w*|exportation\w*|importation\w*|industrie\w*|tourisme|croissance|emploi\w*|entreprise\w*|PIB|commerce extérieur|agriculture|immobilier|logistique|port(?:uaire)?|énergie|renouvelable|ONCF|OCP|CDG|AMMC|impôt\w*|taxe\w*)\b', re.I)
ECON_WORLD = re.compile(r'\b(?:économie|économique|inflation|banques? centrales?|fédérale réserve|fed|bourse|marché financier|croissance|PIB|commerce mondial|droits? de douane|taxes? douanières|pétrole|prix du baril|brent|taux directeurs?|récession|emploi|industrie|investissement|dette publique|exportations?|OMC|FMI|BCE|commerce international|marchés? financiers?|Wall Street|tarifs? douaniers?|euro|dollar)\b', re.I)
AI_WORDS = re.compile(r'\b(?:intelligence artificielle|\bIA\b|\bAI\b|ChatGPT|OpenAI|Anthropic|Claude\b|Gemini\b|DeepSeek|Mistral AI|Copilot|LLM|modèle de langage|agents? IA|générative?s?|machine learning|Nvidia|Grok|xAI)\b', re.I)
GARBAGE = re.compile(r'(?:^|[\s:«])(?:vidéo\s*:|podcast\s*:|en direct\s*:|live\s*:|replay\s*:|bon plan\s*:|promos?\s*:|code promo|horoscope|programme tv|top 10|meilleurs? prix|où acheter|quel modèle choisir|test complet|avis et test|comparatif|notre sélection|guide d.achat|le prix chute|offre à saisir|offre folle|match en direct|résultats? du loto)', re.I)
SIGNIFICANCE = re.compile(r'\b(?:annonce|adopte|vote|accord|loi|réforme|baisse|hausse|augmente|diminue|lance|dévoile|publie|sanctionne|enquête|frappe|conflit|guerre|crise|inflation|élection|investissement|acquisition|fusion|déploiement|cyberattaque|faille|interdit|régulation|record|décision|accorde|condamne|signe|nouveau|résultat|rapport|découvre|développe|création|ouvre|ferme)\b', re.I)

# Signaux éditoriaux : il s'agit d'une priorisation, PAS d'une vérification des faits.
# Les sujets culturels restent accessibles dans « Tout », mais dominent moins « Essentiel ».
MAJOR_EVENT = re.compile(
    r'\b(?:président(?:e|ielle)?|réélu|réélection|premier ministre|gouvernement|parlement|'
    r'élections?|scrutin|référendum|taux directeur|banque centrale|inflation|budget|'
    r'déficit|croissance|investissement|acquisition|fusion|sanctions?|traité|'
    r'lois?|réformes?|conflit|guerre|cessez.le.feu|cyberattaque|piratage|'
    r'cybersécurité|séisme|inondations?|attentat|accords?|'
    r'augmentation|réduction|interdiction|démission|condamnation|'
    r'lancement|déploiement|recherche scientifique|découverte)\b', re.I
)
SOFT_TOPIC = re.compile(
    r'\b(?:roman|littérature|littéraire|écrivain|goncourt|célébrité|people|'
    r'séries? télé|cinéma|concert|spectacle|critique de film|'
    r'téléréalité|recettes? de cuisine|horoscope|football|match amical)\b', re.I
)
EVERGREEN = re.compile(
    r'\b(?:nos conseils|guide pratique|astuces?|tout savoir|'
    r'rétrospective|plongée dans|à (?:lire|voir) absolument|'
    r'il y a \d+ ans|comment choisir|que regarder)\b', re.I
)
PROMOTIONAL = re.compile(
    r'\b(?:découvrez|on vous dit tout|dans cet article|cliquez|'
    r'à découvrir|à ne pas manquer|notre sélection|vous explique)\b', re.I
)

class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.skipping = 0
    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self.skipping += 1
        elif tag in ('p', 'div', 'br', 'li'):
            self.parts.append(' ')
    def handle_endtag(self, tag):
        if tag in ('script', 'style'):
            self.skipping = max(0, self.skipping - 1)
        elif tag in ('p', 'div', 'li'):
            self.parts.append(' ')
    def handle_data(self, data):
        if not self.skipping:
            self.parts.append(data)

def clean_text(value: str) -> str:
    parser = TextExtractor()
    try:
        parser.feed(html.unescape(value or ''))
        s = ' '.join(parser.parts)
    except Exception:
        s = re.sub('<[^>]+>', ' ', value or '')
    s = html.unescape(s)
    s = re.sub(r'\s+', ' ', s).strip()
    s = re.sub(r'^(?:Image\s*:|Crédit photo\s*:|Photo\s*:|Lire la suite\s*:|DR\s*[-–])\s*', '', s, flags=re.I)
    return s

def concise(text: str, max_chars: int = 190) -> str:
    s = clean_text(text)
    # Certains RSS incluent des appels à l'action au début ou après le résumé.
    s = re.sub(r'\s*(?:Lire la suite|En savoir plus|Cet article est apparu en premier sur|Cliquez ici pour lire).*$', '', s, flags=re.I)
    if len(s) <= max_chars:
        return s
    snippet = s[:max_chars+1]
    ends = list(re.finditer(r'[.!?](?:\s|$)', snippet))
    usable = [m for m in ends if m.end() > 85]
    if usable:
        return snippet[:usable[-1].end()].strip()
    return snippet[:max_chars].rsplit(' ', 1)[0].rstrip(' ,;:') + '…'

def child_text(item: ET.Element, *names: str) -> str:
    for n in names:
        element = item.find(n)
        if element is None:
            element = item.find('{http://purl.org/rss/1.0/modules/content/}' + n)
        if element is not None and element.text:
            return element.text.strip()
    return ''

def parse_time(s: str):
    if not s:
        return None
    try:
        parsed = email.utils.parsedate_to_datetime(s)
        return parsed.astimezone(dt.timezone.utc) if parsed.tzinfo else parsed.replace(tzinfo=dt.timezone.utc)
    except (ValueError, TypeError, IndexError):
        pass
    try:
        return dt.datetime.fromisoformat(s.replace('Z', '+00:00')).astimezone(dt.timezone.utc)
    except (ValueError, TypeError):
        return None

def normalize_url(url: str) -> str:
    try:
        p = urllib.parse.urlsplit(url)
        if p.scheme not in ('https', 'http') or not p.netloc:
            return ''
        q = urllib.parse.parse_qsl(p.query, keep_blank_values=True)
        q = [(k, v) for (k, v) in q if not k.lower().startswith('utm_') and k.lower() not in ('fbclid','gclid','igshid')]
        return urllib.parse.urlunsplit((p.scheme, p.netloc, p.path, urllib.parse.urlencode(q), ''))
    except Exception:
        return ''

def fetch_feed(feed):
    req = urllib.request.Request(feed['url'], headers={
        'User-Agent': 'LEssentielPersonalReader/1.0 (+RSS reader; link to publishers)',
        'Accept': 'application/rss+xml,application/atom+xml,application/xml,text/xml,*/*',
    })
    try:
        with urllib.request.urlopen(req, timeout=17) as resp:
            data = resp.read(2_000_001)
            if len(data) > 2_000_000:
                raise ValueError('flux trop grand')
        root = ET.fromstring(data)
        items = root.findall('./channel/item')
        if not items:
            # Atom minimal
            ns = {'a': 'http://www.w3.org/2005/Atom'}
            items = root.findall('a:entry', ns)
        output = []
        for item in items[:90]:
            title = clean_text(child_text(item, 'title', '{http://www.w3.org/2005/Atom}title'))
            url = child_text(item, 'link')
            if not url:
                atom_link = item.find('{http://www.w3.org/2005/Atom}link')
                if atom_link is not None:
                    url = atom_link.attrib.get('href', '')
            url = normalize_url(url)
            if not title or not url or len(title) < 20:
                continue
            publisher = feed['name']
            if feed.get('google_news'):
                publisher = clean_text(child_text(item, 'source'))
                if not publisher or publisher.lower() == 'google actualités':
                    continue
                suffix = ' - ' + publisher
                if title.endswith(suffix):
                    title = title[:-len(suffix)].strip()
            published = parse_time(child_text(item, 'pubDate', 'date', '{http://www.w3.org/2005/Atom}published', '{http://www.w3.org/2005/Atom}updated', '{http://purl.org/dc/elements/1.1/}date'))
            if not published or published > NOW + dt.timedelta(hours=1) or published < NOW - dt.timedelta(days=MAX_AGE_DAYS):
                continue
            # Contenu: préférence pour la description courte de l'éditeur (pas le corps complet).
            description = child_text(item, 'description', '{http://www.w3.org/2005/Atom}summary')
            if not description:
                description = child_text(item, '{http://purl.org/rss/1.0/modules/content/}encoded', '{http://www.w3.org/2005/Atom}content')
            summary = concise(description)
            # Pas de pseudo-résumés inventés: si rien n'est fourni, on ignore l'entrée.
            if not summary or not informative_summary(title, summary):
                continue
            if GARBAGE.search(title):
                continue
            if feed.get('gulf_only') and not gulf_relevant(title, summary):
                continue
            if feed.get('autos_topic_only') and not automotive_related(title, summary):
                continue
            # Le flux Hespress est généraliste : ne pas mélanger les articles étrangers à la rubrique Maroc.
            if feed['name'] == 'Hespress FR' and not MAROC_CONTEXT.search(f'{title} {summary}'):
                continue
            category = feed['category']
            if feed.get('split_economy'):
                category = 'eco-maroc' if ECON_MA.search(title) else 'maroc'
            if feed.get('econ_only') and not ECON_WORLD.search(title):
                continue
            if feed.get('ai_only') and not AI_WORDS.search(title):
                continue
            if feed.get('non_ai') and AI_WORDS.search(title):
                continue
            published_iso = published.isoformat().replace('+00:00', 'Z')
            age_hours = max(0, (NOW - published).total_seconds() / 3600)
            score = editorial_score(title, summary, feed['rank'], age_hours)
            if feed.get('gulf_only'):
                score += 5
            article_id = hashlib.sha256(url.encode('utf-8')).hexdigest()[:20]
            topic_key, topic_label, story_key = classify_story(title, summary, category, article_id)
            output.append({
                'id': article_id,
                'topicKey': topic_key,
                'topicLabel': topic_label,
                'storyKey': story_key,
                'category': category,
                'title': title,
                'summary': summary,
                '_sourceText': clean_text(description)[:1200],
                'source': publisher,
                'publishedAt': published_iso,
                'url': url,
                'score': score,
            })
        return (feed['name'], feed['url'], output, None)
    except Exception as exc:
        return (feed['name'], feed['url'], [], str(exc)[:170])

STOPWORDS = {'les','des','une','dans','pour','avec','sur','aux','est','sont','par','ses','qui','que','son','elle','lui','plus','mais','tout','cette','leur','après','avant','face','contre','france','maroc','monde','nouveau','nouvelle','fait','faites','avoir','sans','entre','chez','sous','depuis'}
def fingerprint(title):
    words = re.findall(r'[a-zà-ÿ0-9]+', title.casefold())
    return {w for w in words if len(w) >= 4 and w not in STOPWORDS}

def similar(a, b):
    aa = fingerprint(a); bb = fingerprint(b)
    if not aa or not bb:
        return False
    overlap = len(aa & bb) / min(len(aa), len(bb))
    return overlap >= .75 and len(aa & bb) >= 3

def informative_summary(title: str, summary: str) -> bool:
    """Écarte les descriptions de type accroche qui ne disent presque rien."""
    if len(summary) < 40:
        return False
    # Ne pas éliminer les véritables nouvelles simplement parce que titre et
    # résumé décrivent le même événement ; il faut seulement un détail nouveau.
    extra = fingerprint(summary) - fingerprint(title)
    return len(extra) >= 2


def editorial_score(title: str, summary: str, rank: int, age_hours: float) -> float:
    """Score de pertinence heuristique, indépendant de toute validation factuelle."""
    score = rank + 3.5 / (1 + max(0, age_hours) / 12)
    if MAJOR_EVENT.search(title):
        score += 3.2
    if SIGNIFICANCE.search(title):
        score += 1.5
    if SIGNIFICANCE.search(summary):
        score += 0.6
    if re.search(r'\b\d+(?:[.,]\d+)?\s*%', title):
        score += 0.7
    if SOFT_TOPIC.search(title):
        score -= 3
    if EVERGREEN.search(title):
        score -= 2
    if PROMOTIONAL.search(summary):
        score -= 1
    return round(score, 2)


def main():
    reports = []
    candidates = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        for source, url, records, err in pool.map(fetch_feed, FEEDS):
            reports.append({'source': source, 'url': url, 'ok': err is None, 'items': len(records), **({'error': err} if err else {})})
            candidates.extend(records)
            print(f"{'OK' if err is None else 'ERREUR'} {source:22} {len(records):>2} {url}" + (f" — {err}" if err else ''))
    candidates.sort(key=lambda a: (a['score'], a['publishedAt']), reverse=True)
    buckets = {key: [] for key in CATEGORIES}
    visited_urls = set()
    for a in candidates:
        key = a['category']
        bucket = buckets.get(key)
        if bucket is None or len(bucket) >= MAX_ITEMS_PER_CATEGORY:
            continue
        if a['url'] in visited_urls or any(similar(a['title'], b['title']) for b in bucket):
            continue
        bucket.append(a)
        visited_urls.add(a['url'])
    for arr in buckets.values():
        arr.sort(key=lambda a: a['publishedAt'], reverse=True)
    total = sum(map(len, buckets.values()))
    # Si le réseau est indisponible, conserver les dernières nouvelles valables au lieu de vider le site.
    if total == 0 and OUTPUT.exists():
        try:
            existing = json.loads(OUTPUT.read_text(encoding='utf-8'))
            if sum(len(v) for v in existing.get('categories', {}).values()) > 0:
                print('Aucun nouvel article: conservation des données précédentes', file=sys.stderr)
                return 0
        except Exception:
            pass
    if total == 0:
        print('Échec : aucun article collecté. On ne remplace pas le site par un flux vide.', file=sys.stderr)
        return 1
    verification = enrich_verification(buckets, NOW)
    print(f"Recoupement : {verification['corroborated']}/{verification['total']} actualités, {verification['checked']} recherches.")
    # Réutiliser d'abord les synthèses fraîches ; appeler l'IA uniquement pour
    # les sujets nouveaux afin de respecter le quota des modèles gratuits.
    cached_ai = restore_recent_summaries(buckets, NOW)
    fresh_ai = summarize_buckets(buckets, NOW)
    ai_count = fresh_ai + cached_ai
    # Ne pas afficher un titre accrocheur comme si c'était un fait confirmé.
    # Priorité au titre descriptif validé ; repli sur une phrase source copiée
    # sans ajout, sinon signaler le titre sensationnaliste d'origine.
    normalized_count = 0
    caution_count = 0
    primary_count = 0
    for group in buckets.values():
        for article in group:
            if apply_primary_correction(article, NOW):
                primary_count += 1
            if sensational(article["title"]):
                if not article.get("displayTitle"):
                    extracted = neutral_title_from_excerpt(
                        article["title"], article.get("_sourceText") or article["summary"]
                    )
                    if extracted:
                        article["displayTitle"] = extracted
                        article["titleType"] = "extract"
                if not article.get("displayTitle"):
                    article["headlineCaution"] = True
                    caution_count += 1
            if article.get("displayTitle"):
                normalized_count += 1
            article.pop("_sourceText", None)
    print(f"Titrage : {normalized_count} titres descriptifs ; {caution_count} titres originaux à vérifier ; {primary_count} corrections avec document primaire.")
    # Conserver un contexte historique clairement daté, sans le présenter
    # comme une nouvelle fraîche. Ajouter si possible un fait récent recoupé.
    live_gulf = [
        a for a in buckets['golfe']
        if a.get('verification', {}).get('status') == 'corroborated'
        and parse_time(a['publishedAt']) is not None
        and 0 <= (NOW - parse_time(a['publishedAt'])).total_seconds() <= 72 * 3600
    ]
    live_gulf.sort(key=lambda a: a['publishedAt'], reverse=True)
    priority = spotlight(live_gulf[0] if live_gulf else None)
    result = {
        'priority': priority,
        'editorialVersion': 3,
        'generatedAt': NOW.isoformat().replace('+00:00', 'Z'),
        'count': total,
        'aiSummaryCount': ai_count,
        'aiCachedCount': cached_ai,
        'verification': verification,
        'categories': buckets,
        'feeds': reports,
    }
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('Articles publiés :', total)
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
