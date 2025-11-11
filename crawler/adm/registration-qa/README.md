# Registration QA PDF Downloader

This script (`app.py`) is designed to download PDF files linked from the National Central University (NCU) registration Q&A page.

## Usage

To run the script, navigate to this directory in your terminal and execute:

```bash
python3 app.py
```

### Options

- `--url`: Specify the URL to crawl (default: `https://pdc.adm.ncu.edu.tw/reg_qa.asp`).
- `--outdir`: Specify the output directory for downloaded PDFs (default: `docs`).
- `--extensions`: Comma-separated file extensions to include for download (default: `pdf`).
- `--insecure`: Disable SSL certificate verification (use with caution, only if you encounter SSL errors).
- `--ca-bundle`: Path to a custom CA bundle file to use for verification.
- `--quiet`: Reduce output verbosity.
- `--no-metadata`: Do not write the metadata.json file.

### Example with `--insecure`

If you encounter SSL certificate verification errors, you can try running the script with the `--insecure` flag:

```bash
python3 app.py --insecure
```

## Dependencies

The script requires the following Python packages:

- `requests`
- `beautifulsoup4`
- `certifi`

These can be installed using `pip` and the `requirements.txt` file:

```bash
pip install -r requirements.txt
```

## Output

Downloaded PDF files will be saved in the `docs/` subdirectory within this folder. A `metadata.json` file will also be created, containing information about the crawled page and the download results. You can disable this with the `--no-metadata` flag.
