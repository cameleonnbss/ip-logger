# 📡 IP Logger

```
  _____  ___       _
  \_   \/ _ \     | | ___   __ _  __ _  ___ _ __
   / /\/ /_)/     | |/ _ \ / _` |/ _` |/ _ \ '__|
/\/ /_/ ___/      | | (_) | (_| | (_| |  __/ |
\____\/            |_|\___/ \__, |\__, |\___|_|
                             |___/ |___/
  by camzzz · github.com/cameleonnbss
```

> IP capture tool with Cloudflare tunnel, GeoIP, browser fingerprinting and a dark dashboard.
> For CTF, OSINT research, and authorized security testing.

---

## ✨ Features

- 🌍 GeoIP — city, ISP, ASN, proxy/VPN/hosting flags (3 sources in cascade)
- 🗺️ GPS geolocation — precise coordinates via browser API
- 🕵️ Fingerprinting — WebGL, canvas, plugins, RAM, CPU, battery, screen
- 🎭 10 lure pages — Cloudflare, Google Drive, Discord, YouTube, Twitch, Netflix, Steam, Dropbox, 404, blank
- ↩️ Mode lure or redirect — fake page OR instant 302
- 🌐 Cloudflare tunnel — auto-installed and auto-started
- 🔒 Basic Auth — server-side dashboard password
- 💾 Persistent config — settings saved across restarts
- 🌏 6 languages — EN · FR · RU · ES · DE · ZH
- 📊 Live dashboard — dark UI, stat bars, full capture modal

---

## 📦 Installation

### Windows
```bat
install.bat
```

### Linux / macOS
```bash
bash install.sh
python3 ip_logger.py
```

### Termux
```bash
pkg update && pkg install python
bash install.sh
python ip_logger.py
```

---

## 🚀 Usage

```bash
python ip_logger.py      # Windows
python3 ip_logger.py     # Linux / macOS / Termux
```

The server starts, tunnel connects, and the interactive menu opens automatically.

---

## 🎭 Lure pages

| Key | Page |
|-----|------|
| `captcha` | Cloudflare "Checking your browser..." |
| `google` | Google Drive opening document |
| `discord` | Discord server invite |
| `youtube` | YouTube video loading |
| `twitch` | Twitch live connecting |
| `netflix` | Netflix "Just a moment..." |
| `steam` | Steam library loading |
| `dropbox` | Dropbox file opening |
| `404` | Generic error page |
| `blank` | Empty page (SSRF / callbacks) |

---

## 🔗 Endpoints

| URL | Description |
|-----|-------------|
| `/t/<token>` | Main tracking URL |
| `/pixel/<token>` | 1×1 GIF pixel |
| `/r/<token>` | Direct 302 redirect |
| `/logs` | Dashboard (Basic Auth) |
| `/logs/json` | Raw JSON export |

---

## 📁 Files

```
ip_logger.py           Main script
install.bat            Windows installer
install.sh             Linux / macOS / Termux installer
iplogger_config.json   Saved config (auto-created)
ip_log.json            Captured visits (auto-created)
docs.html              Documentation
```

---

## ⚖️ Legal

For CTF, authorized pentesting, OSINT research, and educational use only.
Do not use without explicit permission.

---

<div align="center">Made with ❤️ by <a href="https://github.com/cameleonnbss">camzzz</a></div>
