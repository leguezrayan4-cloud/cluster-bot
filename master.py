"""Master Node - Dashboard Pro (Version 100% Réelle & Options Intégrales)."""
import asyncio
import os
import uuid
from urllib.parse import urlparse
from aiohttp import ClientSession, ClientTimeout, web

PORT = int(os.getenv("PORT", "8000"))
WORKER_URLS = os.getenv(
    "WORKER_URLS", 
    "https://slider-crazed-latch.ngrok-free.dev"
).split(",")

session = None
cluster_bot_states = {}

def detect_platform_and_channel(url: str):
    parsed = urlparse(url.strip())
    domain = parsed.netloc.lower()
    path = parsed.path.strip("/")
    
    platform = "unknown"
    channel = path.split("/")[0] if path else ""

    if "twitch.tv" in domain:
        platform = "twitch"
    elif "youtube.com" in domain or "youtu.be" in domain:
        if "shorts" in path:
            platform = "youtube_short"
        elif "watch" in parsed.query or "embed" in path or "v=" in parsed.query:
            platform = "youtube_video"
        else:
            platform = "youtube"
    elif "kick.com" in domain:
        platform = "kick"
    elif domain:
        platform = "custom"
        
    return platform, channel

async def index(request):
    html_content = """<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cluster Bot - Command Center Pro (Real-Time)</title>
    <style>
        :root { --bg: #090d16; --card: #1e293b; --card-alt: #0f172a; --accent: #38bdf8; --text: #f8fafc; --muted: #94a3b8; --success: #22c55e; --danger: #ef4444; --warning: #f59e0b; }
        body { font-family: 'Segoe UI', system-ui, sans-serif; background: var(--bg); color: var(--text); margin: 0; padding: 20px; }
        .main-layout { display: flex; gap: 20px; max-width: 1400px; margin: auto; align-items: flex-start; }
        
        .control-panel { flex: 1; background: var(--card); padding: 25px; border-radius: 12px; border: 1px solid #334155; box-shadow: 0 10px 25px -5px rgba(0,0,0,0.3); }
        .monitor-panel { flex: 1.3; background: var(--card); padding: 25px; border-radius: 12px; border: 1px solid #334155; box-shadow: 0 10px 25px -5px rgba(0,0,0,0.3); max-height: 850px; display: flex; flex-direction: column; }
        
        h1, h2 { color: var(--accent); margin-top: 0; display: flex; align-items: center; justify-content: space-between; font-size: 20px; }
        .badge { background: #0284c7; font-size: 11px; padding: 4px 10px; border-radius: 20px; color: white; text-transform: uppercase; letter-spacing: 0.5px; }
        
        .form-group { margin-bottom: 15px; }
        label { display: block; margin-bottom: 5px; font-weight: 600; font-size: 13px; color: var(--muted); }
        input, select { width: 100%; padding: 10px; background: var(--card-alt); border: 1px solid #334155; color: white; border-radius: 6px; box-sizing: border-box; font-size: 14px; }
        
        .checkbox-group { display: flex; align-items: center; gap: 10px; background: rgba(15, 23, 42, 0.4); padding: 10px; border-radius: 6px; border: 1px solid #334155; margin-bottom: 10px; cursor: pointer; }
        .checkbox-group input { width: 18px; height: 18px; accent-color: var(--accent); cursor: pointer; }
        .checkbox-group label { margin-bottom: 0; color: var(--text); cursor: pointer; font-size: 13px; flex-grow: 1; }

        .reconnect-options-container { display: none; align-items: center; gap: 8px; margin-bottom: 15px; background: rgba(15, 23, 42, 0.6); padding: 8px 12px; border-radius: 6px; border: 1px dashed #334155; }
        .reconnect-options-container.active { display: flex; }
        .reconnect-options-container label { font-size: 12px; color: var(--muted); margin-bottom: 0; }
        .reconnect-options-container select { width: auto; padding: 5px 10px; font-size: 12px; }

        .conditional-group { background: rgba(15, 23, 42, 0.6); padding: 12px; border-radius: 8px; border: 1px dashed #334155; margin-bottom: 15px; display: none; }
        .conditional-group.active { display: block; }

        .detected-info { font-size: 12px; color: var(--accent); margin-top: 4px; font-weight: bold; }
        
        .btn-group { display: flex; gap: 10px; margin-top: 20px; }
        button { flex: 1; padding: 12px; border: none; border-radius: 6px; cursor: pointer; font-weight: bold; font-size: 14px; transition: 0.2s; }
        .btn-start { background: var(--success); color: white; }
        .btn-start:hover { background: #16a34a; }
        
        .btn-stop { background: var(--danger); color: white; }
        .btn-stop:hover { background: #dc2626; }

        .stats-dashboard { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; margin-bottom: 15px; }
        .stat-box { background: var(--card-alt); border: 1px solid #334155; border-radius: 8px; padding: 8px; text-align: center; }
        .stat-box .stat-val { font-size: 15px; font-weight: bold; color: var(--accent); }
        .stat-box .stat-lbl { font-size: 10px; color: var(--muted); text-transform: uppercase; margin-top: 2px; }

        #bots-container { overflow-y: auto; flex-grow: 1; max-height: 500px; padding-right: 5px; margin-top: 10px; }
        
        .bot-card { 
            background: var(--card-alt); 
            border: 1px solid #334155; 
            border-radius: 8px; 
            padding: 10px 12px; 
            margin-bottom: 8px; 
            display: flex; 
            flex-direction: column; 
            gap: 6px; 
            position: relative; 
            overflow: hidden; 
        }

        .bot-card::before { content: ''; position: absolute; left: 0; top: 0; bottom: 0; width: 4px; background: var(--warning); }
        .bot-card.running::before { background: var(--success); }
        .bot-card.warning::before { background: var(--warning); }
        .bot-card.error::before { background: var(--danger); }
        
        .bot-header { display: flex; justify-content: space-between; align-items: center; font-size: 12px; font-weight: bold; }
        .bot-status { font-size: 10px; padding: 2px 6px; border-radius: 4px; background: #334155; color: white; }
        .bot-status.running { background: rgba(34, 197, 94, 0.2); color: #4ade80; border: 1px solid rgba(34, 197, 94, 0.4); }
        .bot-status.warning { background: rgba(245, 158, 11, 0.2); color: #facc15; border: 1px solid rgba(245, 158, 11, 0.4); }
        .bot-status.error { background: rgba(239, 68, 68, 0.2); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.4); }
        
        .bot-progress-container { width: 100%; background: #0b1120; height: 5px; border-radius: 3px; overflow: hidden; margin-top: 2px; }
        .bot-progress-bar { height: 100%; background: var(--accent); width: 0%; transition: width 0.3s ease; }
        
        .bot-details { font-size: 10px; color: var(--muted); display: flex; justify-content: space-between; align-items: center; }
        
        #journal { background: var(--card-alt); padding: 10px; border-radius: 6px; height: 100px; overflow-y: auto; font-family: 'Consolas', monospace; font-size: 11px; border: 1px solid #334155; margin-top: 15px; }
    </style>
</head>
<body>
    <div class="main-layout">
        <div class="control-panel">
            <h1>Cluster Controller <span class="badge" id="platform-badge">Auto-Detect</span></h1>
            
            <div class="form-group">
                <label>URL Cible (Live, Vidéo ou Short)</label>
                <input type="text" id="target_url" value="https://slider-crazed-latch.ngrok-free.dev" oninput="updateInterfaceLogic()">
                <div class="detected-info" id="auto-detect-text">Plateforme détectée : Tunnel ngrok</div>
            </div>

            <div class="form-group">
                <label>Mode de Fonctionnement Principal</label>
                <select id="operation_mode" onchange="updateInterfaceLogic()">
                    <option value="views_live" selected>👁️ Ajouter des vues (Live)</option>
                    <option value="chat_live">⚡ Ajouter des vues + Messages (Live)</option>
                    <option value="views_video">📈 Ajouter des vues (Vidéo / Short)</option>
                </select>
            </div>

            <div class="conditional-group" id="chat-settings-group">
                <div class="form-group">
                    <label>Message Chat à envoyer</label>
                    <input type="text" id="chat_message" value="Raid Bot by {Anonymous}">
                </div>
                <div class="form-group" style="margin-bottom:0;">
                    <label>Intervalle des messages (secondes)</label>
                    <input type="number" id="chat_interval" value="10" min="1">
                </div>
            </div>

            <div class="checkbox-group">
                <input type="checkbox" id="auto_waves_toggle" checked>
                <label for="auto_waves_toggle">🚀 Lancer automatiquement par vagues sécurisées</label>
            </div>

            <div class="checkbox-group">
                <input type="checkbox" id="auto_reconnect_banned" checked>
                <label for="auto_reconnect_banned">🔄 Relancer automatiquement les bots bannis / filtrés</label>
            </div>

            <div class="checkbox-group" style="border-color: rgba(239, 68, 68, 0.3); background: rgba(239, 68, 68, 0.05);">
                <input type="checkbox" id="auto_remove_banned">
                <label for="auto_remove_banned">🗑️ Supprimer automatiquement les bots bannis / filtrés</label>
            </div>

            <div class="reconnect-options-container active" id="reconnect-options-box">
                <label for="reconnect_attempts">Nombre d'essais :</label>
                <select id="reconnect_attempts">
                    <option value="1">1 fois</option>
                    <option value="5">5 fois</option>
                    <option value="infinite" selected>Infini</option>
                </select>
            </div>

            <div class="form-group">
                <label>Nombre de bots (Max : 10000)</label>
                <input type="number" id="users" value="10" min="1" max="10000">
            </div>

            <div class="btn-group">
                <button class="btn-start" onclick="sendCommand('start')">Lancer</button>
                <button class="btn-stop" onclick="sendCommand('stop')">Stopper Tout</button>
            </div>

            <h3 style="font-size: 14px; margin: 15px 0 8px 0; color: var(--muted);">Journal Système</h3>
            <div id="journal"></div>
        </div>

        <div class="monitor-panel">
            <h2>Monitoring Avancé <span class="badge" id="active-bots-count">0 Total</span></h2>
            
            <div class="stats-dashboard">
                <div class="stat-box">
                    <div class="stat-val" id="stat-active">0</div>
                    <div class="stat-lbl">Actifs</div>
                </div>
                <div class="stat-box">
                    <div class="stat-val" id="stat-launching">0</div>
                    <div class="stat-lbl">En lancement</div>
                </div>
                <div class="stat-box">
                    <div class="stat-val" id="stat-banned" style="color: var(--danger);">0</div>
                    <div class="stat-lbl">Bannis</div>
                </div>
                <div class="stat-box" style="border-color: var(--accent);">
                    <div class="stat-val" id="stat-estimated-viewers" style="color: var(--success);">0</div>
                    <div class="stat-lbl">Est. Live</div>
                </div>
            </div>

            <div id="bots-container">
                <div style="text-align: center; color: var(--muted); padding: 40px; font-size: 13px;" id="empty-monitor">
                    Aucune campagne active.
                </div>
            </div>
        </div>
    </div>

    <script>
        let pollInterval = null;

        document.addEventListener("DOMContentLoaded", () => {
            const autoRestartCheckbox = document.getElementById('auto_reconnect_banned');
            const autoRemoveCheckbox = document.getElementById('auto_remove_banned');

            if (autoRestartCheckbox && autoRemoveCheckbox) {
                autoRestartCheckbox.addEventListener('change', function() {
                    if (this.checked) autoRemoveCheckbox.checked = false;
                    toggleReconnectOptions();
                });
                autoRemoveCheckbox.addEventListener('change', function() {
                    if (this.checked) autoRestartCheckbox.checked = false;
                    toggleReconnectOptions();
                });
            }
            toggleReconnectOptions();
            updateInterfaceLogic();
        });

        function toggleReconnectOptions() {
            const checkbox = document.getElementById('auto_reconnect_banned');
            const optionsBox = document.getElementById('reconnect-options-box');
            if (checkbox && checkbox.checked) {
                optionsBox.classList.add('active');
            } else {
                optionsBox.classList.remove('active');
            }
        }

        function log(msg) {
            const j = document.getElementById('journal');
            j.innerHTML += "[" + new Date().toLocaleTimeString() + "] " + msg + "<br>";
            j.scrollTop = j.scrollHeight;
        }

        function updateInterfaceLogic() {
            const urlInput = document.getElementById('target_url').value.trim();
            const badge = document.getElementById('platform-badge');
            const info = document.getElementById('auto-detect-text');
            const modeSelect = document.getElementById('operation_mode').value;
            const chatGroup = document.getElementById('chat-settings-group');
            
            try {
                const parsed = new URL(urlInput);
                const domain = parsed.hostname.toLowerCase();
                if (domain.includes('twitch.tv')) { badge.innerText = 'Twitch'; info.innerText = 'Plateforme détectée : Twitch'; }
                else if (domain.includes('youtube.com') || domain.includes('youtu.be')) { badge.innerText = 'YouTube'; info.innerText = 'Plateforme détectée : YouTube'; }
                else if (domain.includes('kick.com')) { badge.innerText = 'Kick'; info.innerText = 'Plateforme détectée : Kick'; }
                else { badge.innerText = domain; info.innerText = `Cible : ${domain}`; }
            } catch (e) {
                badge.innerText = 'Inconnu';
                info.innerText = 'Entrez une URL valide...';
            }

            if (modeSelect === 'chat_live') {
                chatGroup.classList.add('active');
            } else {
                chatGroup.classList.remove('active');
            }
        }

        async function sendCommand(action) {
            const endpoint = action === 'start' ? '/api/start' : '/api/stop';
            const payload = {
                target_url: document.getElementById('target_url').value,
                users: parseInt(document.getElementById('users').value) || 1,
                operation_mode: document.getElementById('operation_mode').value,
                chat_message: document.getElementById('chat_message').value,
                chat_interval: parseInt(document.getElementById('chat_interval').value) || 10,
                auto_waves: document.getElementById('auto_waves_toggle').checked,
                auto_reconnect: document.getElementById('auto_reconnect_banned').checked,
                auto_remove_banned: document.getElementById('auto_remove_banned').checked,
                reconnect_attempts: document.getElementById('reconnect_attempts').value
            };

            try {
                const res = await fetch(endpoint, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(payload)
                });
                const data = await res.json();
                log(data.message || "Ordre transmis.");
                
                if (action === 'start') {
                    if (pollInterval) clearInterval(pollInterval);
                    pollInterval = setInterval(fetchClusterStatus, 1500);
                } else {
                    if (pollInterval) clearInterval(pollInterval);
                    pollInterval = null;
                    document.getElementById('bots-container').innerHTML = '<div style="text-align: center; color: var(--muted); padding: 40px;">Campagne arrêtée.</div>';
                    resetStats();
                }
            } catch(e) {
                log("Erreur réseau Master.");
            }
        }

        async function fetchClusterStatus() {
            try {
                const res = await fetch('/api/status');
                const data = await res.json();
                updateMonitorUI(data.bots || []);
            } catch(e) {}
        }

        function updateMonitorUI(bots) {
            const container = document.getElementById('bots-container');
            if (!bots || bots.length === 0) return;

            document.getElementById('empty-monitor')?.remove();
            
            let activeCount = 0;
            let launchingCount = 0;
            let bannedCount = 0;

            container.innerHTML = '';

            bots.forEach(bot => {
                if (bot.status === 'running') activeCount++;
                else if (bot.status === 'error') bannedCount++;
                else launchingCount++;

                const card = document.createElement('div');
                card.className = `bot-card ${bot.status}`;
                
                let badgeText = bot.status === 'running' ? 'Actif' : (bot.status === 'error' ? 'Banni' : 'En lancement');
                
                card.innerHTML = `
                    <div class="bot-header">
                       <span>Bot #${bot.id} (${bot.name})</span>
                       <span class="bot-status ${bot.status}">${badgeText}</span>
                    </div>
                    <div class="bot-progress-container">
                       <div class="bot-progress-bar" style="width: ${bot.progress}%;"></div>
                    </div>
                    <div class="bot-details">
                       <span>${bot.statusText}</span>
                       <span>Latence : ${bot.ping}ms</span>
                    </div>
                `;
                container.appendChild(card);
            });

            document.getElementById('stat-active').innerText = activeCount;
            document.getElementById('stat-launching').innerText = launchingCount;
            document.getElementById('stat-banned').innerText = bannedCount;
            document.getElementById('stat-estimated-viewers').innerText = activeCount;
            document.getElementById('active-bots-count').innerText = bots.length + " Total";
        }

        function resetStats() {
            document.getElementById('stat-active').innerText = 0;
            document.getElementById('stat-launching').innerText = 0;
            document.getElementById('stat-banned').innerText = 0;
            document.getElementById('stat-estimated-viewers').innerText = 0;
            document.getElementById('active-bots-count').innerText = "0 Total";
        }

        log("Tableau de bord prêt.");
    </script>
</body>
</html>
"""
    return web.Response(text=html_content, content_type='text/html')

