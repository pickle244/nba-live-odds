from nba_api.stats.static import teams
from app.db.database import SessionLocal, TeamEloRating
from app.services.utility import get_games

class EloIngester:
    def __init__(self):
        team_list = teams._get_teams()
        team_abbrevs = [team['abbreviation'] for team in team_list]

        self.elo_ratings = {
            team: 1500 for team in team_abbrevs
        }

        self.HOME_ADVANTAGE = 100

    def expected_score(self, rating_a, rating_b):
        return 1 / (1 + 10 ** ((rating_b - rating_a) / 400))

    def update_elo(
        self,
        rating,
        expected,
        actual,
        k=20
    ):
        return rating + k * (actual - expected)

    def ingest_elo(self):
        session = SessionLocal()
        games = get_games()

        for game in games:
            home = game.home_team
            away = game.away_team

            home_rating = self.elo_ratings[home] if home in self.elo_ratings else None
            away_rating = self.elo_ratings[away] if away in self.elo_ratings else None

            if home_rating is not None and away_rating is not None:
                expected_home = self.expected_score(
                    home_rating + self.HOME_ADVANTAGE,
                    away_rating
                )

                expected_away = self.expected_score(
                    away_rating,
                    home_rating
                )

                home_won = (
                    game.home_score > game.away_score
                )

                actual_home = 1 if home_won else 0
                actual_away = 0 if home_won else 1

                new_home = self.update_elo(
                    home_rating,
                    expected_home,
                    actual_home
                )

                new_away = self.update_elo(
                    away_rating,
                    expected_away,
                    actual_away
                )

                self.elo_ratings[home] = new_home
                self.elo_ratings[away] = new_away

                home_entry = TeamEloRating(
                    season=game.season,
                    team=home,
                    rating_date=game.game_date,
                    elo_rating=new_home
                )

                away_entry = TeamEloRating(
                    season=game.season,
                    team=away,
                    rating_date=game.game_date,
                    elo_rating=new_away
                )

                session.add(home_entry)
                session.add(away_entry)

        session.commit()
        print(f'ELOs ingested')
