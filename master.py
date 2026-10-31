import os
import requests
from flask import Flask, jsonify, request

app = Flask(__name__)

# Liste centralisée de TOUS tes workers (Render + tes workers persos/autres)
WORKER_URLS = [
    # Tes 3 workers sur Render
    "https://cluster-worker-1.onrender.com",
    "https://cluster-worker-2.onrender.com",
    "https://cluster-worker-3.onrender.com",
    
    # Tu pourras ajouter d'autres liens ici plus tard (ex: tes workers locaux ou autres hébergeurs)
]

@app.route('/')
def home():
    return jsonify({
        "status": "Master Online",
        "total_workers": len(WORKER_URLS),
        "connected_workers": WORKER_URLS
    })

# Route pour dispatcher une tâche à l'ensemble des workers du cluster
@app.route('/dispatch', methods=['POST'])
def dispatch_task():
    task_data = request.json or {}
    results = []

    # Envoi de la tâche à chaque worker de la liste
    for worker_url in WORKER_URLS:
        try:
            # Exemple d'appel HTTP vers l'endpoint /run ou /task de chaque worker
            response = requests.post(f"{worker_url}/run", json=task_data, timeout=5)
            results.append({
                "worker": worker_url,
                "status_code": response.status_code,
                "response": response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
            })
        except Exception as e:
            results.append({
                "worker": worker_url,
                "error": str(e)
            })

    return jsonify({
        "message": "Ordres de mission dispatchés à l'armée de workers !",
        "results": results
    })

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)