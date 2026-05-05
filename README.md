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

Choose your platform below for the most accurate setup instructions.

### 🪟 Windows

```batch
git clone https://github.com/cameleonnbss/ip-logger.git
cd ip-logger
winget install Cloudflare.cloudflared
install.bat
```

### 🐧 Linux / 🍎 macOS

```bash
git clone https://github.com/cameleonnbss/ip-logger.git
cd ip-logger

# Install cloudflared
curl -LO https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64
chmod +x cloudflared-linux-amd64
sudo mv cloudflared-linux-amd64 /usr/local/bin/cloudflared

chmod +x install.sh
./install.sh

# Install dependencies
pip3 install -r requirements.txt

# Run the logger
python3 ip_logger.py
```

### 📱 Termux (Android)

```bash
pkg update && pkg upgrade
pkg install git python cloudflared

git clone https://github.com/cameleonnbss/ip-logger.git
cd ip-logger

chmod +x install.sh
./install.sh

pip install -r requirements.txt
python ip_logger.py
```

### ⚡ Quick Start (for most users)

```bash
git clone https://github.com/cameleonnbss/ip-logger.git
cd ip-logger
pip install -r requirements.txt
python3 ip_logger.py
```

**Notes:**
- Make sure you have Python 3.8+ installed.
- Run these commands in your terminal / command prompt.
- After running, follow any on-screen instructions from the script.
```


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
requirements.txt       (optional)
```

---

## ⚖️ Legal

For CTF, authorized pentesting, OSINT research, and educational use only.
Do not use without explicit permission.

---

<div align="center">Made with ❤️ by <a href="https://github.com/cameleonnbss">camzzz</a></div>
