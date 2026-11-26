import json
import os
import uuid
from pathlib import Path

import pika
import redis
from fastapi import FastAPI, File, Form, HTTPException, UploadFile

app = FastAPI(title="ingestion")

# --- config from .env ---
RABBITMQ_URL = os.getenv("RABBITMQ_URL")
REDIS_URL = os.getenv("REDIS_URL")
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "/data/uploads"))

QUEUE = "ingest_jobs"
DLQ = "ingest_jobs_dlq"
ALLOWED_EXT = {".pdf", ".pptx", ".docx"}

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

r = redis.from_url(REDIS_URL, decode_responses=True)


def _publish(msg: dict) -> None:
    """Publish a job to the ingest_jobs queue with DLQ args."""
    params = pika.URLParameters(RABBITMQ_URL)
    conn = pika.BlockingConnection(params)
    ch = conn.channel()

    # Declare DLQ first so the main queue can reference it.
    ch.queue_declare(queue=DLQ, durable=True)
    ch.queue_declare(
        queue=QUEUE,
        durable=True,
        arguments={
            "x-dead-letter-exchange": "",
            "x-dead-letter-routing-key": DLQ,
        },
    )
    ch.basic_publish(
        exchange="",
        routing_key=QUEUE,
        body=json.dumps(msg),
        properties=pika.BasicProperties(delivery_mode=2),  # persistent
    )
    conn.close()


@app.get("/health")
def health():
    return {"status": "ok", "service": "ingestion"}


@app.post("/ingest")
async def ingest(file: UploadFile = File(...), course: str = Form(...)):
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(415, detail=f"unsupported file type: {ext}")
    if not course.strip():
        raise HTTPException(400, detail="course is required")

    job_id = str(uuid.uuid4())
    dest = UPLOAD_DIR / f"{job_id}{ext}"

    contents = await file.read()
    if not contents:
        raise HTTPException(400, detail="empty file")
    dest.write_bytes(contents)

    # Store job status in Redis
    r.hset(f"job:{job_id}", mapping={
        "status": "queued",
        "course": course,
        "filename": file.filename,
    })

    # Publish to RabbitMQ
    _publish({
        "job_id": job_id,
        "course": course,
        "filename": file.filename,
        "filepath": str(dest),
    })

    return {"job_id": job_id}


@app.get("/jobs/{job_id}")
def get_job(job_id: str):
    job = r.hgetall(f"job:{job_id}")
    if not job:
        raise HTTPException(404, detail="job not found")
    return job
