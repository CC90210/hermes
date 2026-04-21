"""Customer credit hold check before order entry.

Implements Phase 4b — Pricing & Credit Validation (PRE-LAUNCH).

Hermes must never auto-enter a PO against a buyer on credit hold. If it does,
A2000 flags the order for internal hold and Hermes reports success — the operator
discovers the problem days later when the buyer calls asking where their shipment is.

Credit state is not static. A buyer can hit their credit limit mid-day. This module
checks credit status immediately before order entry, not at PO receipt time.

Three outcomes:
  - approve  — order proceeds automatically
  - hold     — order queued for AR review before entry
  - escalate — credit situation requires operator decision immediately

Reference: docs/WHOLESALE_RESEARCH.md — Section 1 (lifecycle Stages 5 and 6,
           Credit Check and Credit Hold), Section 4 (Automation Pitfalls).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal


@dataclass
class CreditCheckResult:
    """Result of a credit check for a specific customer and order total.

    Attributes
    ----------
    on_hold:
        True if the customer account has an active credit hold flag in A2000.
    available_credit:
        Remaining credit available (credit_limit minus current_open_balance).
        May be negative if the customer is over their limit.
    days_past_due:
        Number of days the oldest unpaid invoice is past its due date.
        Zero if all invoices are current.
    action:
        Recommended action for the orchestrator:
        - "approve"   — credit is healthy; proceed with order entry
        - "hold"      — credit is marginal or at limit; queue for AR review
        - "escalate"  — credit hold active or severely past due; notify Emmanuel now
    reason:
        Human-readable explanation for the action decision, included in any
        escalation email to the operator.
    """

    on_hold: bool
    available_credit: Decimal
    days_past_due: int
    action: Literal["approve", "hold", "escalate"]
    reason: str = ""


async def check_credit(
    customer_id: str,
    order_total: Decimal,
    a2000_client,  # A2000ClientBase — typed as Any to avoid circular import
) -> CreditCheckResult:
    """Check credit status for a customer before entering an order.

    Queries A2000 for the customer's current credit limit, open balance,
    hold flag, and oldest past-due invoice. Applies the following decision rules:

    - on_hold == True                           → escalate immediately
    - days_past_due > 60                        → escalate
    - available_credit < order_total            → hold (insufficient headroom)
    - available_credit < order_total * 0.10     → escalate (nearly over limit)
    - all other cases                           → approve

    Parameters
    ----------
    customer_id:
        A2000 customer account code (e.g. Walgreens account ID).
    order_total:
        Total dollar value of the order being submitted. Used to check whether
        the order would push the customer over their credit limit.
    a2000_client:
        Live A2000 client instance. Must support credit-status lookup via
        whichever integration tier is active (API, EDI, or Playwright).

    Returns
    -------
    CreditCheckResult
        Fully populated result with action recommendation.

    Raises
    ------
    RuntimeError
        If A2000 is unreachable or returns an unrecognised credit status.
    NotImplementedError
        Until Phase 4b implementation is complete.
    """
    raise NotImplementedError("Phase 4b — see docs/BUILD_PLAN.md")
