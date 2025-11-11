#!/usr/bin/env python3
"""
Download registration forms from https://pdc.adm.ncu.edu.tw/form_course.asp
The actual forms are in an iframe: https://pdc.adm.ncu.edu.tw/Course/form.html
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import urljoin

import certifi
import requests
from bs4 import BeautifulSoup

# Optional imports for conversion
HAS_PANDAS = False
HAS_OPENPYXL = False
HAS_XLRD = False
HAS_WEASYPRINT = False
HAS_PYPANDOC = False
HAS_PYTHON_DOCX = False

try:
    import pandas as pd
    HAS_PANDAS = True
    try:
        import openpyxl
        HAS_OPENPYXL = True
    except ImportError:
        pass
    try:
        import xlrd
        HAS_XLRD = True
    except ImportError:
        pass
except ImportError:
    pass

try:
    from weasyprint import HTML
    HAS_WEASYPRINT = True
except (ImportError, OSError):
    # OSError: system libraries not available (pango, cairo, etc.)
    pass

try:
    import pypandoc
    HAS_PYPANDOC = True
except ImportError:
    pass

try:
    from docx import Document
    HAS_PYTHON_DOCX = True
except ImportError:
    pass


def download_file(url: str, filepath: Path, insecure: bool = False) -> dict:
    """
    Download a file from URL to filepath.
    Returns a dict with keys: ok (bool), size (int), error (str).
    """
    result = {"ok": False, "size": 0, "error": None}
    try:
        verify_arg = False if insecure else certifi.where()
        resp = requests.get(url, verify=verify_arg, timeout=30)
        resp.raise_for_status()
        
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "wb") as f:
            f.write(resp.content)
        
        result["ok"] = True
        result["size"] = len(resp.content)
    except Exception as e:
        result["error"] = str(e)
    
    return result


def convert_file(filepath: Path, remove_original: bool = False) -> dict:
    """
    Convert files to RAG-friendly formats:
    - Excel (.xls, .xlsx) -> CSV
    - HTML (.html, .htm) -> PDF (or TXT fallback)
    - Word (.doc, .docx) -> PDF (or TXT fallback)
    
    Returns dict with: ok (bool), converted (str), action (str), reason (str)
    """
    result = {"ok": False, "converted": None, "action": "failed", "reason": None}
    
    if not filepath.exists():
        result["reason"] = "file not found"
        return result
    
    ext = filepath.suffix.lower()
    
    # Skip already RAG-friendly formats
    RAG_FRIENDLY_EXTS = {".pdf", ".csv", ".txt"}
    if ext in RAG_FRIENDLY_EXTS:
        result["ok"] = True
        result["action"] = "skipped"
        result["reason"] = f"{ext} is already RAG-friendly"
        return result
    
    try:
        # Excel to CSV
        if ext in (".xls", ".xlsx"):
            if not HAS_PANDAS:
                result["reason"] = "pandas not installed"
                return result
            
            # Choose engine based on extension
            engine = None
            if ext == ".xls":
                if HAS_XLRD:
                    engine = "xlrd"
                else:
                    result["reason"] = "xlrd not installed (required for .xls)"
                    return result
            elif ext == ".xlsx":
                if HAS_OPENPYXL:
                    engine = "openpyxl"
                else:
                    result["reason"] = "openpyxl not installed (required for .xlsx)"
                    return result
            
            try:
                df = pd.read_excel(filepath, engine=engine)
                csv_path = filepath.with_suffix(".csv")
                df.to_csv(csv_path, index=False, encoding="utf-8")
                result["converted"] = str(csv_path)
                result["ok"] = True
                result["action"] = "converted"
                result["reason"] = f"excel->csv (engine={engine})"
                if remove_original:
                    filepath.unlink()
            except Exception as e:
                result["reason"] = f"pandas conversion failed: {e}"
        
        # HTML to PDF or TXT
        elif ext in (".html", ".htm"):
            pdf_path = filepath.with_suffix(".pdf")
            
            # Try WeasyPrint
            if HAS_WEASYPRINT:
                try:
                    HTML(filename=str(filepath)).write_pdf(pdf_path)
                    result["converted"] = str(pdf_path)
                    result["ok"] = True
                    result["action"] = "converted"
                    result["reason"] = "weasyprint conversion"
                    if remove_original:
                        filepath.unlink()
                    return result
                except Exception as e:
                    result["reason"] = f"weasyprint conversion failed: {e}"
            
            # Try wkhtmltopdf CLI
            if shutil.which("wkhtmltopdf"):
                try:
                    subprocess.run(
                        ["wkhtmltopdf", str(filepath), str(pdf_path)],
                        check=True,
                        capture_output=True,
                        text=True
                    )
                    result["converted"] = str(pdf_path)
                    result["ok"] = True
                    result["action"] = "converted"
                    result["reason"] = (result["reason"] or "") + ("; " if result["reason"] else "") + "wkhtmltopdf conversion"
                    if remove_original:
                        filepath.unlink()
                    return result
                except subprocess.CalledProcessError as e:
                    result["reason"] = (result["reason"] or "") + ("; " if result["reason"] else "") + f"wkhtmltopdf failed: {e.stderr}"
            
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
        elif ext in [".doc", ".docx", ".odt"]:
            # Try textutil on macOS first for binary .doc/.odt files (pandoc doesn't support binary .doc, 
            # and pandoc ODT->PDF fails with Chinese characters due to LaTeX limitations)
            if ext in [".doc", ".odt"] and shutil.which("textutil"):
                try:
                    txt_path = filepath.with_suffix(".txt")
                    subprocess.run(
                        ["textutil", "-convert", "txt", "-output", str(txt_path), str(filepath)],
                        check=True,
                        capture_output=True,
                        text=True
                    )
                    result["converted"] = str(txt_path)
                    result["ok"] = True
                    result["action"] = "converted"
                    result["reason"] = f"textutil conversion to txt (binary {ext})"
                    if remove_original:
                        filepath.unlink()
                    return result
                except subprocess.CalledProcessError as e:
                    result["reason"] = f"textutil conversion failed: {e.stderr}"
            
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
                    subprocess.run([pandoc_cli, str(filepath), "-o", str(pdf_path)], check=True, capture_output=True, text=True)
                    result["converted"] = str(pdf_path)
                    result["ok"] = True
                    result["action"] = "converted"
                    result["reason"] = (result["reason"] or "") + ("; " if result["reason"] else "") + "used pandoc CLI"
                    if remove_original:
                        filepath.unlink()
                    return result
                except subprocess.CalledProcessError as e:
                    err_msg = f"Command {e.cmd} returned non-zero exit status {e.returncode}"
                    if ext == ".doc" and e.returncode == 21:
                        err_msg += " (binary .doc not supported by pandoc)"
                    elif ext == ".odt" and e.returncode == 43:
                        err_msg += " (pandoc ODT->PDF fails with Chinese chars, needs LaTeX CJK support)"
                    result["reason"] = (result["reason"] or "") + ("; " if result["reason"] else "") + f"pandoc CLI failed: {err_msg}"

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


def extract_iframe_src(html_text: str) -> str:
    """Extract iframe src from HTML text. Returns empty string if not found."""
    soup = BeautifulSoup(html_text, "html.parser")
    iframe = soup.find("iframe")
    if iframe and iframe.get("src"):
        return iframe["src"]
    return ""


def extract_links(html_text: str, base_url: str, extensions: list) -> list:
    """
    Extract all links from HTML text that match the given extensions.
    Returns list of dicts with keys: text, href, abs_url
    """
    soup = BeautifulSoup(html_text, "html.parser")
    links = []
    
    for link in soup.find_all("a", href=True):
        href = link["href"]
        # Check if any extension matches
        if any(ext.lower() in href.lower() for ext in extensions):
            abs_url = urljoin(base_url, href)
            text = link.get_text(strip=True)
            links.append({
                "text": text,
                "href": href,
                "abs_url": abs_url
            })
    
    return links


def main(argv=None):
    parser = argparse.ArgumentParser(description="Download registration forms from form_course.asp")
    parser.add_argument("--url", default="https://pdc.adm.ncu.edu.tw/form_course.asp",
                        help="URL of the registration forms page")
    parser.add_argument("--extensions", default="pdf,doc,docx,xls,xlsx,odt",
                        help="Comma-separated list of file extensions to download")
    parser.add_argument("--output-dir", default="docs",
                        help="Output directory for downloaded files")
    parser.add_argument("--insecure", action="store_true",
                        help="Disable SSL certificate verification")
    parser.add_argument("--convert", action="store_true",
                        help="Convert files to RAG-friendly formats after download")
    parser.add_argument("--remove-originals", action="store_true",
                        help="Remove original files after successful conversion")
    parser.add_argument("--ca-bundle", default=None,
                        help="Path to CA bundle file for SSL verification")
    parser.add_argument("--no-metadata", action="store_true",
                        help="Do not write the metadata.json file")
    
    args = parser.parse_args(argv)
    
    # Suppress TLS warnings if insecure mode
    if args.insecure:
        try:
            import urllib3
            urllib3.disable_warnings()
        except ImportError:
            pass
    
    extensions = [f".{ext.strip().lstrip('.')}" for ext in args.extensions.split(",")]
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Step 1: Fetch the main page
    print(f"Fetching main page: {args.url}")
    verify_arg = False if args.insecure else (args.ca_bundle or certifi.where())
    
    try:
        r = requests.get(args.url, verify=verify_arg, timeout=30)
        r.encoding = r.apparent_encoding or "big5"
        r.raise_for_status()
    except Exception as e:
        print(f"Error fetching main page: {e}", file=sys.stderr)
        return 1
    
    # Step 2: Extract iframe src
    iframe_src = extract_iframe_src(r.text)
    if not iframe_src:
        print("No iframe found on the page", file=sys.stderr)
        return 1
    
    iframe_url = urljoin(args.url, iframe_src)
    print(f"Found iframe: {iframe_url}")
    
    # Step 3: Fetch iframe content
    try:
        r_iframe = requests.get(iframe_url, verify=verify_arg, timeout=30)
        r_iframe.encoding = r_iframe.apparent_encoding or "big5"
        r_iframe.raise_for_status()
    except Exception as e:
        print(f"Error fetching iframe: {e}", file=sys.stderr)
        return 1
    
    # Step 4: Extract all file links
    links = extract_links(r_iframe.text, iframe_url, extensions)
    print(f"Found {len(links)} file links")
    
    if not links:
        print("No files found to download")
        return 0
    
    # Step 5: Download files
    metadata = []
    downloaded = 0
    failed = 0
    
    for link in links:
        filename = Path(link["abs_url"]).name
        filepath = output_dir / filename
        
        print(f"Downloading: {filename}")
        result = download_file(link["abs_url"], filepath, insecure=args.insecure)
        
        meta = {
            "filename": filename,
            "url": link["abs_url"],
            "text": link["text"],
            "downloaded": result["ok"],
            "size": result["size"],
            "error": result["error"]
        }
        
        if result["ok"]:
            downloaded += 1
            
            # Convert if requested
            if args.convert:
                conv_result = convert_file(filepath, remove_original=args.remove_originals)
                meta["conversion"] = {
                    "ok": conv_result["ok"],
                    "converted": conv_result["converted"],
                    "action": conv_result["action"],
                    "reason": conv_result["reason"]
                }
        else:
            failed += 1
        
        metadata.append(meta)
    
    # Step 6: Save metadata
    if not args.no_metadata:
        metadata_file = output_dir / "metadata.json"
        with open(metadata_file, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    # Step 7: Print summary
    print(f"\n=== Summary ===")
    print(f"Downloaded: {downloaded}")
    print(f"Failed: {failed}")
    
    if args.convert:
        converted = sum(1 for m in metadata if m.get("conversion", {}).get("action") == "converted")
        skipped = sum(1 for m in metadata if m.get("conversion", {}).get("action") == "skipped")
        conv_failed = sum(1 for m in metadata if m.get("conversion", {}).get("action") == "failed")
        print(f"Converted: {converted}")
        print(f"Skipped: {skipped}")
        print(f"Conversion failed: {conv_failed}")
    
    if not args.no_metadata:
        print(f"\nMetadata saved to: {output_dir / 'metadata.json'}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
