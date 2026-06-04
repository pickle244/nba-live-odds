import time
from datetime import datetime
from threading import Lock
from collections import defaultdict
import pandas as pd
import numpy as np
import joblib
from nba_api.stats.endpoints import ScoreboardV3
from nba_api.live.nba.endpoints import playbyplay
from app.db.database import SessionLocal, TeamEloRating
from app.services.utility import game_seconds_remaining
from app.services.features_service import FeatureIngester
from app.services.pbp_service import PlayByPlayIngester
import os
import glob
import pytz
import httpx

eastern = pytz.timezone("US/Eastern")
prediction_lock = Lock()

class LivePrediction:
    def __init__(self, game_date):
        self.game_date = game_date
        self.MAX_HISTORY = 500
        artifact = self.load_latest_model()
        self.model = artifact["model"]
        self.FEATURES = artifact["features"]
        self.timeout = 60
        self.live_predictions = defaultdict(list)

    def load_latest_model(self, model_dir: str = "models") -> dict:
        pattern = os.path.join(model_dir, "*.pkl")
        files = glob.glob(pattern)

        if not files:
            raise FileNotFoundError(f"No models found in {model_dir}")

        latest = max(files, key=os.path.getmtime)
        print(f"Loading model: {latest}")

        return joblib.load(latest)

    def get_current_games(self):
        try:
            board = ScoreboardV3(game_date=self.game_date).get_dict()
            games = board['scoreboard']['games']
            for game in board['scoreboard']['games']:
                print(game['gameId'], game['gameStatus'], game['gameStatusText'])

            if not games:
                print("No live games found")
                return []

            return games
        except Exception as e:
            print(f"NBA API error: {e}")
            return []

    def latest_team_elo(self, team):
        session = SessionLocal()

        latest_elo = (
            session.query(TeamEloRating.elo_rating)
            .filter(
                TeamEloRating.team == team,
                TeamEloRating.rating_date <= self.game_date
            )
            .order_by(
                TeamEloRating.rating_date.desc()
            )
            .limit(1)
            .scalar()
        )

        session.close()
        return latest_elo
    
    def parse_score(self, score_str):
        return 0 if score_str == '' else int(score_str)
    
    def get_live_pbp(self, game_id: str) -> list[dict]:
        url = f"https://cdn.nba.com/static/json/liveData/playbyplay/playbyplay_{game_id}.json"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Referer": "https://www.nba.com/",
            "Origin": "https://www.nba.com",
            "Accept": "application/json",
        }
        r = httpx.get(url, headers=headers)
        r.raise_for_status()
        return r.json()["game"]["actions"]

    def extract_features(self, games):
        features_list = []

        pbpi = PlayByPlayIngester()
        fi = FeatureIngester()
        for game in games:
            game_id = game['gameId']
            print(f'Extracting features for game {game_id}')

            home_team = game['homeTeam']
            away_team = game['awayTeam']

            home_name = home_team['teamTricode']
            away_name = away_team['teamTricode']

            home_elo = self.latest_team_elo(home_name)
            away_elo = self.latest_team_elo(away_name)
            if home_elo == None or away_elo == None:
                print(f'Home/away ELO for game {game_id} not found')
                continue
            elo_diff = home_elo - away_elo
            
            actions = self.get_live_pbp("0042500401")
            if not actions:
                print(f'No events found for game {game_id}')
                return None
            
            latest = actions[-1]

            latest_home_score = self.parse_score(latest['scoreHome'])
            latest_away_score = self.parse_score(latest['scoreAway'])
            score_diff = latest_home_score - latest_away_score

            period = latest['period']
            seconds_remaining = game_seconds_remaining(latest['clock'], period)
            if seconds_remaining is None:
                print(f'Clock for game {game_id} not found')
                return None

            desc = latest['description']
            home_roster = fi.get_home_players(game_id)

            home_possession = fi.infer_possession(desc, home_roster, home_name)
            if home_possession is None:
                home_possession = False

            fouls_dict = fi.parse_fouls(desc, home_roster)
            timeouts_dict = fi.parse_timeouts(desc, home_name)

            window_seconds = seconds_remaining + 120
            home_points_last_2min = 0
            away_points_last_2min = 0

            for prev in reversed(actions[:-1]):
                prev_home_score = self.parse_score(prev['scoreHome'])
                prev_away_score = self.parse_score(prev['scoreAway'])
                home_points_last_2min = latest_home_score - prev_home_score
                away_points_last_2min = latest_away_score - prev_away_score

                prev_period = prev['period']
                prev_seconds_remaining = game_seconds_remaining(prev['clock'], prev_period)
                if prev_seconds_remaining is None:
                    continue
                prev_seconds = (4 - prev_period) * 720 + prev_seconds_remaining
                if prev_seconds > window_seconds:
                    break

            features_list.append(
                {
                    'game_id': game_id, 
                    'home_name': home_name, 
                    'away_name': away_name, 
                    'seconds_remaining': seconds_remaining, 
                    'score_diff': score_diff, 
                    'elo_diff': elo_diff,
                    'home_possession': home_possession,
                    'home_team_fouls': fouls_dict['home_team_fouls'],
                    'away_team_fouls': fouls_dict['away_team_fouls'],
                    'home_in_bonus': fouls_dict['home_in_bonus'],
                    'away_in_bonus': fouls_dict['away_in_bonus'],
                    'home_in_double_bonus': fouls_dict['home_in_double_bonus'],
                    'away_in_double_bonus': fouls_dict['away_in_double_bonus'],
                    'home_full_timeouts': timeouts_dict['home_full_timeouts'],
                    'away_full_timeouts': timeouts_dict['away_full_timeouts'],
                    'home_short_timeouts': timeouts_dict['home_short_timeouts'],
                    'away_short_timeouts': timeouts_dict['away_short_timeouts'],
                    'home_points_last_2min': home_points_last_2min,
                    'away_points_last_2min': away_points_last_2min,
                }
            )
        
        return features_list

    def self_ping(self):
        try:
            httpx.get("https://nba-live-odds-rho.vercel.app/health", timeout=10)
            print("Pinged self")
        except Exception as e:
            print(f"Self-ping failed: {e}")

    def postprocess(self, probas: np.ndarray, df: pd.DataFrame) -> np.ndarray:
        result = probas.copy()

        game_over = df["seconds_remaining"] <= 0
        home_won = df["score_diff"] > 0
        home_lost = df["score_diff"] < 0

        result[game_over & home_won] = 1.0
        result[game_over & home_lost] = 0.0

        return result

    def poll_predict(self):
        while True:
            self.self_ping()
            print(f"Polling for games on {self.game_date}")
            games = self.get_current_games()
            
            if not games:
                print(f'No games found on {self.game_date}')
                time.sleep(self.timeout)
                continue

            features_list = self.extract_features(games)
            if not features_list:
                print('Unable to extract features')
                time.sleep(self.timeout)
                continue
            
            live_df = pd.DataFrame([list(f.values())[3:] for f in features_list], columns=self.FEATURES)
            pred_probas = self.model.predict_proba(live_df)[:, 1]
            pred_probas = self.postprocess(pred_probas, live_df)
            for features, proba in zip(features_list, pred_probas):
                pred_entry = dict()
                pred_entry['home_name'] = features['home_name']
                pred_entry['away_name'] = features['away_name']
                pred_entry['score_diff'] = features['score_diff']
                pred_entry['seconds_remaining'] = features['seconds_remaining']
                pred_entry['home_team_fouls'] = features['home_team_fouls']
                pred_entry['away_team_fouls'] = features['away_team_fouls']
                pred_entry['home_team_timeouts'] = features['home_full_timeouts'] + features['home_short_timeouts']
                pred_entry['away_team_timeouts'] = features['away_full_timeouts'] + features['away_short_timeouts']
                pred_entry['last_updated'] = datetime.now(eastern).isoformat()
                pred_entry['probability'] = proba
                print(pred_entry)

                with prediction_lock:
                    game_id = features['game_id']
                    history = self.live_predictions[game_id]
                    history.append(pred_entry)
                    if len(history) > self.MAX_HISTORY:
                        history.pop(0)
                
            time.sleep(self.timeout)
