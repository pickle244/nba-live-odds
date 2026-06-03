from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import declarative_base
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set. Please set it before running this script.")

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
from sqlalchemy import Boolean
from sqlalchemy import Float
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy.sql import func

class Game(Base):

    __tablename__ = "games"

    id = Column(String, primary_key=True)

    season = Column(String)

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

    seconds_remaining = Column(
        Integer,
        nullable=False,
        index=True
    )

    score_diff = Column(
        Integer,
        nullable=False,
        index=True
    )

    elo_diff = Column(
        Float,
        nullable=True,
        index=True
    )

    home_has_possession = Column(
        Boolean,
        nullable=True    # nullable because some events are ambiguous
    )

    home_team_fouls = Column(Integer, nullable=True)

    away_team_fouls = Column(Integer, nullable=True)

    home_in_bonus = Column(Boolean, nullable=True)

    away_in_bonus = Column(Boolean, nullable=True)

    home_in_double_bonus = Column(Boolean, nullable=True)

    away_in_double_bonus = Column(Boolean, nullable=True)

    home_full_timeouts = Column(Integer, nullable=True)

    away_full_timeouts = Column(Integer, nullable=True)

    home_short_timeouts = Column(Integer, nullable=True)

    away_short_timeouts = Column(Integer, nullable=True)

    home_points_last_2min = Column(Integer, nullable=True, default=0)

    away_points_last_2min = Column(Integer, nullable=True, default=0)

    home_win = Column(
        Boolean,
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
        String,
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

class GameOdds(Base):

    __tablename__ = "game_odds"

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

    bookmaker = Column(
        String,
        nullable=False
    )

    fetched_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    home_odds = Column(
        Integer,
        nullable=False
    )

    away_odds = Column(
        Integer,
        nullable=False
    )

    home_implied_prob = Column(
        Float,
        nullable=False
    )

    away_implied_prob = Column(
        Float,
        nullable=False
    )

    is_opening_line = Column(
        Boolean,
        default=False,
        nullable=False
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )