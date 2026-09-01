"use client";

import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";
import { DiscrepancyTypeBucket } from "@/lib/types";

export default function DiscrepancyChart({ byType }: { byType: Record<string, DiscrepancyTypeBucket> }) {
  const data = Object.entries(byType)
    .map(([type, bucket]) => ({
      type: type.replace(/_/g, " "),
      count: bucket.count,
      amount: parseFloat(bucket.amount),
    }))
    .sort((a, b) => b.amount - a.amount);

  if (data.length === 0) {
    return <p className="empty-state">No discrepancies to chart yet.</p>;
  }

  return (
    <div style={{ width: "100%", height: 320 }}>
      <ResponsiveContainer>
        <BarChart data={data} layout="vertical" margin={{ left: 24, right: 24 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis type="number" tickFormatter={(v) => `$${v}`} />
          <YAxis type="category" dataKey="type" width={160} tick={{ fontSize: 12 }} />
          <Tooltip
            formatter={(value: number, name: string) =>
              name === "amount" ? [`$${value.toFixed(2)}`, "Amount at risk"] : [value, "Count"]
            }
          />
          <Bar dataKey="amount" fill="#c0392b" radius={[0, 4, 4, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
