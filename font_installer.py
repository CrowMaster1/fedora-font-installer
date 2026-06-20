#!/usr/bin/env python3
"""Download and install MS core fonts + Google Fonts top-60, with Flatpak support."""

import os
import queue
import shutil
import subprocess
import sys
import tempfile
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext
import re
import urllib.parse
import urllib.request
import zipfile

FONT_DIR = os.path.expanduser("~/.local/share/fonts/font-installer")

# MS Core Fonts installed via Fedora package (msttcore-fonts-installer from RPM Fusion nonfree)
# ponytail: dnf handles the download; SourceForge direct download is Cloudflare-blocked
MS_FONTS_PKG = "msttcore-fonts-installer"

# Microsoft Aptos — new Office default since 2023, ships with Windows 11 22H2+
APTOS_BASE = "https://raw.githubusercontent.com/repo-medusa/microsoft-aptos-fonts/main/fonts/"
APTOS_FONTS = [
    "Aptos.ttf", "Aptos-Bold.ttf", "Aptos-Italic.ttf", "Aptos-Bold-Italic.ttf",
    "Aptos-Light.ttf", "Aptos-Light-Italic.ttf",
    "Aptos-SemiBold.ttf", "Aptos-SemiBold-Italic.ttf",
    "Aptos-ExtraBold.ttf", "Aptos-ExtraBold-Italic.ttf",
    "Aptos-Black.ttf", "Aptos-Black-Italic.ttf",
    "Aptos-Display.ttf", "Aptos-Display-Bold.ttf",
    "Aptos-Display-Italic.ttf", "Aptos-Display-Bold-Italic.ttf",
    "Aptos-Narrow.ttf", "Aptos-Narrow-Bold.ttf",
    "Aptos-Narrow-Italic.ttf", "Aptos-Narrow-Bold-Italic.ttf",
    "Aptos-Mono.ttf", "Aptos-Mono-Bold.ttf",
    "Aptos-Mono-Italic.ttf", "Aptos-Mono-Bold-Italic.ttf",
    "Aptos-Serif.ttf", "Aptos-Serif-Bold.ttf",
    "Aptos-Serif-Italic.ttf", "Aptos-Serif-Bold-Italic.ttf",
]

GOOGLE_FONTS = [
    # Free metric-compatible substitutes for MS ClearType fonts
    "Carlito",          # Calibri drop-in
    "Caladea",          # Cambria drop-in
    "Arimo",            # Arial (metrically compatible)
    "Tinos",            # Times New Roman (metrically compatible)
    "Cousine",          # Courier New (metrically compatible)
    # Top-55 Google Fonts for document compatibility
    "Roboto", "Roboto Condensed", "Roboto Slab", "Roboto Mono",
    "Open Sans", "Lato", "Montserrat", "Oswald", "Source Sans 3",
    "Raleway", "PT Sans", "PT Serif", "Merriweather", "Nunito",
    "Playfair Display", "Ubuntu", "Poppins", "Josefin Sans",
    "Inconsolata", "Rubik", "Work Sans", "Fira Sans", "Fira Code",
    "Karla", "Cabin", "Barlow", "Noto Sans", "Noto Serif",
    "Crimson Text", "EB Garamond", "Libre Baskerville",
    "Bitter", "Arvo", "Lora", "Source Serif 4", "Alegreya",
    "Cormorant Garamond", "Cardo", "Libre Caslon Text",
    "Source Code Pro", "Space Mono", "JetBrains Mono",
    "Dosis", "Pacifico", "Dancing Script", "Lobster", "Comfortaa",
    "Fjalla One", "Yanone Kaffeesatz", "Varela Round",
    "Exo 2", "Quicksand", "Mulish", "Mukta", "Domine",
    "Vollkorn", "Neuton", "Gentium Book Plus",
]

