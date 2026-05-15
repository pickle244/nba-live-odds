from nba_api.stats.endpoints import playbyplayv2
import pandas as pd

def find_game_pbp(game_id: str) -> pd.DataFrame:
    pbp = playbyplayv2.PlayByPlayV2(
        game_id=game_id
    )

    pbp_df = pbp.get_data_frames()[0]

    return pbp_df

def clock_to_seconds(clock):

    minutes, seconds = map(
        int,
        clock.split(":")
    )

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

    scores = pbp_df["SCORE"].str.split(" - ", expand=True)

    pbp_df["home_score"] = pd.to_numeric(scores[0])
    pbp_df["away_score"] = pd.to_numeric(scores[1])

    session = SessionLocal()

    for _, row in pbp_df.iterrows():
        event = PlayByPlayEvent(
            game_id=row["GAME_ID"],
            event_num=row["EVENTNUM"],
            period=row["PERIOD"],
            clock=row["PCTIMESTRING"],
            seconds_remaining=clock_to_seconds(
                row["PCTIMESTRING"]
            ),
            home_score=row['home_score'],
            away_score=row['away_score'],
            description=(
                row["HOMEDESCRIPTION"]
                or row["VISITORDESCRIPTION"]
                or ""
            )
        )

        session.add(event)

    session.commit()