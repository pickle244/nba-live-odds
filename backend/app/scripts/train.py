from app.ml.data_preprocessor import Preprocessor
from app.ml.trainer import Trainer

if __name__ == "__main__":
    pp = Preprocessor(test_size=0.2, random_seed=42)
    df = pp.get_df()
    X, y = pp.get_features(df)
    X = pp.ensure_numeric_cols(X)
    print(f'Features: {X.columns}')
    groups = df['game_id']
    train_idx, test_idx = pp.splits(X, y, groups)

    X_train = X.iloc[train_idx]
    X_test = X.iloc[test_idx]
    y_train = y.iloc[train_idx]
    y_test = y.iloc[test_idx]

    trainer = Trainer()
    best_model = trainer.train(X_train, y_train, groups.iloc[train_idx])
    trainer.evaluate(best_model, X_test, y_test)
