import threading

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from services.live_data import poll_predict, live_predictions

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    threading.Thread(
        target=poll_predict,
        daemon=True
    ).start()

    yield

app = FastAPI(lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,

    allow_origins=[
        "http://localhost:3000",
        "https://nba-live-odds-rho.vercel.app/"
    ],

    allow_credentials=True,

    allow_methods=["*"],

    allow_headers=["*"],
)

# Root endpoint
@app.get("/")
def root():
    return {
        "status": "running"
    }

# Health check
@app.get("/health")
def health():
    return {
        "status": "healthy"
    }

# Live predictions
@app.get("/live_predictions")
def get_live_predictions():
    return live_predictions

# Single game endpoint
@app.get("/games/{game_id}")
def get_game(game_id: str):
    return live_predictions.get(game_id, [])
