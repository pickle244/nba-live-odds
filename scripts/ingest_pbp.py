from nba_api.stats.endpoints import playbyplayv3
import pandas as pd
from requests.exceptions import ReadTimeout
from requests.exceptions import ConnectionError
from nba_api.stats.library.http import NBAStatsHTTP

NBAStatsHTTP.timeout = 60

def find_game_pbp(game_id: str, retries=5) -> pd.DataFrame:
    for attempt in range(retries):
        try:
            # print(f'Game {game_id}')
            pbp = playbyplayv3.PlayByPlayV3(game_id=game_id)

            return pbp.get_data_frames()[0]

        except (
            ReadTimeout,
            ConnectionError
        ) as e:
            print(f"Retry {attempt+1}: {e}")

            time.sleep(2)

    return None

import re

def clock_to_seconds(clock):
    match = re.match(r"PT(\d+)M([\d.]+)S", clock)

    minutes = int(match.group(1))
    seconds = float(match.group(2))

    return minutes * 60 + seconds

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from database import SessionLocal
from database import PlayByPlayEvent

def ingest_game_pbp(game_id: str):
    pbp_df = find_game_pbp(game_id)

    session = SessionLocal()

    for _, row in pbp_df.iterrows():
        try:
            home_score = row["scoreHome"]
            away_score = row["scoreAway"]

            event = PlayByPlayEvent(
                game_id=game_id,
                period=row["period"],
                clock=row["clock"],
                seconds_remaining=clock_to_seconds(
                    row["clock"]
                ),
                home_score=(
                    0
                    if home_score == ""
                    else int(home_score)
                ),
                away_score=(
                    0
                    if away_score == ""
                    else int(away_score)
                ),
                description=row["description"]
            )

            session.merge(event)
        except Exception as row_error:
            print(f"[{game_id}] Failed processing row")
            print(row_error)
            continue
        
    session.commit()

from database import Game

import time
if __name__ == "__main__":
    session = SessionLocal()
    games = (
        session.query(Game)
        .all()
    )

    for i, game in enumerate(games):
        existing = (
            session.query(PlayByPlayEvent)
            .filter(PlayByPlayEvent.game_id == game.id)
            .first()
        )

        if existing:
            print(f"Skipping already ingested game {game.id}")
            continue
        
        ingest_game_pbp(game.id)
        print(f"Events for game {game.id} ingested ({i + 1} / {len(games)})")
        time.sleep(1.5)