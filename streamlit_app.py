import re
import pandas as pd
import streamlit as st

# ============================================================
# App Setup
# ============================================================
st.set_page_config(
    page_title="Year Over Year Store Comparison",
    layout="wide"
)

st.title("Year Over Year Store Comparison")
st.caption(
    "Paste Worker Sales by Product Category reports for 2026 and 2025. "
    "This compares Sales, UPS, Mailbox, Notary, Packing, and Public Service Payments."
)

# ============================================================
# Store Setup
# ============================================================
CENTER_NAMES = {
    "1504": "Yucaipa",
    "5027": "Beaumont",
    "5052": "Ontario",
    "5255": "Summit",
    "5778": "Citrus",
    "6176": "Sierra",
    "6769": "Loma Linda",
    "7261": "Ayala",
}

CENTER_ORDER = ["1504", "5027", "5052", "5255", "5778", "6176", "6769", "7261"]

MONEY_COLS = [
    "Sales",
    "UPS",
    "Mailbox",
    "Notary",
    "Packing",
    "Public Service Payments",
]

PCT_COLS = [
    "UPS %",
    "Mailbox %",
    "Notary %",
    "Packing %",
    "Public Service Payments %",
]

DISPLAY_COLS = [
    "Center",
    "Store",
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

COMPARE_COLS = [
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

# ============================================================
# Helper Functions
# ============================================================
def clean_text(text):
    if not text:
        return ""
    text = text.replace("\t", " ")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ ]{2,}", " ", text)
    return text.strip()


def money_to_float(value):
    if value is None:
        return 0.0
    return float(value.replace("$", "").replace(",", "").strip())


def find_center(text):
    patterns = [
        r"Center\s*:?\s*\n\s*(\d{4})",
        r"Center\s*:?\s*(\d{4})",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            return match.group(1)

    return None


def parse_report(text):
    text = clean_text(text)
    center = find_center(text)

    rows = {}

    row_pattern = re.compile(
        r"^[+\-]?\s*(.+?)\s+(\d+)\s+(\d+)\s+\$([\d,]+\.\d{2})\s+\$([\d,]+\.\d{2})\s+\$([\d,]+\.\d{2})\s*$",
        re.MULTILINE
    )

    for category, customer_count, item_count, income, customer_avg, item_avg in row_pattern.findall(text):
        category_clean = category.strip().lower()
        rows[category_clean] = money_to_float(income)

    totals_match = re.search(
        r"Totals\s+\d+\s+\d+\s+\$([\d,]+\.\d{2})",
        text,
        re.I
    )

    total_sales = money_to_float(totals_match.group(1)) if totals_match else 0.0

    def find_income(keywords):
        total = 0.0
        for category, amount in rows.items():
            if any(keyword in category for keyword in keywords):
                total += amount
        return total

    ups = find_income([
        "shipping charges",
        "ups shipping",
    ])

    mailbox = find_income([
        "mailbox service",
        "mailbox",
        "mailboxes",
    ])

    notary = find_income([
        "notary",
    ])

    packing = find_income([
        "packaging materials",
        "packing materials",
        "packaging service fee",
        "packing service fee",
        "packaging service fees",
        "packing service fees",
        "retail shipping supplies",
        "office supplies",
    ])

    psp = find_income([
        "public service payments",
        "public svcs payments",
        "psp",
    ])

    def pct_of_sales(amount):
        return amount / total_sales if total_sales else 0.0

    return {
        "Center": center,
        "Store": CENTER_NAMES.get(center, ""),
        "Sales": total_sales,
        "UPS": ups,
        "UPS %": pct_of_sales(ups),
        "Mailbox": mailbox,
        "Mailbox %": pct_of_sales(mailbox),
        "Notary": notary,
        "Notary %": pct_of_sales(notary),
        "Packing": packing,
        "Packing %": pct_of_sales(packing),
        "Public Service Payments": psp,
        "Public Service Payments %": pct_of_sales(psp),
    }


def build_dataframe(reports):
    data = [parse_report(report) for report in reports if report.strip()]

    if not data:
        return pd.DataFrame(columns=DISPLAY_COLS)

    df = pd.DataFrame(data)

    df = (
        df.set_index("Center")
        .reindex(CENTER_ORDER)
        .dropna(how="all")
        .reset_index()
    )

    df["Store"] = df["Center"].map(CENTER_NAMES)

    for col in MONEY_COLS + PCT_COLS:
        if col not in df.columns:
            df[col] = 0.0

    return df[DISPLAY_COLS]


def format_table(df):
    out = df.copy()

    for col in MONEY_COLS:
        if col in out.columns:
            out[col] = out[col].fillna(0).apply(lambda x: f"${x:,.0f}")

    for col in PCT_COLS:
        if col in out.columns:
            out[col] = out[col].fillna(0).apply(lambda x: f"{x:.1%}")

    return out


def style_variance(value):
    if isinstance(value, (int, float)):
        if value > 0:
            return "color: green; font-weight: bold;"
        if value < 0:
            return "color: red; font-weight: bold;"
    return ""


def format_variance_table(df):
    return (
        df.style
        .map(style_variance, subset=COMPARE_COLS)
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
        })
    )


