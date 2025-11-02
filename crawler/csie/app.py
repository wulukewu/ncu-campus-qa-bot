#!/usr/bin/env python3
"""
crawl_announcements.py

Crawl announcement pages for multiple categories until the end.

Usage:
    python crawl_announcements.py [--max-pages N] [--output-dir OUT] [category1 category2 ...]

If no categories are provided the script will crawl all predefined categories.

It uses `requests` (recommended) and `beautifulsoup4` when available. It will
fall back to basic substring heuristics if bs4 is not installed.
"""
from __future__ import annotations

import sys
import os
import argparse
import time
import re
from typing import List


DEFAULT_CATEGORIES = [
    "得獎訊息",
    "徵才訊息",
    "招生快訊",
    "演講公告",
    "活動快訊",
    "課程訊息",
    "系辦公告",
]


def slugify(name: str) -> str:
    # Very small slug: replace spaces and slashes with underscore
        return re.sub(r"[^0-9A-Za-z\x00-\x7F]+", "_", name).strip("_") or "cat"


def fetch(url: str, timeout: int = 15, headers=None):
    headers = headers or {"User-Agent": "Mozilla/5.0 (compatible; csie-crawler/1.0)"}
    try:
        import requests
    except Exception:
        requests = None

    if requests:
        try:
            r = requests.get(url, headers=headers, timeout=timeout)
            return r.status_code, r.content, getattr(r, "url", url)
        except Exception as e:
            print(f"requests error for {url}: {e}")
            return None, None, url

    # fallback to urllib
    try:
        import urllib.request
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            content = resp.read()
            return resp.getcode(), content, getattr(resp, "geturl", lambda: url)()
    except Exception as e:
        print(f"urllib error for {url}: {e}")
        return None, None, url


def page_has_announcements(html: bytes) -> bool:
    text = html.decode("utf-8", errors="ignore")

    # Try BeautifulSoup if available for more accurate detection
    try:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(text, "html.parser")
        # Look for <a> links that likely point to announcement details
        anchors = soup.find_all("a", href=True)
        count = 0
        for a in anchors:
            href = a["href"]
            if "/announcement/" in href or "announcement" in href:
                count += 1
        return count > 0
    except Exception:
        # Fallback heuristics: look for typical keywords or announcement links
        if re.search(r"(查無資料|沒有資料|無資料)", text):
            return False
        # Count occurrences of 'announcement' paths or common link patterns
        return bool(re.search(r"/announcement/|announcement", text))


def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def crawl(categories: List[str], max_pages: int = 200, output_dir: str = None, delay: float = 0.5):
    base = "https://www.csie.ncu.edu.tw/announcement/page/{page}/category/{category}"
    out_base = output_dir or os.path.join(os.path.dirname(__file__), "output")
    for cat in categories:
        cat_enc = cat
        try:
            from urllib.parse import quote_plus

            cat_enc = quote_plus(cat)
        except Exception:
            pass

        slug = slugify(cat)
        cat_out = os.path.join(out_base, slug)
        ensure_dir(cat_out)
        print(f"Crawling category: {cat} -> {cat_out}")

        page = 1
        consecutive_failures = 0
        while page <= max_pages:
            url = base.format(page=page, category=cat_enc)
            print(f"  fetching page {page}: {url}")
            status, content, final_url = fetch(url)
            if status is None:
                print("   failed to fetch (network error), stopping this category")
                break
            if status >= 400:
                print(f"   HTTP {status} — stopping at page {page}")
                break

            # If returned content is very small, treat as end
            if not content or len(content) < 500:
                consecutive_failures += 1
                print(f"   small page ({len(content) if content else 0} bytes).")
                if consecutive_failures >= 2:
                    print("   likely end of pages — stopping")
                    break
            else:
                consecutive_failures = 0

            has = page_has_announcements(content)
            if not has and page > 1:
                print("   no announcement links found — reached the end")
                break

            fname = os.path.join(cat_out, f"page_{page}.html")
            try:
                with open(fname, "wb") as f:
                    f.write(content)
                print(f"   saved {len(content)} bytes -> {fname}")
            except Exception as e:
                print(f"   cannot save file {fname}: {e}")

            page += 1
            time.sleep(delay)


def parse_args(argv: List[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Crawl CSIE announcement pages by category and page until no more pages.")
    p.add_argument("categories", nargs="*", help="Categories to crawl (defaults to all)")
    p.add_argument("--max-pages", type=int, default=200, help="Maximum pages to try per category")
    p.add_argument("--output-dir", default=None, help="Directory to save pages (default: crawler/csie/output)")
    p.add_argument("--delay", type=float, default=0.5, help="Delay between requests in seconds")
    return p.parse_args(argv[1:])


def main(argv: List[str]) -> int:
    args = parse_args(argv)
    cats = args.categories if args.categories else DEFAULT_CATEGORIES
    crawl(cats, max_pages=args.max_pages, output_dir=args.output_dir, delay=args.delay)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
