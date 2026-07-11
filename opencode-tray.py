#!/usr/bin/python3
"""
OpenCode Tray — OpenCode Go allowance in the system tray.
Auto-refreshes from dashboard via saved GitHub session cookies.
Shows the OpenCode logo with color-coded background.
"""

import os
import json
import signal
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gtk, GLib, Gdk, GdkPixbuf, Pango

from PIL import Image, ImageDraw

CONFIG_PATH = Path.home() / ".config/opencode-tray.json"
COOKIE_PATH = Path.home() / ".config/opencode-cookies.json"
CACHE_PATH = Path.home() / ".config/opencode-usage-cache.json"
ICON_DIR = Path(tempfile.gettempdir()) / "opencode-tray-icons"
LOGO_PATH = ICON_DIR / "opencode-o.png"

# Ensure the O glyph exists as a proper icon
def _is_dark_mode() -> bool:
    """Check if the system uses a dark theme."""
    try:
        import subprocess
        r = subprocess.run(
            ["gsettings", "get", "org.gnome.desktop.interface", "gtk-theme"],
            capture_output=True, text=True, timeout=2
        )
        theme = r.stdout.strip().strip("'")
        if "dark" in theme.lower():
            return True
    except:
        pass
    return False


def _ensure_logo():
    if LOGO_PATH.exists():
        return
    ICON_DIR.mkdir(parents=True, exist_ok=True)
    from PIL import Image, ImageDraw
    size = 48
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    if _is_dark_mode():
        # Dark logo variant — light outer ring, dark inner fill
        light = (75, 70, 70)      # #4B4646 — inner block (dark)
        dark  = (183, 177, 177)   # #B7B1B1 — outer ring (light)
    else:
        # Light logo variant — medium outer ring, lighter inner fill
        light = (207, 206, 205)   # #CFCECD — inner block (light)
        dark  = (101, 99, 99)     # #656363 — outer ring (medium)
    # The O from opencode SVG paths, scaled to fit
    sc = 1.0
    ox = (size - 24 * sc) / 2
    oy = (size - 42 * sc) / 2
    def sr(x1, y1, x2, y2):
        return (ox + x1*sc, oy + y1*sc, ox + x2*sc, oy + y2*sc)
    # Inner top block
    draw.rectangle(sr(6, 18, 18, 30), fill=light)
    # Outer frame
    draw.rectangle(sr(0, 6, 24, 36), fill=dark)
    # Cut out inner
    draw.rectangle(sr(6, 12, 18, 30), fill=light)
    small = img.resize((22, 22), Image.LANCZOS)
    small.save(str(LOGO_PATH))

_ensure_logo()

DEFAULT_CONFIG = {
    "percentages": {"5h": 0, "weekly": 0, "monthly": 0},
    "resets": {"5h": "?", "weekly": "?", "monthly": "?"},
    "thresholds": {"yellow": 75, "orange": 90, "red": 100},
    "last_updated": None,
}


# ── helpers ─────────────────────────────────────────────────────────

def load_config() -> dict:
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text())
        except:
            pass
    CONFIG_PATH.write_text(json.dumps(DEFAULT_CONFIG, indent=2) + "\n")
    return dict(DEFAULT_CONFIG)


def save_config(cfg: dict):
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2) + "\n")


def bar(pct: float, width: int = 10) -> str:
    filled = round(min(pct, 100) / 100 * width)
    return "█" * filled + "░" * (width - filled)


def get_bg_color(pct: int, thresholds: dict) -> tuple:
    """Return (R,G,B) for the icon background."""
    if pct >= thresholds.get("red", 100):
        return (200, 50, 50)    # red
    if pct >= thresholds.get("orange", 90):
        return (220, 140, 30)   # orange
    if pct >= thresholds.get("yellow", 75):
        return (200, 180, 40)   # yellow
    return (60, 60, 70)         # default dark


