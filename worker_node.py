"""Worker Node - Playwright Réel & Rapports en Temps Réel."""
import asyncio
import os
from aiohttp import ClientSession, web
from playwright.async_api import async_playwright

PORT = int(os.getenv("PORT", "8001"))
NODE_NAME = os.getenv("NODE_NAME", "Worker-1")
BOT_CONCURRENCY = int(os.getenv("BOT_CONCURRENCY", "4"))
QUEUE_SIZE = 100

active_bot_tasks = set()

async def browser_bot_session(target_url, bot_id, master_callback_url):
    async def update_status(progress, status, status_text):
        payload = {
            "id": bot_id,
            "name": f"bot_{bot_id}",
            "progress": progress,
            "status": status,
            "statusText": status_text,
            "ping": 10
        }
        try:
            async with ClientSession() as session:
                await session.post(master_callback_url, json=payload, timeout=2)
        except Exception:
            pass

    await update_status(15, "warning", "Lancement navigateur...")
    await asyncio.sleep(0.3)

    async with async_playwright() as p:
        try:
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

            await update_status(50, "warning", "Chargement page cible...")
            await page.goto(target_url, timeout=30000, wait_until="domcontentloaded")
            
            await update_status(100, "running", "Flux actif / Connecté")

            while True:
                await asyncio.sleep(10)
                await update_status(100, "running", "Flux actif / Connecté")

        except asyncio.CancelledError:
            pass
        except Exception as exc:
            await update_status(100, "error", f"Erreur : {str(exc)[:15]}")
        finally:
            await browser.close()

async def worker(queue, master_callback_url):
    while True:
        item = await queue.get()
        task = None
        try:
            if item is None:
                return
            target_url = item.get("target_url")
            bot_id = item.get("bot_id")
            if target_url:
                task = asyncio.create_task(browser_bot_session(target_url, bot_id, master_callback_url))
                active_bot_tasks.add(task)
                await task
        except asyncio.CancelledError:
            break
        except Exception as exc:
            pass
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
    offset = int(data.get("worker_offset", 0))

    if not target_url:
        return web.json_response({"error": "URL cible manquante"}, status=400)

    master_host = request.headers.get("Host", "localhost:8000").split(":")[0]
    master_callback_url = f"http://{master_host}:8000/api/report"

    items = [{"target_url": target_url, "bot_id": offset + i + 1} for i in range(users)]
    asyncio.create_task(run_cluster_task(items, master_callback_url))

    return web.json_response({
        "status": "success",
        "message": f"{users} navigateurs lancés sur {NODE_NAME}."
    })

async def stop_bots_handler(request):
    global active_bot_tasks
    cancelled_count = len(active_bot_tasks)
    for task in active_bot_tasks:
        task.cancel()
    active_bot_tasks.clear()

    return web.json_response({"status": "success", "message": f"Arrêt sur {NODE_NAME}."})

async def run_cluster_task(items, master_callback_url):
    queue = asyncio.Queue(maxsize=QUEUE_SIZE)
    workers = [asyncio.create_task(worker(queue, master_callback_url)) for _ in range(BOT_CONCURRENCY)]
    
    for item in items:
        await queue.put(item)
        
    await queue.join()
    
    for _ in workers:
        await queue.put(None)

app = web.Application()
app.router.add_post("/start-bots", start_bots_handler)
app.router.add_post("/stop-bots", stop_bots_handler)

if __name__ == "__main__":
    print(f"[{NODE_NAME}] Démarrage du worker sur le port {PORT}...")
    web.run_app(app, host="0.0.0.0", port=PORT)