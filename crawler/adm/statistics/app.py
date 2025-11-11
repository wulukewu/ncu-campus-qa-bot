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
import shutil
import subprocess

import requests
try:
    import certifi
except Exception:
    certifi = None
from bs4 import BeautifulSoup

# Optional conversion dependencies
try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

try:
    from weasyprint import HTML as WeasyprintHTML
    HAS_WEASYPRINT = True
except (ImportError, OSError):
    # OSError can occur if system libraries (libgobject, pango, etc.) are missing
    HAS_WEASYPRINT = False

try:
    import pypandoc
    HAS_PYPANDOC = True
except ImportError:
    HAS_PYPANDOC = False

try:
    from docx import Document
    HAS_PYTHON_DOCX = True
except ImportError:
    HAS_PYTHON_DOCX = False


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


RAG_FRIENDLY_EXTS = {".pdf", ".csv", ".txt"}


def convert_file(filepath: Path, remove_original: bool = False) -> dict:
    """Convert files to RAG-friendly formats.
    
    - Excel (xls, xlsx) -> CSV
    - HTML (htm, html) -> PDF
    - Word (doc, docx) -> PDF
    
    Returns dict with conversion status.
    """
    result = {"original": str(filepath), "converted": None, "ok": False, "reason": None, "action": "failed"}
    ext = filepath.suffix.lower()
    
    try:
        # Already RAG-friendly formats: skip
        if ext in RAG_FRIENDLY_EXTS:
            result["ok"] = True
            result["reason"] = "already RAG-friendly format"
            result["action"] = "skipped"
            return result

        # Excel to CSV
        if ext in [".xls", ".xlsx"]:
            if not HAS_PANDAS:
                result["reason"] = "pandas not installed"
                return result
            
            # Select engine based on extension
            engine = "xlrd" if ext == ".xls" else "openpyxl"
            try:
                df = pd.read_excel(filepath, sheet_name=None, engine=engine)  # Read all sheets
            except Exception as e:
                result["reason"] = f"read_excel failed: {e}"
                return result

            if len(df) == 1:
                # Single sheet - save as single CSV
                csv_path = filepath.with_suffix(".csv")
                list(df.values())[0].to_csv(csv_path, index=False, encoding="utf-8")
                result["converted"] = str(csv_path)
            else:
                # Multiple sheets - save each sheet
                converted_files = []
                for sheet_name, sheet_df in df.items():
                    safe_sheet = re.sub(r'[^\w\-]', '_', sheet_name)
                    csv_path = filepath.parent / f"{filepath.stem}_{safe_sheet}.csv"
                    sheet_df.to_csv(csv_path, index=False, encoding="utf-8")
                    converted_files.append(str(csv_path))
                result["converted"] = converted_files
            
            result["ok"] = True
            result["action"] = "converted"
            if remove_original:
                filepath.unlink()
        
        # HTML to PDF (fallback chain: weasyprint -> wkhtmltopdf -> TXT)
        elif ext in [".htm", ".html"]:
            # Attempt weasyprint
            if HAS_WEASYPRINT:
                try:
                    pdf_path = filepath.with_suffix(".pdf")
                    WeasyprintHTML(filename=str(filepath)).write_pdf(str(pdf_path))
                    result["converted"] = str(pdf_path)
                    result["ok"] = True
                    result["action"] = "converted"
                    if remove_original:
                        filepath.unlink()
                    return result
                except Exception as e:
                    result["reason"] = f"weasyprint failed: {e}"
            
            # Attempt wkhtmltopdf CLI
            wkhtml = shutil.which("wkhtmltopdf")
            if wkhtml:
                try:
                    pdf_path = filepath.with_suffix(".pdf")
                    subprocess.run([wkhtml, str(filepath), str(pdf_path)], check=True)
                    result["converted"] = str(pdf_path)
                    result["ok"] = True
                    result["action"] = "converted"
                    result["reason"] = (result["reason"] or "") + ("; " if result["reason"] else "") + "used wkhtmltopdf"
                    if remove_original:
                        filepath.unlink()
                    return result
                except Exception as e:
                    result["reason"] = (result["reason"] or "") + ("; " if result["reason"] else "") + f"wkhtmltopdf failed: {e}"

            # Fallback: extract text from HTML to .txt
            try:
                # Try to detect encoding (common Chinese encodings)
                html_content = None
                for enc in ['utf-8', 'big5', 'gb2312', 'gbk']:
                    try:
                        with open(filepath, "r", encoding=enc) as fh:
                            html_content = fh.read()
                            break
                    except (UnicodeDecodeError, LookupError):
                        continue
                
                if html_content is None:
                    with open(filepath, "r", encoding="utf-8", errors="ignore") as fh:
                        html_content = fh.read()
                
                soup = BeautifulSoup(html_content, "html.parser")
                text = soup.get_text("\n", strip=True)
                txt_path = filepath.with_suffix(".txt")
                with open(txt_path, "w", encoding="utf-8") as out:
                    out.write(text)
                result["converted"] = str(txt_path)
                result["ok"] = True
                result["action"] = "converted"
                result["reason"] = (result["reason"] or "") + ("; " if result["reason"] else "") + "html->txt fallback"
                if remove_original:
                    filepath.unlink()
            except Exception as e:
                result["reason"] = (result["reason"] or "") + ("; " if result["reason"] else "") + f"html->txt fallback failed: {e}"
        
        # Word to PDF (prefer pandoc). Fallback: DOCX->TXT if python-docx available.
        elif ext in [".doc", ".docx"]:
            tried_pandoc = False
            pdf_path = filepath.with_suffix(".pdf")
            if HAS_PYPANDOC:
                tried_pandoc = True
                try:
                    pypandoc.convert_file(str(filepath), 'pdf', outputfile=str(pdf_path))
                    result["converted"] = str(pdf_path)
                    result["ok"] = True
                    result["action"] = "converted"
                    if remove_original:
                        filepath.unlink()
                    return result
                except Exception as e:
                    result["reason"] = f"pypandoc conversion failed: {e}"

            # Try pandoc CLI
            pandoc_cli = shutil.which("pandoc")
            if pandoc_cli:
                tried_pandoc = True
                try:
                    subprocess.run([pandoc_cli, str(filepath), "-o", str(pdf_path)], check=True)
                    result["converted"] = str(pdf_path)
                    result["ok"] = True
                    result["action"] = "converted"
                    result["reason"] = (result["reason"] or "") + ("; " if result["reason"] else "") + "used pandoc CLI"
                    if remove_original:
                        filepath.unlink()
                    return result
                except Exception as e:
                    result["reason"] = (result["reason"] or "") + ("; " if result["reason"] else "") + f"pandoc CLI failed: {e}"

            # Fallback: For .docx only, extract text using python-docx
            if ext == ".docx" and HAS_PYTHON_DOCX:
                try:
                    doc = Document(str(filepath))
                    lines = [p.text for p in doc.paragraphs]
                    txt_path = filepath.with_suffix(".txt")
                    with open(txt_path, "w", encoding="utf-8") as out:
                        out.write("\n".join(lines))
                    result["converted"] = str(txt_path)
                    result["ok"] = True
                    result["action"] = "converted"
                    extra = " (pandoc not available)" if not tried_pandoc else " (pandoc failed)"
                    result["reason"] = (result["reason"] or "") + ("; " if result["reason"] else "") + f"docx->txt fallback{extra}"
                    if remove_original:
                        filepath.unlink()
                except Exception as e:
                    result["reason"] = (result["reason"] or "") + ("; " if result["reason"] else "") + f"docx->txt fallback failed: {e}"
            else:
                if not tried_pandoc:
                    result["reason"] = "doc/docx conversion requires pandoc (pypandoc not installed). For .docx, install python-docx for text fallback."
        
        else:
            result["reason"] = f"unsupported format: {ext}"
    
    except Exception as e:
        result["reason"] = str(e)
    
    return result


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
    parser.add_argument("--convert", action="store_true", help="Convert files to RAG-friendly formats (Excel->CSV, HTML/Word->PDF)")
    parser.add_argument("--remove-originals", action="store_true", help="Remove original files after conversion (only with --convert)")
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
    if args.insecure:
        try:
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        except Exception:
            pass

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
        
        # Convert files if requested
        if args.convert:
            logging.info("Page %s: converting files to RAG-friendly formats", n)
            conversion_results = []
            for rec in results:
                if rec.get("ok") and rec.get("filename"):
                    filepath = Path(rec["filename"])
                    if filepath.exists():
                        ext = filepath.suffix.lower()
                        if ext in RAG_FRIENDLY_EXTS:
                            # Skip already friendly formats entirely
                            rec["conversion"] = {"original": str(filepath), "converted": None, "ok": True, "reason": "already RAG-friendly format", "action": "skipped"}
                            continue

                        logging.info("[%s] Converting %s", n, filepath.name)
                        conv_rec = convert_file(filepath, remove_original=args.remove_originals)
                        conversion_results.append(conv_rec)
                        rec["conversion"] = conv_rec

            conv_converted = sum(1 for c in conversion_results if c.get("action") == "converted")
            conv_failed = sum(1 for c in conversion_results if c.get("action") == "failed")
            conv_skipped = sum(1 for r in results if isinstance(r.get("conversion"), dict) and r["conversion"].get("action") == "skipped")
            logging.info("Page %s: %d converted, %d skipped, %d failed", n, conv_converted, conv_skipped, conv_failed)

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