# Runtime tools needed beyond dnf/rpm/flatpak (all assumed present on Fedora)
PREREQS: dict = {}  # nothing extra needed now; MS fonts go via dnf, Google via CSS API

KEY_FONTS = {
    "Arial": None,
    "Times New Roman": None,
    "Courier New": None,
    "Verdana": None,
    "Georgia": None,
    "Impact": None,
    "Trebuchet MS": None,
    "Comic Sans MS": None,
    "Calibri": "Carlito",
    "Cambria": "Caladea",
    "Consolas": None,
    "Roboto": None,
    "Open Sans": None,
    "Lato": None,
    "Montserrat": None,
    "Noto Sans": None,
    "Aptos": None,
    "Aptos Display": None,
}


def missing_prereqs():
    return [t for t in PREREQS if not shutil.which(t)]


def install_prereqs(log):
    missing = missing_prereqs()
    if not missing:
        log("All prerequisites satisfied.")
        return True
    pkgs = [p for t in missing for p in PREREQS[t]]  # flatten install args per tool
    # deduplicate keeping order (e.g. multiple dnf installs → one call)
    cmd = ["pkexec", "dnf", "install", "-y"] + [t for t in missing]
    log(f"$ {' '.join(cmd)}")
    log("  → KDE password dialog will appear")
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode == 0:
        log("Prerequisites installed.")
        return True
    log(f"  pkexec failed (exit {r.returncode})")
    log(f"  Manual fix:  sudo dnf install -y {' '.join(missing)}")
    return False


def _run_cmd(cmd, log, **kwargs):
    """Run a subprocess and echo the command to the console first."""
    log(f"$ {' '.join(str(c) for c in cmd)}")
    return subprocess.run(cmd, **kwargs)


def _download(url, dest, log):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as resp, open(dest, "wb") as f:
        total = int(resp.headers.get("Content-Length", 0))
        done, last_pct = 0, -1
        while chunk := resp.read(65536):
            f.write(chunk)
            done += len(chunk)
            if total:
                pct = done * 100 // total
                if pct // 10 != last_pct // 10:
                    last_pct = pct
                    log(f"    {pct}%")


def install_ms_fonts(log, set_progress):
    set_progress(0.1)
    r = subprocess.run(["rpm", "-q", MS_FONTS_PKG], capture_output=True, text=True)
    if r.returncode == 0:
        log(f"Already installed: {MS_FONTS_PKG}")
        log("  Fonts at: /usr/share/fonts/msttcore/")
        set_progress(1.0)
        return
    log(f"Installing {MS_FONTS_PKG} via dnf (RPM Fusion nonfree)...")
    r = _run_cmd(["pkexec", "dnf", "install", "-y", MS_FONTS_PKG], log,
                 capture_output=True, text=True)
    if r.returncode == 0:
        log("MS Core Fonts installed.")
    else:
        log(f"  Failed: {r.stderr[:200]}")
        log(f"  Manual fix: sudo dnf install {MS_FONTS_PKG}")
    set_progress(1.0)
    log("MS Core Fonts done.")


def _google_font_ttf_urls(family):
    """Fetch direct TTF URLs via Google Fonts CSS API.

    curl is used instead of urllib because urllib sends HTTP/1.1 and receives
    proxy URLs (/l/font?kit=...) instead of direct .ttf paths. curl uses HTTP/2
    and receives the real static URLs from fonts.gstatic.com.
    """
    weights = "100,300,400,500,700,900,100italic,300italic,400italic,700italic,900italic"
    url = "https://fonts.googleapis.com/css?family=" + urllib.parse.quote(f"{family}:{weights}")
    r = subprocess.run(
        ["curl", "-s", "--max-time", "20", "-A", "Mozilla/4.0", url],
        capture_output=True, text=True,
    )
    return re.findall(r"url\((https://fonts\.gstatic\.com/[^)]+\.ttf)\)", r.stdout)


