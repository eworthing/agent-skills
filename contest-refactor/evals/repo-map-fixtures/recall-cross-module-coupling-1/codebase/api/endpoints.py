"""HTTP endpoint stubs — high fan-out consumer of billing and reporting."""

from billing import Invoice, apply_discount
from reporting import Summary, record_policy_event


def create_invoice_endpoint(customer_id: str, amount: float, tier: str) -> dict:
    discounted = apply_discount(amount, tier)
    inv = Invoice(customer_id)
    inv.add_line("service", discounted)
    return {"invoice_total": inv.total()}


def get_report_endpoint(title: str) -> dict:
    record_policy_event("report_requested", {"title": title})
    s = Summary(title)
    return {"report": s.render()}
