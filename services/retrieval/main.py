from fastapi import FastAPI
app = FastAPI(title="retrieval")

@app.get("/health")
def health():
    return {"status": "ok", "service": "retrieval"}