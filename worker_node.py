import asyncio
import random
import os
from aiohttp import web
from curl_cffi.requests import AsyncSession

PORT = int(os.getenv("PORT", "8001"))
NODE_NAME = os.getenv("NODE_NAME", "Worker-1")
BOT_CONCURRENCY = int(os.getenv("BOT_CONCURRENCY", "8"))
QUEUE_SIZE = 100

# Ensemble global pour suivre et annuler proprement les tâches en cours sur ce worker
active_bot_tasks = set()

async def maintain_presence_loop(base_url):
    base_url = base_url.rstrip("/")
    hls_url = f"{base_url}/hls/stream.m3u8"
    
    try:
        async with AsyncSession(impersonate="chrome120") as session:
            resp_init = await session.get(base_url, timeout=12, allow_redirects=True)
            if resp_init.status_code >= 400:
                print(f"[{NODE_NAME}] Refusé par le serveur Owncast (Code {resp_init.status_code}) sur {base_url}")
                return

            while True:
                await asyncio.sleep(random.uniform(4.0, 7.0))
                response = await session.get(hls_url, timeout=10, allow_redirects=True)
                
                if response.status_code >= 400:
                    print(f"[{NODE_NAME}] Erreur HLS {response.status_code} sur {hls_url}")
                
                if response.status_code >= 500:
                    break
    except asyncio.CancelledError:
        print(f"[{NODE_NAME}] Tâche bot proprement interrompue.")
        raise
    except Exception as exc:
        print(f"[{NODE_NAME}] Exception attrapée pour un bot : {exc}")

async def worker(queue):
    while True:
        item = await queue.get()
        task = None
        try:
            if item is None:
                return
            target_url = item.get("target_url")
            if target_url:
                task = asyncio.create_task(maintain_presence_loop(target_url))
                active_bot_tasks.add(task)
                await task
        except asyncio.CancelledError:
            break
        except Exception as exc:
            print(f"[{NODE_NAME}] Erreur dans le worker: {exc}")
        finally:
            if task and task in active_bot_tasks:
                active_bot_tasks.remove(task)
            queue.task_done()

async def start_bots_handler(request):
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Payload JSON invalide"}, status=400)

    target_url = data.get("target_url")
    users = int(data.get("users", 1))

    if not target_url:
        return web.json_response({"error": "URL cible manquante"}, status=400)

    items = [{"target_url": target_url} for _ in range(users)]
    asyncio.create_task(run_cluster_task(items))

    return web.json_response({
        "status": "success",
        "message": f"Campagne lancée sur {NODE_NAME} avec {users} instances vers {target_url}.",
        "target": target_url
    })

async def stop_bots_handler(request):
    global active_bot_tasks
    cancelled_count = len(active_bot_tasks)
    for task in active_bot_tasks:
        task.cancel()
    active_bot_tasks.clear()

    return web.json_response({
        "status": "success",
        "message": f"Arrêt d'urgence exécuté sur {NODE_NAME} : {cancelled_count} tâches de bots stoppées."
    })

async def run_cluster_task(items):
    queue = asyncio.Queue(maxsize=QUEUE_SIZE)
    workers = [asyncio.create_task(worker(queue)) for _ in range(BOT_CONCURRENCY)]
    
    for item in items:
        await queue.put(item)
        
    await queue.join()
    
    for _ in workers:
        await queue.put(None)
        
    asyncio.gather(*workers)

app = web.Application()
app.router.add_post("/start-bots", start_bots_handler)
app.router.add_post("/stop-bots", stop_bots_handler)

if __name__ == "__main__":
    print(f"[{NODE_NAME}] Démarrage du worker de debug Owncast sur le port {PORT}...")
    web.run_app(app, host="0.0.0.0", port=PORT)