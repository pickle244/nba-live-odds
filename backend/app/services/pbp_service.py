import time

import pandas as pd

from requests.exceptions import ReadTimeout, ConnectionError

from nba_api.stats.endpoints import playbyplayv3
from nba_api.stats.library.http import NBAStatsHTTP

from app.db.database import SessionLocal, PlayByPlayEvent, Game
from app.services.utility import clock_to_seconds

NBAStatsHTTP.timeout = 60
class PlayByPlayIngester:
    def find_game_pbp(self, game_id: str, retries=5) -> pd.DataFrame:
        for attempt in range(retries):
            try:
                pbp = playbyplayv3.PlayByPlayV3(game_id=game_id)

                return pbp.get_data_frames()[0]

            except (
                ReadTimeout,
                ConnectionError
            ) as e:
                print(f"Retry {attempt+1}: {e}")

                time.sleep(2)

        return None

    def store_pbp(self):
        session = SessionLocal()
        games = (
            session.query(Game)
            .all()
        )

        for i, game in enumerate(games):
            game_id = game.id
            existing = (
                session.query(PlayByPlayEvent)
                .filter(PlayByPlayEvent.game_id == game_id)
                .first()
            )

            if existing:
                print(f"PBP for game {game_id} already stored")
                continue
        
            pbp_df = self.find_game_pbp(game_id)

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
            print(f"Events for game {game.id} ingested ({i + 1} / {len(games)})")
            time.sleep(1.5)

        session.close()
