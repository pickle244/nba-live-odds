from app.services.pbp_service import PlayByPlayIngester

if __name__ == "__main__":
    pbpi = PlayByPlayIngester()

    pbpi.store_pbp()
    