import Link from "next/link";

export default function Home() {
  return (
    <main className="page">
      <h1>Reconciliation Dashboard</h1>
      <p className="subtitle">
        Reconcile store orders against payment processor records and see where they disagree.
      </p>
      <p>
        <Link href="/upload">Upload your orders and payments CSVs →</Link>
      </p>
      <p>
        <Link href="/dashboard">Or go straight to the dashboard →</Link>
      </p>
    </main>
  );
}
