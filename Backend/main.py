from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

if __package__:
    from . import cashcast
    from .cashcast import initialize_auth, initialize_database, initialize_runtime, router
else:
    import cashcast
    from cashcast import initialize_auth, initialize_database, initialize_runtime, router

logger = logging.getLogger("cashcast")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    initialize_auth()
    initialize_runtime()
    try:
        initialize_database()
    except Exception:
        logger.exception("Persistence initialization failed; local fallback may be unavailable.")
    yield


app = FastAPI(
    title="CashCast · ATM Cash Demand Predictor",
    description="Historical ATM cash-demand forecasting and replenishment simulation for Bank Muscat Project P_136.",
    version="2.0.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174").split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)
app.include_router(router)


@app.get("/health", tags=["Health"])
def health():
    model_ready = cashcast.get_model() is not None and cashcast.get_data() is not None
    database = cashcast.database_is_up()
    return {
        "status": "healthy" if model_ready and database else "degraded",
        "model_loaded": cashcast.get_model() is not None,
        "dataset_loaded": cashcast.get_data() is not None,
        "database": "up" if database else "down",
    }
