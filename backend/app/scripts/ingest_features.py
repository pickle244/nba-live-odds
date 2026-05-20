from app.db.database import SessionLocal, Game, PlayByPlayEvent, FeatureSnapshot, TeamEloRating

def get_games():
    session = SessionLocal()
    games = (
        session.query(Game)
        .order_by(Game.game_date.asc())
        .all()
    )

    return games

def ingest_features():
    games = get_games()

    session = SessionLocal()
    for i, game in enumerate(games):
        existing = (
            session.query(FeatureSnapshot)
            .filter(FeatureSnapshot.game_id == game.id)
            .first()
        )

        if existing:
            print(f"Skipping already ingested game {game.id}")
            continue
        
        eventual_winner = game.winner
        
        home_elo = (
            session.query(TeamEloRating.elo_rating)
            .where(
                TeamEloRating.team == game.home_team,
                TeamEloRating.rating_date <= game.game_date
            )
            .order_by(
                TeamEloRating.rating_date.desc()
            )
            .limit(1)
            .scalar()
        )

        away_elo = (
            session.query(TeamEloRating.elo_rating)
            .where(
                TeamEloRating.team == game.away_team,
                TeamEloRating.rating_date <= game.game_date
            )
            .order_by(
                TeamEloRating.rating_date.desc()
            )
            .limit(1)
            .scalar()
        )

        elo_diff = home_elo - away_elo

        snapshots = []

        events = (
            session.query(PlayByPlayEvent)
            .filter_by(game_id=game.id)
            .all()
        )

        for event in events:
            score_diff = (event.home_score - event.away_score)

            seconds_remaining = (
                (4 - event.period) * 720
                + event.seconds_remaining
            )

            snapshot = FeatureSnapshot(
                game_id=game.id,
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
        print(f'Features for game {game.id} ingested ({i + 1} / {len(games)})')

if __name__ == "__main__":
    ingest_features()