def generate_icon(pct: int, thresholds: dict, size: int = 24) -> str:
    """Draw the opencode O with threshold colors only on the lighter parts.
    Background stays neutral dark."""
    ICON_DIR.mkdir(parents=True, exist_ok=True)
    bg = (45, 45, 50)  # neutral dark background, always the same

    # Determine the accent color based on usage
    accent = (150, 150, 160)  # default neutral light
    if pct >= thresholds.get("red", 100):
        accent = (220, 60, 60)     # red
    elif pct >= thresholds.get("orange", 90):
        accent = (230, 150, 40)    # orange
    elif pct >= thresholds.get("yellow", 75):
        accent = (210, 190, 50)    # yellow

    key = f"oc_{pct}_{size}_{thresholds.get('yellow')}_{thresholds.get('orange')}_{thresholds.get('red')}"
    icon_path = ICON_DIR / f"{key}.png"
    if icon_path.exists():
        return str(icon_path)

    from PIL import Image, ImageDraw

    # Icon at exact tray size, no extra padding
    bg_img = Image.new("RGBA", (size, size), (*bg, 255))
    draw = ImageDraw.Draw(bg_img)

    # Draw the O glyph directly, scaled to fill the icon
    margin = 1
    avail = size - 2 * margin
    sc = min(avail / 24, avail / 42)  # O is 24x42 in the SVG
    ox = (size - 24 * sc) / 2
    oy = (size - 42 * sc) / 2
    def sr(x1, y1, x2, y2):
        return (ox + x1*sc, oy + y1*sc, ox + x2*sc, oy + y2*sc)

    dark_fill = (55, 50, 50)       # dark inner part — always stays dark
    light_part = accent            # lighter part — takes threshold color

    # Outer frame (the ring)
    draw.rectangle(sr(0, 6, 24, 36), fill=light_part)
    # Inner top block (the light/highlight part)
    draw.rectangle(sr(6, 18, 18, 30), fill=light_part)
    # Cut out inner (reveals dark fill underneath)
    draw.rectangle(sr(6, 12, 18, 30), fill=dark_fill)

    bg_img.save(str(icon_path))
    return str(icon_path)


# ── tray app ────────────────────────────────────────────────────────

