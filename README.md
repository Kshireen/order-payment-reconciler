# Order/Payment Reconciliation Dashboard

Reconciles a store's order export against its payment processor's export, surfaces
every case where they disagree, and explains the discrepancies in plain language.

## Architecture

```
backend/   Django + DRF API
  apps/orders/          Order model, CSV upload, list
  apps/payments/         Payment model, CSV upload, list
  apps/reconciliation/   engine.py (pure, deterministic matching logic - no DB, no
                          Django import) + models/views that persist and serve results
  apps/llm/               Groq client, prompt, structured-output validation
frontend/  Next.js (App Router) + TypeScript
  app/upload             upload both CSVs, triggers a reconciliation run
  app/dashboard           summary cards, discrepancy-by-type chart (Recharts),
                          filterable/searchable drill-down table with per-row
                          "Explain with AI"
```

Auth: `apps/accounts` — plain SimpleJWT, nothing more. `POST /api/auth/signup/`
(creates a user, returns tokens), `POST /api/auth/login/`, `POST
/api/auth/refresh/`, `POST /api/auth/logout/` (blacklists the refresh token -
`token_blacklist` is in `INSTALLED_APPS` for this). Every other view is
`IsAuthenticated` + filters querysets by `request.user`, so isolation holds
automatically once a request carries a valid access token.

The reconciliation engine (`apps/reconciliation/engine.py`) is deliberately pure
Python with no Django or I/O dependency: same input, same output, always. It's
unit-tested directly against the sample `orders.csv`/`payments.csv` - the tests
assert on the *specific* discrepancies described below, not just "some rows got
flagged."

## What's actually wrong with the sample data

Investigated both files before writing any matching logic. Two kinds of problems:
export/formatting noise that a naive join would mishandle, and real business
discrepancies.

**Formatting noise (handled by normalization, not treated as a discrepancy):**
- Two payment rows reference orders as `ord-1802` and `' ord-1801 '` - lowercase
  and whitespace-padded. All matching keys are trimmed + uppercased before
  comparison, so these still match correctly.
- `ORD-1004` appears twice in `orders.csv` as an identical duplicate row. Deduped
  to one order (would double-count revenue otherwise).
- `processed_at` is `DD/MM/YYYY` while `order_date` is ISO - both are stored as
  raw strings rather than parsed dates, since the reconciliation logic never
  needs to compare them (see "What I'd improve" below for a case where it would).

**Real discrepancies, one instance of each type found in the sample data:**

| Type | Example | What it means |
|---|---|---|
| `MISSING_PAYMENT` | `ORD-1201`-`1204` | Order marked `completed`, no payment record at all - revenue booked with nothing behind it. |
| `ORPHAN_PAYMENT` | `TXN700161`-`163` → `ORD-1301`-`1303` | Payments reference orders that don't exist in the order export. |
| `DUPLICATE_CHARGE` | `ORD-1501`, `ORD-1502` | Same order charged twice, identical amount, ~29 min apart - classic webhook-retry double-charge. |
| `CURRENCY_MISMATCH` | `ORD-1601` (USD) ↔ EUR payment; `ORD-1602` (EUR) ↔ USD payment | Same numeric amount, different currency - not actually equal value. No FX rate is supplied, so these are flagged for manual review rather than silently converted. |
| `AMOUNT_OVERPAID` / `AMOUNT_UNDERPAID` | `ORD-1401` paid \$117.81 vs ordered \$92.81; `ORD-1402` paid \$109.12 vs ordered \$127.62; `ORD-1403` paid \$259.01 vs ordered \$199.01 | Real gaps ($18-60), not rounding. |
| `UNSETTLED_PAYMENT` | `ORD-2001` (charge `failed`), `ORD-2002` (charge `pending`) | Order marked `completed` but the money was never actually collected. |
| `CANCELLED_NOT_REFUNDED` | `ORD-1701` | Order cancelled, charge still settled, no refund issued. |
| `REFUND_STATUS_DRIFT` | `ORD-1703` | Charged and fully refunded, but order status is still `completed`. |

