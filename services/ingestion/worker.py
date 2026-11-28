import json
import os
import time

import pika
import redis
from qdrant_utils import get_client, ensure_collection, upsert_chunks
from parsing import parse_and_chunk

RABBITMQ_URL = os.getenv("RABBITMQ_URL")
REDIS_URL = os.getenv("REDIS_URL")
EMBEDDING_URL = os.getenv("EMBEDDING_URL")

QUEUE = "ingest_jobs"
DLQ = "ingest_jobs_dlq"
MAX_ATTEMPTS = 3
BATCH_SIZE = 16

r = redis.from_url(REDIS_URL, decode_responses=True)


def set_status(job_id: str, status: str, **extra):
    """Update the job hash in Redis."""
    r.hset(f"job:{job_id}", mapping={"status": status, **extra})


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Call the embedding service in batches."""
    import httpx
    out = []
    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i:i + BATCH_SIZE]
        resp = httpx.post(f"{EMBEDDING_URL}/embed", json={"texts": batch}, timeout=120)
        resp.raise_for_status()
        out.extend(resp.json()["embeddings"])
    return out


def process(msg: dict):
    """The actual work for one job. Raises on any failure."""
    job_id = msg["job_id"]
    course = msg["course"]
    filename = msg["filename"]
    filepath = msg["filepath"]

    set_status(job_id, "processing")

    chunks = parse_and_chunk(filepath)
    if not chunks:
        raise ValueError("no text extracted from file")

    texts = [c["text"] for c in chunks]
    vectors = embed_texts(texts)

    client = get_client()
    ensure_collection(client)
    upsert_chunks(client, course, filename, chunks, vectors)

    set_status(job_id, "done", chunks=len(chunks))


def on_message(ch, method, properties, body):
    """RabbitMQ callback. Handles retries, ack, and DLQ."""
    try:
        msg = json.loads(body)
    except Exception as e:
        print(f"[worker] bad message, dropping: {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        return

    job_id = msg.get("job_id", "?")
    attempts = (msg.get("_attempts") or 0) + 1

    try:
        process(msg)
        ch.basic_ack(delivery_tag=method.delivery_tag)
        print(f"[worker] job {job_id} done")
    except Exception as e:
        print(f"[worker] job {job_id} attempt {attempts} failed: {e}")
        if attempts >= MAX_ATTEMPTS:
            set_status(job_id, "failed", error=str(e))
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            # requeue=False + queue has DLQ args → message goes to ingest_jobs_dlq
        else:
            msg["_attempts"] = attempts
            ch.basic_publish(
                exchange="",
                routing_key=QUEUE,
                body=json.dumps(msg),
                properties=pika.BasicProperties(delivery_mode=2),
            )
            ch.basic_ack(delivery_tag=method.delivery_tag)


def main():
    while True:
        try:
            params = pika.URLParameters(RABBITMQ_URL)
            conn = pika.BlockingConnection(params)
            ch = conn.channel()
            ch.queue_declare(queue=DLQ, durable=True)
            ch.queue_declare(
                queue=QUEUE,
                durable=True,
                arguments={
                    "x-dead-letter-exchange": "",
                    "x-dead-letter-routing-key": DLQ,
                },
            )
            ch.basic_qos(prefetch_count=1)
            ch.basic_consume(queue=QUEUE, on_message_callback=on_message)
            print("[worker] waiting for jobs...")
            ch.start_consuming()
        except KeyboardInterrupt:
            print("[worker] shutting down")
            break
        except Exception as e:
            print(f"[worker] connection error: {e}. Reconnecting in 5s...")
            time.sleep(5)


if __name__ == "__main__":
    main()