async def api_status(request):
    all_bots = list(cluster_bot_states.values())
    return web.json_response({"bots": all_bots})

async def api_start(request):
    global cluster_bot_states
    cluster_bot_states.clear()
    
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Payload invalide"}, status=400)
    
    target_url = data.get("target_url", "")
    total_users = max(1, int(data.get("users", 1)))
    num_workers = len(WORKER_URLS)
    
    base_users = total_users // num_workers
    remainder = total_users % num_workers

    results = []
    async def dispatch_worker(index, worker_url):
        users_for_this_worker = base_users + (1 if index < remainder else 0)
        if users_for_this_worker <= 0:
            return
        
        payload = dict(data)
        payload["users"] = users_for_this_worker
        payload["worker_offset"] = index * base_users

        try:
            async with session.post(f"{worker_url.strip()}/start-bots", json=payload, timeout=ClientTimeout(total=5)) as resp:
                results.append({"worker": worker_url.strip(), "status": resp.status})
        except Exception as e:
            results.append({"worker": worker_url.strip(), "error": str(e)})

    await asyncio.gather(*(dispatch_worker(i, url) for i, url in enumerate(WORKER_URLS)))

    return web.json_response({
        "status": "success",
        "message": f"Campagne lancée sur {num_workers} workers pour {total_users} bots réels."
    })

async def api_report(request):
    try:
        data = await request.json()
        bot_id = data.get("id")
        if bot_id is not None:
            cluster_bot_states[bot_id] = data
        return web.json_response({"status": "ack"})
    except Exception:
        return web.json_response({"error": "Invalid report"}, status=400)

async def api_stop(request):
    cluster_bot_states.clear()
    async def stop_worker(worker_url):
        try:
            async with session.post(f"{worker_url.strip()}/stop-bots", timeout=ClientTimeout(total=5)) as resp:
                pass
        except Exception:
            pass

    await asyncio.gather(*(stop_worker(url) for url in WORKER_URLS))
    return web.json_response({"status": "success", "message": "Cluster arrêté."})

async def startup(app):
    global session
    session = ClientSession()

async def cleanup(app):
    await session.close()

app = web.Application()
app.on_startup.append(startup)
app.on_cleanup.append(cleanup)
app.router.add_get("/", index)
app.router.add_get("/api/status", api_status)
app.router.add_post("/api/start", api_start)
app.router.add_post("/api/report", api_report)
app.router.add_post("/api/stop", api_stop)

if __name__ == "__main__":
    web.run_app(app, host="0.0.0.0", port=PORT)