**Not flagged, on purpose:** `ORD-1902` differs by \$0.02 (\$68.65 vs \$68.63) -
inside the \$0.05 tolerance used for float-rounding noise. `ORD-1702` (charged
\$240, refunded \$120, status already `refunded`) is a correctly-recorded partial
refund, not a discrepancy.

Minor data-quality notes not treated as discrepancies: one order is missing
`customer_email`/`discount`, one payment is missing `processed_at` - both are
stored as `null` rather than guessed at.

## Reconciliation logic

Matching key: `order_id` / `order_reference`, trimmed + uppercased. Amount
comparisons use a **\$0.05 tolerance** - large enough to absorb float rounding,
small enough that it doesn't mask any real mismatch in the sample data (the
smallest genuine mismatch is ~\$18). Currency is compared as a hard equality
check; there's no FX rate in the data to justify converting instead of flagging.

Duplicate charges: only the 2nd+ *settled* charge for an order counts as the
discrepancy (the amount at risk), not the first - the first charge is the
legitimate one.

Cancelled-but-charged and completed-but-fully-refunded are both treated as
**status drift** between the two systems rather than amount mismatches, since
the dollar amounts actually agree - it's the order's status field that's stale.

## LLM approach

Provider: Groq (OpenAI-compatible chat completions API), model configurable via
`LLM_MODEL` env var (default `llama-3.3-70b-versatile`).

- **Called server-side only** (`apps/llm/client.py`) - the API key never reaches
  the frontend.
- **Structured output**: requests `response_format: json_object` *and*
  independently validates the parsed shape (`overview` + `items[]` with the
  expected keys) - getting JSON back isn't the same guarantee as getting the
  JSON the app actually needs.
- **Malformed/failed response handling**: one retry with a stricter prompt
  reminder, then a labeled degraded response (`{"ok": false, "error": "..."}`)
  rather than a 500. The dashboard/reconciliation results are never affected by
  an LLM outage, since the LLM only explains decisions the deterministic engine
  already made.
- **Temperature: 0.2.** This step explains and summarizes matching decisions
  that were already made deterministically - it shouldn't be creative, but 0.0
  tends to produce repetitive phrasing across a batch of items, so a small
  amount of variance is allowed. It's never used for anything that affects
  matching.
- The system prompt explicitly instructs the model not to re-classify or
  contradict the discrepancy type it's given.

## Running it locally

**Backend**
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in GROQ_API_KEY at minimum
python manage.py migrate
python manage.py createsuperuser   # or however your auth flow creates users
python manage.py runserver
```

**Backend tests** (engine unit tests + API integration tests, run against the
real sample CSVs in `apps/reconciliation/tests/fixtures/`):
```bash
cd backend
python -m pytest apps/ -v
```

**Frontend**
```bash
cd frontend
cp .env.local.example .env.local   # point NEXT_PUBLIC_API_BASE_URL at the backend
npm install
npm run dev
```

## Deployment

Backend is deploy-ready for any Postgres-capable host (Render, Railway, Fly, etc.):
set `DATABASE_URL`, `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=false`,
`DJANGO_ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, `GROQ_API_KEY`, then
`python manage.py migrate` and run via `gunicorn config.wsgi`. Frontend deploys
to Vercel as-is; set `NEXT_PUBLIC_API_BASE_URL` to the deployed backend URL.

## What I'd improve with more time

- Parse `order_date`/`processed_at` into real datetimes and add a
  time-window sanity check (e.g. a "matching" payment settled 6 months after
  the order is itself suspicious even if the amount lines up).
- Configurable tolerance per currency (a \$0.05 tolerance means something
  different for JPY than USD).
- Pagination/streaming for CSV uploads well beyond the sample size - the
  current upload view loads the whole file into memory.
- Batch LLM explanations more efficiently (currently one call per discrepancy
  or per type; could group a full run into fewer, larger calls).
- Auto-refresh the access token on 401 instead of requiring a fresh login once
  it expires (currently a manual re-login, on purpose, to keep the auth layer
  small).

## AI tool use

Built with Claude (Anthropic) doing the implementation from a plan I reviewed
and directed - data investigation, reconciliation rule design, and code
structure decisions were made and checked by me at each step, not generated in
one pass.
