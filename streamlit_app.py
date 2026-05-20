# streamlit_app.py
import re
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Year Over Year Store Comparison", layout="wide")

st.title("Year Over Year Store Comparison")
st.caption("Paste Worker Sales by Product Category reports for 2026 and 2025. The app compares Sales, UPS, Mailbox, and Notary.")

CENTER_ORDER = ["1504", "5027", "5052", "5255", "5778", "6176", "6769", "7261"]

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
        category = category.strip().lower()
        rows[category] = money_to_float(income)

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

    return {
        "Center": center,
        "Sales": total_sales,
        "UPS": ups,
        "Mailbox": mailbox,
        "Notary": notary,
    }

def format_money(df):
    out = df.copy()
    for col in ["Sales", "UPS", "Mailbox", "Notary"]:
        out[col] = out[col].apply(lambda x: f"${x:,.0f}")
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

    for col in ["Sales", "UPS", "Mailbox", "Notary"]:
        variance[col] = df_2026[col].fillna(0) - df_2025[col].fillna(0)

    st.markdown("## Gross Sales - All Profit Centers")

    st.markdown("### 2026")
    st.dataframe(format_money(df_2026), hide_index=True, use_container_width=True)

    st.markdown("### 2025")
    st.dataframe(format_money(df_2025), hide_index=True, use_container_width=True)

    st.markdown("### Variance Compared to Last Year")
    st.dataframe(
        variance.style
        .map(style_variance, subset=["Sales", "UPS", "Mailbox", "Notary"])
        .format({
            "Sales": "${:,.0f}",
            "UPS": "${:,.0f}",
            "Mailbox": "${:,.0f}",
            "Notary": "${:,.0f}",
        }),
        hide_index=True,
        use_container_width=True
    )
