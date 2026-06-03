import re
from app.db.database import SessionLocal, Game, PlayByPlayEvent

def clock_to_seconds(clock):
    if not clock:
        return None

    match = re.match(r"PT(\d+)M([\d.]+)S", clock)

    minutes = int(match.group(1))
    seconds = float(match.group(2))

    return minutes * 60 + seconds

def game_seconds_remaining(clock, period):
    seconds_on_clock = clock_to_seconds(clock)
    if seconds_on_clock is None:
        return None
    return (4 - period) * 720 + seconds_on_clock

def get_games():
    session = SessionLocal()
    games = (
        session.query(Game)
        .order_by(Game.game_date.asc())
        .all()
    )

    session.close()

    return games

def get_game_pbp(game_id):
    session = SessionLocal()
    events = (
        session.query(PlayByPlayEvent)
        .filter_by(game_id=game_id)
        .order_by(PlayByPlayEvent.seconds_remaining.desc())
        .all()
    )

    session.close()
    return events