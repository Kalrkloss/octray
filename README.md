# OpenCode Tray

System tray indicator for **OpenCode Go** subscription usage. Shows your remaining allowance with color-coded icons and a monospace menu.

![Icon states](oc-strip.png)
*Icon colors: default neutral (gray), yellow (≥75%), orange (≥90%), red (100%)*

## Features

- **Tray icon** — The OpenCode "O" mark on a dark background. The light parts change color based on usage.
- **Three windows** — 5-hour rolling, weekly, and monthly usage with reset timers in `dd:hh:mm`.
- **Monospace menu** — Bars and percentages aligned with a monospace font.
- **Auto-refresh** — Uses saved GitHub OAuth session to scrape the dashboard every ~10 minutes.
- **Configurable thresholds** — Set yellow/orange/red limits in the right-click menu.
- **Fallback mode** — If cookies expire, reads from `~/.config/opencode-tray.json`.

## Menu

```
OpenCode Go Allowance
──────────────────────────────────
5-hour     2%  ░░░░░░░░░░  reset 0:04:39
Weekly     3%  ███░░░░░░░  reset 1:07:00
Monthly   16%  ██████░░░░  reset 24:05:00
──────────────────────────────────
Source: live (auto)
Auto-refresh active
──────────────────────────────────
Refresh Now
Login with GitHub (browser)
Open Dashboard
OpenCode Stats
──────────────────────────────────
Thresholds: Yellow>75%  Orange>90%  Red=99%
  Set Yellow threshold (75%)
  Set Orange threshold (90%)
  Set Red threshold (99%)
──────────────────────────────────
Quit
```

## Files

| File | Purpose |
|---|---|
| `opencode-tray.py` | Main tray app (Gtk.StatusIcon) |
| `opencode-login.py` | One-time GitHub login via Playwright (saves session cookies) |
| `opencode-scrape.py` | Background scraper — loads dashboard headlessly, parses usage % |
| `opencode-discover-api.py` | Helper to discover API endpoints |
| `opencode-tray.json` | Config: percentages, thresholds, reset timers |
| `opencode-tray.desktop` | XDG autostart entry |

## Requirements

- **System:** Linux with GTK3, Pillow, Gtk.StatusIcon support (Cinnamon, GNOME, etc.)
- **Python packages:** `PyGObject`, `Pillow`
- **Optional (auto-refresh):** Python `playwright` + Chromium (in `~/.local/venv/scraper/`)

## Setup

### 1. Install dependencies

```bash
sudo apt install python3-gi python3-pil gir1.2-gtk-3.0
```

### 2. Run the tray app

```bash
~/.local/bin/opencode-tray.py
```

Or autostart on login:

```bash
cp opencode-tray.desktop ~/.config/autostart/
```

### 3. (Optional) Enable auto-refresh

```bash
python3 -m venv ~/.local/venv/scraper
~/.local/venv/scraper/bin/pip install playwright
~/.local/venv/scraper/bin/playwright install chromium
```

Then right-click → **Login with GitHub (browser)**. Log in once; cookies are saved for background scraping.

### 4. Manual config fallback

Edit `~/.config/opencode-tray.json`:

```json
{
  "percentages": {"5h": 0, "weekly": 0, "monthly": 15},
  "resets": {"5h": "0:00:00", "weekly": "0:00:00", "monthly": "0:00:00"},
  "thresholds": {"yellow": 75, "orange": 90, "red": 100}
}
```

## Icon reference

| State | Appearance |
|---|---|
| < 75% | ![default](oc-default.png) Neutral gray on dark bg |
| ≥ 75% | ![yellow](oc-yellow.png) Yellow accent |
| ≥ 90% | ![orange](oc-orange.png) Orange accent |
| = 100% | ![red](oc-red.png) Red accent |
