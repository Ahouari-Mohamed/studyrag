from fastapi import FastAPI
app = FastAPI(title="embedding")

@app.get("/health")
def health():
    return {"status": "ok", "service": "embedding"}