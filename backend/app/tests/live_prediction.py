from app.services.live_prediction import LivePrediction

if __name__ == '__main__':
    date = '2026-04-10'
    lp = LivePrediction(date)
    lp.poll_predict()
