# OpenCode Tray

System tray indicator for **OpenCode Go** subscription usage. Shows your remaining allowance (5-hour rolling, weekly, monthly) with color-coded icons that change at configurable thresholds.

![Icon states: default (neutral), yellow (≥75%), orange (≥90%), red (100%)](oc-strip.png)

## Features

- **Tray icon** — The OpenCode "O" mark on a dark background. The light parts of the O change color based on usage.
- **Three time windows** — 5-hour rolling, weekly, and monthly usage percentages shown in the tooltip.
- **Auto-refresh** — Uses a saved GitHub OAuth session to scrape the OpenCode dashboard every ~10 minutes.
- **Configurable thresholds** — Right-click → menu: set yellow/orange/red limits (default: 75/90/100).
- **Fallback mode** — If cookies expire, reads from `~/.config/opencode-tray.json`.

## Files

| File | Purpose |
|---|---|
| `opencode-tray.py` | Main tray app (GTK + AppIndicator) |
| `opencode-login.py` | One-time GitHub login via Playwright (saves session cookies) |
| `opencode-scrape.py` | Background scraper — loads dashboard headlessly, parses usage % |
| `opencode-discover-api.py` | Helper to discover API endpoints from the dashboard |
| `opencode-tray.json` | Config: percentages, thresholds, reset timers |
| `opencode-tray.desktop` | XDG autostart entry |

## Requirements

- **System:** Linux with AyatanaAppIndicator (Cinnamon, GNOME, etc.)
- **Python packages:** `PyGObject`, `Pillow` (system Python)
- **Optional (auto-refresh):** Python `playwright` + Chromium (in `~/.local/venv/scraper/`)

## Setup

### 1. Install dependencies

```bash
sudo apt install python3-gi python3-pil gir1.2-ayatanaappindicator3-0.1
```

### 2. Run the tray app manually

```bash
~/.local/bin/opencode-tray.py
```

Or make it autostart on login:

```bash
cp opencode-tray.desktop ~/.config/autostart/
```

### 3. (Optional) Enable auto-refresh

The app shows manually-configured percentages by default. To scrape live data from your OpenCode dashboard:

```bash
python3 -m venv ~/.local/venv/scraper
~/.local/venv/scraper/bin/pip install playwright
~/.local/venv/scraper/bin/playwright install chromium
```

Then right-click the tray icon → **Login with GitHub (browser)**. Log in once, and the session cookies are saved for automatic background scraping.

### 4. Manual config fallback

Edit `~/.config/opencode-tray.json`:

```json
{
  "percentages": {"5h": 0, "weekly": 0, "monthly": 15},
  "resets": {"5h": "?", "weekly": "?", "monthly": "?"},
  "thresholds": {"yellow": 75, "orange": 90, "red": 100}
}
```

## Usage

Right-click the tray icon:

```
OpenCode Go Allowance
──────────────────────────────────
5-hour     2%  ░░░░░░░░░░  reset 1h 31min
Weekly     1%  ░░░░░░░░░░  reset 1d 9h
Monthly   15%  ██░░░░░░░░  reset 24d 7h
──────────────────────────────────
Source: live (auto)
Auto-refresh active
```

- **Login with GitHub (browser)** — Opens a Playwright browser to authenticate
- **Open Dashboard** — Opens the OpenCode Go workspace in your browser
- **OpenCode Stats** — Shows token/cost stats from the local database
- **Thresholds: Yellow>75% Orange>90% Red=100%** — Shows current limits
- **Set Yellow/Orange/Red threshold** — Click to change the color transition points

## How it works

1. The tray icon is rendered with Pillow: a dark rounded-square background with the OpenCode "O" drawn directly on it.
2. The lighter parts of the O (outer ring + highlight block) take on the accent color based on the highest usage percentage across the three windows.
3. If cookies are available, the app spawns a headless Playwright browser every 10 minutes, loads the workspace dashboard, and parses the percentage text from the page. Results are cached to `~/.config/opencode-usage-cache.json`.
4. Without cookies, it falls back to the manual config file.

## Color reference

| Usage | Accent | Icon preview |
|---|---|---|
| < 75% | Neutral gray | ![default](oc-default.png) |
| ≥ 75% | Yellow | ![yellow](oc-yellow.png) |
| ≥ 90% | Orange | ![orange](oc-orange.png) |
| = 100% | Red | ![red](oc-red.png) |
