"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import { Discrepancy, PaginatedResponse } from "@/lib/types";
import DiscrepancyRow from "./DiscrepancyRow";

const TYPE_OPTIONS = [
  "",
  "MISSING_PAYMENT",
  "ORPHAN_PAYMENT",
  "DUPLICATE_CHARGE",
  "CURRENCY_MISMATCH",
  "AMOUNT_UNDERPAID",
  "AMOUNT_OVERPAID",
  "UNSETTLED_PAYMENT",
  "CANCELLED_NOT_REFUNDED",
  "REFUND_STATUS_DRIFT",
];

export default function DiscrepancyTable() {
  const [type, setType] = useState("");
  const [search, setSearch] = useState("");
  const [data, setData] = useState<PaginatedResponse<Discrepancy> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const params = new URLSearchParams();
    if (type) params.set("type", type);
    if (search) params.set("search", search);

    setLoading(true);
    setError(null);
    const timeout = setTimeout(() => {
      apiFetch<PaginatedResponse<Discrepancy>>(`/reconciliation/discrepancies/?${params.toString()}`)
        .then(setData)
        .catch((err) => setError(err instanceof Error ? err.message : "Failed to load discrepancies."))
        .finally(() => setLoading(false));
    }, 250); // debounce search typing

    return () => clearTimeout(timeout);
  }, [type, search]);

  return (
    <div className="discrepancy-table">
      <div className="table-controls">
        <select value={type} onChange={(e) => setType(e.target.value)}>
          <option value="">All types</option>
          {TYPE_OPTIONS.filter(Boolean).map((t) => (
            <option key={t} value={t}>
              {t.replace(/_/g, " ")}
            </option>
          ))}
        </select>
        <input
          type="text"
          placeholder="Search by order id…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      {loading && <p className="empty-state">Loading…</p>}
      {error && <p className="explain-error">{error}</p>}

      {!loading && !error && data && (
        <>
          <p className="table-count">{data.count} discrepancies</p>
          <table>
            <thead>
              <tr>
                <th>Order</th>
                <th>Type</th>
                <th>Amount at risk</th>
                <th>Detail</th>
              </tr>
            </thead>
            <tbody>
              {data.results.map((d) => (
                <DiscrepancyRow key={d.id} d={d} />
              ))}
            </tbody>
          </table>
          {data.count === 0 && <p className="empty-state">No discrepancies match this filter.</p>}
        </>
      )}
    </div>
  );
}
