import threading
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.services.live_prediction import LivePrediction
from contextlib import asynccontextmanager
from datetime import datetime
import pytz

eastern = pytz.timezone("US/Eastern")
today = datetime.now(eastern).strftime("%Y-%m-%d")
lp = LivePrediction(today)

@asynccontextmanager
async def lifespan(app: FastAPI):
    poll_thread = threading.Thread(
        target=lp.poll_predict,
        daemon=True
    )

    poll_thread.start()

    yield

    print("Shutting down...")

app = FastAPI(lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,

    allow_origins=[
        "http://localhost:3000",
        "https://nba-live-odds-rho.vercel.app"
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
    return lp.live_predictions

# Single game endpoint
@app.get("/games/{game_id}")
def get_game(game_id: str):
    return lp.live_predictions.get(game_id, [])
