"use client";

import { useEffect, useState } from "react";
import ProbabilityChart from "./../../components/ProbabilityChart";
import { Timestamp } from "next/dist/server/lib/cache-handlers/types";
import { use } from "react";

type Game = {
  home_name: string;
  away_name: string;
  probability: number;
  score_diff: number;
  seconds_remaining: number;
  last_updated: Timestamp;
};

export default function GamePage({
  params,
}: {
  params: Promise<{ gameId: string }>;
}) {
  const { gameId } = use(params);
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

  if (!game || game.length === 0) {
    return <p>No data available yet...</p>;
  }

  console.log("gameId:", gameId);
  console.log("game data:", game);

  const last = game[game.length - 1];
  return (
    <main style={{ padding: 20 }}>
      <h1>{last.home_name} vs {last.away_name}</h1>
      
      <ProbabilityChart
        history={game}
      />

      <p>
        Home Team Win Probability: {last.probability}
      </p>

      <p>
        Score Diff: {last.score_diff}
      </p>

      <p>
        Seconds Remaining: {last.seconds_remaining}
      </p>

      <p>
        Last Updated: {last.last_updated}
      </p>
    </main>
  );
}