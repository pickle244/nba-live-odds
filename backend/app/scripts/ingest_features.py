from app.services.features_service import FeatureIngester

if __name__ == "__main__":
    fi = FeatureIngester()

    fi.store_features()