import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from database import engine
import pandas as pd

FEATURES = [
    "score_diff",
    "seconds_remaining",
    "elo_diff",
]

def get_df():
    query = """
    SELECT *
    FROM feature_snapshots
    """

    df = pd.read_sql(query, engine)

    df["home_win"] = (
        df["eventual_winner"]
        == df["home_team"]
    ).astype(int)

    return df

from sklearn.model_selection import train_test_split

TEST_SIZE = 0.2
RANDOM_STATE = 42

def split_df(df):
    game_ids = df["game_id"].unique()

    train_games, test_games = train_test_split(
        game_ids,
        test_size=TEST_SIZE,
        random_state=RANDOM_STATE
    )

    train_df = df[
        df["game_id"].isin(train_games)
    ]

    test_df = df[
        df["game_id"].isin(test_games)
    ]

    X_train = train_df[FEATURES]
    y_train = train_df["home_win"]

    X_test = test_df[FEATURES]
    y_test = test_df["home_win"]

    return X_train, y_train, X_test, y_test

from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

def get_results():
    df = get_df()
    X_train, y_train, X_test, y_test = split_df(df)

    model = LogisticRegression()

    model.fit(X_train, y_train)

    home_win_probs = model.predict_proba(X_test)[:, 1]

    aucroc = roc_auc_score(
        y_test,
        home_win_probs
    )

    return home_win_probs, aucroc

home_win_probs, aucroc = get_results()

print(f'Test AUCROC: {aucroc}')
