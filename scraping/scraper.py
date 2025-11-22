#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Scraper multi-sites unifié :
- Sites : L'Humanité, GameSpot, Marianne, Le Monde, France 24, France 3 Régions, Médiacités, Le Point
- Stockage unique dans MongoDB : base `articles_db`, collection `articles`
- Déduplication automatique via index (source + url)
- Envoi automatique à l’API REST /predict pour analyse de toxicité
"""

import os
import time
import datetime
from typing import Optional, List, Tuple
import requests
from requests.adapters import HTTPAdapter, Retry
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from pymongo import MongoClient, ASCENDING, errors as mongo_errors

# =========================
# Configuration MongoDB
# =========================

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME = "articles_db"
COLLECTION_NAME = "articles"

mongo_client = MongoClient(MONGO_URI)
db = mongo_client[DB_NAME]
collection = db[COLLECTION_NAME]

collection.create_index(
    [("source", ASCENDING), ("url", ASCENDING)],
    unique=True,
    name="uniq_source_url"
)

# =========================
# Configuration API REST
# =========================

API_URL = "http://127.0.0.1:8000/predict"

def envoyer_a_api(text: str, url: str):
    """Envoie un texte à l’API REST pour analyse de toxicité"""
    try:
        data = {"text": text, "url": url}
        response = requests.post(API_URL, json=data, timeout=60)
        if response.status_code == 200:
            print(f"✅ Analyse API enregistrée pour {url}")
        else:
            print(f"❌ Erreur API ({response.status_code}) sur {url} :", response.text)
    except Exception as e:
        print(f"⚠️ Impossible d’envoyer à l’API pour {url} :", e)

# =========================
# HTTP Session robuste
# =========================

def build_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
        "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
    })
    retries = Retry(total=3, backoff_factor=0.6, status_forcelist=[429, 500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retries)
    s.mount("http://", adapter)
    s.mount("https://", adapter)
    return s

SESSION = build_session()

# =========================
# Fonctions utilitaires
# =========================

def normalize_url(base: str, href: Optional[str]) -> Optional[str]:
    if not href or href.startswith(("javascript:", "#")):
        return None
    if href.startswith("//"):
        scheme = urlparse(base).scheme or "https"
        return f"{scheme}:{href}"
    if href.startswith("/"):
        return urljoin(base, href)
    return href if urlparse(href).scheme in ("http", "https") else urljoin(base, href)

def get_soup(url: str, timeout: int = 10) -> Optional[BeautifulSoup]:
    try:
        r = SESSION.get(url, timeout=timeout)
        if r.status_code != 200:
            print(f"[WARN] {url} → HTTP {r.status_code}")
            return None
        return BeautifulSoup(r.text, "html.parser")
    except requests.RequestException as e:
        print(f"[ERR] {url}: {e}")
        return None

def extract_text(soup: BeautifulSoup, selectors: List[Tuple[str, str]]) -> str:
    for sel, mode in selectors:
        node = soup.select_one(sel)
        if node:
            if mode == "paragraphs":
                ps = [p.get_text(strip=True) for p in node.find_all("p") if p.get_text(strip=True)]
                return "\n".join(ps) if ps else node.get_text(strip=True)
            else:
                return node.get_text(strip=True)
    ps = [p.get_text(strip=True) for p in soup.find_all("p") if p.get_text(strip=True)]
    return "\n".join(ps) if ps else ""

def save_article(title: Optional[str], url: Optional[str], content: Optional[str], source: str):
    if not title or not url or not content:
        print(f"[SKIP] {source} article incomplet.")
        return

    doc = {
        "source": source,
        "title": title.strip(),
        "url": url.strip(),
        "content": content.strip(),
        "scraped_at": datetime.datetime.utcnow(),
    }

    try:
        collection.update_one({"source": source, "url": url}, {"$setOnInsert": doc}, upsert=True)
        print(f"[OK] {source} → {title[:80]}")

        # 🔁 Envoi du texte à ton API REST pour analyse de toxicité
        envoyer_a_api(content, url)

    except mongo_errors.DuplicateKeyError:
        print(f"[DUP] {source} déjà présent : {url}")

# =========================
# Scrapers
# =========================

def scrape_humanite():
    print("\n=== L'Humanité ===")
    base = "https://www.humanite.fr/"
    soup = get_soup(base)
    if not soup:
        return
    for art in soup.find_all("article", class_="myvertical-card"):
        a = art.find("a", href=True)
        title = art.find("h3", class_="vertical-card__title")
        title = title.get_text(strip=True) if title else None
        url = normalize_url(base, a["href"]) if a else None
        if url:
            art_soup = get_soup(url)
            if art_soup:
                content = extract_text(art_soup, [("div.article-content", "paragraphs"), ("article", "paragraphs")])
                save_article(title, url, content, "L'Humanité")

def scrape_gamespot():
    print("\n=== GameSpot ===")
    base = "https://www.gamespot.com/"
    soup = get_soup(base)
    if not soup:
        return
    for c in soup.find_all("div", class_="card-item__content"):
        a = c.find("a", href=True)
        title = c.find("h4", class_="card-item__title")
        title = title.get_text(strip=True) if title else None
        url = normalize_url(base, a["href"]) if a else None
        if url:
            art = get_soup(url)
            if art:
                content = extract_text(art, [("article", "paragraphs"), ("div.js-content-entity-body", "paragraphs")])
                save_article(title, url, content, "GameSpot")

def scrape_marianne():
    print("\n=== Marianne ===")
    base = "https://www.marianne.net/"
    soup = get_soup(base)
    if not soup:
        return
    for art in soup.find_all("article", class_="thumbnail"):
        a = art.find("a", class_="thumbnail__link")
        title = a.get_text(strip=True) if a else None
        url = normalize_url(base, a["href"]) if a else None
        if url:
            art_soup = get_soup(url)
            if art_soup:
                content = extract_text(art_soup, [("article", "paragraphs"), ("div.article__content", "paragraphs")])
                save_article(title, url, content, "Marianne")

def scrape_lemonde():
    print("\n=== Le Monde ===")
    base = "https://www.lemonde.fr"
    soup = get_soup(f"{base}/international/")
    if not soup:
        return
    for art in soup.select("section.area--runner div.article"):
        a = art.find("a", class_="lmd-link-clickarea__link")
        title = art.find("p", class_="article__title")
        title = title.get_text(strip=True) if title else None
        url = normalize_url(base, a["href"]) if a else None
        if url:
            art_soup = get_soup(url)
            if art_soup:
                content = extract_text(art_soup, [("section.article__content", "paragraphs"), ("article", "paragraphs")])
                save_article(title, url, content, "Le Monde")

def scrape_france3():
    print("\n=== France 3 Régions ===")
    base = "https://france3-regions.franceinfo.fr/"
    soup = get_soup(base)
    if not soup:
        return
    for a in soup.select("a.article-card__title"):
        title = a.get_text(strip=True)
        url = normalize_url(base, a.get("href"))
        if url:
            art_soup = get_soup(url)
            if art_soup:
                content = extract_text(art_soup, [("div.article__body", "paragraphs"), ("article", "paragraphs")])
                save_article(title, url, content, "France 3 Régions")

def scrape_mediacites():
    print("\n=== Médiacités ===")
    base = "https://www.mediacites.fr/"
    soup = get_soup(base)
    if not soup:
        return
    for h2 in soup.find_all("h2", class_="title"):
        a = h2.find("a", href=True)
        if a:
            title = a.get_text(strip=True)
            url = normalize_url(base, a["href"])
            art_soup = get_soup(url)
            if art_soup:
                content = extract_text(art_soup, [("article", "paragraphs"), ("div.content", "paragraphs")])
                save_article(title, url, content, "Médiacités")

def scrape_lepoint():
    print("\n=== Le Point ===")
    base = "https://www.lepoint.fr/"
    soup = get_soup(base)
    if not soup:
        return
    for a in soup.select("article.full-click a[href]"):
        url = normalize_url(base, a.get("href"))
        title_tag = a.find("h2")
        title = title_tag.get_text(strip=True) if title_tag else a.get_text(strip=True)
        if url:
            art_soup = get_soup(url)
            if art_soup:
                content = extract_text(art_soup, [("div.article-content", "paragraphs"), ("article", "paragraphs")])
                save_article(title, url, content, "Le Point")

# =========================
# Orchestration
# =========================

SITE_FUNCS = [
    scrape_humanite,
    scrape_gamespot,
    scrape_marianne,
    scrape_lemonde,
    scrape_france3,
    scrape_mediacites,
    scrape_lepoint,
]

def run(selected: Optional[List[str]] = None):
    name_map = {f.__name__.replace("scrape_", ""): f for f in SITE_FUNCS}
    to_run = SITE_FUNCS if not selected else [name_map[s] for s in selected if s in name_map]
    start = time.time()
    for func in to_run:
        try:
            func()
        except Exception as e:
            print(f"[ERR] {func.__name__}: {e}")
    print(f"\nScraping terminé en {time.time() - start:.1f}s.")

if __name__ == "__main__":
    env_sites = os.getenv("SITES")
    if env_sites:
        run([s.strip().lower() for s in env_sites.split(",")])
    else:
        run()
