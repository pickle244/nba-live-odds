# nba-live-odds

Author: Jeffrey Li

Purpose: a web app that displays live winning odds for NBA games.

Design: historical game and play-by-play was collected using swar's nba_api to
engineer features such as score differential, time remaining, possession, and
foul and timeout counts. These features were used to train a Logistic Regression
model that outputs predictions as the probability that the home team wins. A
webapp was made using Next.js and FastAPI to display relevant stats and 
graph the changes in odds as games progress.