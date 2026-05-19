from nba_api.stats.endpoints import playbyplayv3
import pandas as pd

def find_game_pbp(game_id: str) -> pd.DataFrame:
    try:
        pbp = playbyplayv3.PlayByPlayV3(
            game_id=game_id
        )

        pbp_df = pbp.get_data_frames()[0]

        return pbp_df

    except Exception as e:
        print(f"Failed for {game_id}")
        print(e)

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
        home_score = row['scoreHome']
        away_score = row['scoreAway']
        event = PlayByPlayEvent(
            game_id=game_id,
            period=row["period"],
            clock=row["clock"],
            seconds_remaining=clock_to_seconds(
                row["clock"]
            ),
            home_score=0 if home_score == '' else int(home_score),
            away_score=0 if away_score == '' else int(away_score),
            description=(
                row["description"]
            )
        )

        session.merge(event)

    session.commit()
    print(f'Events for game {game_id} ingested')

from database import Game

session = SessionLocal()
games = (
    session.query(Game)
    .all()
)

import time
if __name__ == "__main__":
    for game in games:
        ingest_game_pbp(game.id)
        time.sleep(1.0)