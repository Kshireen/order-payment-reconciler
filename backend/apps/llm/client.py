"""
Thin wrapper around Groq's (OpenAI-compatible) chat completions API.

Temperature: 0.2. This step only explains and summarizes decisions the
deterministic engine already made - it should not be creative or vary
between calls on the same input, but 0.0 tends to produce stilted/repetitive
phrasing across many items in one batch, so a small amount of variance (0.2)
is used instead. If this were doing anything that affected matching
decisions, it would be 0 or not use an LLM at all - see engine.py docstring.

Structured output: we ask for JSON (response_format=json_object where the
model supports it) AND validate the parsed shape ourselves, because
"the model returned JSON" and "the model returned the JSON we asked for"
are not the same guarantee. On a malformed/incomplete response we retry once
with a stricter reminder, then fall back to a clearly-labeled degraded
response rather than raising - a broken LLM call must never break the
dashboard, since the LLM is explanation-only, not the reconciliation itself.
"""

from __future__ import annotations

import json
import logging

from django.conf import settings
from groq import Groq

from .prompts import SYSTEM_PROMPT, build_user_prompt

logger = logging.getLogger(__name__)


class LLMExplanationError(Exception):
    pass


def _client() -> Groq:
    if not settings.GROQ_API_KEY:
        raise LLMExplanationError("GROQ_API_KEY is not configured.")
    return Groq(api_key=settings.GROQ_API_KEY)


def _validate_shape(parsed: dict, expected_order_ids: set[str | None]) -> bool:
    if not isinstance(parsed, dict):
        return False
    if "overview" not in parsed or "items" not in parsed:
        return False
    if not isinstance(parsed["items"], list):
        return False
    for item in parsed["items"]:
        if not isinstance(item, dict):
            return False
        if not {"order_id", "explanation", "recommended_action"} <= item.keys():
            return False
    return True


def _call_once(discrepancies: list[dict], strict_reminder: bool = False) -> dict:
    client = _client()
    user_prompt = build_user_prompt(discrepancies)
    if strict_reminder:
        user_prompt += "\n\nReminder: respond with ONLY the JSON object. No other text."

    response = client.chat.completions.create(
        model=settings.LLM_MODEL,
        temperature=settings.LLM_TEMPERATURE,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )
    raw = response.choices[0].message.content
    return json.loads(raw)  # may raise json.JSONDecodeError


def explain_discrepancies(discrepancies: list[dict]) -> dict:
    """discrepancies: list of dicts with keys type/order_id/amount_at_risk/
    payment_refs/detail (matches DiscrepancySerializer output).

    Returns a dict always shaped as:
      {"ok": bool, "overview": str, "items": [...], "error": str | None}
    Never raises - callers (the view) don't need their own try/except for the
    LLM call itself, only for e.g. bad request bodies.
    """
    expected_ids = {d.get("order_id") for d in discrepancies}

    for attempt, strict in enumerate([False, True]):
        try:
            parsed = _call_once(discrepancies, strict_reminder=strict)
        except Exception as exc:  # network error, auth error, timeout, etc.
            logger.warning("LLM call failed (attempt %s): %s", attempt, exc)
            continue

        if _validate_shape(parsed, expected_ids):
            return {"ok": True, "overview": parsed["overview"], "items": parsed["items"], "error": None}

        logger.warning("LLM response failed shape validation (attempt %s): %r", attempt, parsed)

    return {
        "ok": False,
        "overview": None,
        "items": [],
        "error": "The explanation service returned an unexpected response. The reconciliation "
        "results above are unaffected - only the plain-language explanation is unavailable.",
    }
