"""Lecture limitée des articles publics, si le site l'autorise.

Ne contourne ni paywall ni robots.txt ; pas de navigateur, cookie, login ni proxy.
Le texte collecté est éphémère : seuls des résumés courts sont publiés.
"""
from __future__ import annotations

import concurrent.futures
import datetime as dt
import html
from html.parser import HTMLParser
import ipaddress
import json
import re
from threading import Lock
import urllib.parse
import urllib.request
import urllib.robotparser

USER_AGENT = "LEssentielPublicArticleReader/1.0"
MAX_FETCH = 12
BODY_LIMIT = 4500
MIN_BODY = 480
MAX_DOWNLOAD = 850_000

ALLOWED_PUBLISHERS = frozenset({
    "rfi.fr", "france24.com", "franceinfo.fr", "fr.hespress.com",
    "hespress.com", "01net.com", "numerama.com", "clubic.com",
    "blogdumoderateur.com", "lecourrierdelatlas.com",
})
robots_cache = {}
robots_lock = Lock()
SKIP_HTML = re.compile(
    r"(?:cookie|consent|paywall|subscribe|abonnement|newsletter|"
    r"publi(?:cite|city)|advertisement|advert|share|social|related|"
    r"recommend|commentaire|comments|footer|breadcrumb)", re.I
)


def publisher_host(url):
    try:
        info = urllib.parse.urlsplit(url)
        if info.scheme != "https" or info.username or info.password:
            return None
        host = (info.hostname or "").lower().rstrip(".")
        if not host or host in {"localhost", "127.0.0.1"}:
            return None
        try:
            if not ipaddress.ip_address(host).is_global:
                return None
        except ValueError:
            pass
        allowed = any(host == root or host.endswith("." + root) for root in ALLOWED_PUBLISHERS)
        return host if allowed else None
    except ValueError:
        return None


class SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not publisher_host(newurl):
            raise ValueError("Redirection hors liste des éditeurs autorisés")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def may_fetch(url, opener=None):
    host = publisher_host(url)
    if not host:
        return False
    robots_url = "https://" + host + "/robots.txt"
    with robots_lock:
        decision = robots_cache.get(host)
    if decision is None:
        try:
            # Ne pas supposer qu'un robots.txt inaccessible vaut autorisation.
            req = urllib.request.Request(robots_url, headers={"User-Agent": USER_AGENT})
            agent = opener or urllib.request.build_opener(SafeRedirect)
            with agent.open(req, timeout=5) as response:
                raw = response.read(250_000)
            rp = urllib.robotparser.RobotFileParser()
            rp.parse(raw.decode("utf-8", "replace").splitlines())
            decision = rp
        except (OSError, ValueError):
            return False
        with robots_lock:
            robots_cache[host] = decision
    return decision.can_fetch(USER_AGENT, url)


class ArticleParagraphs(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.exclude = 0
        self.in_paragraph = 0
        self.chunks = []
        self.paragraphs = []
        self.has_article = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        style = " ".join(str(attrs.get(k, "")) for k in ("id", "class", "role"))
        skip = bool(SKIP_HTML.search(style) or tag in {"script", "style", "nav", "footer", "aside", "form", "noscript", "svg"})
        self.stack.append((tag, skip))
        if skip:
            self.exclude += 1
        if tag in ("article", "main") and not self.exclude:
            self.has_article = True
        if tag == "p" and not self.exclude and any(k in ("main", "article") for k, _ in self.stack):
            self.in_paragraph += 1
            self.chunks = []

    def handle_data(self, data):
        if self.in_paragraph and self.exclude == 0:
            self.chunks.append(data)

    def handle_endtag(self, tag):
        if tag == "p" and self.in_paragraph:
            text = re.sub(r"\s+", " ", html.unescape(" ".join(self.chunks))).strip()
            if len(text) >= 40:
                self.paragraphs.append(text)
            self.chunks = []
            self.in_paragraph = 0
        # Repair tag stack for nested HTML with imperfect source.
        while self.stack:
            current, skip = self.stack.pop()
            if skip:
                self.exclude = max(0, self.exclude - 1)
            if current == tag:
                break


def extract_text(page):
    if not isinstance(page, str):
        return ""
    parser = ArticleParagraphs()
    try:
        parser.feed(page)
    except (ValueError, TypeError):
        return ""
    text = " ".join(parser.paragraphs)
    # Collect only compact source context; never republish an article body.
    return text[:BODY_LIMIT] if len(text) >= MIN_BODY else ""


def read_public_article(article, opener=None):
    url = article.get("url") or ""
    if not may_fetch(url, opener=opener):
        return None
    agent = opener or urllib.request.build_opener(SafeRedirect)
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": USER_AGENT, "Accept": "text/html"},
        )
        with agent.open(req, timeout=9) as response:
            if "text/html" not in (response.headers.get("Content-Type") or "").lower():
                return None
            raw = response.read(MAX_DOWNLOAD + 1)
        if len(raw) > MAX_DOWNLOAD:
            return None
        content = raw.decode("utf-8", "replace")
        body = extract_text(content)
        return body if body else None
    except (OSError, ValueError, UnicodeError):
        return None


def hydrate_articles(buckets, now, fetcher=None):
    fetcher = fetcher or read_public_article
    picks = []
    for entries in buckets.values():
        recent = []
        for a in entries:
            if a.get("summaryType") == "primary":
                continue
            try:
                when = dt.datetime.fromisoformat(a["publishedAt"].replace("Z", "+00:00"))
                age = (now - when).total_seconds()
            except (KeyError, ValueError, TypeError):
                continue
            if -3600 <= age <= 36 * 3600:
                recent.append(a)
        recent.sort(key=lambda a: (a.get("verification", {}).get("status") == "corroborated", a.get("score", 0)), reverse=True)
        picks.extend(recent[:2])
    # One short run, not dozens of page requests.
    picks = picks[:MAX_FETCH]
    for a in picks:
        embedded = a.get("_embeddedArticle", "")
        if len(embedded) >= MIN_BODY:
            a["_articleText"] = embedded[:BODY_LIMIT]
            a["articleRead"] = "rss-full"
    missing = [a for a in picks if not a.get("_articleText")]
    if missing:
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            results = list(executor.map(fetcher, missing))
        for a, body in zip(missing, results):
            if isinstance(body, str) and len(body) >= MIN_BODY:
                a["_articleText"] = body[:BODY_LIMIT]
                a["articleRead"] = "public-html"
    found = sum(bool(a.get("_articleText")) for a in picks)
    print(f"Lecture approfondie : {found}/{len(picks)} articles consultables (autres : RSS seulement).")
    return found