def build_variance(df_current, df_prior):
    current = df_current.set_index("Center")
    prior = df_prior.set_index("Center")

    all_centers = [c for c in CENTER_ORDER if c in current.index or c in prior.index]

    rows = []

    for center in all_centers:
        row = {
            "Center": center,
            "Store": CENTER_NAMES.get(center, ""),
        }

        for col in COMPARE_COLS:
            current_value = current[col].get(center, 0) if col in current.columns and center in current.index else 0
            prior_value = prior[col].get(center, 0) if col in prior.columns and center in prior.index else 0
            row[col] = current_value - prior_value

        rows.append(row)

    return pd.DataFrame(rows)[DISPLAY_COLS]


def build_summary(df_2026, df_2025):
    total_2026_sales = df_2026["Sales"].sum()
    total_2025_sales = df_2025["Sales"].sum()

    rows = []

    for category in ["UPS", "Mailbox", "Notary", "Packing", "Public Service Payments"]:
        current = df_2026[category].sum()
        prior = df_2025[category].sum()

        rows.append({
            "Category": category,
            "2026": current,
            "2026 % of Sales": current / total_2026_sales if total_2026_sales else 0,
            "2025": prior,
            "2025 % of Sales": prior / total_2025_sales if total_2025_sales else 0,
            "Variance": current - prior,
            "Variance %": ((current - prior) / prior) if prior else 0,
        })

    return pd.DataFrame(rows)


def style_summary(df):
    return (
        df.style
        .map(style_variance, subset=["Variance", "Variance %"])
        .format({
            "2026": "${:,.0f}",
            "2026 % of Sales": "{:.1%}",
            "2025": "${:,.0f}",
            "2025 % of Sales": "{:.1%}",
            "Variance": "${:,.0f}",
            "Variance %": "{:.1%}",
        })
    )


def build_rankings(df, category):
    ranking = df[["Center", "Store", category]].copy()
    ranking = ranking.sort_values(category, ascending=False)
    ranking.insert(0, "Rank", range(1, len(ranking) + 1))
    return ranking


# ============================================================
# UI Tabs
# ============================================================
tab_input, tab_2026, tab_2025, tab_variance, tab_summary, tab_rankings = st.tabs([
    "Paste Reports",
    "2026 Results",
    "2025 Results",
    "Variance",
    "Summary",
    "Rankings",
])

# ============================================================
# Input Tab
# ============================================================
with tab_input:
    st.subheader("Paste Reports")

    st.info(
        "Paste the 2026 reports on the left and the matching 2025 reports on the right. "
        "You can paste one report per store."
    )

    left, right = st.columns(2, gap="large")

    reports_2026 = []
    reports_2025 = []

    with left:
        st.markdown("### 2026 Reports")

        for i in range(8):
            center_label = CENTER_ORDER[i]
            store_label = CENTER_NAMES.get(center_label, "")

            with st.expander(f"2026 Report #{i + 1} — {center_label} {store_label}", expanded=i == 0):
                reports_2026.append(
                    st.text_area(
                        "Paste 2026 report here",
                        height=220,
                        key=f"report_2026_{i}",
                        label_visibility="collapsed",
                    )
                )

    with right:
        st.markdown("### 2025 Reports")

        for i in range(8):
            center_label = CENTER_ORDER[i]
            store_label = CENTER_NAMES.get(center_label, "")

            with st.expander(f"2025 Report #{i + 1} — {center_label} {store_label}", expanded=i == 0):
                reports_2025.append(
                    st.text_area(
                        "Paste 2025 report here",
                        height=220,
                        key=f"report_2025_{i}",
                        label_visibility="collapsed",
                    )
                )

    compare_clicked = st.button(
        "Compare Reports",
        type="primary",
        use_container_width=True
    )

