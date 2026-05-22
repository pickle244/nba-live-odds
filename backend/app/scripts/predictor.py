import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
import joblib

from app.db.database import engine

def get_df():
    query = """
    SELECT *
    FROM feature_snapshots
    """

    df = pd.read_sql(query, engine)

    print(df.head())

    print(df.columns)

    return df

def preprocess_df(df):
    df = df.copy()

    df["final_home_score"] = (
        df.groupby("game_id")["home_score"]
        .transform("last")
    )

    df["final_away_score"] = (
        df.groupby("game_id")["away_score"]
        .transform("last")
    )

    df["home_win"] = (df["final_home_score"] > df["final_away_score"]).astype(int)

    df = df.drop(
        columns=[
            'id',
            'season', 
            'period', 
            'home_score', 
            'away_score', 
            'home_elo', 
            'away_elo', 
            'eventual_winner', 
            'created_at',
            'final_home_score',
            'final_away_score'
        ]
    )

    return df

def split_df(df, test_size, random_seed):
    game_ids = df["game_id"].unique()

    train_games, test_games = train_test_split(
        game_ids,
        test_size=test_size,
        random_state=random_seed
    )

    train_df = df[
        df["game_id"].isin(train_games)
    ]

    test_df = df[
        df["game_id"].isin(test_games)
    ]

    print(train_df.head())

    print(test_df.head())

    return train_df, test_df

TEST_SIZE = 0.2
RANDOM_SEED = 42
FEATURES = [
    "score_diff",
    "seconds_remaining",
    "elo_diff",
]

if __name__ == "__main__":
    df = get_df()
    print(f'Shape of dataset: {df.shape}')

    df = preprocess_df(df)
    
    train_df, test_df = split_df(df, TEST_SIZE, RANDOM_SEED)

    X_train = train_df[FEATURES]
    print(f'Shape of training set: {X_train.shape}')
    y_train = train_df["home_win"]

    X_test = test_df[FEATURES]
    print(f'Shape of test set: {X_test.shape}')
    y_test = test_df["home_win"]

    live_odds = LogisticRegression()

    live_odds.fit(X_train, y_train)

    artifact = {
        "model": live_odds,
        "features": FEATURES
    }

    joblib.dump(
        artifact,
        "models/live_odds.pkl"
    )

    home_win_probs = live_odds.predict_proba(X_test)[:, 1]
    
    probs_sorted = np.sort(home_win_probs)

    print(f'Five highest probabilities: {probs_sorted[-5:]}')
    print(f'Five lowest probabilities: {probs_sorted[:5]}')

    aucroc = roc_auc_score(
        y_test,
        home_win_probs
    )

    print(f'Test set AUCROC: {aucroc}')
