from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
from core.config import settings

def setup_cors(app: FastAPI) -> None:
    """Setup CORS middleware"""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )