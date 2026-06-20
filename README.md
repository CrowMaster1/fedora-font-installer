# Fedora Font Installer

GUI tool to download and install Microsoft Core Fonts, Google Fonts (top 60), and Aptos on Fedora Linux — for maximum Word/Office document compatibility.

## Features

- **Microsoft Core Fonts** — Arial, Times New Roman, Courier New, Verdana, Georgia, Impact, Trebuchet MS, Comic Sans, Webdings, Andale Mono (via `msttcore-fonts-installer`)
- **Free ClearType substitutes** — Carlito (Calibri), Caladea (Cambria), Arimo (Arial), Tinos (Times New Roman), Cousine (Courier New)
- **Google Fonts top 60** — Roboto, Open Sans, Lato, Montserrat, Noto Sans/Serif, and more
- **Aptos** — Microsoft's new Office default font (all variants: Display, Narrow, Mono, Serif)
- **Font check** — scans installed fonts and reports OK / substitute / missing
- **Flatpak support** — refreshes `fc-cache` inside each sandboxed app (LibreOffice, etc.)
- **Prerequisite installer** — uses `pkexec` (KDE polkit dialog) for any required `dnf` installs

## Requirements

- Fedora Linux (tested on Fedora 44)
- Python 3.8+ with `tkinter` (included in Fedora's Python)
- RPM Fusion nonfree repository (for `msttcore-fonts-installer`)
- `curl` (standard on Fedora)

## Install RPM Fusion (if not already enabled)

```bash
sudo dnf install \
  https://download1.rpmfusion.org/free/fedora/rpmfusion-free-release-$(rpm -E %fedora).noarch.rpm \
  https://download1.rpmfusion.org/nonfree/fedora/rpmfusion-nonfree-release-$(rpm -E %fedora).noarch.rpm
```

## Usage

```bash
./start.sh
```

Or directly:

```bash
python3 font_installer.py
```

## Buttons

| Button | What it does |
|--------|-------------|
| **Install Prerequisites** | Installs missing system tools via `pkexec dnf` |
| **Install Fonts** | Downloads and installs selected font sets |
| **Check Fonts** | Reports which key fonts are present or missing |
| **Update Flatpaks** | Runs `fc-cache` inside each Flatpak sandbox |

## Font sources

| Set | Source |
|-----|--------|
| MS Core Fonts | `msttcore-fonts-installer` (RPM Fusion nonfree) |
| Google Fonts | `fonts.googleapis.com` CSS API → direct TTF from `fonts.gstatic.com` |
| Aptos | `github.com/repo-medusa/microsoft-aptos-fonts` |

Fonts are installed to `~/.local/share/fonts/font-installer/` and visible to all apps including Flatpak sandboxes.
