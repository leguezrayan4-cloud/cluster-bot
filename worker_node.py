import asyncio
import os
from aiohttp import web
from playwright.async_api import async_playwright

PORT = int(os.getenv("PORT", "8001"))
NODE_NAME = os.getenv("NODE_NAME", "Worker-1")
BOT_CONCURRENCY = int(os.getenv("BOT_CONCURRENCY", "4")) # On réduit un peu la concurrence car un navigateur consomme plus de RAM
QUEUE_SIZE = 100

active_bot_tasks = set()

async def browser_bot_session(target_url, bot_id):
    async with async_playwright() as p:
        # Lancement de Chromium en mode headless (sans interface graphique visible sur Render)
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-accelerated-2d-canvas",
                "--disable-gpu"
            ]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        try:
            print(f"[{NODE_NAME}] Bot #{bot_id} -> Chargement de la page : {target_url}")
            # Navigation vers la page du stream Owncast
            await page.goto(target_url, timeout=30000, wait_until="domcontentloaded")
            
            # Maintien de la session active sur la page pour faire compter le viewer
            while True:
                await asyncio.sleep(10)
        except asyncio.CancelledError:
            print(f"[{NODE_NAME}] Bot #{bot_id} proprement stoppé.")
        except Exception as exc:
            print(f"[{NODE_NAME}] Bot #{bot_id} erreur : {exc}")
        finally:
            await browser.close()

async def worker(queue):
    while True:
        item = await queue.get()
        task = None
        try:
            if item is None:
                return
            target_url = item.get("target_url")
            bot_id = item.get("bot_id")
            if target_url:
                task = asyncio.create_task(browser_bot_session(target_url, bot_id))
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

    items = [{"target_url": target_url, "bot_id": i+1} for i in range(users)]
    asyncio.create_task(run_cluster_task(items))

    return web.json_response({
        "status": "success",
        "message": f"Campagne navigateur lancée sur {NODE_NAME} avec {users} instances vers {target_url}.",
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
        "message": f"Arrêt d'urgence exécuté sur {NODE_NAME} : {cancelled_count} navigateurs stoppés."
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
    print(f"[{NODE_NAME}] Démarrage du worker Playwright sur le port {PORT}...")
    web.run_app(app, host="0.0.0.0", port=PORT)