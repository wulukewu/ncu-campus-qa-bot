Converter environment setup

This folder contains `setup_converter_env.sh`, a helper to prepare a Linux environment for document conversions used by the crawlers.

Quick guide

1. Make the script executable (if not already):

   chmod +x crawler/setup_converter_env.sh

2. Run the script interactively and install system packages:

   ./crawler/setup_converter_env.sh

   or non-interactively:

   ./crawler/setup_converter_env.sh -y

3. To also install Python packages (recommended) into a virtualenv inside `crawler/.venv`:

   ./crawler/setup_converter_env.sh -y --pip --venv crawler/.venv

4. After the script completes, activate the venv before running crawlers that depend on Python packages:

   source crawler/.venv/bin/activate

   python crawler/adm/course-form/app.py --convert --output-dir ./docs

Notes

- The script detects `apt`, `dnf`, `yum` or `pacman`. It will skip packages unavailable in the distro repositories.
- It installs LibreOffice (soffice) and prefers LibreOffice headless conversion for doc/docx/odt files. This avoids having to install a full TeX stack.
- If you want PDF generation via `pandoc`, you must ensure a LaTeX engine is available (e.g. `texlive` packages). This script does not automatically install the full TeX live distribution.
- If you need to run crawlers in system services or CI, activate the virtualenv in the service wrapper or install the pip requirements globally (less recommended).

New flag: --only-missing / -m

If you run the setup script with `--only-missing` (or `-m`), it will check which packages are already installed on the system and only attempt to install the missing ones. This is useful for idempotent runs on existing machines or in provisioning scripts.

Troubleshooting

- If conversions still fail, check the saved metadata (`--output-dir`/`metadata.json`) and look at `conversion.reason` for the specific error.
- For WeasyPrint to work you may need additional system libraries (`cairo`, `pango`, `gdk-pixbuf`), the script attempts to install commonly-named deps when available.

If you'd like, I can also:
- Add an automated wrapper that always runs crawlers inside the venv, or
- Add separate `required` and `optional` package groups and prompt before installing optional extras.
