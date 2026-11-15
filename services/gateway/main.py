from fastapi import FastAPI
app = FastAPI(title="gateway")

@app.get("/health")
def health():
    return {"status": "ok", "service": "gateway"}