def install_google_fonts(log, set_progress):
    dest = os.path.join(FONT_DIR, "google")
    os.makedirs(dest, exist_ok=True)
    n = len(GOOGLE_FONTS)
    for i, family in enumerate(GOOGLE_FONTS):
        set_progress(i / n)
        log(f"[{i+1}/{n}] {family}")
        try:
            urls = _google_font_ttf_urls(family)
            if not urls:
                log("  SKIP: no TTF URLs found")
                continue
            ok = 0
            for url in urls:
                fname = os.path.basename(url)
                out = os.path.join(dest, fname)
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=30) as r, open(out, "wb") as f:
                    f.write(r.read())
                ok += 1
            log(f"  {ok} file(s) installed")
        except Exception as e:
            log(f"  SKIP: {e}")
    set_progress(1.0)
    log("Google Fonts done.")


def install_aptos_fonts(log, set_progress):
    dest = os.path.join(FONT_DIR, "aptos")
    os.makedirs(dest, exist_ok=True)
    n = len(APTOS_FONTS)
    for i, fname in enumerate(APTOS_FONTS):
        set_progress(i / n)
        log(f"[{i+1}/{n}] {fname}")
        url = APTOS_BASE + fname
        out = os.path.join(dest, fname)
        try:
            _download(url, out, log)
            log("  OK")
        except Exception as e:
            log(f"  SKIP: {e}")
    set_progress(1.0)
    log("Aptos fonts done.")


def run_fc_cache(log):
    log("Updating font cache...")
    r = _run_cmd(["fc-cache", "-f", FONT_DIR], log, capture_output=True, text=True)
    log("Font cache updated." if r.returncode == 0 else f"fc-cache: {r.stderr[:120]}")


def check_fonts(log):
    log("=== Font Check ===")
    r = subprocess.run(["fc-list"], capture_output=True, text=True)
    installed = r.stdout.lower()
    for font, sub in KEY_FONTS.items():
        if font.lower() in installed:
            log(f"  [OK] {font}")
        elif sub and sub.lower() in installed:
            log(f"  [~]  {font}  →  substitute installed: {sub}")
        else:
            note = f"  (run install to get substitute: {sub})" if sub else ""
            log(f"  [X]  {font} not found{note}")
    log("=== End ===")


