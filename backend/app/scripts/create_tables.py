from app.db.database import engine
from app.db.database import Base

Base.metadata.create_all(bind=engine)

print("Tables created")