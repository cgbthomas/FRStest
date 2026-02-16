import re
import io
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Store Report Calculator", layout="wide")
st.title("Store Report Calculator")
st.caption("Paste the 'Worker Sales by Product Category' report text below, then click Process.")

# -----------------------------
# Helpers
# -----------------------------
def money_to_float(s: str) -> float:
    return float(s.replace(",", "").replace("$", "").strip())

def parse_worker_sales_by_category(text: str):
    """
    Parses lines like:
    + Copies 108 779 $272.61 $2.52 $0.35
    - Shipping Charges (UPS) 109 109 $6112.74 $56.08 $56.08

    Also parses:
    Center:\n1504
    Date Range:\n2/9/2026\nto\n2/14/2026
    Totals 1240 2358 $18057.89 $14.56 $7.66
    """
    # Meta: Center
    center = None
    m = re.search(r"Center:\s*\n(\d+)", text, flags=re.IGNORECASE)
    if m:
        center = m.group(1).strip()

    # Meta: Date range
    m = re.search(r"Date Range:\s*\n([0-9/]+)\s*\nto\s*\n([0-9/]+)", text, flags=re.IGNORECASE)
    date_range = None
    if m:
        date_range = f"{m.group(1).strip()} to {m.group(2).strip()}"

    # Rows
    row_re = re.compile(
        r"^[\+\-]\s*(.+?)\s+(\d+)\s+(\d+)\s+\$([\d,]+\.\d{2})\s+\$([\d,]+\.\d{2})\s+\$([\d,]+\.\d{2})\s*$",
        flags=re.MULTILINE
    )

    rows = {}
    for cat, cust_cnt, item_cnt, income, cust_avg, item_avg in row_re.findall(text):
        cat = cat.strip()
        rows[cat] = {
            "customer_count": int(cust_cnt),
            "item_count": int(item_cnt),
            "income": money_to_float(income),
            "customer_avg": money_to_float(cust_avg),
            "item_avg": money_to_float(item_avg),
        }

    # Totals
    m = re.search(
        r"^Totals\s+(\d+)\s+(\d+)\s+\$([\d,]+\.\d{2})\s+\$([\d,]+\.\d{2})\s+\$([\d,]+\.\d{2})\s*$",
        text,
        flags=re.MULTILINE | re.IGNORECASE
    )
    totals = None
    if m:
        totals = {
            "customer_count": int(m.group(1)),
            "item_count": int(m.group(2)),
            "income": money_to_float(m.group(3)),
            "customer_avg": money_to_float(m.group(4)),
            "item_avg": money_to_float(m.group(5)),
        }

    return {"center": center, "date_range": date_range}, rows, totals

def get_income(rows, category_name, default=0.0):
    return rows.get(category_name, {}).get("income", default)

def get_customer_count(rows, category_name, default=0):
    return rows.get(category_name, {}).get("customer_count", default)

# -----------------------------
# UI
# -----------------------------
store_name = st.text_input("Store / Center Name (optional)", placeholder="e.g., 1504 Yucaipa")
override_date = st.text_input("Date Range (optional)", placeholder="leave blank to auto-detect from paste")
report_text = st.text_area("Paste Report Text Here", height=360)

if st.button("Process Report", type="primary"):

    if not report_text.strip():
        st.error("Please paste report text first.")
        st.stop()

    meta, rows, totals = parse_worker_sales_by_category(report_text)

    # -----------------------------
    # Core metrics (locked to Shipping Charges (UPS))
    # -----------------------------
    sales = totals["income"] if totals else None

    ups_shipping = get_income(rows, "Shipping Charges (UPS)", default=None)
    ups_packages = get_customer_count(rows, "Shipping Charges (UPS)", default=0) or None

    meter_sales = get_income(rows, "Meter Mail", default=None)
    mailbox_sales = get_income(rows, "Mailbox Service", default=None)

    notary_income = get_income(rows, "Notary", default=0.0)
    psp_income = get_income(rows, "Public Service Payments", default=0.0)
    notary_psp = notary_income + psp_income

    printing_copies = (
        get_income(rows, "Printing", default=0.0)
        + get_income(rows, "Copies", default=0.0)
        + get_income(rows, "Color Copies", default=0.0)
    )

    packaging_bucket = (
        get_income(rows, "Office Supplies", default=0.0)
        + get_income(rows, "Packaging Materials", default=0.0)
        + get_income(rows, "Packaging Service Fee", default=0.0)
        + get_income(rows, "Retail Shipping Supplies", default=0.0)
    )

    shred_sales = get_income(rows, "Shred Sales", default=0.0)  # may not exist in this report

    # -----------------------------
    # Derived metrics
    # -----------------------------
    avg_ups_pkg = (ups_shipping / ups_packages) if (ups_shipping is not None and ups_packages) else None
    avg_meter_pkg = (meter_sales / ups_packages) if (meter_sales is not None and ups_packages) else None

    # Prefer detected center/date if user didn’t type them
    final_store = store_name.strip() or (meta["center"] or "")
    final_range = override_date.strip() or (meta["date_range"] or "")

    # Output in your preferred order
    ordered = {
        "Store": final_store,
        "Date Range": final_range,
        "Sales": sales,
        "Average Meter Per Package": avg_meter_pkg,
        "Total UPS Shipping": ups_shipping,
        "Average UPS Package": avg_ups_pkg,
        "Total Meter Sales": meter_sales,
        "Packaging/Office Supplies/Service Fees": packaging_bucket,
        "Notary + Public Service Payments": notary_psp,
        "Mailbox Sales": mailbox_sales,
        "Printing & Copies": printing_copies,
        "Shred Sales": shred_sales,
    }

    df = pd.DataFrame([ordered])

    st.subheader("Results")
    st.dataframe(df, use_container_width=True)

    # Excel export
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Recap")

    st.download_button(
        "Download Excel",
        data=buffer.getvalue(),
        file_name="store_recap.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )

    # Summary text
    def fmt_money(x):
        return "—" if x is None else f"${x:,.2f}"

    summary = (
        f"{final_store} ({final_range}): "
        f"Sales {fmt_money(sales)} | "
        f"UPS {fmt_money(ups_shipping)} (Avg {fmt_money(avg_ups_pkg)}) | "
        f"Meter {fmt_money(meter_sales)} (Avg {fmt_money(avg_meter_pkg)}) | "
        f"Pack/OS/Fees {fmt_money(packaging_bucket)} | "
        f"Notary+PSP {fmt_money(notary_psp)} | "
        f"Mailbox {fmt_money(mailbox_sales)} | "
        f"Print+Copies {fmt_money(printing_copies)} | "
        f"Shred {fmt_money(shred_sales)}"
    )

    st.text_area("Copy/paste summary for manager update", summary, height=90)
