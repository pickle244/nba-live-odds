import httpx
import pandas as pd
import kagglehub
from kagglehub import KaggleDatasetAdapter
import os
from dotenv import load_dotenv
from app.db.database import SessionLocal, Game, GameOdds
from sqlalchemy.sql import func

class OddsService:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = httpx.Client()
        self.base_url = "https://api.the-odds-api.com/v4"
        self.abbrevs_map = {
            'sa': 'SAS',
            'gs': 'GSW',
            'lal': 'LAL',
            'tor': 'TOR',
            'ind': 'IND',
            'orl': 'ORL',
            'bkn': 'BKN',
            'cle': 'CLE',
            'mem': 'MEM',
            'no': 'NOP',
            'den': 'DEN',
            'mia': 'MIA',
            'utah': 'UTA',
            'okc': 'OKC',
            'cha': 'CHA',
            'atl': 'ATL',
            'bos': 'BOS',
            'min': 'MIN',
            'chi': 'CHI',
            'phx': 'PHX',
            'lac': 'LAC',
            'phi': 'PHI',
            'wsh': 'WAS',
            'mil': 'MIL',
            'hou': 'HOU',
            'dal': 'DAL',
            'ny': 'NYK',
            'det': 'DET',
            'sac': 'SAC',
            'por': 'POR'
        }
    
    def get_db(self):
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    def load_betting_data(self):
        # Set the path to the file you'd like to load
        file_path = "nba_2008-2025.csv"

        # Load the latest version
        df = kagglehub.dataset_load(
          KaggleDatasetAdapter.PANDAS,
          "cviaxmiwnptr/nba-betting-data-october-2007-to-june-2024",
          file_path,
        )

        print(f'Columns: {df.columns}')
        print("First 5 records:", df.head())

        return df

    def fetch_nba_odds(self) -> list[dict]:
        url = f"{self.base_url}/sports/basketball_nba/odds"
        params = {
            "apiKey": self.api_key,
            "regions": "us",
            "markets": "h2h",          # moneyline
            "oddsFormat": "american",
            "dateFormat": "iso",
        }
        with self.client as client:
            r = client.get(url, params=params)
            r.raise_for_status()
            res = r.json()
            print(res)
            return res

    def store(self, odds: pd.DataFrame) -> None:
        """Vig-strip and upsert 2024-25 season odds into game_odds table."""

        # Filter to 2024-25 season only
        df = odds[odds["season"] == 2023].copy()
        df['home'] = df['home'].replace(self.abbrevs_map)
        df['away'] = df['away'].replace(self.abbrevs_map)

        print(df.shape)
        print(df.head())

        print('Number of missing values:')
        print(f'moneyline_home: {df['moneyline_home'].isna().sum()}')
        print(f'moneyline_away: {df['moneyline_away'].isna().sum()}')

        # Drop rows with missing moneylines
        df = df.dropna(subset=["moneyline_home", "moneyline_away"])

        return
        db = SessionLocal()
        
        try:
            inserted = 0
            skipped = 0

            for _, row in df.iterrows():
                # Match to your game by date + home + away team
                game_date = pd.to_datetime(row["date"]).date()

                game = db.query(Game).filter(
                    func.date(Game.game_date) == game_date,
                    Game.home_team == row["home"].upper(),
                    Game.away_team == row["away"].upper()
                ).first()

                if not game:
                    skipped += 1
                    continue

                # Skip if already stored for this game + bookmaker
                existing = db.query(GameOdds).filter(
                    GameOdds.game_id == game.id,
                    GameOdds.bookmaker == "kaggle_historical"
                ).first()

                if existing:
                    skipped += 1
                    continue

                # Vig-strip
                home_implied, away_implied = self.remove_vig(
                    int(row["moneyline_home"]),
                    int(row["moneyline_away"])
                )

                db.add(GameOdds(
                    game_id=game.id,
                    bookmaker="kaggle_historical",
                    home_odds=int(row["moneyline_home"]),
                    away_odds=int(row["moneyline_away"]),
                    home_implied_prob=home_implied,
                    away_implied_prob=away_implied,
                    is_opening_line=True
                ))
                inserted += 1

            db.commit()
            print(f"Done — inserted: {inserted}, skipped: {skipped}")

        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def poll_and_store(self) -> None:
        """Scheduled job: fetch + store in one call."""
        odds = self.fetch_current()
        self.store(odds)

    def get_opening_lines(self, game_ids: list[str]) -> pd.DataFrame:
        """Feature engineering hook — returns vig-stripped probs for training."""
        ...

    def close(self):
        self.client.aclose()

if __name__ == "__main__":
    load_dotenv()
    ODDS_API_KEY = os.getenv("ODDS_API_KEY")
    odds = OddsService(ODDS_API_KEY)
    df = odds.load_betting_data()
    res = odds.fetch_nba_odds()
    odds.store(df)
