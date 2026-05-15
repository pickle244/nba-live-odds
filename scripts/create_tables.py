import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from database import engine
from database import Base
from database import Game, PlayByPlayEvent, FeatureSnapshot, TeamEloRating

Base.metadata.create_all(bind=engine)

print("Tables created")