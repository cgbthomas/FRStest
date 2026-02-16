import re
import io
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Store Report Calculator", layout="wide")
st.title("Store Report Calculator")
st.caption("Paste report text below and click Process.")

# -----------------------------
# Helper Functions
# -----------------------------
def money_to_float(s: str):
    return float(s.replace(",", "").replace("$", "").strip())

def extract_money(text, label):
    pattern = rf"{label}.*?\$?([\d,]+\.\d{{2}})"
    match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
    return money_to_float(match.group(1)) if match else None

def extract_int(text, label):
    pattern = rf"{label}.*?([\d,]+)"
    match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
    return int(match.group(1).replace(",", "")) if match else None

# -----------------------------
# UI Input
# -----------------------------
store_name = st.text_input("Store / Center Name (optional)")
date_range = st.text_input("Date Range (optional)")
report_text = st.text_area("Paste Report Text Here", height=300)

if st.button("Process Report"):

    if not report_text.strip():
        st.error("Please paste report text first.")
        st.stop()

    # -----------------------------
    # Extraction (we will tune these)
    # -----------------------------
    sales = extract_money(report_text, "Total Sales")
    ups_shipping = extract_money(report_text, "UPS Shipping")
    ups_packages = extract_int(report_text, "UPS Packages")
    meter_sales = extract_money(report_text, "Meter Sales")
    mailbox_sales = extract_money(report_text, "Mailbox")
    print_sales = extract_money(report_text, "Print")
    notary_psp = extract_money(report_text, "Notary")
    shred_sales = extract_money(report_text, "Shred")
    packaging = extract_money(report_text, "Packaging")

    # -----------------------------
    # Calculations
    # -----------------------------
    avg_ups_pkg = (ups_shipping / ups_packages) if ups_shipping and ups_packages else None
    avg_meter_pkg = (meter_sales / ups_packages) if meter_sales and ups_packages else None

    # -----------------------------
    # Output Table (Your Preferred Order)
    # -----------------------------
    data = {
        "Store": store_name,
        "Date Range": date_range,
        "Sales": sales,
        "Average Meter Per Package": avg_meter_pkg,
        "Total UPS Shipping": ups_shipping,
        "Average UPS Package": avg_ups_pkg,
        "Total Meter Sales": meter_sales,
        "Packaging/Office Supplies/Service Fees": packaging,
        "Notary + PSP": notary_psp,
        "Mailbox Sales": mailbox_sales,
        "Printing & Copies": print_sales,
        "Shred Sales": shred_sales,
    }

    df = pd.DataFrame([data])

    st.subheader("Results")
    st.dataframe(df, use_container_width=True)

    # -----------------------------
    # Download Excel
    # -----------------------------
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)

    st.download_button(
        label="Download Excel",
        data=buffer.getvalue(),
        file_name="store_recap.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # -----------------------------
    # Copy Summary Text
    # -----------------------------
    summary = f"""
{store_name} ({date_range})
Sales: ${sales:,.2f} 
UPS: ${ups_shipping:,.2f} (Avg ${avg_ups_pkg:,.2f})
Meter: ${meter_sales:,.2f} (Avg ${avg_meter_pkg:,.2f})
Packaging: ${packaging:,.2f}
Notary+PSP: ${notary_psp:,.2f}
Mailbox: ${mailbox_sales:,.2f}
Print+Copies: ${print_sales:,.2f}
Shred: ${shred_sales:,.2f}
"""

    st.text_area("Copy Summary for Manager Update", summary, height=200)
