from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import declarative_base
import os

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False
)

Base = declarative_base()

from sqlalchemy import Column
from sqlalchemy import String
from sqlalchemy import Integer
from sqlalchemy import Float
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy.sql import func

class Game(Base):

    __tablename__ = "games"

    id = Column(String, primary_key=True)

    season = Column(Integer)

    game_date = Column(DateTime)

    home_team = Column(String)
    away_team = Column(String)

    home_score = Column(Integer)
    away_score = Column(Integer)

    winner = Column(String)

class PlayByPlayEvent(Base):

    __tablename__ = "play_by_play_events"

    id = Column(Integer, primary_key=True)

    game_id = Column(
        String,
        ForeignKey("games.id")
    )

    event_num = Column(Integer)

    period = Column(Integer)

    clock = Column(String)

    seconds_remaining = Column(Integer)

    home_score = Column(Integer)
    away_score = Column(Integer)

    description = Column(String)

class FeatureSnapshot(Base):

    __tablename__ = "feature_snapshots"

    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    game_id = Column(
        String,
        ForeignKey("games.id"),
        nullable=False,
        index=True
    )

    event_num = Column(
        Integer,
        nullable=False
    )

    season = Column(
        Integer,
        nullable=False,
        index=True
    )

    period = Column(
        Integer,
        nullable=False
    )

    seconds_remaining = Column(
        Integer,
        nullable=False,
        index=True
    )

    home_score = Column(
        Integer,
        nullable=False
    )

    away_score = Column(
        Integer,
        nullable=False
    )

    score_diff = Column(
        Integer,
        nullable=False,
        index=True
    )

    home_elo = Column(
        Float,
        nullable=True
    )

    away_elo = Column(
        Float,
        nullable=True
    )

    elo_diff = Column(
        Float,
        nullable=True,
        index=True
    )

    eventual_winner = Column(
        String,
        nullable=False,
        index=True
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

class TeamEloRating(Base):

    __tablename__ = "team_elo_ratings"

    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    season = Column(
        Integer,
        nullable=False,
        index=True
    )

    team = Column(
        String,
        nullable=False,
        index=True
    )

    rating_date = Column(
        DateTime,
        nullable=False,
        index=True
    )

    elo_rating = Column(
        Float,
        nullable=False,
        index=True
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )