import time
import pandas as pd
from requests.exceptions import ReadTimeout, ConnectionError
from nba_api.stats.endpoints import PlayByPlayV3
from nba_api.stats.library.http import NBAStatsHTTP
from app.db.database import SessionLocal, PlayByPlayEvent
from app.services.utility import game_seconds_remaining

NBAStatsHTTP.timeout = 60

class PlayByPlayIngester:
    def __init__(self, game_id: str):
        self.game_id = game_id
        self.home_score = 0
        self.away_score = 0

    def find_game_pbp(self, retries=5) -> pd.DataFrame:
        for attempt in range(retries):
            try:
                pbp = PlayByPlayV3(game_id=self.game_id)
                return pbp.get_data_frames()[0]
            except (ReadTimeout, ConnectionError) as e:
                print(f"Retry {attempt+1}: {e}")
                time.sleep(2)
        return None
    
    def process_event(self, row):
        try:
            home_score = row["scoreHome"]
            if home_score == "":
                self.home_score = self.home_score
            else:
                self.home_score = int(home_score)

            away_score = row["scoreAway"]
            if away_score == "":
                self.away_score = self.away_score
            else:
                self.away_score = int(away_score)

            # print(f'Score: {self.home_score} : {self.away_score}')

            event = PlayByPlayEvent(
                game_id=self.game_id,
                period=row["period"],
                clock=row["clock"],
                seconds_remaining=game_seconds_remaining(
                    row["clock"],
                    row['period']
                ),
                home_score=self.home_score,
                away_score=self.away_score,
                description=row["description"]
            )

            return event
        except Exception as row_error:
            print(f"[{self.game_id}] Failed processing row")
            print(row_error)
            return None

    def store_pbp(self):
        session = SessionLocal()
        existing = (
            session.query(PlayByPlayEvent)
            .filter(PlayByPlayEvent.game_id == self.game_id)
            .first()
        )

        if existing:
            print(f"PBP for game {self.game_id} already stored")
    
        pbp_df = self.find_game_pbp()
        for _, row in pbp_df.iterrows():
            event = self.process_event(row)
            session.merge(event)
        session.commit()

        session.close()
