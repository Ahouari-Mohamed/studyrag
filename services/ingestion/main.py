from fastapi import FastAPI
app = FastAPI(title="ingestion")

@app.get("/health")
def health():
    return {"status": "ok", "service": "ingestion"}