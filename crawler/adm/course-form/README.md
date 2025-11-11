# Course Form Downloader

Download course-related forms from the NCU Admin website. The script automatically extracts the iframe URL and downloads all linked files.

**Main page:** https://pdc.adm.ncu.edu.tw/form_course.asp  
**Iframe URL:** https://pdc.adm.ncu.edu.tw/Course/form.html

> 💡 **Need to find iframe URLs?** See [HOW_TO_FIND_IFRAME.md](../HOW_TO_FIND_IFRAME.md) or use `python ../find_iframe.py <url> --insecure`

## Usage

Default behavior (downloads all forms):

```bash
# from crawler/adm/registration-form
python app.py --insecure
```

Defaults:

- URL: https://pdc.adm.ncu.edu.tw/form_course.asp
- Extensions: pdf, doc, docx, xls, xlsx, odt
- Output directory: `docs/`

You can override with flags:

```bash
python app.py --insecure --extensions pdf,docx --output-dir forms
```

## File Conversion for RAG

To convert downloaded files to RAG-friendly formats (Excel→CSV, HTML/Word→PDF):

```bash
python app.py --insecure --convert
```

To also remove original files after conversion:

```bash
python app.py --insecure --convert --remove-originals
```

**Conversion requirements**

- Excel to CSV (pip): `pandas`, `openpyxl`, plus `xlrd` for legacy `.xls` files.
- HTML to PDF:
  - Prefer `weasyprint` (pip) but it also needs system libraries on macOS: `brew install pango cairo gdk-pixbuf libffi`.
  - Alternative (no Python libs): install `wkhtmltopdf` and the script will use it automatically if WeasyPrint isn't available: `brew install wkhtmltopdf`.
  - If neither is available, the script falls back to extracting text to `.txt` (supports Big5/UTF-8/GB2312/GBK encoding detection).
- Word (DOC/DOCX) to PDF:
  - **Binary `.doc` files**: On macOS, the script tries `textutil` first (built-in) to convert to `.txt`. Note that pandoc does not support legacy binary `.doc` format (exit code 21).
  - **`.docx` files**: Use `pypandoc` (pip) with `pandoc` binary: `brew install pandoc`.
  - If `pypandoc` is missing but `pandoc` is installed, the script uses the `pandoc` CLI directly.
  - If neither is available, `.docx` falls back to plain text using `python-docx` (pip).
- **ODT files**: Require `pandoc` for conversion to PDF.

Already RAG-friendly formats (`.pdf`, `.csv`, `.txt`) are skipped (counted as `skipped`) rather than re-converted. Conversion logs differentiate `converted`, `skipped`, and `failed`.

## Output

All files are saved to the `docs/` directory with a `metadata.json` file containing:

- Download status and file size
- Conversion status (if `--convert` used)
- Original URLs and link text

## Dependencies

Install from the parent `crawler/requirements.txt`:

```bash
cd ../../
pip install -r requirements.txt
```