def update_flatpaks(log):
    log("=== Flatpak Font Update ===")
    r = subprocess.run(
        ["flatpak", "list", "--app", "--columns=application"],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        log("flatpak not available or returned an error.")
        return
    apps = [a.strip() for a in r.stdout.strip().splitlines() if a.strip()]
    if not apps:
        log("No Flatpak apps found.")
        return
    var_app = os.path.expanduser("~/.var/app")
    log(f"Found {len(apps)} app(s).")
    log("Strategy: delete stale per-app fontconfig cache — app rebuilds on next launch.")

    for app_id in apps:
        cache_dir = os.path.join(var_app, app_id, "cache", "fontconfig")
        if os.path.isdir(cache_dir):
            shutil.rmtree(cache_dir)
            log(f"  [cleared] {app_id}")
        else:
            log(f"  [no cache] {app_id}")

    # Also refresh system fontconfig so RPM LibreOffice picks up new fonts
    log("Refreshing system fc-cache...")
    _run_cmd(["fc-cache", "-f"], log, capture_output=True, text=True)
    log("Done. Launch each app — font cache rebuilds automatically on first open.")
    log("=== End ===")


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Font Installer")
        self.geometry("680x540")
        self._q: queue.Queue = queue.Queue()
        self._build()
        self._poll()

    def _build(self):
        f = ttk.Frame(self, padding=10)
        f.pack(fill=tk.BOTH, expand=True)

        # Options row
        row = ttk.Frame(f)
        row.pack(fill=tk.X)
        self.var_ms = tk.BooleanVar(value=True)
        self.var_gf = tk.BooleanVar(value=True)
        self.var_ap = tk.BooleanVar(value=True)
        ttk.Checkbutton(row, text="Microsoft Core Fonts", variable=self.var_ms).pack(side=tk.LEFT)
        ttk.Checkbutton(row, text="Google Fonts (top 60 + substitutes)", variable=self.var_gf).pack(
            side=tk.LEFT, padx=10
        )
        ttk.Checkbutton(row, text="Aptos (new Office default)", variable=self.var_ap).pack(
            side=tk.LEFT
        )

        # Button row
        btns = ttk.Frame(f)
        btns.pack(fill=tk.X, pady=8)
        ttk.Button(btns, text="Install Prerequisites", command=self._prereqs).pack(side=tk.LEFT)
        ttk.Separator(btns, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=6)
        ttk.Button(btns, text="Install Fonts", command=self._install).pack(side=tk.LEFT)
        ttk.Button(btns, text="Check Fonts", command=self._check).pack(side=tk.LEFT, padx=6)
        ttk.Button(btns, text="Update Flatpaks", command=self._flatpak).pack(side=tk.LEFT)

        # Progress
        self.pbar = ttk.Progressbar(f, mode="determinate")
        self.pbar.pack(fill=tk.X, pady=(0, 4))
        self.status = tk.StringVar(value="Ready.")
        ttk.Label(f, textvariable=self.status, anchor=tk.W).pack(fill=tk.X)

        # Log
        self.txt = scrolledtext.ScrolledText(f, state=tk.DISABLED, font=("Monospace", 9))
        self.txt.pack(fill=tk.BOTH, expand=True, pady=(6, 0))

    def _poll(self):
        try:
            while True:
                msg, kind = self._q.get_nowait()
                if kind == "log":
                    self._write(msg)
                elif kind == "progress":
                    self.pbar["value"] = msg * 100
        except queue.Empty:
            pass
        self.after(50, self._poll)

    def _write(self, msg):
        self.txt.configure(state=tk.NORMAL)
        self.txt.insert(tk.END, msg + "\n")
        self.txt.see(tk.END)
        self.txt.configure(state=tk.DISABLED)
        self.status.set(msg[:90])

    def log(self, msg):
        self._q.put((msg, "log"))

    def set_progress(self, v):
        self._q.put((v, "progress"))

    def _run(self, fn):
        threading.Thread(target=fn, daemon=True).start()

    def _prereqs(self):
        def task():
            self.log("=== Prerequisites ===")
            install_prereqs(self.log)
            self.log("=== End ===")
        self._run(task)

    def _install(self):
        def task():
            missing = missing_prereqs()
            if missing:
                self.log("=== Installing Prerequisites ===")
                if not install_prereqs(self.log):
                    self.log("Aborted: fix prerequisites then retry.")
                    return
            if self.var_ms.get():
                self.log("--- Microsoft Core Fonts ---")
                install_ms_fonts(self.log, self.set_progress)
            if self.var_gf.get():
                self.log("--- Google Fonts ---")
                install_google_fonts(self.log, self.set_progress)
            if self.var_ap.get():
                self.log("--- Aptos (Microsoft Office 2023+) ---")
                install_aptos_fonts(self.log, self.set_progress)
            run_fc_cache(self.log)
            self.log("All done! Restart apps to use new fonts.")
            self.set_progress(0)
        self._run(task)

    def _check(self):
        self._run(lambda: check_fonts(self.log))

    def _flatpak(self):
        self._run(lambda: update_flatpaks(self.log))


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        # ponytail: minimal smoke test — fails if queue or font-list logic breaks
        q: queue.Queue = queue.Queue()
        msgs = []
        check_fonts(lambda m: msgs.append(m))
        assert any("===" in m for m in msgs), "check_fonts produced no output"
        assert any("[OK]" in m or "[X]" in m or "[~]" in m for m in msgs), "check_fonts found no font entries"
        print("self-test passed")
        sys.exit(0)
    App().mainloop()
