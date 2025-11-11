# NCU Freshman Note Crawler

This script (`app.py`) crawls and downloads all PDF documents linked from the NCU Freshman Note page.

## Usage

To run the script:
```bash
python app.py
```

If you encounter SSL errors, you can use the `--insecure` flag:
```bash
python app.py --insecure
```

## Options

- `--url`: The URL of the Freshman Note page to crawl. (Default: `https://pdc.adm.ncu.edu.tw/newble_note.asp`)
- `--outdir`: The output directory for downloaded files. (Default: `docs`)
- `--insecure`: Disable SSL certificate verification.
- `--no-metadata`: Do not write the `metadata.json` file.

## Output

The script downloads all found PDF files into the `docs` directory.

It also creates a `metadata.json` file in the `docs` directory, which contains a list of all downloaded files and their source URLs.

To disable the creation of `metadata.json`, use the `--no-metadata` flag.
