# NCU Courses Regulation Crawler

This script (`app.py`) crawls and downloads PDF documents related to course regulations for a range of academic years from the NCU website.

## Usage

To run the script for the default year range (111-114):
```bash
python app.py
```

If you encounter SSL errors, you can use the `--insecure` flag:
```bash
python app.py --insecure
```

## Options

- `--url`: The base URL template for the regulations page. The year in the URL is replaced dynamically. (Default: `https://pdc.adm.ncu.edu.tw/rule/rule114/12/12.html`)
- `--outdir`: The main output directory for all downloaded files. (Default: `docs`)
- `--extensions`: Comma-separated list of file extensions to download. (Default: `pdf`)
- `--years`: The range or list of academic years to crawl. Examples: `111-114`, `114`, `111,113`. (Default: `111-114`)
- `--insecure`: Disable SSL certificate verification.
- `--no-metadata`: Do not write `metadata.json` for each year or the top-level `summary.json`.
- `--quiet`: Reduce logging output.
- `--ca-bundle`: Path to a custom CA bundle file for SSL verification.

## Output

The script creates a directory for each year inside the `docs` folder. Each of these directories will contain the downloaded PDFs and a `metadata.json` file detailing the files for that year.

A top-level `summary.json` is also created in the `docs` folder, which contains a summary of all crawled years.

To disable the creation of all JSON files (`metadata.json` and `summary.json`), use the `--no-metadata` flag.
