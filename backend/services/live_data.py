import time
from datetime import date, datetime, timezone
from threading import Lock
from collections import defaultdict

import pandas as pd
import joblib

from nba_api.stats.endpoints import ScoreboardV3

from app.db.database import SessionLocal, TeamEloRating
from app.scripts.ingest_pbp import clock_to_seconds

live_predictions = defaultdict(list)
prediction_lock = Lock()

def get_current_games():

    try:
        today = date.today().strftime("%Y-%m-%d")
        print(today)
        board = ScoreboardV3(game_date=today).get_dict()
        # print(board)

        games = board['scoreboard']['games']
        print(games)

        if not games:

            print("No live games found")

            return today, []

        return today, games

    except Exception as e:

        print(f"NBA API error: {e}")

        return today, []

def latest_elo(team, date):
    session = SessionLocal()

    latest_elo = (
        session.query(TeamEloRating.elo_rating)
        .filter(
            TeamEloRating.team == team,
            TeamEloRating.rating_date <= date
        )
        .order_by(
            TeamEloRating.rating_date.desc()
        )
        .limit(1)
        .scalar()
    )

    return latest_elo

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

MAX_HISTORY = 500

def poll_predict():
    artifact = joblib.load(
        "models/live_odds.pkl"
    )

    live_odds = artifact["model"]

    FEATURES = artifact["features"]

    while True:
        print("Polling...")
        date, games = get_current_games()
        
        if date is None or not games:
            time.sleep(60)
            continue

        features_list = extract_features(date, games)

        if len(features_list) == 0:
            time.sleep(60)
            continue

        live_df = pd.DataFrame([f[3:] for f in features_list], columns=FEATURES)

        pred_probas = live_odds.predict_proba(live_df)[:, 1]

        for features, proba in zip(features_list, pred_probas):
            pred_entry = dict()
            pred_entry['home_team'] = features[1]
            pred_entry['away_team'] = features[2]
            pred_entry['score_diff'] = features[3]
            pred_entry['seconds_remaining'] = features[4]
            pred_entry['last_updated'] = datetime.now(timezone.utc).isoformat()
            pred_entry['probability'] = proba

            with prediction_lock:
                game_id = features[0]
                history = live_predictions[game_id]
                history.append(pred_entry)

                if len(history) > MAX_HISTORY:
                    history.pop(0)
        
        print(live_predictions)

        time.sleep(60)
