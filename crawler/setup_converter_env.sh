#!/usr/bin/env bash
set -euo pipefail

# Setup script to install converter dependencies for crawlers
# Places: /workspaces/ncu-campus-qa-bot/crawler/setup_converter_env.sh
# Usage:
#   ./crawler/setup_converter_env.sh           # interactive install (asks for sudo if needed)
#   ./crawler/setup_converter_env.sh -y        # assume yes to install
#   ./crawler/setup_converter_env.sh --dry-run # show what would be installed
#   ./crawler/setup_converter_env.sh --no-sudo # install without sudo (must be root)

ASSUME_YES=0
DRY_RUN=0
NO_SUDO=0
INSTALL_PIP=0
VENV_DIR=".venv"
ONLY_MISSING=0


show_help() {
  cat <<EOF
Usage: $0 [options]

Options:
  -y, --yes        Assume yes for package installs (non-interactive)
  --dry-run        Print actions only, do not install
  --no-sudo        Do not use sudo even when not root
  -h, --help       Show this help

This script detects a package manager (apt, dnf, pacman) and installs
common converter packages used by crawlers: LibreOffice, pandoc,
wkhtmltopdf, ImageMagick, ghostscript, poppler-utils and common fonts.

This script intentionally performs only environment setup (installs)
and does not perform any file conversions itself.
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    -y|--yes) ASSUME_YES=1; shift ;;
    --dry-run) DRY_RUN=1; shift ;;
    --no-sudo) NO_SUDO=1; shift ;;
    -h|--help) show_help; exit 0 ;;
    --pip) INSTALL_PIP=1; shift ;;
    --venv) if [ -n "$2" ]; then VENV_DIR="$2"; shift 2; else echo "--venv requires a path"; exit 1; fi ;;
    -m|--only-missing) ONLY_MISSING=1; shift ;;
    *) echo "Unknown option: $1"; show_help; exit 1 ;;
  esac
done

echo "Preparing converter environment setup"

is_root() { [ "$(id -u)" -eq 0 ]; }

detect_pkg_mgr() {
  if command -v apt-get >/dev/null 2>&1; then
    echo apt
  elif command -v dnf >/dev/null 2>&1; then
    echo dnf
  elif command -v yum >/dev/null 2>&1; then
    echo yum
  elif command -v pacman >/dev/null 2>&1; then
    echo pacman
  else
    echo none
  fi
}

PKG_MGR=$(detect_pkg_mgr)
if [ "$PKG_MGR" = "none" ]; then
  echo "No supported package manager found (apt/dnf/yum/pacman). Exiting." >&2
  exit 2
fi

echo "Detected package manager: $PKG_MGR"

SUDO_CMD=""
if ! is_root && [ "$NO_SUDO" -eq 0 ]; then
  if command -v sudo >/dev/null 2>&1; then
    SUDO_CMD="sudo"
  else
    echo "sudo not found and not running as root. Either run as root or pass --no-sudo and run as root." >&2
    exit 3
  fi
fi

# Map package names by package manager
declare -a packages
case "$PKG_MGR" in
  apt)
    # NOTE: some Ubuntu releases may not have libreoffice-pdfimport; skip it
    packages=(\
      libreoffice-core libreoffice-writer libreoffice-common \
      pandoc wkhtmltopdf imagemagick ghostscript poppler-utils \
      fonts-noto-cjk fonts-noto-color-emoji fonts-dejavu-core fonts-dejavu-extra \
      unoconv curl wget unzip python3-pip python3-venv \
      )
    # extra system libs used by WeasyPrint (cairo/pango)
    weasy_deps=(libcairo2 libpango-1.0-0 libgdk-pixbuf2.0-0 libffi-dev shared-mime-info)
    ;;
  dnf|yum)
    packages=(\
      libreoffice libreoffice-writer libreoffice-calc libreoffice-impress \
      pandoc wkhtmltopdf ImageMagick ghostscript poppler-utils \
      google-noto-emoji-fonts dejavu-sans-fonts unoconv curl wget unzip python3-pip python3-virtualenv \
      )
    weasy_deps=(cairo pango gdk-pixbuf libffi shared-mime-info)
    ;;
  pacman)
    packages=(\
      libreoffice-still pandoc wkhtmltopdf imagemagick ghostscript poppler \
      noto-fonts noto-fonts-emoji ttf-dejavu unoconv curl wget unzip python-pip python-virtualenv \
      )
    weasy_deps=(cairo pango gdk-pixbuf libffi shared-mime-info)
    ;;
esac

