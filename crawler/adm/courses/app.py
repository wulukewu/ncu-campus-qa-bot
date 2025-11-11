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
    parser.add_argument("--years", required=False, help="Year or range to crawl, e.g. 111-114 or 114 or 111,113",
                        default="111-114")
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

    # parse years list
    def parse_years(s: str):
        s = s.strip()
        years = set()
        for part in s.split(','):
            part = part.strip()
            if '-' in part:
                a, b = part.split('-', 1)
                try:
                    a_i = int(a)
                    b_i = int(b)
                    for y in range(a_i, b_i + 1):
                        years.add(str(y))
                except ValueError:
                    continue
            else:
                if part:
                    years.add(part)
        return sorted(years)

    years = parse_years(args.years)
    if not years:
        logging.error("No valid years parsed from --years=%s", args.years)
        sys.exit(2)

    logging.info("Will crawl years: %s", ",".join(years))
    # determine verification mode
    if args.insecure:
        verify = False
    elif args.ca_bundle:
        verify = args.ca_bundle
    else:
        verify = certifi.where() if certifi is not None else True

    all_results = []
    # For each year, build the page URL and download matching files into out_dir/<year>/
    for year in years:
        page_url = args.url.replace("rule114", f"rule{year}")
        logging.info("Fetching page for year %s: %s", year, page_url)
        try:
            r = session.get(page_url, timeout=20, verify=verify)
            r.raise_for_status()
        except requests.RequestException as e:
            logging.error("Failed to fetch %s: %s", page_url, e)
            all_results.append({"year": year, "source_page": page_url, "results": [], "error": str(e)})
            continue

        links = extract_links(r.text, page_url)
        logging.info("Found %d links on the page for year %s", len(links), year)

        # filter and deduplicate
        to_download = []
        seen = set()
        for link in links:
            if link in seen:
                continue
            seen.add(link)
            if has_allowed_ext(link, allowed):
                to_download.append(link)

        logging.info("Year %s: Will download %d files (matching extensions)", year, len(to_download))

        year_out = out_dir / year
        year_out.mkdir(parents=True, exist_ok=True)

        results = []
        for url in to_download:
            logging.info("[%s] Downloading %s", year, url)
            rec = download_file(session, url, year_out, verify=verify)
            results.append(rec)

        meta_file = year_out / "metadata.json"
        with open(meta_file, "w", encoding="utf-8") as fh:
            json.dump({"source_page": page_url, "fetched_at": int(time.time()), "results": results}, fh, ensure_ascii=False, indent=2)

        ok_count = sum(1 for r in results if r.get("ok"))
        logging.info("Year %s completed: %d succeeded, %d failed. Metadata: %s", year, ok_count, len(results) - ok_count, meta_file)
        all_results.append({"year": year, "source_page": page_url, "results": results})

    # write top-level summary
    summary_file = out_dir / "summary.json"
    with open(summary_file, "w", encoding="utf-8") as fh:
        json.dump({"years": years, "fetched_at": int(time.time()), "data": all_results}, fh, ensure_ascii=False, indent=2)

    logging.info("All done. Summary: %s", summary_file)


if __name__ == "__main__":
    main()
