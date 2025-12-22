from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import generation

app = FastAPI(
    title="Candlr API",
    description="API for generating custom candle mold 3D models",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for Docker deployment
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(generation.router, prefix="/api", tags=["generation"])


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
