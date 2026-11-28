import os
import uuid

from qdrant_client import QdrantClient
from qdrant_client.http import models as qm

QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")
COLLECTION = os.getenv("QDRANT_COLLECTION", "studyrag_chunks")
EMBED_DIM = int(os.getenv("EMBED_DIM", "1024"))

# Frozen namespace — NEVER change, or all point IDs change
_NS = uuid.UUID("6f1b3c2a-9d4e-4a1b-9c2e-8f0a1b2c3d4e")


def get_client() -> QdrantClient:
    return QdrantClient(url=QDRANT_URL)


def ensure_collection(client: QdrantClient) -> None:
    existing = {c.name for c in client.get_collections().collections}
    if COLLECTION in existing:
        return
    client.create_collection(
        collection_name=COLLECTION,
        vectors_config=qm.VectorParams(size=EMBED_DIM, distance=qm.Distance.COSINE),
    )
    client.create_payload_index(
        collection_name=COLLECTION,
        field_name="course",
        field_schema=qm.PayloadSchemaType.KEYWORD,
    )


def point_id(course: str, filename: str, chunk_index: int) -> str:
    return str(uuid.uuid5(_NS, f"{course}:{filename}:{chunk_index}"))


def upsert_chunks(client, course, filename, chunks, vectors):
    if len(chunks) != len(vectors):
        raise ValueError("chunks/vectors length mismatch")
    points = [
        qm.PointStruct(
            id=point_id(course, filename, i),
            vector=vec,
            payload={
                "course": course,
                "file": filename,
                "chunk_index": i,
                "page": chunk.get("page"),
                "text": chunk["text"],
            },
        )
        for i, (chunk, vec) in enumerate(zip(chunks, vectors))
    ]
    client.upsert(collection_name=COLLECTION, points=points)
