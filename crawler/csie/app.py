#!/usr/bin/env python3
"""
crawl_announcements.py

Crawl announcement pages for multiple categories and extract to CSV.

Usage:
    python app.py [--max-pages N] [--output announcements.csv] [category1 category2 ...]

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
import csv
from typing import List, Tuple


DEFAULT_CATEGORIES = [
    "得獎訊息",
    "徵才訊息",
    "招生快訊",
    "演講公告",
    "活動快訊",
    "課程訊息",
    "系辦公告",
]


def fetch(url: str, timeout: int = 15, headers=None):
    headers = headers or {"User-Agent": "Mozilla/5.0 (compatible; csie-crawler/1.0)"}
    try:
        import requests
    except Exception:
        requests = None

    # Try with requests first (with a few retries)
    if requests:
        session = None
        try:
            session = requests.Session()
            # Best-effort attach retry adapter if available
            try:
                from urllib3.util.retry import Retry  # type: ignore
                from requests.adapters import HTTPAdapter  # type: ignore

                retry = Retry(total=2, backoff_factor=0.5, status_forcelist=[429, 500, 502, 503, 504])
                adapter = HTTPAdapter(max_retries=retry)
                session.mount("http://", adapter)
                session.mount("https://", adapter)
            except Exception:
                pass

            last_exc = None
            for attempt in range(3):
                try:
                    r = session.get(url, headers=headers, timeout=timeout)
                    return r.status_code, r.content, getattr(r, "url", url)
                except Exception as e:
                    last_exc = e
                    print(f"requests attempt {attempt+1}/3 failed for {url}: {e}")
                    time.sleep(min(1.5, 0.3 * (2 ** attempt)))
            print(f"requests failed for {url}: {last_exc}; falling back to urllib")
        except Exception as e:
            print(f"requests error for {url}: {e}; falling back to urllib")
        finally:
            try:
                if session:
                    session.close()
            except Exception:
                pass

    # Fallback to urllib
    try:
        import urllib.request
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            content = resp.read()
            return resp.getcode(), content, getattr(resp, "geturl", lambda: url)()
    except Exception as e:
        print(f"urllib error for {url}: {e}")
        return None, None, url


def parse_announcements_from_html(html: bytes, category: str) -> List[Tuple[str, str, str]]:
    """
    Parse HTML content and extract announcements.
    Returns a list of (category, title, date) tuples.
    """
    text = html.decode("utf-8", errors="ignore")

    # Try BeautifulSoup for accurate parsing
    try:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(text, "html.parser")
        links = soup.find_all("a", class_="link", href=True)
        results = []
        for link in links:
            title_div = link.find("div", class_="item-title")
            time_div = link.find("div", class_="item-time")
            if title_div and time_div:
                title = title_div.get_text(strip=True)
                date = time_div.get_text(strip=True)
                results.append((category, title, date))
        return results
    except Exception:
        # Fallback: regex-based extraction
        results = []
        pattern = re.compile(
            r'<a[^>]*class="link"[^>]*>.*?'
            r'<div class="item-title">([^<]+)</div>.*?'
            r'<div class="item-time">([^<]+)</div>',
            re.DOTALL,
        )
        for match in pattern.finditer(text):
            title = match.group(1).strip()
            date = match.group(2).strip()
            results.append((category, title, date))
        return results


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


def write_csv(announcements: List[Tuple[str, str, str]], output_path: str):
    """
    Write announcements to a CSV file with columns: category, title, date.
    """
    try:
        with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["category", "title", "date"])
            for cat, title, date in announcements:
                writer.writerow([cat, title, date])
        print(f"\nWrote {len(announcements)} announcements to {output_path}")
    except Exception as e:
        print(f"Error writing CSV: {e}")
        raise


def crawl(categories: List[str], max_pages: int = 200, output_csv: str = "announcements.csv", delay: float = 0.5):
    base = "https://www.csie.ncu.edu.tw/announcement/page/{page}/category/{category}"
    all_announcements = []
    
    for cat in categories:
        cat_enc = cat
        try:
            from urllib.parse import quote_plus
            cat_enc = quote_plus(cat)
        except Exception:
            pass

        print(f"Crawling category: {cat}")

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

            # Parse announcements from this page
            announcements = parse_announcements_from_html(content, cat)
            all_announcements.extend(announcements)
            print(f"   extracted {len(announcements)} announcements from page {page}")

            page += 1
            time.sleep(delay)

    # Write all collected announcements to CSV
    if all_announcements:
        write_csv(all_announcements, output_csv)
    else:
        print("\nNo announcements found.")
    
    return len(all_announcements)


def parse_args(argv: List[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Crawl CSIE announcement pages and export to CSV.")
    p.add_argument("categories", nargs="*", help="Categories to crawl (defaults to all)")
    p.add_argument("--max-pages", type=int, default=200, help="Maximum pages to try per category")
    p.add_argument("--output", default="announcements.csv", help="Output CSV file path (default: announcements.csv)")
    p.add_argument("--delay", type=float, default=0.5, help="Delay between requests in seconds")
    return p.parse_args(argv[1:])


def main(argv: List[str]) -> int:
    args = parse_args(argv)
    cats = args.categories if args.categories else DEFAULT_CATEGORIES
    count = crawl(cats, max_pages=args.max_pages, output_csv=args.output, delay=args.delay)
    return 0 if count > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
