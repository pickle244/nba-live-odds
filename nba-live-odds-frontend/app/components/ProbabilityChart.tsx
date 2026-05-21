"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer
} from "recharts";

export default function ProbabilityChart({
  history
}: any) {
  const chartData = history.map(
    (item: any) => ({

      time: new Date(
        item.last_updated
      ).toLocaleTimeString([], {
        minute: "2-digit",
        second: "2-digit"
      }),

      probability:
        item.probability
    })
  );
  return (

    <ResponsiveContainer
      width="100%"
      height={300}
    >

      <LineChart data={chartData}>

        <XAxis dataKey="time" />

        <YAxis domain={[0, 1]} />

        <Tooltip />

        <Line
          type="monotone"
          dataKey="probability"
        />

      </LineChart>

    </ResponsiveContainer>
  );
}