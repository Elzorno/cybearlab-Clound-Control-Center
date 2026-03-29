from fastapi import FastAPI

app = FastAPI(
    title="ISCS1800 Unified Admin + Grader API",
    version="0.1.0",
)


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "version": app.version,
        "queue_depth": 0,
    }
