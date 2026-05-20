from nba_api.stats.static import teams

from app.db.database import SessionLocal, Game, TeamEloRating

HOME_ADVANTAGE = 100

def initialize_elos():
    team_list = teams._get_teams()
    team_abbrevs = [team['abbreviation'] for team in team_list]

    elo_ratings = {
        team: 1500 for team in team_abbrevs
    }

    return elo_ratings

def expected_score(rating_a, rating_b):
    return 1 / (1 + 10 ** ((rating_b - rating_a) / 400))

def update_elo(
    rating,
    expected,
    actual,
    k=20
):
    return rating + k * (actual - expected)

def ingest_elos(season: str):
    session = SessionLocal()
    games = (
        session.query(Game)
        .where(Game.season==season)
        .order_by(Game.game_date.asc())
        .all()
    )

    elo_ratings = initialize_elos()

    for game in games:
        home = game.home_team
        away = game.away_team

        home_rating = elo_ratings[home] if home in elo_ratings else None
        away_rating = elo_ratings[away] if away in elo_ratings else None

        if home_rating is not None and away_rating is not None:
            expected_home = expected_score(
                home_rating + HOME_ADVANTAGE,
                away_rating
            )

            expected_away = expected_score(
                away_rating,
                home_rating
            )

            home_won = (
                game.home_score > game.away_score
            )

            actual_home = 1 if home_won else 0
            actual_away = 0 if home_won else 1

            new_home = update_elo(
                home_rating,
                expected_home,
                actual_home
            )

            new_away = update_elo(
                away_rating,
                expected_away,
                actual_away
            )

            elo_ratings[home] = new_home
            elo_ratings[away] = new_away

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
    print(f'ELOs for {season} season ingested')

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
        ingest_elos(season)