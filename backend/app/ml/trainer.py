from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GridSearchCV, StratifiedGroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score
import joblib
import datetime
import numpy as np

class Trainer:
    def train(self, X_train, y_train, groups):
        cv = StratifiedGroupKFold(n_splits=10)

        param_grid = {
            "model__C": [0.001, 0.01, 0.1, 1, 10, 100],        # regularization strength
            "model__solver": ["saga"],                           # only solver that supports all penalties
            "model__l1_ratio": [0, 0.25, 0.5, 0.75, 1],               # only used when penalty=elasticnet
            "model__class_weight": [None, "balanced"],           # handles class imbalance
        }

        pipeline = Pipeline([
            ("scaler", StandardScaler()),
            ("model", LogisticRegression(max_iter=1000))
        ])

        searcher = GridSearchCV(
            pipeline,
            param_grid,
            cv=cv,
            verbose=3,
            scoring="roc_auc",
            n_jobs=-1,
        )

        searcher.fit(X_train, y_train, groups=groups)

        print('Search results:')
        print(f'Best params: {searcher.best_params_}')
        print(f'Best score: {searcher.best_score_}')

        best_estimator = searcher.best_estimator_
        date = datetime.datetime.now()
        artifact = {
            "model": best_estimator,
            "features": X_train.columns,
            "date": date
        }

        joblib.dump(
            artifact,
            f"models/model-{date}.pkl"
        )

        return best_estimator
    
    def evaluate(self, best_estimator, X_test, y_test):
        y_pred_probas = best_estimator.predict_proba(X_test)[:, 1]
        aucroc = roc_auc_score(y_test, y_pred_probas)

        probs_sorted = np.sort(y_pred_probas)

        print(f'Five highest probabilities: {probs_sorted[-5:]}')
        print(f'Five lowest probabilities: {probs_sorted[:5]}')

        print(f'Test set AUCROC: {aucroc}')
