export interface Order {
  id: number;
  order_id: string;
  order_date_raw: string | null;
  customer_email: string | null;
  currency: string;
  gross_amount: string;
  discount: string;
  net_amount: string;
  status: string;
  uploaded_at: string;
}

export interface Payment {
  id: number;
  transaction_ref: string;
  processed_at_raw: string | null;
  order_reference: string;
  currency: string;
  amount: string;
  fee: string;
  net_settled: string;
  type: "charge" | "refund";
  status: "settled" | "pending" | "failed";
  uploaded_at: string;
}

export interface DiscrepancyTypeBucket {
  count: number;
  amount: string;
}

export interface ReconciliationRun {
  id: number;
  created_at: string;
  total_orders: number;
  total_payments: number;
  total_order_value: string;
  total_value_reconciled: string;
  total_value_in_dispute: string;
  discrepancy_count: number;
  by_type_json: Record<string, DiscrepancyTypeBucket>;
}

export interface Discrepancy {
  id: number;
  type: string;
  order_id: string | null;
  payment_refs_json: string[];
  amount_at_risk: string;
  detail: string;
}

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface ExplainItem {
  order_id: string | null;
  explanation: string;
  recommended_action: string;
}

export interface ExplainResponse {
  ok: boolean;
  overview: string | null;
  items: ExplainItem[];
  error: string | null;
}
