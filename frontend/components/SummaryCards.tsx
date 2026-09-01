import { ReconciliationRun } from "@/lib/types";

function formatMoney(value: string): string {
  const n = parseFloat(value);
  return n.toLocaleString(undefined, { style: "currency", currency: "USD" });
}

export default function SummaryCards({ run }: { run: ReconciliationRun }) {
  const cards = [
    { label: "Total orders", value: run.total_orders.toLocaleString() },
    { label: "Total payments", value: run.total_payments.toLocaleString() },
    { label: "Value reconciled", value: formatMoney(run.total_value_reconciled) },
    { label: "Value in dispute", value: formatMoney(run.total_value_in_dispute), highlight: true },
    { label: "Discrepancies found", value: run.discrepancy_count.toLocaleString() },
  ];

  return (
    <div className="summary-cards">
      {cards.map((c) => (
        <div key={c.label} className={`summary-card${c.highlight ? " summary-card--risk" : ""}`}>
          <div className="summary-card__label">{c.label}</div>
          <div className="summary-card__value">{c.value}</div>
        </div>
      ))}
    </div>
  );
}
