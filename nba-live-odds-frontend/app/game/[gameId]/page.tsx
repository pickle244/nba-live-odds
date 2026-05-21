"use client";

import { useEffect, useState } from "react";

type Game = {
  home_team: string;
  away_team: string;
  home_win_probability: number;
  score_diff: number;
  seconds_remaining: number;
};

export default function GamePage({
  params
}: any) {
  const { gameId } = params;
  const [game, setGame] = useState<Game | null>(null);

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
      <h1>
        {game.home_team}
        vs
        {game.away_team}
      </h1>
      <p>
        Win Probability:
        {game.home_win_probability}
      </p>
      <p>
        Score Diff:
        {game.score_diff}
      </p>
    </main>
  );
}