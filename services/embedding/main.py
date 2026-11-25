import os
from typing import List

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer

# Contract keys: EMBED_MODEL / EMBED_DIM (NOT EMBEDDING_*)
MODEL_NAME = os.getenv("EMBED_MODEL", "BAAI/bge-m3")
EMBED_DIM = int(os.getenv("EMBED_DIM", "1024"))

app = FastAPI(title="embedding")

# Load model once at startup. First container start downloads ~2.2 GB,
# subsequent starts read from the mounted hf_cache volume.
_model: SentenceTransformer | None = None


@app.on_event("startup")
def load_model():
    global _model
    _model = SentenceTransformer(MODEL_NAME, device="cpu")


class EmbedRequest(BaseModel):
    texts: List[str]


class EmbedResponse(BaseModel):
    embeddings: List[List[float]]
    dim: int


@app.get("/health")
def health():
    return {"status": "ok", "service": "embedding", "model": MODEL_NAME, "dim": EMBED_DIM}


@app.post("/embed", response_model=EmbedResponse)
def embed(req: EmbedRequest):
    if not req.texts:
        raise HTTPException(status_code=400, detail="texts must be non-empty")
    if _model is None:
        raise HTTPException(status_code=503, detail="model not loaded yet")

    # normalize_embeddings=True -> unit-length vectors.
    # Why: makes cosine similarity == dot product, which Qdrant uses by default.
    vecs = _model.encode(
        req.texts,
        batch_size=16,
        normalize_embeddings=True,
        convert_to_numpy=True,
    )
    return EmbedResponse(
        embeddings=vecs.tolist(),
        dim=EMBED_DIM,
    )
