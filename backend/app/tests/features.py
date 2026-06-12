from app.services.features_service import FeatureIngester, Game, SessionLocal
from app.services.utility import get_game_pbp
from sqlalchemy import inspect
from app.db.database import FeatureSnapshot

if __name__ == '__main__':
    
    
    game_ids = [
        # '0022501187',
        # '0022501193',
        '0022500002'
    ]

    session = SessionLocal()

    for i, id in enumerate(game_ids):
        game = (
            session.query(Game)
            .filter(Game.id == id)
            .first()
        )
        events = get_game_pbp(game.id)
        fi = FeatureIngester(id)
        fi.create_snapshots(events, game)
        print(f'Snapshots for game {id} created ({i + 1} / {len(game_ids)})')

    inspector = inspect(FeatureSnapshot)
    print([c.key for c in inspector.mapper.column_attrs])
