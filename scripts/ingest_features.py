import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from database import SessionLocal
from database import Game, PlayByPlayEvent, FeatureSnapshot, TeamEloRating
import pandas as pd

def get_season_games(season):
    session = SessionLocal()
    games = (
        session.query(Game)
        .where(Game.season==season)
        .order_by(Game.game_date.asc())
        .all()
    )

    return games

def ingest_features(season):
    games = get_season_games(season)

    session = SessionLocal()
    for game in games:
        events = (
            session.query(PlayByPlayEvent)
            .filter_by(game_id=game.id)
            .order_by(
                PlayByPlayEvent.event_num.asc()
            )
            .all()
        )

        eventual_winner = (
            game.home_team
            if game.home_score > game.away_score
            else game.away_team
        )
        
        home_elo = (
            session.query(TeamEloRating)
            .where(
                TeamEloRating.team==game.home_team & 
                TeamEloRating.rating_date==game.game_date
            )
        )

        away_elo = (
            session.query(TeamEloRating)
            .where(
                TeamEloRating.team==game.away_team & 
                TeamEloRating.rating_date==game.game_date
            )
        )

        elo_diff = home_elo - away_elo

        snapshots = []

        for event in events:
            score_diff = (
                event.home_score
                - event.away_score
            )

            seconds_remaining = (
                (4 - event.period) * 720
                + event.seconds_remaining
            )

            snapshot = FeatureSnapshot(

                game_id=game.id,

                event_num=event.event_num,

                season=game.season,

                period=event.period,

                seconds_remaining=seconds_remaining,

                home_score=event.home_score,
                away_score=event.away_score,

                score_diff=score_diff,

                home_elo=home_elo,
                away_elo=away_elo,

                elo_diff=elo_diff,

                eventual_winner=eventual_winner
            )

            snapshots.append(snapshot)
        session.bulk_save_objects(snapshots)

        session.commit()