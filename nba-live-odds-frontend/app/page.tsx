"use client";

import { useEffect, useState } from "react";

export default function Home() {

  const [data, setData] = useState<any>({});

  async function fetchOdds() {

    const res = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL}/live_predictions`
    );

    const json = await res.json();

    setData(json);
  }

  useEffect(() => {

    fetchOdds();

    const interval = setInterval(fetchOdds, 10000);

    return () => clearInterval(interval);

  }, []);

  return (
    <main style={{ padding: 20 }}>

      <h1>NBA Live Odds</h1>

      {Object.keys(data || {}).length === 0 ? (
        <p>No live games</p>
      ) : (
        Object.entries(data).map(([gameId, game]: any) => (
          <div key={gameId} style={{ marginBottom: 20 }}>
            <h3>{game.home_team} vs {game.away_team}</h3>

            <p>
              Win Probability: {game.home_win_probability}
            </p>

            <p>
              Score Diff: {game.score_diff}
            </p>
          </div>
        ))
      )}

    </main>
  );
}