class OpenCodeTray:
    def __init__(self):
        self.config = load_config()
        self.current_overall = 0
        self.current_thresholds = self.config.get("thresholds",
                                                    DEFAULT_CONFIG["thresholds"])

        self.icon = Gtk.StatusIcon()
        self.icon.set_tooltip_text("OpenCode Go")
        self.icon.connect("popup-menu", self._on_popup_menu)
        self._rebuild()
        GLib.timeout_add_seconds(60, self._rebuild)

    def _on_popup_menu(self, _icon, button, time):
        self._rebuild_menu()
        self.menu.show_all()
        self.menu.popup(None, None, None, None, button, time)

    def _rebuild(self):
        self.config = load_config()
        self.current_thresholds = self.config.get("thresholds",
                                                    DEFAULT_CONFIG["thresholds"])
        self._maybe_scrape()
        self._update_display()
        # Menu is rebuilt on popup

    def _maybe_scrape(self):
        if not COOKIE_PATH.exists():
            return
        if CACHE_PATH.exists():
            try:
                cache = json.loads(CACHE_PATH.read_text())
                age = datetime.now(timezone.utc).timestamp() - cache.get("timestamp", 0)
                if age < 600:
                    return
            except:
                pass
        subprocess.Popen(
            ["~/.local/venv/scraper/bin/python3", "~/.local/bin/opencode-scrape.py"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            shell=True
        )

    def _get_percentages(self):
        key_map = {"rolling": "5h", "weekly": "weekly", "monthly": "monthly"}
        if CACHE_PATH.exists():
            try:
                cache = json.loads(CACHE_PATH.read_text())
                age = datetime.now(timezone.utc).timestamp() - cache.get("timestamp", 0)
                if age < 600:
                    mapped = {"percentages": {}, "resets": {}}
                    for src_key, dst_key in key_map.items():
                        mapped["percentages"][dst_key] = cache.get("percentages", {}).get(src_key, 0)
                        mapped["resets"][dst_key] = cache.get("resets", {}).get(src_key, "?")
                    return mapped, "live"
            except:
                pass
        raw = self.config
        mapped = {"percentages": {}, "resets": {}}
        for src_key, dst_key in key_map.items():
            mapped["percentages"][dst_key] = raw.get("percentages", {}).get(src_key) or raw.get("percentages", {}).get(dst_key, 0)
            mapped["resets"][dst_key] = raw.get("resets", {}).get(src_key) or raw.get("resets", {}).get(dst_key, "?")
        return mapped, "manual"

    def _update_display(self):
        data, source = self._get_percentages()
        pcts = data.get("percentages", {})
        resets = data.get("resets", {})

        p5h = min(pcts.get("5h", 0), 100)
        pwk = min(pcts.get("weekly", 0), 100)
        pmo = min(pcts.get("monthly", 0), 100)
        overall = max(p5h, pwk, pmo)
        self.current_overall = overall
        # Set the tray icon
        icon_path = generate_icon(overall, self.current_thresholds)
        pixbuf = GdkPixbuf.Pixbuf.new_from_file(str(icon_path))
        self.icon.set_from_pixbuf(pixbuf)

        # Tooltip text
        lines = ["OpenCode Go Allowance", "─" * 34]
        lines.append(f"5-hour   {p5h:3d}%  {bar(p5h)}  reset {resets.get('5h', '?')}")
        lines.append(f"Weekly   {pwk:3d}%  {bar(pwk)}  reset {resets.get('weekly', '?')}")
        lines.append(f"Monthly  {pmo:3d}%  {bar(pmo)}  reset {resets.get('monthly', '?')}")
        lines.append("─" * 34)
        lines.append(f"Source: {source}")
        if COOKIE_PATH.exists():
            lines.append("Auto-refresh active")

        self.tooltip = "\n".join(lines)

    def _rebuild_menu(self):
        self.menu = Gtk.Menu()

        # Build each line as a separate menu item with monospace font
        for line in self.tooltip.split("\n"):
            item = Gtk.MenuItem()
            label = Gtk.Label(label=line)
            label.override_font(Pango.FontDescription("monospace 9"))
            label.set_xalign(0.0)
            item.add(label)
            item.set_sensitive(False)
            self.menu.append(item)
        self.menu.append(Gtk.SeparatorMenuItem())

        # Refresh now
        item_refresh = Gtk.MenuItem(label="Refresh Now")
        item_refresh.connect("activate", self._on_refresh)
        self.menu.append(item_refresh)

        # Login / Dashboard
        item_login = Gtk.MenuItem(label="Login with GitHub (browser)")
        item_login.connect("activate", self._on_login)
        self.menu.append(item_login)

        item_dash = Gtk.MenuItem(label="Open Dashboard")
        item_dash.connect("activate", self._on_dashboard)
        self.menu.append(item_dash)

        item_stats = Gtk.MenuItem(label="OpenCode Stats")
        item_stats.connect("activate", self._on_open_stats)
        self.menu.append(item_stats)

        self.menu.append(Gtk.SeparatorMenuItem())

        th = self.current_thresholds
        info_th = Gtk.MenuItem(label=f"Thresholds: Yellow>{th['yellow']}%  Orange>{th['orange']}%  Red={th['red']}%")
        info_th.set_sensitive(False)
        self.menu.append(info_th)

        for key, label in [("yellow", "Yellow"), ("orange", "Orange"), ("red", "Red")]:
            item = Gtk.MenuItem(label=f"  Set {label} threshold ({th[key]}%)")
            item.connect("activate", self._on_set_threshold, key)
            self.menu.append(item)

        self.menu.append(Gtk.SeparatorMenuItem())

        item_quit = Gtk.MenuItem(label="Quit")
        item_quit.connect("activate", self._on_quit)
        self.menu.append(item_quit)

        self.menu.show_all()

    def _on_refresh(self, _widget):
        # Force immediate scrape
        subprocess.Popen(
            ["~/.local/venv/scraper/bin/python3", "~/.local/bin/opencode-scrape.py"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            shell=True
        )
        # Schedule a UI rebuild in 10 seconds to pick up new data
        GLib.timeout_add_seconds(10, self._rebuild)

    def _on_set_threshold(self, _widget, key):
        """Open a simple dialog to set a threshold value."""
        th = self.current_thresholds
        current = th.get(key, DEFAULT_CONFIG["thresholds"][key])

        dialog = Gtk.MessageDialog(
            None,
            Gtk.DialogFlags.MODAL,
            Gtk.MessageType.QUESTION,
            Gtk.ButtonsType.OK_CANCEL,
            f"Enter {key} threshold % (currently {current}%)"
        )
        entry = Gtk.Entry()
        entry.set_text(str(current))
        entry.set_max_length(3)
        entry.set_width_chars(5)
        dialog.get_content_area().pack_start(entry, True, True, 0)
        dialog.show_all()
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            try:
                val = int(entry.get_text().strip())
                val = max(1, min(100, val))
                self.config.setdefault("thresholds", {})[key] = val
                save_config(self.config)
                # Clear icon cache so icons regenerate with new thresholds
                for f in ICON_DIR.glob("oc_*.png"):
                    f.unlink()
            except ValueError:
                pass
        dialog.destroy()
        self._rebuild()

    def _on_login(self, _widget):
        os.system("gnome-terminal -- bash -c '~/.local/venv/scraper/bin/python3 ~/.local/bin/opencode-login.py; echo; echo Press Enter to close...; read' &")

    def _on_dashboard(self, _widget):
        os.system("xdg-open https://opencode.ai/workspace/wrk_01KW7A4093QJB0A77XNPH9SCFH/go &")

    def _on_open_stats(self, _widget):
        os.system('gnome-terminal -- bash -c "/home/keiner/.opencode/bin/opencode stats; echo; echo Press Enter to close...; read" &')

    def _on_quit(self, _widget):
        Gtk.main_quit()


def main():
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    OpenCodeTray()
    Gtk.main()


if __name__ == "__main__":
    main()
