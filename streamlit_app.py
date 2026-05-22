# streamlit_app.py
import re
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Year Over Year Store Comparison", layout="wide")

st.title("Year Over Year Store Comparison")
st.caption("Compares Sales, UPS, Mailbox, Notary, Packing, and Public Service Payments year over year.")

CENTER_ORDER = ["1504", "5027", "5052", "5255", "5778", "6176", "6769", "7261"]

CATEGORIES = [
    "Sales",
    "UPS",
    "UPS %",
    "Mailbox",
    "Mailbox %",
    "Notary",
    "Notary %",
    "Packing",
    "Packing %",
    "Public Service Payments",
    "Public Service Payments %",
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
    psp = find_income(["public service payments", "public svcs payments", "psp"])

    packing = find_income([
        "packaging materials",
        "packing materials",
        "packaging service fee",
        "packing service fee",
        "retail shipping supplies",
        "office supplies",
    ])

    def pct(amount):
        return amount / total_sales if total_sales else 0

    return {
        "Center": center,
        "Sales": total_sales,
        "UPS": ups,
        "UPS %": pct(ups),
        "Mailbox": mailbox,
        "Mailbox %": pct(mailbox),
        "Notary": notary,
        "Notary %": pct(notary),
        "Packing": packing,
        "Packing %": pct(packing),
        "Public Service Payments": psp,
        "Public Service Payments %": pct(psp),
    }

def format_table(df):
    out = df.copy()

    money_cols = [
        "Sales",
        "UPS",
        "Mailbox",
        "Notary",
        "Packing",
        "Public Service Payments",
    ]

    pct_cols = [
        "UPS %",
        "Mailbox %",
        "Notary %",
        "Packing %",
        "Public Service Payments %",
    ]

    for col in money_cols:
        if col in out.columns:
            out[col] = out[col].apply(lambda x: f"${x:,.0f}")

    for col in pct_cols:
        if col in out.columns:
            out[col] = out[col].apply(lambda x: f"{x:.1%}")

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

    compare_cols = [
        "Sales",
        "UPS",
        "UPS %",
        "Mailbox",
        "Mailbox %",
        "Notary",
        "Notary %",
        "Packing",
        "Packing %",
        "Public Service Payments",
        "Public Service Payments %",
    ]

    for col in compare_cols:
        variance[col] = df_2026[col].fillna(0) - df_2025[col].fillna(0)

    st.markdown("## Gross Sales - All Profit Centers")

    st.markdown("### 2026")
    st.dataframe(format_table(df_2026), hide_index=True, use_container_width=True)

    st.markdown("### 2025")
    st.dataframe(format_table(df_2025), hide_index=True, use_container_width=True)

    st.markdown("### Variance Compared to Last Year")
    st.dataframe(
        variance.style
        .map(style_variance, subset=compare_cols)
        .format({
            "Sales": "${:,.0f}",
            "UPS": "${:,.0f}",
            "UPS %": "{:.1%}",
            "Mailbox": "${:,.0f}",
            "Mailbox %": "{:.1%}",
            "Notary": "${:,.0f}",
            "Notary %": "{:.1%}",
            "Packing": "${:,.0f}",
            "Packing %": "{:.1%}",
            "Public Service Payments": "${:,.0f}",
            "Public Service Payments %": "{:.1%}",
        }),
        hide_index=True,
        use_container_width=True
    )
