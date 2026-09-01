"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { apiFetch, ApiError } from "@/lib/api";
import { isAuthenticated } from "@/lib/auth";
import { ReconciliationRun } from "@/lib/types";
import SummaryCards from "@/components/SummaryCards";
import DiscrepancyChart from "@/components/DiscrepancyChart";
import DiscrepancyTable from "@/components/DiscrepancyTable";
import Link from "next/link";

export default function DashboardPage() {
  const router = useRouter();
  const [run, setRun] = useState<ReconciliationRun | null>(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace("/login");
      return;
    }
    apiFetch<ReconciliationRun>("/reconciliation/summary/")
      .then(setRun)
      .catch((err) => {
        if (err instanceof ApiError && err.status === 404) {
          setNotFound(true);
        } else if (err instanceof ApiError && err.status === 401) {
          router.replace("/login");
        } else {
          setError(err instanceof Error ? err.message : "Failed to load dashboard.");
        }
      })
      .finally(() => setLoading(false));
  }, [router]);

  if (loading) {
    return (
      <main className="page">
        <p className="empty-state">Loading…</p>
      </main>
    );
  }

  if (notFound) {
    return (
      <main className="page">
        <h1>No reconciliation run yet</h1>
        <p className="subtitle">
          Upload your orders and payments CSVs first. <Link href="/upload">Go to upload →</Link>
        </p>
      </main>
    );
  }

  if (error) {
    return (
      <main className="page">
        <p className="explain-error">{error}</p>
      </main>
    );
  }

  return (
    <main className="page">
      <h1>Reconciliation Dashboard</h1>
      <p className="subtitle">Last run {run && new Date(run.created_at).toLocaleString()}</p>

      {run && <SummaryCards run={run} />}

      <section className="chart-section">
        <h2>Discrepancies by type</h2>
        {run && <DiscrepancyChart byType={run.by_type_json} />}
      </section>

      <section className="table-section">
        <h2>Drill down</h2>
        <DiscrepancyTable />
      </section>
    </main>
  );
}
