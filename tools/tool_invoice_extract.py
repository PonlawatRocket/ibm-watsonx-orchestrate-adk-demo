from datetime import datetime
from ibm_watsonx_orchestrate.agent_builder.tools import tool

@tool(
    name="tool_invoice_extract",
    description="Validates and extracts fields from a supplier invoice. "
                "The agent reads the invoice uploaded by the user (PDF or JSON), "
                "structures the fields into a dict, then passes it to this tool for validation. "
                "Checks for duplicate line items, math errors, VAT mismatches, and date issues."
)
def tool_invoice_extract(invoice: dict) -> dict:
    """
    Validate and extract fields from a structured invoice.

    The agent calls this tool after reading the invoice the user uploaded
    (PDF or JSON) and structuring its fields into a dict.

    Runs validation checks:
      - Duplicate line items
      - Line item math (qty x unit_price = total)
      - Subtotal matches sum of line items
      - VAT = subtotal x 7% (+-1 THB rounding tolerance)
      - Total = subtotal + VAT
      - Invoice date is not in the future

    Args:
        invoice: Structured invoice as a dict. Must contain:
                 invoice_id, invoice_date, due_date,
                 supplier (id, name, tax_id), bill_to, po_reference,
                 line_items (list of description/qty/unit_price/total),
                 subtotal, vat_7_percent, total_amount, currency, payment_terms.

    Returns:
        Extracted invoice fields plus anomalies found and overall status.
    """
    # ── Validate required fields ─────────────────────────────────
    required = [
        "invoice_id", "invoice_date", "due_date", "supplier",
        "bill_to", "po_reference", "line_items",
        "subtotal", "vat_7_percent", "total_amount", "currency", "payment_terms"
    ]
    missing = [f for f in required if f not in invoice]
    if missing:
        return {
            "success": False,
            "error": f"Invoice is missing required fields: {missing}"
        }

    data = invoice
    anomalies = []

    # ── Check 1: Duplicate line items ────────────────────────────
    seen_items = []
    for item in data["line_items"]:
        key = (item["description"].strip().lower(), item["unit_price"])
        if key in seen_items:
            anomalies.append({
                "rule": "DUPLICATE_LINE_ITEM",
                "severity": "high",
                "detail": f"Line item '{item['description']}' appears more than once with the same unit price."
            })
        else:
            seen_items.append(key)

    # ── Check 2: Line item math (qty x unit_price = total) ───────
    for item in data["line_items"]:
        expected = round(item["qty"] * item["unit_price"], 2)
        if abs(expected - item["total"]) > 0.01:
            anomalies.append({
                "rule": "LINE_ITEM_MATH_ERROR",
                "severity": "medium",
                "detail": (
                    f"'{item['description']}': "
                    f"{item['qty']} x {item['unit_price']:,.2f} = {expected:,.2f} "
                    f"but line total says {item['total']:,.2f}."
                )
            })

    # ── Check 3: Subtotal = sum of line item totals ───────────────
    computed_subtotal = round(sum(i["total"] for i in data["line_items"]), 2)
    if abs(computed_subtotal - data["subtotal"]) > 0.01:
        anomalies.append({
            "rule": "SUBTOTAL_MISMATCH",
            "severity": "medium",
            "detail": (
                f"Sum of line items = {computed_subtotal:,.2f} "
                f"but invoice subtotal says {data['subtotal']:,.2f}."
            )
        })

    # ── Check 4: VAT = subtotal x 7% (+-1 THB rounding) ─────────
    expected_vat = round(data["subtotal"] * 0.07)
    if abs(expected_vat - data["vat_7_percent"]) > 1:
        anomalies.append({
            "rule": "VAT_MISMATCH",
            "severity": "low",
            "detail": (
                f"Expected VAT (7%) = {expected_vat:,.2f} "
                f"but invoice declares {data['vat_7_percent']:,.2f}."
            )
        })

    # ── Check 5: Total = subtotal + VAT ──────────────────────────
    expected_total = round(data["subtotal"] + data["vat_7_percent"], 2)
    if abs(expected_total - data["total_amount"]) > 1:
        anomalies.append({
            "rule": "TOTAL_AMOUNT_MISMATCH",
            "severity": "medium",
            "detail": (
                f"Subtotal {data['subtotal']:,.2f} + VAT {data['vat_7_percent']:,.2f} "
                f"= {expected_total:,.2f} but invoice total says {data['total_amount']:,.2f}."
            )
        })

    # ── Check 6: Invoice date not in the future ───────────────────
    try:
        inv_date = datetime.strptime(data["invoice_date"], "%Y-%m-%d").date()
        if inv_date > datetime.today().date():
            anomalies.append({
                "rule": "FUTURE_INVOICE_DATE",
                "severity": "medium",
                "detail": f"Invoice date {data['invoice_date']} is in the future."
            })
    except ValueError:
        anomalies.append({
            "rule": "INVALID_DATE_FORMAT",
            "severity": "low",
            "detail": f"Invoice date '{data['invoice_date']}' is not in YYYY-MM-DD format."
        })

    # ── Build result ─────────────────────────────────────────────
    status = "flagged" if anomalies else "clean"

    return {
        "success"        : True,
        "invoice_id"     : data["invoice_id"],
        "invoice_date"   : data["invoice_date"],
        "due_date"       : data["due_date"],
        "supplier_id"    : data["supplier"].get("id", ""),
        "supplier_name"  : data["supplier"].get("name", ""),
        "supplier_tax_id": data["supplier"].get("tax_id", ""),
        "bill_to"        : data["bill_to"],
        "po_reference"   : data["po_reference"],
        "line_items"     : data["line_items"],
        "subtotal"       : data["subtotal"],
        "vat_7_percent"  : data["vat_7_percent"],
        "total_amount"   : data["total_amount"],
        "currency"       : data["currency"],
        "payment_terms"  : data["payment_terms"],
        "anomalies_found": len(anomalies),
        "anomalies"      : anomalies,
        "status"         : status,
    }
