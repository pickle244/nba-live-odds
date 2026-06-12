from app.services.pbp_service import PlayByPlayIngester
from app.db.database import SessionLocal, Game

if __name__ == "__main__":
    session = SessionLocal()
    games = (
        session.query(Game)
        .all()
    )

    for i, game in enumerate(games):
        pbpi = PlayByPlayIngester(game.id)
        pbpi.store_pbp()
        print(f"Events for game {game.id} ingested ({i + 1} / {len(games)})")
    
    