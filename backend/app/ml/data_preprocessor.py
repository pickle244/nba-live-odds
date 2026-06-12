import pandas as pd
from sklearn.model_selection import GroupShuffleSplit, StratifiedGroupKFold
from app.db.database import engine

class Preprocessor:
    def __init__(self, test_size: float, random_seed: int):
        self.TEST_SIZE = test_size
        self.RANDOM_SEED = random_seed
        self.BOOL_FEATURES = [
            "home_possession",
            "home_in_bonus",
            "away_in_bonus",
        ]

    def get_df(self):
        query = """
        SELECT *
        FROM feature_snapshots
        """

        df = pd.read_sql(query, engine)
        print(f'First five rows of dataset: {df.head()}')
        print(f'Shape of dataset: {df.shape}')
        print(f'Colums of dataset: {df.columns}')

        return df

    def ensure_numeric_cols(self, X):
        X = X.copy()
        for col in self.BOOL_FEATURES:
            if col in X.columns:
                X[col] = X[col].fillna(False).astype('float')  # float preserves NaN, int doesn't

        X_numeric = X.select_dtypes(include=['number', 'bool']).copy()
        bool_cols = X_numeric.select_dtypes(include=['bool']).columns
        if len(bool_cols):
            X_numeric[bool_cols] = X_numeric[bool_cols].astype(int)

        return X_numeric
    
    def get_features(self, df: pd.DataFrame):
        X = df.drop(columns=[
            'id',
            'game_id',
            'created_at',
            'home_win'])
        print(f'Features: {X.columns}')
        y = df["home_win"]
        
        return X, y

    def splits(self, X, y, groups):
        sgkf = GroupShuffleSplit(n_splits=1, test_size=self.TEST_SIZE, random_state=self.RANDOM_SEED)
        train_idx, test_idx = next(sgkf.split(X, y, groups=groups))

        return train_idx, test_idx