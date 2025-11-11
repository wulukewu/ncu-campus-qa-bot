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
