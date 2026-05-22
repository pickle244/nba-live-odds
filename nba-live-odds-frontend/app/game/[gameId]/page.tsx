"use client";

import { useEffect, useState } from "react";
import ProbabilityChart from "./../../components/ProbabilityChart";
import { Timestamp } from "next/dist/server/lib/cache-handlers/types";

type Game = {
  home_team: string;
  away_team: string;
  probability: number;
  score_diff: number;
  seconds_remaining: number;
  last_updated: Timestamp;
};

export default function GamePage({
  params
}: any) {
  const { gameId } = params;
  const [game, setGame] = useState<Game[] | null>(null);

  useEffect(() => {
    async function fetchGame() {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/games/${gameId}`
      );

      const json = await res.json();

      setGame(json);
    }

    fetchGame();

  }, [gameId]);

  if (!game) {
    return <p>Loading...</p>;
  }

  return (
    <main style={{ padding: 20 }}>
      <h1>{game[-1].home_team} vs {game[-1].away_team}</h1>
      
      <ProbabilityChart
        history={game}
      />

      <p>
        Home Team Win Probability: {game[-1].probability}
      </p>

      <p>
        Score Diff: {game[-1].score_diff}
      </p>

      <p>
        Seconds Remaining: {game[-1].seconds_remaining}
      </p>

      <p>
        Last Updated: {game[-1].last_updated}
      </p>
    </main>
  );
}