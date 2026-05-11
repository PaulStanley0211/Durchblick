from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import comparison

app = FastAPI(title="Durchblick API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(comparison.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
