"""
Webhook server leve (FastAPI) que o Airflow chama ao fim de cada DAG run.
Ele invalida o cache do Streamlit e pode disparar um reload via Server-Sent Events.
"""
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
import subprocess
import time
import os
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="Weather Dashboard Webhook")

# Token simples de segurança (defina em config/.env como WEBHOOK_TOKEN=...)
WEBHOOK_TOKEN = os.getenv("WEBHOOK_TOKEN", "weather-secret-token")

# Timestamp da última atualização (compartilhado via arquivo para o Streamlit ler)
LAST_UPDATE_FILE = "/tmp/dashboard_last_update.txt"


def write_timestamp(ts: int):
    with open(LAST_UPDATE_FILE, "w") as f:
        f.write(str(ts))


@app.post("/webhook/dag-success")
async def dag_success(request: Request):
    """
    Chamado pelo Airflow após cada DAG run bem-sucedido.
    Corpo esperado (JSON):
        { "token": "...", "dag_id": "weather_pipeline", "run_id": "..." }
    """
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Body JSON inválido")

    if body.get("token") != WEBHOOK_TOKEN:
        raise HTTPException(status_code=403, detail="Token inválido")

    ts = int(time.time())
    write_timestamp(ts)

    logger.info(f"✅ DAG '{body.get('dag_id')}' concluída — timestamp {ts}")

    return JSONResponse({
        "status": "ok",
        "message": "Dashboard notificado",
        "timestamp": ts,
        "streamlit_url": f"http://localhost:8501?ts={ts}",
    })


@app.get("/health")
async def health():
    ts = None
    if os.path.exists(LAST_UPDATE_FILE):
        with open(LAST_UPDATE_FILE) as f:
            ts = f.read().strip()
    return {"status": "healthy", "last_dag_trigger": ts}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8502, log_level="info")