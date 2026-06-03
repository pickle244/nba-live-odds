from app.services.elo_service import EloIngester

if __name__ == "__main__":
    ei = EloIngester()

    ei.ingest_elo()