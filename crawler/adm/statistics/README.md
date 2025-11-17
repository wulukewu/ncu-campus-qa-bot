Download files (pdf/doc/xls/html etc.) from the statistics pages and save them into per-number folders under `docs/`.

Default behavior:

```bash
# from crawler/adm/statistics
python app.py --insecure
```

Defaults:

- URL template: https://pdc.adm.ncu.edu.tw/rate_note_reg1.asp (script will replace the number 1 with 1..4)
- Range: 1..4
- Extensions: pdf, doc, docx, xls, xlsx, ppt, pptx, txt, zip, rar, htm, html

You can override with flags:

```bash
python app.py --start 1 --end 4 --extensions pdf,html --url "https://.../rate_note_reg{n}.asp"
```

- `--quiet`: Quiet mode.
- `--no-metadata`: Do not write `metadata.json` for each page or the top-level `summary.json`.

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

Already RAG-friendly formats (`.pdf`, `.csv`, `.txt`) are skipped (counted as `skipped`) rather than re-converted. Conversion logs differentiate `converted`, `skipped`, and `failed`.

## Output

The script downloads files into `docs/<n>/` folders, where `<n>` corresponds to the page number. Each of these subdirectories will contain a `metadata.json` file with details about the downloaded files for that page.

A top-level `summary.json` is also created in the `docs/` folder, which contains a summary of all crawled pages.

To disable the creation of all JSON files (`metadata.json` and `summary.json`), use the `--no-metadata` flag.

