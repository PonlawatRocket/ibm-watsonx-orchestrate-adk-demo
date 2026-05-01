from ibm_watsonx_orchestrate.agent_builder.tools import tool

# Approved supplier IDs — hardcoded for demo
APPROVED_TAX_IDS = ["0105565077777", "0105565012345", "0105565098765"]


@tool(
    name="tool_fraud_check",
    description="Runs fraud detection rules against a structured invoice dict. "
                "Checks if the supplier is in the approved supplier list. "
                "Call this after tool_invoice_extract. "
                "Pass the full invoice dict as returned by tool_invoice_extract."
)
def tool_fraud_check(invoice: dict) -> dict:
    """
    Run fraud detection rules against an invoice.
    Only checks rules relevant to the current demo scenarios.

    Rules applied:
      - FR-004: Supplier not in approved list → block

    Args:
        invoice: Structured invoice dict (output from tool_invoice_extract).

    Returns:
        Fraud check findings and recommended action.
    """
    findings = []

    # ── FR-001: Supplier not in approved list ─────────────────────
    supplier_tax_id = invoice.get("supplier_tax_id", "")
    if supplier_tax_id not in APPROVED_TAX_IDS:
        findings.append({
            "rule_id"  : "FR-001",
            "rule_name": "Supplier not in approved list",
            "severity" : "high",
            "action"   : "block",
            "detail": f"Supplier tax ID '{supplier_tax_id}' is not registered in the approved supplier list."
        })

    # ── Summarise ─────────────────────────────────────────────────
    has_block = any(f["action"] == "block" for f in findings)

    if has_block:
        fraud_status   = "rejected"
        overall_action = "block"
    else:
        fraud_status   = "passed"
        overall_action = "approve"

    return {
        "success"        : True,
        "invoice_id"     : invoice.get("invoice_id", ""),
        "fraud_status"   : fraud_status,
        "overall_action" : overall_action,
        "rules_triggered": len(findings),
        "findings"       : findings,
    }
