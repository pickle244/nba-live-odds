"use client";

import { useEffect, useState } from "react";
import Link from 'next/link';

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
        Object.entries(data).map(([gameId, game]: any) => {

          const last = game[game.length - 1];

          if (!last) return null;

          return (
            <Link href={`/game/${gameId}`} key={gameId}>
              <div style={{ marginBottom: 20, cursor: "pointer" }}>

                <h3>
                  {last.home_team} vs {last.away_team}
                </h3>

                <p>
                  Home Team Win Probability: {last.probability}
                </p>

                <p>
                  Score Diff: {last.score_diff}
                </p>

                <p>
                  Seconds Remaining: {last.seconds_remaining}
                </p>

              </div>
            </Link>
          );
        })
      )}

    </main>
  );
}