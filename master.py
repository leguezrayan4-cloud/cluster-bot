"""Master Node - Dashboard Pro (Version Multi-IP Intégrale & Arrêt Forcé)."""
import asyncio
import os
import uuid
from urllib.parse import urlparse
from aiohttp import ClientSession, ClientTimeout, web

PORT = int(os.getenv("PORT", "8000"))
# URL ngrok mise à jour pour que le Master et les workers ciblent ton serveur local Owncast
WORKER_URLS = os.getenv(
    "WORKER_URLS", 
    "https://slider-crazed-latch.ngrok-free.dev"
).split(",")

session = None

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
    <title>Cluster Bot - Command Center Pro (Multi-IP Edition)</title>
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

        .stats-dashboard { display: grid; grid-template-columns: repeat(5, 1fr); gap: 8px; margin-bottom: 15px; }
        .stat-box { background: var(--card-alt); border: 1px solid #334155; border-radius: 8px; padding: 8px; text-align: center; }
        .stat-box .stat-val { font-size: 15px; font-weight: bold; color: var(--accent); }
        .stat-box .stat-lbl { font-size: 10px; color: var(--muted); text-transform: uppercase; margin-top: 2px; }

        .trend-indicator { display: flex; justify-content: center; align-items: center; gap: 4px; margin-top: 4px; font-size: 11px; }
        .trend-arrow { opacity: 0.2; transition: 0.3s; }
        .trend-arrow.active-up { opacity: 1; color: var(--success); text-shadow: 0 0 8px rgba(34, 197, 94, 0.6); transform: scale(1.2); }
        .trend-arrow.active-down { opacity: 1; color: var(--danger); text-shadow: 0 0 8px rgba(239, 68, 68, 0.6); transform: scale(1.2); }

        #bots-container { overflow-y: auto; flex-grow: 1; max-height: 500px; padding-right: 5px; margin-top: 10px; }
        
        .pack-frame { background: rgba(15, 23, 42, 0.5); border: 1px solid #334155; border-radius: 10px; padding: 12px; margin-bottom: 15px; transition: all 0.3s ease; }
        .pack-header { font-size: 12px; font-weight: bold; color: var(--accent); margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #334155; padding-bottom: 6px; }
        .pack-subinfo { font-size: 11px; color: var(--muted); margin-bottom: 10px; display: flex; gap: 12px; flex-wrap: wrap; }

        .btn-show-more { background: #334155; color: var(--text); width: 100%; padding: 8px; font-size: 12px; margin-top: 5px; border-radius: 6px; border: 1px dashed #475569; cursor: pointer; }
        .btn-show-more:hover { background: #475569; }

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
            transition: all 0.4s ease-out;
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
                <label>URL Cible (Live, Vidéo YouTube ou Short)</label>
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
                <label id="users-label">Nombre de bots (Max : 10000)</label>
                <input type="number" id="users" value="50" min="1" max="10000" onchange="enforceMaxLimit()" onkeydown="if(event.key==='Enter'){enforceMaxLimit();sendCommand('start');}">
            </div>

            <div class="btn-group">
                <button class="btn-start" id="btn-action" onclick="enforceMaxLimit(); sendCommand('start')">Commandé</button>
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
                    <div class="stat-val" id="stat-running">0</div>
                    <div class="stat-lbl">En cours</div>
                </div>
                <div class="stat-box">
                    <div class="stat-val" id="stat-banned" style="color: var(--danger);">0</div>
                    <div class="stat-lbl">Bannis</div>
                </div>
                <div class="stat-box" style="border-color: var(--accent);">
                    <div class="stat-val" id="stat-estimated-viewers" style="color: var(--success);">0</div>
                    <div class="stat-lbl" id="metric-label">Est. Bots sur le Live</div>
                    <div class="trend-indicator">
                        <span class="trend-arrow" id="trend-up">▲</span>
                        <span class="trend-arrow" id="trend-down">▼</span>
                    </div>
                </div>
            </div>

            <div id="bots-container">
                <div style="text-align: center; color: var(--muted); padding: 40px; font-size: 13px;" id="empty-monitor">
                    Aucune campagne active. Lancez vos bots pour structurer les packs.
                </div>
            </div>
        </div>

    </div>

    <script>
        const MAX_BOTS_LIMIT = 10000;
        let currentTargetType = 'custom';
        let botStates = [];
        let globalMonitorLoop = null;
        let viewsSyncInterval = null;
        let totalGlobalBots = 0;
        let packCounter = 0;
        let isStopping = false;
        let previousEstimatedValue = 0;
        let expandedPacks = {};

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

        function enforceMaxLimit() {
            const input = document.getElementById('users');
            let val = parseInt(input.value) || 1;
            if (val > MAX_BOTS_LIMIT) {
                input.value = MAX_BOTS_LIMIT;
                log(`⚠️ Limite maximale atteinte : ramené automatiquement à ${MAX_BOTS_LIMIT} bots.`);
            } else if (val < 1) {
                input.value = 1;
            }
        }

        function updateInterfaceLogic() {
            const urlInput = document.getElementById('target_url').value.trim();
            const badge = document.getElementById('platform-badge');
            const info = document.getElementById('auto-detect-text');
            const modeSelect = document.getElementById('operation_mode').value;
            const chatGroup = document.getElementById('chat-settings-group');
            const metricLabel = document.getElementById('metric-label');
            
            try {
                const parsed = new URL(urlInput);
                const domain = parsed.hostname.toLowerCase();
                const port = parsed.port ? `:${parsed.port}` : '';

                if (domain.includes('twitch.tv')) {
                    currentTargetType = 'twitch';
                    badge.innerText = 'Twitch';
                    info.innerText = 'Plateforme détectée : Twitch (Live)';
                } else if (urlInput.includes('shorts')) {
                    currentTargetType = 'youtube_short';
                    badge.innerText = 'Short YouTube';
                    info.innerText = 'Plateforme détectée : Short YouTube (Vues)';
                } else if (domain.includes('youtube.com') || domain.includes('youtu.be')) {
                    if (urlInput.includes('watch') || urlInput.includes('v=')) {
                        currentTargetType = 'youtube_video';
                        badge.innerText = 'Vidéo YouTube';
                        info.innerText = 'Plateforme détectée : Vidéo YouTube classique';
                    } else {
                        currentTargetType = 'youtube_live';
                        badge.innerText = 'YouTube Live';
                        info.innerText = 'Plateforme détectée : YouTube Live';
                    }
                } else if (domain.includes('kick.com')) {
                    currentTargetType = 'kick';
                    badge.innerText = 'Kick';
                    info.innerText = 'Plateforme détectée : Kick (Live)';
                } else {
                    currentTargetType = 'custom';
                    badge.innerText = domain + port;
                    info.innerText = `Cible personnalisée / Tunnel : ${domain + port}`;
                }
            } catch (e) {
                currentTargetType = 'unknown';
                badge.innerText = 'Inconnu';
                info.innerText = 'Entrez une URL valide...';
            }

            if (modeSelect === 'chat_live') {
                chatGroup.classList.add('active');
            } else {
                chatGroup.classList.remove('active');
            }

            if (modeSelect.includes('live')) {
                metricLabel.innerText = 'Est. Bots sur le Live';
            } else {
                metricLabel.innerText = 'Est. Vues Vidéo / Short';
            }
        }

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

        function refreshEstimatedViewers() {
            let total = botStates.length;
            if (total === 0) {
                document.getElementById('stat-estimated-viewers').innerText = "0";
                updateTrendArrows(0);
                return;
            }

            let verifiedRunningCount = 0;
            botStates.forEach(b => {
                if (!b.filtered && b.deleting === false && b.status === "running") {
                    verifiedRunningCount++;
                }
            });

            if (verifiedRunningCount === 0) {
                document.getElementById('stat-estimated-viewers').innerText = "0";
                updateTrendArrows(0);
                return;
            }

            let conversionFactor = 0.85;
            let realisticEstimation = Math.floor(verifiedRunningCount * conversionFactor);
            realisticEstimation = Math.min(realisticEstimation, verifiedRunningCount);

            const viewEl = document.getElementById('stat-estimated-viewers');
            if (viewEl) {
                viewEl.innerText = Math.max(0, realisticEstimation);
            }

            updateTrendArrows(realisticEstimation);
            previousEstimatedValue = realisticEstimation;
        }

        function updateTrendArrows(currentVal) {
            const upArrow = document.getElementById('trend-up');
            const downArrow = document.getElementById('trend-down');
            if (!upArrow || !downArrow) return;

            upArrow.className = "trend-arrow";
            downArrow.className = "trend-arrow";

            if (currentVal > previousEstimatedValue) {
                upArrow.classList.add('active-up');
            } else if (currentVal < previousEstimatedValue) {
                downArrow.classList.add('active-down');
            }
        }

        function updateGlobalStats() {
            let active = 0, launching = 0, running = 0, banned = 0;
            botStates.forEach(b => {
                if (b.filtered) {
                    banned++;
                } else if (b.status === "running") {
                    active++;
                    running++;
                } else {
                    if (b.progress < 50) launching++;
                    else running++;
                }
            });

            document.getElementById('stat-active').innerText = active;
            document.getElementById('stat-launching').innerText = launching;
            document.getElementById('stat-running').innerText = running;
            document.getElementById('stat-banned').innerText = banned;
            document.getElementById('active-bots-count').innerText = totalGlobalBots.toLocaleString('fr-FR') + " Total";
        }

        function renderPackBots(packId) {
            const packBotsContainer = document.getElementById(`pack-bots-container-${packId}`);
            if (!packBotsContainer) return;

            const packBots = botStates.filter(b => b.packId === packId && !b.deleting);
            const isExpanded = expandedPacks[packId] || false;
            const limit = isExpanded ? packBots.length : 25;
            const displayedBots = packBots.slice(0, limit);
            const hiddenCount = packBots.length - displayedBots.length;

            packBotsContainer.innerHTML = '';

            displayedBots.forEach(bot => {
                const card = document.createElement('div');
                card.className = `bot-card ${bot.status}`;
                card.id = `bot-card-${bot.id}`;
                
                let badgeClass = bot.filtered ? "bot-status error" : `bot-status ${bot.status}`;
                let badgeText = bot.filtered ? "Filtré / Banni" : (bot.status === "running" ? "Actif" : "En cours");

                card.innerHTML = `
                    <div class="bot-header">
                       <span>Bot #${bot.id} (${bot.name})</span>
                       <span class="${badgeClass}" id="status-badge-${bot.id}">${badgeText}</span>
                    </div>
                    <div class="bot-progress-container">
                       <div class="bot-progress-bar" id="progress-bar-${bot.id}" style="width: ${bot.progress}%;"></div>
                    </div>
                    <div class="bot-details">
                       <span id="action-text-${bot.id}">${bot.statusText}</span>
                       <span id="ping-${bot.id}">Latence : ${bot.ping}ms</span>
                    </div>
                `;
                packBotsContainer.appendChild(card);
            });

            if (hiddenCount > 0) {
                const showMoreBtn = document.createElement('button');
                showMoreBtn.className = 'btn-show-more';
                showMoreBtn.innerText = `Afficher plus (+${hiddenCount} bots masqués)`;
                showMoreBtn.onclick = () => {
                    expandedPacks[packId] = true;
                    renderPackBots(packId);
                };
                packBotsContainer.appendChild(showMoreBtn);
            } else if (isExpanded && packBots.length > 25) {
                const showLessBtn = document.createElement('button');
                showLessBtn.className = 'btn-show-more';
                showLessBtn.innerText = `Afficher moins (réduire à 25)`;
                showLessBtn.onclick = () => {
                    expandedPacks[packId] = false;
                    renderPackBots(packId);
                };
                packBotsContainer.appendChild(showLessBtn);
            }
        }

        function startBotCampaign(totalUsersToAdd) {
            isStopping = false;
            const container = document.getElementById('bots-container');
            const emptyMsg = document.getElementById('empty-monitor');
            if (emptyMsg) emptyMsg.remove();

            packCounter++;
            const packId = packCounter;
            expandedPacks[packId] = false;

            const isAutoWaves = document.getElementById('auto_waves_toggle').checked;
            const modeSelect = document.getElementById('operation_mode').value;
            let modeDesc = "Vues Pures";
            if (modeSelect === 'chat_live') modeDesc = "Vues + Chat";
            if (modeSelect === 'views_video') modeDesc = "Vues Vidéo/Short";
            
            const packFrame = document.createElement('div');
            packFrame.className = 'pack-frame';
            packFrame.id = `pack-frame-${packId}`;
            
            packFrame.innerHTML = `
                <div class="pack-header">
                    <span>📦 Pack #${packId} (${totalUsersToAdd} instances | Cible: Tunnel ngrok)</span>
                    <span class="badge" id="pack-badge-${packId}">En cours</span>
                </div>
                <div class="pack-subinfo">
                    <span>Mode : <b>${modeDesc}</b></span>
                    <span>Vagues Auto : <b>${isAutoWaves ? 'Activé' : 'Désactivé'}</b></span>
                    <span>Réussites : <b id="pack-success-${packId}">0</b> / ${totalUsersToAdd}</span>
                    <span>Filtrés : <b id="pack-banned-${packId}" style="color: var(--danger);">0</b></span>
                </div>
                <div id="pack-bots-container-${packId}"></div>
            `;
            container.prepend(packFrame);

            let spawnedInThisPack = 0;
            const baseInterval = isAutoWaves ? 50 : 10;
            const intervalTime = totalUsersToAdd > 200 ? 5 : baseInterval;

            const packWaveTimer = setInterval(() => {
                if (isStopping) { clearInterval(packWaveTimer); return; }
                
                const batchSize = totalUsersToAdd > 200 ? 20 : 5;
                let added = 0;

                while (added < batchSize && spawnedInThisPack < totalUsersToAdd) {
                    totalGlobalBots++;
                    const i = totalGlobalBots;
                    const botName = `owncast_bot_${i}`;
                    const assignedPing = Math.floor(Math.random() * 15) + 4;
                    
                    botStates.push({
                        id: i,
                        packId: packId,
                        name: botName,
                        progress: 0,
                        speed: Math.random() * 2.0 + 1.0,
                        status: "warning",
                        statusText: `Connexion au tunnel HLS...`,
                        ping: assignedPing,
                        deleting: false,
                        filtered: false,
                        reconnectCount: 0
                    });

                    spawnedInThisPack++;
                    added++;
                }

                renderPackBots(packId);
                updateGlobalStats();
                refreshEstimatedViewers();

                if (spawnedInThisPack >= totalUsersToAdd) {
                    clearInterval(packWaveTimer);
                    log(`Pack #${packId} : Déploiement des ${totalUsersToAdd} instances vers ngrok terminé.`);
                }
            }, intervalTime);

            if (!globalMonitorLoop) {
                globalMonitorLoop = setInterval(() => {
                    if (isStopping) return;
                    
                    const autoRemoveBanned = document.getElementById('auto_remove_banned').checked;
                    const autoReconnect = document.getElementById('auto_reconnect_banned').checked;

                    for (let pId = 1; pId <= packCounter; pId++) {
                        const packBots = botStates.filter(b => b.packId === pId && !b.deleting);
                        if (packBots.length > 0) {
                            const successCount = packBots.filter(b => b.status === "running").length;
                            const bannedCount = packBots.filter(b => b.filtered).length;
                            
                            const successEl = document.getElementById(`pack-success-${pId}`);
                            const bannedEl = document.getElementById(`pack-banned-${pId}`);
                            if (successEl) successEl.innerText = successCount;
                            if (bannedEl) bannedEl.innerText = bannedCount;
                        }
                    }

                    botStates.forEach(bot => {
                        if (bot.deleting) return;

                        if (bot.filtered) {
                            if (autoRemoveBanned) {
                                bot.deleting = true;
                                return;
                            }

                            const maxAttemptsSetting = document.getElementById('reconnect_attempts').value;
                            let maxAttempts = maxAttemptsSetting === 'infinite' ? 999999 : parseInt(maxAttemptsSetting);

                            if (autoReconnect && bot.reconnectCount < maxAttempts && Math.random() < 0.3) {
                                bot.reconnectCount++;
                                bot.filtered = false;
                                bot.progress = 0;
                                bot.status = "warning";
                                bot.statusText = `🔄 Reconnexion au flux...`;
                                updateGlobalStats();
                                refreshEstimatedViewers();
                            }
                            return;
                        }

                        bot.progress += bot.speed;
                        if (bot.progress > 100) bot.progress = 100;

                        const progInt = Math.floor(bot.progress);
                        const currentMode = document.getElementById('operation_mode').value;

                        if (progInt < 99) {
                            bot.statusText = `Chargement HLS... (${progInt}%)`;
                            bot.status = "warning";
                        } else {
                            bot.statusText = `Flux actif / Vues comptabilisées`;
                            bot.status = "running";
                        }
                    });

                    for (let pId = 1; pId <= packCounter; pId++) {
                        if (document.getElementById(`pack-frame-${pId}`)) {
                            renderPackBots(pId);
                        }
                    }
                    updateGlobalStats();
                    refreshEstimatedViewers();
                }, 800);
            }

            if (!viewsSyncInterval) {
                viewsSyncInterval = setInterval(() => {
                    if (isStopping) return;
                    refreshEstimatedViewers();
                }, 2000);
            }
        }

        async function sendCommand(action) {
            const endpoint = action === 'start' ? '/api/start' : '/api/stop';
            const usersCount = parseInt(document.getElementById('users').value) || 1;
            const modeVal = document.getElementById('operation_mode').value;

            if (action === 'start') {
                startBotCampaign(usersCount);
            } else {
                isStopping = true;
                if (globalMonitorLoop) { clearInterval(globalMonitorLoop); globalMonitorLoop = null; }
                if (viewsSyncInterval) { clearInterval(viewsSyncInterval); viewsSyncInterval = null; }
                
                log("Arrêt d'urgence et nettoyage complet de l'interface...");

                botStates = [];
                totalGlobalBots = 0;
                packCounter = 0;
                previousEstimatedValue = 0;
                expandedPacks = {};
                updateGlobalStats();
                document.getElementById('stat-estimated-viewers').innerText = "0";
                updateTrendArrows(0);
                
                const container = document.getElementById('bots-container');
                container.innerHTML = `
                    <div style="text-align: center; color: var(--muted); padding: 40px; font-size: 13px;" id="empty-monitor">
                        Raid BOT ended. Tous les flux ont été déconnectés proprement.
                    </div>
                `;
                log("Raid BOT ended.");
            }

            const payload = {
                target_url: document.getElementById('target_url').value,
                operation_mode: modeVal,
                chat_message: document.getElementById('chat_message').value,
                chat_interval: parseInt(document.getElementById('chat_interval').value) || 10,
                users: usersCount,
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
                log("Réponse Master : " + JSON.stringify(data));
            } catch(e) {
                log("Erreur de communication réseau : " + e);
            }
        }

        log("Master Dashboard Pro initialisé avec le tunnel ngrok.");
    </script>
</body>
</html>"""
    return web.Response(text=html_content, content_type='text/html')

async def api_start(request):
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Payload invalide"}, status=400)
    
    target_url = data.get("target_url", "")
    platform, channel = detect_platform_and_channel(target_url)
    total_users = max(1, int(data.get("users", 1)))
    num_workers = len(WORKER_URLS)
    
    base_users = total_users // num_workers
    remainder = total_users % num_workers

    payload_base = {
        "order_id": f"cmd_{uuid.uuid4().hex[:10]}",
        "target_url": target_url,
        "platform": platform,
        "channel": channel,
        "operation_mode": str(data.get("operation_mode", "views_live")),
        "chat_message": str(data.get("chat_message", "Raid Bot by {Anonymous}")),
        "chat_interval": max(1, int(data.get("chat_interval", 10))),
        "auto_waves": bool(data.get("auto_waves", False)),
        "auto_reconnect": bool(data.get("auto_reconnect", False)),
        "auto_remove_banned": bool(data.get("auto_remove_banned", False)),
        "reconnect_attempts": str(data.get("reconnect_attempts", "infinite"))
    }

    results = []
    async def dispatch_worker(index, worker_url):
        users_for_this_worker = base_users + (1 if index < remainder else 0)
        if users_for_this_worker <= 0:
            return
        
        worker_payload = dict(payload_base)
        worker_payload["users"] = users_for_this_worker

        try:
            async with session.post(f"{worker_url.strip()}/start-bots", json=worker_payload, timeout=ClientTimeout(total=5)) as resp:
                body = await resp.json()
                results.append({"worker": worker_url.strip(), "status": resp.status, "body": body})
        except Exception as e:
            error_msg = str(e) if str(e) else repr(e)
            results.append({"worker": worker_url.strip(), "error": error_msg})

    await asyncio.gather(*(dispatch_worker(i, url) for i, url in enumerate(WORKER_URLS)))

    return web.json_response({
        "status": "success",
        "message": f"Campagne répartie sur {num_workers} workers distincts pour {total_users} bots au total.",
        "details": results
    })

async def api_stop(request):
    results = []
    async def stop_worker(worker_url):
        try:
            async with session.post(f"{worker_url.strip()}/stop-bots", timeout=ClientTimeout(total=5)) as resp:
                body = await resp.json()
                results.append({"worker": worker_url.strip(), "status": resp.status, "body": body})
        except Exception as e:
            error_msg = str(e) if str(e) else repr(e)
            results.append({"worker": worker_url.strip(), "error": error_msg})

    await asyncio.gather(*(stop_worker(url) for url in WORKER_URLS))
    return web.json_response({
        "status": "success",
        "message": "Ordre d'arrêt global diffusé à tous les workers du cluster.",
        "details": results
    })

async def startup(app):
    global session
    session = ClientSession()

async def cleanup(app):
    await session.close()

app = web.Application()
app.on_startup.append(startup)
app.on_cleanup.append(cleanup)
app.router.add_get("/", index)
app.router.add_post("/api/start", api_start)
app.router.add_post("/api/stop", api_stop)

if __name__ == "__main__":
    web.run_app(app, host="0.0.0.0", port=PORT)