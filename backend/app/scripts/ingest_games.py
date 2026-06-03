from app.services.games_service import GameIngester

if __name__ == "__main__":
    gi = GameIngester([
        '2025-26'
    ])

    gi.store_season_games()
