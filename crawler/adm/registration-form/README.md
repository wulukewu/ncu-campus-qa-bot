# Registration Form Downloader

Download registration forms from the NCU Admin website. The script automatically extracts the iframe URL and downloads all linked files.

**Main page:** https://pdc.adm.ncu.edu.tw/form_reg.asp  
**Iframe URL:** https://pdc.adm.ncu.edu.tw/Register/form_reg_i.asp

> 💡 **Need to find iframe URLs?** See [HOW_TO_FIND_IFRAME.md](../HOW_TO_FIND_IFRAME.md) or use `python ../find_iframe.py <url> --insecure`

## Usage

To run the script, navigate to this directory in your terminal and execute:

```bash
python3 app.py
```

### Options

- `--url`: Specify the URL to crawl (default: `https://pdc.adm.ncu.edu.tw/form_reg.asp`).
- `--extensions`: Comma-separated file extensions to download (default: `pdf,doc,docx,xls,xlsx,odt`).
- `--output-dir`: Directory to save files (default: `docs`).
- `--insecure`: Disable SSL certificate verification.
- `--convert`: Convert downloaded files to RAG-friendly formats (e.g., `.doc` to `.pdf`, `.xls` to `.csv`).
- `--remove-originals`: After a successful conversion, remove the original file.

### Dependencies

This script has several optional dependencies for file conversion. To install all dependencies, use the `requirements.txt` file in the parent `crawler` directory:

```bash
pip install -r ../requirements.txt 
```
Key dependencies include:
- `requests`
- `beautifulsoup4`
- `certifi`
- `pandas`, `openpyxl`, `xlrd` (for Excel conversion)
- `weasyprint` or `wkhtmltopdf` (for HTML conversion)
- `pypandoc` or `python-docx` (for Word conversion)

## Output

Downloaded files are saved in the `docs/` subdirectory. A `metadata.json` file is also created with details about each downloaded file and any conversions performed.