# ============================================================
# Processing
# ============================================================
if compare_clicked:
    df_2026 = build_dataframe(reports_2026)
    df_2025 = build_dataframe(reports_2025)

    if df_2026.empty or df_2025.empty:
        st.error("Please paste at least one 2026 report and one 2025 report.")
        st.stop()

    variance_df = build_variance(df_2026, df_2025)
    summary_df = build_summary(df_2026, df_2025)

    st.session_state["df_2026"] = df_2026
    st.session_state["df_2025"] = df_2025
    st.session_state["variance_df"] = variance_df
    st.session_state["summary_df"] = summary_df

# ============================================================
# Results Display
# ============================================================
if "df_2026" not in st.session_state:
    with tab_2026:
        st.warning("Paste reports and click Compare Reports first.")

    with tab_2025:
        st.warning("Paste reports and click Compare Reports first.")

    with tab_variance:
        st.warning("Paste reports and click Compare Reports first.")

    with tab_summary:
        st.warning("Paste reports and click Compare Reports first.")

    with tab_rankings:
        st.warning("Paste reports and click Compare Reports first.")

else:
    df_2026 = st.session_state["df_2026"]
    df_2025 = st.session_state["df_2025"]
    variance_df = st.session_state["variance_df"]
    summary_df = st.session_state["summary_df"]

    total_2026_sales = df_2026["Sales"].sum()
    total_2025_sales = df_2025["Sales"].sum()
    total_variance = total_2026_sales - total_2025_sales
    total_variance_pct = total_variance / total_2025_sales if total_2025_sales else 0

    with tab_2026:
        st.subheader("2026 Results")

        col1, col2, col3 = st.columns(3)
        col1.metric("2026 Total Sales", f"${total_2026_sales:,.0f}")
        col2.metric("2026 UPS Sales", f"${df_2026['UPS'].sum():,.0f}")
        col3.metric("2026 Packing Sales", f"${df_2026['Packing'].sum():,.0f}")

        st.dataframe(
            format_table(df_2026),
            hide_index=True,
            use_container_width=True
        )

    with tab_2025:
        st.subheader("2025 Results")

        col1, col2, col3 = st.columns(3)
        col1.metric("2025 Total Sales", f"${total_2025_sales:,.0f}")
        col2.metric("2025 UPS Sales", f"${df_2025['UPS'].sum():,.0f}")
        col3.metric("2025 Packing Sales", f"${df_2025['Packing'].sum():,.0f}")

        st.dataframe(
            format_table(df_2025),
            hide_index=True,
            use_container_width=True
        )

    with tab_variance:
        st.subheader("Variance Compared to Last Year")

        col1, col2, col3 = st.columns(3)
        col1.metric("2026 Sales", f"${total_2026_sales:,.0f}")
        col2.metric("2025 Sales", f"${total_2025_sales:,.0f}")
        col3.metric(
            "Variance",
            f"${total_variance:,.0f}",
            f"{total_variance_pct:.1%}"
        )

        st.dataframe(
            format_variance_table(variance_df),
            hide_index=True,
            use_container_width=True
        )

    with tab_summary:
        st.subheader("Company Summary")

        st.dataframe(
            style_summary(summary_df),
            hide_index=True,
            use_container_width=True
        )

    with tab_rankings:
        st.subheader("Store Rankings")

        ranking_category = st.selectbox(
            "Choose ranking category",
            ["Sales", "UPS", "Mailbox", "Notary", "Packing", "Public Service Payments"]
        )

        col1, col2 = st.columns(2)

        with col1:
            st.markdown(f"### 2026 Ranking by {ranking_category}")
            ranking_2026 = build_rankings(df_2026, ranking_category)
            st.dataframe(
                ranking_2026.style.format({ranking_category: "${:,.0f}"}),
                hide_index=True,
                use_container_width=True
            )

        with col2:
            st.markdown(f"### 2025 Ranking by {ranking_category}")
            ranking_2025 = build_rankings(df_2025, ranking_category)
            st.dataframe(
                ranking_2025.style.format({ranking_category: "${:,.0f}"}),
                hide_index=True,
                use_container_width=True
            )
