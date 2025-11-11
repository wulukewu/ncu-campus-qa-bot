# How to Find Iframe URLs

Many pages on the NCU Admin website (https://pdc.adm.ncu.edu.tw/) use iframes to embed content. The actual downloadable files are often in these embedded pages, not the main page.

## Quick Method: Use the `find_iframe.py` Script

We've created a utility script to automatically extract iframe URLs:

```bash
cd /path/to/crawler/adm
python find_iframe.py <URL> --insecure
```

### Examples:

**Course Forms:**
```bash
python find_iframe.py https://pdc.adm.ncu.edu.tw/form_course.asp --insecure
```
Output:
```
✅ Found 1 iframe(s)

Iframe #1:
  Relative: ./Course/form.html
  Absolute: https://pdc.adm.ncu.edu.tw/Course/form.html
```

**Registration Forms:**
```bash
python find_iframe.py https://pdc.adm.ncu.edu.tw/form_reg.asp --insecure
```
Output:
```
✅ Found 1 iframe(s)

Iframe #1:
  Relative: ./Register/form_reg_i.asp
  Absolute: https://pdc.adm.ncu.edu.tw/Register/form_reg_i.asp
```

## Manual Method: Using Browser DevTools

If you prefer to find iframes manually:

1. **Open the page in your browser**
   - Navigate to the target URL (e.g., https://pdc.adm.ncu.edu.tw/form_course.asp)

2. **Open Developer Tools**
   - Chrome/Edge: Press `F12` or `Ctrl+Shift+I` (Windows) / `Cmd+Option+I` (Mac)
   - Firefox: Press `F12` or `Ctrl+Shift+I` (Windows) / `Cmd+Option+I` (Mac)

3. **Inspect the page**
   - Press `Ctrl+F` (Windows) or `Cmd+F` (Mac) in DevTools
   - Search for `<iframe`
   - Look for the `src` attribute in the iframe tag

4. **Extract the URL**
   - Copy the `src` value (e.g., `./Course/form.html`)
   - If it's a relative URL (starts with `.` or `/`), combine it with the base URL:
     - `./Course/form.html` → `https://pdc.adm.ncu.edu.tw/Course/form.html`
     - `/Register/form_reg_i.asp` → `https://pdc.adm.ncu.edu.tw/Register/form_reg_i.asp`

## Manual Method: Using Command Line

You can also use curl and grep:

```bash
curl -k https://pdc.adm.ncu.edu.tw/form_course.asp | grep -i "iframe"
```

This will show you the iframe tags in the HTML.

## Known Iframe URLs

Here are the iframe URLs we've discovered so far:

| Main Page | Iframe URL | Purpose |
|-----------|------------|---------|
| https://pdc.adm.ncu.edu.tw/form_course.asp | https://pdc.adm.ncu.edu.tw/Course/form.html | Course-related forms |
| https://pdc.adm.ncu.edu.tw/form_reg.asp | https://pdc.adm.ncu.edu.tw/Register/form_reg_i.asp | Registration forms |
| https://pdc.adm.ncu.edu.tw/rate_note_reg1.asp | (contains iframe to statistics table) | Statistics data |

## How the Downloaders Use This

All our downloader scripts (`course-form/app.py`, `registration-form/app.py`, etc.) follow this pattern:

1. **Fetch the main page** - Get the HTML from the user-provided URL
2. **Extract iframe src** - Use BeautifulSoup to find `<iframe>` tags
3. **Build absolute URL** - Convert relative URLs to absolute using `urljoin()`
4. **Fetch iframe content** - Get the actual page with downloadable files
5. **Extract file links** - Find all links matching the target extensions

This is implemented in the `extract_iframe_src()` function in each script.

## Troubleshooting

**Problem: "No iframe found on the page"**
- The page might not use iframes
- The content might be loaded dynamically with JavaScript
- Try accessing the page with `--insecure` flag

**Problem: "Found 0 file links"**
- Check if the iframe URL is correct
- Verify the file extensions in your `--extensions` flag
- The iframe page might also use JavaScript to load content

**Problem: SSL certificate errors**
- Use the `--insecure` flag (for development only!)
- Or provide a CA bundle with `--ca-bundle /path/to/bundle.pem`