echo "Will ensure the following packages are installed:"
  for p in "${packages[@]}"; do
    echo "  - $p"
  done

  if [ "$INSTALL_PIP" -eq 1 ]; then
    echo "Also will install Python packages from requirements.txt into venv: $VENV_DIR"
  fi

  # helper: check if a package is available in the package manager
  pkg_available() {
    pkg="$1"
    case "$PKG_MGR" in
      apt)
        # apt-cache policy shows Candidate: (none) when unavailable
        if apt-cache policy "$pkg" 2>/dev/null | grep -q "Candidate: (none)"; then
          return 1
        fi
        # apt-cache policy may still print Candidate: (none) for virtual pkgs; check show
        if ! apt-cache show "$pkg" >/dev/null 2>&1; then
          return 1
        fi
        return 0
        ;;
      dnf)
        if dnf --quiet info "$pkg" >/dev/null 2>&1; then
          return 0
        else
          return 1
        fi
        ;;
      yum)
        if yum --quiet info "$pkg" >/dev/null 2>&1; then
          return 0
        else
          return 1
        fi
        ;;
      pacman)
        if pacman -Ss "^${pkg}($|/)" >/dev/null 2>&1; then
          return 0
        else
          return 1
        fi
        ;;
      *) return 1 ;;
    esac
  }

  # helper: check if a package is already installed
  pkg_installed() {
    pkg="$1"
    case "$PKG_MGR" in
      apt)
        dpkg -s "$pkg" >/dev/null 2>&1 && return 0 || return 1
        ;;
      dnf)
        rpm -q "$pkg" >/dev/null 2>&1 && return 0 || return 1
        ;;
      yum)
        rpm -q "$pkg" >/dev/null 2>&1 && return 0 || return 1
        ;;
      pacman)
        pacman -Qi "$pkg" >/dev/null 2>&1 && return 0 || return 1
        ;;
      *) return 1 ;;
    esac
  }

  # Build list of actually-available packages to avoid apt failing on missing candidates
  available_pkgs=()
  for p in "${packages[@]}"; do
    if pkg_available "$p"; then
      available_pkgs+=("$p")
    else
      echo "Note: package not available in repos and will be skipped: $p"
    fi
  done

  # Also include optional weasy_deps if available (don't fail if not)
  if [ -n "${weasy_deps[*]:-}" ]; then
    for p in "${weasy_deps[@]}"; do
      if pkg_available "$p"; then
        # avoid duplicates
        skip=0
        for ap in "${available_pkgs[@]}"; do if [ "$ap" = "$p" ]; then skip=1; break; fi; done
        if [ $skip -eq 0 ]; then available_pkgs+=("$p"); fi
      else
        echo "Note: weasy dependency not present: $p (weasyprint may not work)"
      fi
    done
  fi

  if [ ${#available_pkgs[@]} -eq 0 ]; then
    echo "No available packages found for installation on this system. Exiting." >&2
    exit 0
  fi

  # If requested, restrict to only missing (not already installed) packages
  install_list=()
  if [ "$ONLY_MISSING" -eq 1 ]; then
    echo "Checking which of the available packages are not already installed (only-missing mode)"
    for p in "${available_pkgs[@]}"; do
      if pkg_installed "$p"; then
        echo "  - already installed: $p"
      else
        install_list+=("$p")
      fi
    done
    if [ ${#install_list[@]} -eq 0 ]; then
      echo "All available packages are already installed. Nothing to do."
      exit 0
    fi
  else
    install_list=("${available_pkgs[@]}")
  fi

if [ "$DRY_RUN" -eq 1 ]; then
  echo "Dry-run mode; no changes will be made. Exiting."
  exit 0
fi

if [ "$ASSUME_YES" -eq 0 ]; then
  read -r -p "Proceed to install the packages above? [Y/n] " resp || true
  resp=${resp:-Y}
  if ! [[ "$resp" =~ ^[Yy] ]]; then
    echo "Aborted by user."; exit 0
  fi
fi

echo "Installing packages..."
case "$PKG_MGR" in
  apt)
    $SUDO_CMD apt-get update -y
    $SUDO_CMD apt-get install -y "${install_list[@]}"
    ;;
  dnf)
    $SUDO_CMD dnf install -y "${install_list[@]}"
    ;;
  yum)
    $SUDO_CMD yum install -y "${install_list[@]}"
    ;;
  pacman)
    # pacman requires --noconfirm
    if [ "$NO_SUDO" -eq 0 ] && ! is_root; then
      $SUDO_CMD pacman -Sy --noconfirm "${install_list[@]}"
    else
      pacman -Sy --noconfirm "${install_list[@]}"
    fi
    ;;
  *)
    echo "Unsupported package manager: $PKG_MGR" >&2; exit 4
    ;;
esac

echo "Install commands finished. Performing quick sanity checks..."

check_cmds=(soffice pandoc wkhtmltopdf convert gs pdftoppm python3)
for c in "${check_cmds[@]}"; do
  if command -v "$c" >/dev/null 2>&1; then
    echo "  - $c: OK ($(command -v $c))"
  else
    echo "  - $c: MISSING (some functionality may not work)"
  fi
done

# If requested, install Python packages from requirements.txt
if [ "$INSTALL_PIP" -eq 1 ]; then
  REQ_FILE="$(pwd)/requirements.txt"
  if [ ! -f "$REQ_FILE" ]; then
    echo "requirements.txt not found at $REQ_FILE. Skipping pip install.";
  else
    echo "Installing Python packages from $REQ_FILE into venv $VENV_DIR"
    if [ ! -d "$VENV_DIR" ]; then
      python3 -m venv "$VENV_DIR"
      echo "Created venv at $VENV_DIR"
    fi
    # Activate and install
    # shellcheck source=/dev/null
    . "$VENV_DIR/bin/activate"
    pip install --upgrade pip
    pip install -r "$REQ_FILE"
    deactivate
    echo "Python packages installed into $VENV_DIR"
  fi
fi

if [ "$INSTALL_PIP" -eq 1 ]; then
  cat <<'INFO'

Next steps (important):

- Activate the virtualenv before running any crawler that depends on the Python packages:
    source "$VENV_DIR/bin/activate"

- Run the crawler with that Python so it sees the installed packages, for example:
    python /path/to/crawler/adm/course-form/app.py --convert --output-dir ./docs

- If you prefer running the crawler with the system Python, you can install the same pip packages globally
  (not recommended) by running:
    sudo python3 -m pip install -r requirements.txt

INFO
fi

echo "Done. If some converters are still missing, consider installing specific packages for your distribution or installing additional fonts."

exit 0
