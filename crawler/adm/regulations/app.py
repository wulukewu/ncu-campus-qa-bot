#!/usr/bin/env python3
"""Download all PDF files linked from a single regulations page.

Usage:
    python app.py --url <PAGE_URL> [--outdir docs] [--insecure]

Default URL: https://pdc.adm.ncu.edu.tw/rule_note1.asp
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


def safe_filename(name: str) -> str:
    name = name.split("?")[0].split("#")[0]
    name = unquote(name)
    name = name.replace("/", "_")
    name = name.strip()
    if not name:
        name = hashlib.sha1(os.urandom(16)).hexdigest()
    return name


def extract_links(html: str, base: str) -> List[str]:
    soup = BeautifulSoup(html, "html.parser")
    links: List[str] = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith("javascript:") or href.startswith("#"):
            continue
        links.append(urljoin(base, href))
    return links


def is_pdf_link(url: str) -> bool:
    p = urlparse(url)
    if p.path.lower().endswith(".pdf"):
        return True
    return False


def download_file(session: requests.Session, url: str, dest: Path, verify=True) -> dict:
    rec = {"url": url, "ok": False, "filename": None, "reason": None}
    try:
        resp = session.get(url, stream=True, timeout=20, verify=verify)
        if resp.status_code != 200:
            rec["reason"] = f"status_{resp.status_code}"
            return rec

        # Determine filename
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

        rec.update({"ok": True, "filename": str(outpath)})
        return rec

    except requests.RequestException as e:
        rec["reason"] = str(e)
        return rec


def main(argv=None):
    parser = argparse.ArgumentParser(description="Download PDFs linked from a regulations page")
    parser.add_argument("--url", required=False, default="https://pdc.adm.ncu.edu.tw/rule/rule114/index.html")
    parser.add_argument("--outdir", required=False, default="docs")
    parser.add_argument("--insecure", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    base_dir = Path(__file__).resolve().parent
    out_dir = base_dir / args.outdir
    out_dir.mkdir(parents=True, exist_ok=True)

    session = requests.Session()
    session.headers.update({"User-Agent": "ncu-campus-qa-bot/1.0"})

    if args.insecure:
        verify = False
    else:
        verify = certifi.where() if certifi is not None else True

    logging.info("Fetching %s", args.url)
    try:
        r = session.get(args.url, timeout=20, verify=verify)
        r.raise_for_status()
    except requests.RequestException as e:
        logging.error("Failed to fetch %s: %s", args.url, e)
        sys.exit(2)

    links = extract_links(r.text, args.url)
    pdf_links = [l for l in links if is_pdf_link(l)]
    logging.info("Found %d PDF links", len(pdf_links))

    results = []
    for url in pdf_links:
        logging.info("Downloading %s", url)
        rec = download_file(session, url, out_dir, verify=verify)
        results.append(rec)

    meta = {"source_page": args.url, "fetched_at": int(time.time()), "results": results}
    with open(out_dir / "metadata.json", "w", encoding="utf-8") as fh:
        json.dump(meta, fh, ensure_ascii=False, indent=2)

    ok = sum(1 for r in results if r.get("ok"))
    logging.info("Done: %d succeeded, %d failed. Metadata saved to %s", ok, len(results) - ok, out_dir / "metadata.json")


if __name__ == "__main__":
    main()
