#!/usr/bin/env python3
"""Simple crawler/downloader for a single page.

Usage:
    python app.py --url <PAGE_URL> [--outdir docs] [--extensions pdf,docx,...]

It downloads linked files (by extension) into the outdir and writes a metadata.json file.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
import hashlib
from pathlib import Path
from typing import List
from urllib.parse import urljoin, urlparse, unquote

import requests
try:
    import certifi
except Exception:
    certifi = None
from bs4 import BeautifulSoup


DEFAULT_EXTENSIONS = [
    "pdf",
    # "doc",
    # "docx",
    # "xls",
    # "xlsx",
    # "ppt",
    # "pptx",
    # "txt",
    # "zip",
    # "rar",
    # "htm",
    # "html",
]


def safe_filename(name: str) -> str:
    # strip query and fragments
    name = name.split("?")[0].split("#")[0]
    name = unquote(name)
    name = name.replace("/", "_")
    name = name.strip()
    if not name:
        # fallback to hash
        name = hashlib.sha1(os.urandom(16)).hexdigest()
    return name


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

            # determine filename
            parsed = urlparse(url)
            name = os.path.basename(parsed.path)
            name = safe_filename(name)
            if not Path(name).suffix:
                # try to infer from Content-Type
                ctype = resp.headers.get("content-type", "")
                if "pdf" in ctype:
                    name = name + ".pdf"
                elif "word" in ctype or "officedocument" in ctype:
                    # fallback to .docx
                    name = name + ".docx"

            outpath = dest / name
            # avoid overwriting: if exists, add suffix
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
                        default="https://pdc.adm.ncu.edu.tw/rule/rule114/12/12.html")
    parser.add_argument("--outdir", required=False, help="Output directory (created inside this script dir)", default="docs")
    parser.add_argument("--extensions", required=False, help="Comma-separated file extensions to include",
                        default=",".join(DEFAULT_EXTENSIONS))
    parser.add_argument("--quiet", action="store_true", help="Reduce output")
    parser.add_argument("--insecure", action="store_true", help="Disable SSL certificate verification (insecure)")
    parser.add_argument("--ca-bundle", required=False, help="Path to a custom CA bundle file to use for verification", default=None)
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

    logging.info("Fetching page %s", args.url)
    # determine verification mode
    if args.insecure:
        verify = False
    elif args.ca_bundle:
        verify = args.ca_bundle
    else:
        verify = certifi.where() if certifi is not None else True

    try:
        r = session.get(args.url, timeout=20, verify=verify)
        r.raise_for_status()
    except requests.RequestException as e:
        logging.error("Failed to fetch %s: %s", args.url, e)
        sys.exit(2)

    links = extract_links(r.text, args.url)
    logging.info("Found %d links on the page", len(links))

    # filter and deduplicate
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

    # save metadata
    meta_file = out_dir / "metadata.json"
    with open(meta_file, "w", encoding="utf-8") as fh:
        json.dump({"source_page": args.url, "fetched_at": int(time.time()), "results": results}, fh, ensure_ascii=False, indent=2)

    ok_count = sum(1 for r in results if r.get("ok"))
    logging.info("Completed: %d succeeded, %d failed. Metadata: %s", ok_count, len(results) - ok_count, meta_file)


if __name__ == "__main__":
    main()
