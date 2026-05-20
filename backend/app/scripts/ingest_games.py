import re

import pandas as pd

from nba_api.stats.endpoints import leaguegamefinder

from app.db.database import SessionLocal, Game

def find_season_games(season: str) -> pd.DataFrame:
    games = leaguegamefinder.LeagueGameFinder(
        season_type_nullable=['Regular Season','Playoffs'],
        season_nullable=season
    )

    games_df = games.get_data_frames()[0]

    return games_df

def ingest_season_games(season: str):
    games_df = find_season_games(season)

    # Remove duplicate rows for the same GAME_ID before merging.
    # The NBA API often returns one row per team in the same game.
    games_df = games_df.drop_duplicates(subset=["GAME_ID"], keep="last")

    session = SessionLocal()

    try:
        pattern = r"(?:vs\.|@)\s+([A-Z]{3})"
        for _, row in games_df.iterrows():
            home_team = row["TEAM_ABBREVIATION"]
            away_team = re.search(pattern, row['MATCHUP']).group(1)
            home_score = row['PTS']
            away_score = home_score - row['PLUS_MINUS']
            game = Game(
                id=str(row["GAME_ID"]),
                season=season,
                game_date=row['GAME_DATE'],
                home_team=home_team,
                away_team=away_team,
                home_score=home_score,
                away_score=away_score,
                winner=home_team if home_score > away_score else away_team
            )
            # merge() handles insert or update automatically
            session.merge(game)

        session.commit()

        print(f'{season} season ingested')
    except Exception as e:
        session.rollback()
        print(f"Error ingesting {season}: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    seasons = [
        # '2020-21', 
        # '2021-22',
        # '2022-23',
        # '2023-24',
        '2024-25',
        '2025-26'
    ]

    for season in seasons:
        ingest_season_games(season)
