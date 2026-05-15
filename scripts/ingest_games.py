from nba_api.stats.endpoints import leaguegamefinder
import pandas as pd

def find_season_games(season: str) -> pd.DataFrame:
    games = leaguegamefinder.LeagueGameFinder(
        season_nullable=season
    )

    games_df = games.get_data_frames()[0]

    print(games_df.head())

    return games_df

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from database import SessionLocal
from database import Game

def ingest_season_games(season: str):
    games_df = find_season_games(season)

    session = SessionLocal()

    for _, row in games_df.iterrows():

        game = Game(
            id=row["GAME_ID"],
            season=season,
            home_team=row["MATCHUP"],
            away_team="TODO"
        )

        session.merge(game)

    session.commit()