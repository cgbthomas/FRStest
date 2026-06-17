import re
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Year Over Year Store Comparison", layout="wide")

st.title("Year Over Year Store Comparison")
st.caption("Compares Sales, UPS, Average UPS Shipping Sale, Mailbox, Packing, Notary, and Live Scan year over year.")

CENTER_ORDER = ["1504", "5027", "5052", "5255", "5778", "6176", "6769", "7261"]

COMPARE_COLS = [
    "Sales",
    "UPS",
    "Avg UPS Sale",
    "Mailbox",
    "Total Packing",
    "Pack % vs UPS",
    "Notary",
    "Live Scan",
]

def money_to_float(x):
    return float(x.replace("$", "").replace(",", "").strip())

def parse_report(text):
    center_match = re.search(r"Center\s*:?\s*\n?\s*(\d{4})", text, re.I)
    center = center_match.group(1) if center_match else None

    rows = {}

    line_re = re.compile(
        r"^[+\-]?\s*(.*?)\s+\d+\s+\d+\s+\$([\d,]+\.\d{2})",
        re.MULTILINE
    )

    for category, income in line_re.findall(text):
        rows[category.strip().lower()] = money_to_float(income)

    totals_match = re.search(
        r"Totals\s+\d+\s+\d+\s+\$([\d,]+\.\d{2})",
        text,
        re.I
    )

    total_sales = money_to_float(totals_match.group(1)) if totals_match else 0

    def find_income(keywords):
        total = 0
        for cat, amount in rows.items():
            if any(k in cat for k in keywords):
                total += amount
        return total

    ups = find_income(["shipping charges"])
    mailbox = find_income(["mailbox"])
    notary = find_income(["notary"])

    live_scan = find_income([
        "public service payments",
        "public svcs payments",
        "psp",
        "live scan",
        "livescan",
    ])

    total_packing = find_income([
        "packaging materials",
        "packing materials",
        "packaging service fee",
        "packing service fee",
        "retail shipping supplies",
        "retail shipment supplies",
        "office supplies",
    ])

    # Average UPS Sale - pulls Customer Average from Shipping Charges / UPS row
    avg_ups_sale = 0

    shipping_line_match = re.search(
        r"^.*shipping charges.*ups.*$",
        text,
        re.I | re.MULTILINE
    )

    if shipping_line_match:
        shipping_line = shipping_line_match.group(0)
        dollar_values = re.findall(r"\$([\d,]+\.\d{2})", shipping_line)

        # FRS usually has Income first and Customer Average later.
        # Customer Average is usually the last dollar value on the Shipping Charges / UPS line.
        if len(dollar_values) >= 2:
            avg_ups_sale = money_to_float(dollar_values[-1])
        elif len(dollar_values) == 1:
            avg_ups_sale = money_to_float(dollar_values[0])

    # Backup search if the Shipping Charges / UPS line does not pull correctly
    if avg_ups_sale == 0:
        avg_ups_match = re.search(
            r"customer average.*?\$([\d,]+\.\d{2})",
            text,
            re.I | re.S
        )
        avg_ups_sale = money_to_float(avg_ups_match.group(1)) if avg_ups_match else 0

    pack_vs_ups = total_packing / ups if ups else 0

    return {
        "Center": center,
        "Sales": total_sales,
        "UPS": ups,
        "Avg UPS Sale": avg_ups_sale,
        "Mailbox": mailbox,
        "Total Packing": total_packing,
        "Pack % vs UPS": pack_vs_ups,
        "Notary": notary,
        "Live Scan": live_scan,
    }

def format_table(df):
    out = df.copy()

    money_cols = [
        "Sales",
        "UPS",
        "Avg UPS Sale",
        "Mailbox",
        "Total Packing",
        "Notary",
        "Live Scan",
    ]

    for col in money_cols:
        if col in out.columns:
            out[col] = out[col].apply(lambda x: f"${x:,.2f}")

    if "Pack % vs UPS" in out.columns:
        out["Pack % vs UPS"] = out["Pack % vs UPS"].apply(lambda x: f"{x:.1%}")

    return out

def style_variance(val):
    if isinstance(val, (int, float)):
        if val > 0:
            return "color: green; font-weight: bold;"
        if val < 0:
            return "color: red; font-weight: bold;"
    return ""

st.subheader("Paste Reports")

left, right = st.columns(2)

reports_2026 = []
reports_2025 = []

with left:
    st.markdown("## 2026")
    for i in range(8):
        reports_2026.append(
            st.text_area(f"2026 Store Report #{i+1}", height=160, key=f"2026_{i}")
        )

with right:
    st.markdown("## 2025")
    for i in range(8):
        reports_2025.append(
            st.text_area(f"2025 Store Report #{i+1}", height=160, key=f"2025_{i}")
        )

if st.button("Compare Reports", type="primary", use_container_width=True):

    data_2026 = [parse_report(r) for r in reports_2026 if r.strip()]
    data_2025 = [parse_report(r) for r in reports_2025 if r.strip()]

    df_2026 = pd.DataFrame(data_2026)
    df_2025 = pd.DataFrame(data_2025)

    if df_2026.empty or df_2025.empty:
        st.error("Please paste at least one 2026 report and one 2025 report.")
        st.stop()

    df_2026 = df_2026.set_index("Center").reindex(CENTER_ORDER).dropna(how="all").reset_index()
    df_2025 = df_2025.set_index("Center").reindex(CENTER_ORDER).dropna(how="all").reset_index()

    variance = df_2026.copy()

    for col in COMPARE_COLS:
        variance[col] = df_2026[col].fillna(0) - df_2025[col].fillna(0)

    st.markdown("## Gross Sales - All Profit Centers")

    st.markdown("### 2026")
    st.dataframe(format_table(df_2026), hide_index=True, use_container_width=True)

    st.markdown("### 2025")
    st.dataframe(format_table(df_2025), hide_index=True, use_container_width=True)

    st.markdown("### Variance Compared to Last Year")
    st.dataframe(
        variance.style
        .map(style_variance, subset=COMPARE_COLS)
        .format({
            "Sales": "${:,.2f}",
            "UPS": "${:,.2f}",
            "Avg UPS Sale": "${:,.2f}",
            "Mailbox": "${:,.2f}",
            "Total Packing": "${:,.2f}",
            "Pack % vs UPS": "{:.1%}",
            "Notary": "${:,.2f}",
            "Live Scan": "${:,.2f}",
        }),
        hide_index=True,
        use_container_width=True
    )
