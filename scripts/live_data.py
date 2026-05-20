from nba_api.live.nba.endpoints import scoreboard

def get_current_games():
    try:
        board = scoreboard.ScoreBoard()
        date = board.score_board_date
        games = board.games.get_dict()

        return date, games
    except Exception as e:
        print(f"NBA API error: {e}")
        time.sleep(5)
        return None, []

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from database import SessionLocal
from database import TeamEloRating

def latest_elo(team, date):
    session = SessionLocal()

    latest_elo = (
        session.query(TeamEloRating)
        .filter(
            TeamEloRating.team == team,
            TeamEloRating.rating_date <= date
        )
        .order_by(
            TeamEloRating.rating_date.desc()
        )
        .first()
    )

    return latest_elo

from scripts.ingest_pbp import clock_to_seconds

def extract_features(date, games):
    features_list = []

    for game in games:
        home_team = game['homeTeam']
        away_team = game['awayTeam']

        score_diff = home_team['score'] - away_team['score']

        seconds_on_clock = clock_to_seconds(game['gameClock'])
        seconds_remaining = (4 - game['period']) * 720 + seconds_on_clock

        home_name = home_team['teamTricode']
        away_name = away_team['teamTricode']

        home_elo = latest_elo(home_name, date)
        away_elo = latest_elo(away_name, date)
        elo_diff = home_elo - away_elo

        features_list.append(
            [
                game['gameId'], 
                home_name, 
                away_name, 
                score_diff, 
                seconds_remaining, 
                elo_diff
            ]
        )
    
    return features_list

import time
import threading
import joblib
import pandas as pd
from fastapi import FastAPI

app = FastAPI()

live_predictions = dict()
from threading import Lock

prediction_lock = Lock()

def poll_predict():
    artifact = joblib.load(
        "models/live_odds.pkl"
    )

    live_odds = artifact["model"]

    FEATURES = artifact["features"]

    while True:
        date, games = get_current_games()
        
        if date is None or not games:
            time.sleep(10)
            continue

        features_list = extract_features(date, games)

        if len(features_list) == 0:
            time.sleep(10)
            continue

        live_df = pd.DataFrame([f[3:] for f in features_list], columns=FEATURES)

        pred_probas = live_odds.predict_proba(live_df)[: 1]

        for features, proba in zip(features_list, pred_probas):
            pred_entry = dict()
            pred_entry['home_team'] = features_list[1]
            pred_entry['away_team'] = features_list[2]
            pred_entry['score_diff'] = features_list[3]
            pred_entry['seconds_remaining'] = features_list[4]
            pred_entry['last_updated'] = time.now()

            with prediction_lock:
                live_predictions[features_list[0]].append(pred_entry)
        
        print(live_predictions)

        time.sleep(10)

@app.on_event("startup")
def startup_event():
    threading.Thread(
        target=poll_predict,
        daemon=True
    ).start()

@app.get("/live_predictions")
def get_live_predictions():
    return live_predictions