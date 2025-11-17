#!/usr/bin/env python3
"""Simple crawler/downloader for a single page.

Usage:
    python app.py

It downloads linked files (by extension) into the outdir and writes a metadata.json file.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import re
import time
from pathlib import Path
from typing import List
from urllib.parse import urljoin, urlparse, unquote

import requests
try:
    import certifi
except ImportError:
    certifi = None
from bs4 import BeautifulSoup


DEFAULT_EXTENSIONS = ["pdf"]


def safe_filename(name: str) -> str:
    name = name.split("?")[0].split("#")[0]
    name = unquote(name)
    name = name.replace("/", "_")
    name = name.strip()
    if not name:
        name = hashlib.sha1(os.urandom(16)).hexdigest()
    return name


def extract_iframe_src(html: str, base: str) -> str:
    """Extract the first iframe src attribute if present."""
    soup = BeautifulSoup(html, "html.parser")
    iframe = soup.find("iframe", src=True)
    if iframe:
        return urljoin(base, iframe["src"])
    return None


def is_valid_link(href: str) -> bool:
    if not href:
        return False
    href = href.strip()
    if href.startswith("javascript:"):
        return False
    if href.startswith("#"):
        return False
    return True


def extract_links(html: str, base: str) -> List[str]:
    soup = BeautifulSoup(html, "html.parser")
    links: List[str] = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if not is_valid_link(href):
            continue
        full = urljoin(base, href)
        links.append(full)
    return links


def has_allowed_ext(url: str, allowed: List[str]) -> bool:
    parsed = urlparse(url)
    path = parsed.path.lower()
    for ext in allowed:
        if path.endswith("." + ext.lower()):
            return True
    return False


def download_file(session: requests.Session, url: str, dest: Path, max_retries: int = 3, verify=True) -> dict:
    record = {"url": url, "ok": False, "filename": None, "reason": None}
    for attempt in range(1, max_retries + 1):
        try:
            resp = session.get(url, stream=True, timeout=20, verify=verify)
            if resp.status_code != 200:
                record["reason"] = f"status_{resp.status_code}"
                logging.debug("Non-200 for %s: %s", url, resp.status_code)
                time.sleep(1)
                continue

            parsed = urlparse(url)
            name = os.path.basename(parsed.path)
            name = safe_filename(name)
            if not Path(name).suffix:
                ctype = resp.headers.get("content-type", "")
                if "pdf" in ctype:
                    name = name + ".pdf"

            outpath = dest / name

            if outpath.exists():
                stem = outpath.stem
                suffix = outpath.suffix
                i = 1
                while True:
                    candidate = dest / f"{stem}_{i}{suffix}"
                    if not candidate.exists():
                        outpath = candidate
                        break
                    i += 1

            with open(outpath, "wb") as fh:
                for chunk in resp.iter_content(chunk_size=8192):
                    if chunk:
                        fh.write(chunk)

            record.update({"ok": True, "filename": str(outpath), "reason": None})
            return record

        except requests.RequestException as e:
            record["reason"] = str(e)
            logging.debug("Attempt %s failed for %s: %s", attempt, url, e)
            time.sleep(1)
            continue

    return record


def main(argv=None):
    parser = argparse.ArgumentParser(description="Download linked files from a single page into a docs/ folder")
    parser.add_argument("--url", required=False, help="Page URL to crawl",
                        default="https://pdc.adm.ncu.edu.tw/reg_qa.asp")
    parser.add_argument("--outdir", required=False, help="Output directory (created inside this script dir)", default="docs")
    parser.add_argument("--extensions", required=False, help="Comma-separated file extensions to include",
                        default=",".join(DEFAULT_EXTENSIONS))
    parser.add_argument("--quiet", action="store_true", help="Reduce output")
    parser.add_argument("--insecure", action="store_true", help="Disable SSL certificate verification (insecure)")
    parser.add_argument("--ca-bundle", required=False, help="Path to a custom CA bundle file to use for verification", default=None)
    parser.add_argument("--no-metadata", action="store_true", help="Do not write the metadata.json file")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO if not args.quiet else logging.WARNING,
                        format="%(levelname)s: %(message)s")

    allowed = [e.strip().lower() for e in args.extensions.split(",") if e.strip()]

    base_dir = Path(__file__).resolve().parent
    out_dir = base_dir / args.outdir
    out_dir.mkdir(parents=True, exist_ok=True)

    session = requests.Session()
    session.headers.update({
        "User-Agent": "ncu-campus-qa-bot/1.0 (+https://github.com/)"
    })

    if args.insecure:
        verify = False
        try:
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        except Exception:
            pass
    elif args.ca_bundle:
        verify = args.ca_bundle
    else:
        verify = certifi.where() if certifi is not None else True

    page_url = args.url
    logging.info("Fetching page: %s", page_url)
    try:
        r = session.get(page_url, timeout=20, verify=verify)
        r.raise_for_status()
        r.encoding = r.apparent_encoding or 'big5'
    except requests.RequestException as e:
        logging.error("Failed to fetch %s: %s", page_url, e)
        return

    links = []
    iframe_src = extract_iframe_src(r.text, page_url)
    if iframe_src:
        logging.info("Found iframe with src: %s", iframe_src)
        # If the iframe src is a downloadable file, treat it as the only link
        if has_allowed_ext(iframe_src, allowed):
            links.append(iframe_src)
        else:
            # Otherwise, fetch the iframe content and parse for links
            logging.info("Fetching iframe content from %s", iframe_src)
            try:
                r_iframe = session.get(iframe_src, timeout=20, verify=verify)
                r_iframe.raise_for_status()
                r_iframe.encoding = r_iframe.apparent_encoding or 'big5'
                links = extract_links(r_iframe.text, iframe_src)
            except requests.RequestException as e:
                logging.error("Failed to fetch iframe %s: %s", iframe_src, e)
                return
    else:
        links = extract_links(r.text, page_url)

    logging.info("Found %d links to process", len(links))

    to_download = []
    seen = set()
    for link in links:
        if link in seen:
            continue
        seen.add(link)
        if has_allowed_ext(link, allowed):
            to_download.append(link)

    logging.info("Will download %d files (matching extensions)", len(to_download))

    results = []
    for url in to_download:
        logging.info("Downloading %s", url)
        rec = download_file(session, url, out_dir, verify=verify)
        results.append(rec)

    ok_count = sum(1 for r in results if r.get("ok"))
    if not args.no_metadata:
        meta_file = out_dir / "metadata.json"
        with open(meta_file, "w", encoding="utf-8") as fh:
            json.dump({"source_page": page_url, "fetched_at": int(time.time()), "results": results}, fh, ensure_ascii=False, indent=2)
        logging.info("Completed: %d succeeded, %d failed. Metadata: %s", ok_count, len(results) - ok_count, meta_file)
    else:
        logging.info("Completed: %d succeeded, %d failed.", ok_count, len(results) - ok_count)


if __name__ == "__main__":
    main()
