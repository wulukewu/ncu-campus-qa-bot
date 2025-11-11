#!/usr/bin/env python3
"""Download files linked from a sequence of statistics pages.

This script visits pages like:
  https://pdc.adm.ncu.edu.tw/rate_note_reg1.asp
  https://pdc.adm.ncu.edu.tw/rate_note_reg2.asp
  ...

It downloads links matching DEFAULT_EXTENSIONS into `docs/<n>/` folders where n is 1..4 by default.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import re
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
    "doc",
    "docx",
    "xls",
    "xlsx",
    "ppt",
    "pptx",
    "txt",
    # "zip",
    # "rar",
    "htm",
    "html",
]


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


def extract_links(html: str, base: str) -> List[str]:
    soup = BeautifulSoup(html, "html.parser")
    links: List[str] = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith("javascript:") or href.startswith("#"):
            continue
        links.append(urljoin(base, href))
    return links


def has_allowed_ext(url: str, allowed: List[str]) -> bool:
    parsed = urlparse(url)
    path = parsed.path.lower()
    for ext in allowed:
        if path.endswith("." + ext.lower()):
            return True
    return False


def download_file(session: requests.Session, url: str, dest: Path, verify=True) -> dict:
    rec = {"url": url, "ok": False, "filename": None, "reason": None}
    try:
        resp = session.get(url, stream=True, timeout=20, verify=verify)
        if resp.status_code != 200:
            rec["reason"] = f"status_{resp.status_code}"
            return rec

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


def build_url_template(url: str) -> str:
    """Return a template where {n} will be substituted.

    If the provided url contains '{n}' use it. Otherwise attempt to replace the last number
    before the extension (e.g. rate_note_reg1.asp) with {n}.
    """
    if "{n}" in url:
        return url
    # attempt to find a number before .asp or end
    m = re.search(r"(.*?)(\d+)(\.asp.*|$)", url)
    if m:
        prefix, num, suffix = m.group(1), m.group(2), m.group(3)
        return f"{prefix}{{n}}{suffix}"
    # fallback: append ?n={n}
    if "?" in url:
        return url + "&n={n}"
    return url + "?n={n}"


def main(argv=None):
    parser = argparse.ArgumentParser(description="Download files from statistics pages into docs/<n>/ folders")
    parser.add_argument("--url", required=False, default="https://pdc.adm.ncu.edu.tw/rate_note_reg1.asp",
                        help="Template URL or example URL (script will replace number with 1..4 by default)")
    parser.add_argument("--outdir", required=False, default="docs")
    parser.add_argument("--start", type=int, default=1, help="Start number (inclusive)")
    parser.add_argument("--end", type=int, default=4, help="End number (inclusive)")
    parser.add_argument("--extensions", required=False, default=",".join(DEFAULT_EXTENSIONS),
                        help="Comma-separated list of extensions to include")
    parser.add_argument("--insecure", action="store_true", help="Disable SSL verification (insecure)")
    parser.add_argument("--quiet", action="store_true", help="Quiet mode")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO if not args.quiet else logging.WARNING, format="%(levelname)s: %(message)s")

    allowed = [e.strip().lower() for e in args.extensions.split(",") if e.strip()]

    base_dir = Path(__file__).resolve().parent
    out_dir = base_dir / args.outdir
    out_dir.mkdir(parents=True, exist_ok=True)

    session = requests.Session()
    session.headers.update({"User-Agent": "ncu-campus-qa-bot/1.0"})

    verify = False if args.insecure else (certifi.where() if certifi is not None else True)

    template = build_url_template(args.url)
    logging.info("Using URL template: %s", template)

    all_results = []
    for n in range(args.start, args.end + 1):
        page_url = template.format(n=n)
        logging.info("Fetching page %s", page_url)
        try:
            r = session.get(page_url, timeout=20, verify=verify)
            r.raise_for_status()
            # Try to decode with proper encoding (site uses Big5)
            r.encoding = r.apparent_encoding or 'big5'
        except requests.RequestException as e:
            logging.error("Failed to fetch %s: %s", page_url, e)
            all_results.append({"n": n, "source_page": page_url, "results": [], "error": str(e)})
            continue

        # Check for iframe - if present, fetch iframe content instead
        iframe_src = extract_iframe_src(r.text, page_url)
        if iframe_src:
            logging.info("Found iframe, fetching content from %s", iframe_src)
            try:
                r_iframe = session.get(iframe_src, timeout=20, verify=verify)
                r_iframe.raise_for_status()
                r_iframe.encoding = r_iframe.apparent_encoding or 'big5'
                links = extract_links(r_iframe.text, iframe_src)
            except requests.RequestException as e:
                logging.error("Failed to fetch iframe %s: %s", iframe_src, e)
                all_results.append({"n": n, "source_page": page_url, "iframe": iframe_src, "results": [], "error": str(e)})
                continue
        else:
            links = extract_links(r.text, page_url)

        # filter
        to_download = []
        seen = set()
        for link in links:
            if link in seen:
                continue
            seen.add(link)
            if has_allowed_ext(link, allowed):
                to_download.append(link)

        logging.info("Page %s: found %d candidate files", n, len(to_download))

        n_out = out_dir / str(n)
        n_out.mkdir(parents=True, exist_ok=True)

        results = []
        for url in to_download:
            logging.info("[%s] Downloading %s", n, url)
            rec = download_file(session, url, n_out, verify=verify)
            results.append(rec)

        meta_file = n_out / "metadata.json"
        with open(meta_file, "w", encoding="utf-8") as fh:
            json.dump({"source_page": page_url, "fetched_at": int(time.time()), "results": results}, fh, ensure_ascii=False, indent=2)

        ok_count = sum(1 for r in results if r.get("ok"))
        logging.info("Page %s completed: %d succeeded, %d failed. Metadata: %s", n, ok_count, len(results) - ok_count, meta_file)
        all_results.append({"n": n, "source_page": page_url, "results": results})

    summary_file = out_dir / "summary.json"
    with open(summary_file, "w", encoding="utf-8") as fh:
        json.dump({"start": args.start, "end": args.end, "fetched_at": int(time.time()), "data": all_results}, fh, ensure_ascii=False, indent=2)

    logging.info("All done. Summary: %s", summary_file)


if __name__ == "__main__":
    main()
