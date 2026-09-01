"use client";

import { useState } from "react";
import { apiFetch } from "@/lib/api";
import { Discrepancy, ExplainResponse } from "@/lib/types";

export default function DiscrepancyRow({ d }: { d: Discrepancy }) {
  const [explain, setExplain] = useState<ExplainResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleExplain() {
    setLoading(true);
    setError(null);
    try {
      const result = await apiFetch<ExplainResponse>("/llm/explain/", {
        method: "POST",
        body: { discrepancy_ids: [d.id] },
      });
      setExplain(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <tr>
      <td>{d.order_id ?? "—"}</td>
      <td>
        <span className="badge">{d.type.replace(/_/g, " ")}</span>
      </td>
      <td className="amount-cell">${parseFloat(d.amount_at_risk).toFixed(2)}</td>
      <td className="detail-cell">
        <div>{d.detail}</div>
        {!explain && !loading && (
          <button className="explain-btn" onClick={handleExplain}>
            Explain with AI
          </button>
        )}
        {loading && <span className="explain-loading">Explaining…</span>}
        {error && <span className="explain-error">{error}</span>}
        {explain && explain.ok && explain.items[0] && (
          <div className="explain-result">
            <p>{explain.items[0].explanation}</p>
            <p className="explain-action">→ {explain.items[0].recommended_action}</p>
          </div>
        )}
        {explain && !explain.ok && <span className="explain-error">{explain.error}</span>}
      </td>
    </tr>
  );
}
