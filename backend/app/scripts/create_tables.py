from app.db.database import engine
from app.db.database import Base

if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    print("Tables created")
    