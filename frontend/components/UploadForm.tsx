"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { apiFetch, uploadFile } from "@/lib/api";

type Status = "idle" | "uploading" | "running" | "done" | "error";

export default function UploadForm() {
  const router = useRouter();
  const [ordersFile, setOrdersFile] = useState<File | null>(null);
  const [paymentsFile, setPaymentsFile] = useState<File | null>(null);
  const [status, setStatus] = useState<Status>("idle");
  const [message, setMessage] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!ordersFile || !paymentsFile) {
      setMessage("Select both an orders CSV and a payments CSV.");
      return;
    }

    try {
      setStatus("uploading");
      setMessage(null);
      const ordersResult = await uploadFile("/orders/upload/", ordersFile);
      const paymentsResult = await uploadFile("/payments/upload/", paymentsFile);

      setStatus("running");
      await apiFetch("/api/reconciliation/run/", { method: "POST" });

      setStatus("done");
      const skipped = ordersResult.skipped_rows.length + paymentsResult.skipped_rows.length;
      setMessage(
        `Loaded ${ordersResult.created} orders and ${paymentsResult.created} payments` +
          (skipped ? ` (${skipped} rows skipped — see console)` : "") +
          ". Redirecting to dashboard…"
      );
      if (skipped) {
        console.warn("Skipped order rows:", ordersResult.skipped_rows);
        console.warn("Skipped payment rows:", paymentsResult.skipped_rows);
      }
      setTimeout(() => router.push("/dashboard"), 1200);
    } catch (err) {
      setStatus("error");
      setMessage(err instanceof Error ? err.message : "Upload failed.");
    }
  }

  const busy = status === "uploading" || status === "running";

  return (
    <form className="upload-form" onSubmit={handleSubmit}>
      <label>
        Orders CSV
        <input type="file" accept=".csv" onChange={(e) => setOrdersFile(e.target.files?.[0] ?? null)} />
      </label>
      <label>
        Payments CSV
        <input type="file" accept=".csv" onChange={(e) => setPaymentsFile(e.target.files?.[0] ?? null)} />
      </label>
      <button type="submit" disabled={busy}>
        {status === "uploading" ? "Uploading…" : status === "running" ? "Reconciling…" : "Upload & reconcile"}
      </button>
      {message && <p className={status === "error" ? "explain-error" : "empty-state"}>{message}</p>}
    </form>
  );
}
