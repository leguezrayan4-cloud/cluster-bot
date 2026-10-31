"""Master Node - Dashboard Pro (Version 100% Réelle & Synchronisée)."""
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
# État global des bots centralisé sur le Master
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

        .detected-info { font-size: 12px; color: var(--accent); margin-top: 4px; font-weight: bold; }
        
        .btn-group { display: flex; gap: 10px; margin-top: 20px; }
        button { flex: 1; padding: 12px; border: none; border-radius: 6px; cursor: pointer; font-weight: bold; font-size: 14px; transition: 0.2s; }
        .btn-start { background: var(--success); color: white; }
        .btn-start:hover { background: #16a34a; }
        
        .btn-stop { background: var(--danger); color: white; }
        .btn-stop:hover { background: #dc2626; }

        /* Grille mise à jour : 4 éléments demandés (Actifs, En lancement, Bannis, Est. Live) */
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
                <select id="operation_mode">
                    <option value="views_live" selected>👁️ Ajouter des vues (Live)</option>
                    <option value="chat_live">⚡ Ajouter des vues + Messages (Live)</option>
                    <option value="views_video">📈 Ajouter des vues (Vidéo / Short)</option>
                </select>
            </div>

            <div class="form-group">
                <label>Nombre de bots</label>
                <input type="number" id="users" value="10" min="1" max="1000">
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
            
            <!-- Dashboard des stats épuré selon tes consignes (sans le bloc "en cours") -->
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

        function log(msg) {
            const j = document.getElementById('journal');
            // Journal simplifié : affichage direct de messages courts et propres
            j.innerHTML += "[" + new Date().toLocaleTimeString() + "] " + msg + "<br>";
            j.scrollTop = j.scrollHeight;
        }

        function updateInterfaceLogic() {
            // Logique de détection d'URL
        }

        async function sendCommand(action) {
            const endpoint = action === 'start' ? '/api/start' : '/api/stop';
            const payload = {
                target_url: document.getElementById('target_url').value,
                users: parseInt(document.getElementById('users').value) || 1,
                operation_mode: document.getElementById('operation_mode').value
            };

            try {
                const res = await fetch(endpoint, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(payload)
                });
                const data = await res.json();
                log(data.message || "Ordre transmis au cluster.");
                
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
                log("Erreur réseau avec le Master.");
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
            if (bots.length === 0) return;

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
            document.getElementById('stat-estimated-viewers').innerText = activeCount; // Estimation réelle basée sur les bots connectés
            document.getElementById('active-bots-count').innerText = bots.length + " Total";
        }

        function resetStats() {
            document.getElementById('stat-active').innerText = 0;
            document.getElementById('stat-launching').innerText = 0;
            document.getElementById('stat-banned').innerText = 0;
            document.getElementById('stat-estimated-viewers').innerText = 0;
            document.getElementById('active-bots-count').innerText = "0 Total";
        }

        log("Tableau de bord synchronisé prêt.");
    </script>
</body>
</html>
"""
    return web.Response(text=html_content, content_type='text/html')

async def api_status(request):
    # Renvoie l'état réel de tous les bots enregistrés
    all_bots = list(cluster_bot_states.values())
    return web.json_response({"bots": all_bots})

async def api_start(request):
    global cluster_bot_states
    cluster_bot_states.clear()
    
    data = await request.json()
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
        
        payload = {
            "target_url": target_url,
            "users": users_for_this_worker,
            "worker_offset": index * base_users
        }

        try:
            async with session.post(f"{worker_url.strip()}/start-bots", json=payload, timeout=ClientTimeout(total=5)) as resp:
                body = await resp.json()
                results.append({"worker": worker_url.strip(), "status": resp.status})
        except Exception as e:
            results.append({"worker": worker_url.strip(), "error": str(e)})

    await asyncio.gather(*(dispatch_worker(i, url) for i, url in enumerate(WORKER_URLS)))

    return web.json_response({
        "status": "success",
        "message": f"Campagne lancée sur {num_workers} workers pour {total_users} bots réels."
    })

async def api_report(request):
    """Route par laquelle les workers envoient la télémétrie réelle des bots"""
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