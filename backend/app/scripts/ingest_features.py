from app.services.features_service import FeatureIngester
from app.services.utility import get_games

if __name__ == "__main__":
    games = get_games()
    for i, game in enumerate(games):
        fi = FeatureIngester(game.id)
        fi.store_features()
        print(f'Features for game {game.id} ingested ({i + 1} / {len(games)})')
    