import re
import io
import calendar
from datetime import datetime, date, timedelta

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Multi-Store Report Calculator", layout="wide")
st.title("Multi-Store Report Calculator")
st.caption("Paste up to 8 'Worker Sales by Product Category' reports. Calculates Net Sales (Sales - PSP), exact-calendar prorated goals, and totals.")

# -----------------------------
# Defaults (Feb goals you provided)
# -----------------------------
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

FEB_GOALS_2026 = {
    "1504": 80000.0,
    "5027": 90200.0,
    "5052": 59300.0,
    "5255": 63200.0,
    "5778": 56550.0,
    "6176": 63100.0,
    "6769": 53600.0,
    "7261": 59600.0,
}

# -----------------------------
# Helpers
# -----------------------------
def money_to_float(s: str) -> float:
    return float(s.replace(",", "").replace("$", "").strip())

def parse_date_any(s: str):
    s = s.strip()
    for fmt in ("%m/%d/%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    return None

def parse_worker_sales_by_category(text: str):
    # Center
    center = None
    m = re.search(r"Center:\s*\n(\d+)", text, flags=re.IGNORECASE)
    if m:
        center = m.group(1).strip()

    # Date range
    start_date = end_date = None
    m = re.search(r"Date Range:\s*\n([0-9/]+)\s*\nto\s*\n([0-9/]+)", text, flags=re.IGNORECASE)
    if m:
        start_date = parse_date_any(m.group(1))
        end_date = parse_date_any(m.group(2))

    date_range_str = None
    if start_date and end_date:
        date_range_str = f"{start_date.month}/{start_date.day}/{start_date.year} to {end_date.month}/{end_date.day}/{end_date.year}"
    elif m:
        date_range_str = f"{m.group(1).strip()} to {m.group(2).strip()}"

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

    # Totals line
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

    meta = {
        "center": center,
        "date_range": date_range_str,
        "start_date": start_date,
        "end_date": end_date,
    }
    return meta, rows, totals

def get_income(rows, category_name, default=0.0):
    return rows.get(category_name, {}).get("income", default)

def get_customer_count(rows, category_name, default=0):
    return rows.get(category_name, {}).get("customer_count", default)

def fmt_money(x):
    return "—" if x is None or pd.isna(x) else f"${x:,.2f}"

def daterange_inclusive(d1: date, d2: date):
    cur = d1
    while cur <= d2:
        yield cur
        cur += timedelta(days=1)

def is_sunday(d: date) -> bool:
    return d.weekday() == 6  # Monday=0 ... Sunday=6

def month_days(year: int, month: int):
    return calendar.monthrange(year, month)[1]

def count_sundays_in_month(year: int, month: int) -> int:
    sundays = 0
    dim = month_days(year, month)
    for day in range(1, dim + 1):
        if is_sunday(date(year, month, day)):
            sundays += 1
    return sundays

def prorated_goal_exact_calendar(monthly_goal: float, start: date, end: date, six_day_store: bool) -> float:
    """
    Exact calendar proration, day-by-day (handles ranges that span months).
    - 7-day store: daily goal = monthly_goal / days_in_month
    - 6-day store: daily goal = monthly_goal / (days_in_month - sundays_in_month), and Sundays count 0
    """
    if monthly_goal is None or start is None or end is None:
        return None

    total = 0.0
    for d in daterange_inclusive(start, end):
        y, m = d.year, d.month
        dim = month_days(y, m)

        if six_day_store:
            workdays_in_month = dim - count_sundays_in_month(y, m)
            if workdays_in_month <= 0:
                continue
            daily_goal = monthly_goal / workdays_in_month
            if is_sunday(d):
                daily_goal = 0.0
        else:
            daily_goal = monthly_goal / dim

        total += daily_goal

    return total

# -----------------------------
# UI: Multi store input
# -----------------------------
st.subheader("Paste Reports (up to 8)")
cols = st.columns(2, gap="large")
report_texts = []
for i in range(8):
    with cols[i % 2]:
        report_texts.append(
            st.text_area(
                f"Store Report #{i+1}",
                height=220,
                placeholder="Paste one full 'Worker Sales by Product Category' report here..."
            )
        )

st.divider()
st.subheader("Monthly Goals + Store Workweek")

st.caption("Goals prefilled for Feb 2026. Check the two centers that are 6-day stores (closed Sundays).")

# Prefill table with your 8 centers
prefill_rows = []
for c in ["1504","5027","5052","5255","5778","6176","6769","7261"]:
    prefill_rows.append({
        "Center": c,
        "Store": CENTER_NAMES.get(c, ""),
        "Monthly Goal ($)": FEB_GOALS_2026.get(c, None),
        "6-Day Store (Closed Sundays)": False,  # YOU CHECK the two stores here
    })

goals_df = pd.DataFrame(prefill_rows)

goals_df = st.data_editor(
    goals_df,
    use_container_width=True,
    num_rows="fixed",
    column_config={
        "Center": st.column_config.TextColumn(disabled=True),
        "Store": st.column_config.TextColumn(disabled=True),
        "Monthly Goal ($)": st.column_config.NumberColumn(min_value=0),
        "6-Day Store (Closed Sundays)": st.column_config.CheckboxColumn(),
    },
    key="goals_editor"
)

process = st.button("Process All Reports", type="primary", use_container_width=True)

# -----------------------------
# Processing
# -----------------------------
if process:
    # Build goal lookup
    goal_lookup = {}
    for _, r in goals_df.iterrows():
        c = str(r.get("Center") or "").strip()
        g = r.get("Monthly Goal ($)")
        s6 = bool(r.get("6-Day Store (Closed Sundays)") or False)
        if c and pd.notna(g):
            goal_lookup[c] = (float(g), s6)

    rows_out = []

    for idx, text in enumerate(report_texts, start=1):
        if not text.strip():
            continue

        meta, rows, totals = parse_worker_sales_by_category(text)

        center = (meta.get("center") or "").strip()
        store_name = CENTER_NAMES.get(center, "")
        date_range = meta.get("date_range") or ""
        start_date = meta.get("start_date")
        end_date = meta.get("end_date")

        # Total sales from Totals row
        total_sales = totals["income"] if totals else None

        # Locked to Shipping Charges (UPS)
        ups_shipping = get_income(rows, "Shipping Charges (UPS)", default=None)
        ups_packages = get_customer_count(rows, "Shipping Charges (UPS)", default=0) or None

        meter_sales = get_income(rows, "Meter Mail", default=None)
        mailbox_sales = get_income(rows, "Mailbox Service", default=None)

        notary_income = get_income(rows, "Notary", default=0.0)
        psp_income = get_income(rows, "Public Service Payments", default=0.0)
        notary_plus_psp = notary_income + psp_income

        # Net Sales (Sales - PSP)
        net_sales = (total_sales - psp_income) if (total_sales is not None) else None

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

        shred_sales = (
            get_income(rows, "Shred Sales", default=0.0)
            + get_income(rows, "Shred", default=0.0)
            + get_income(rows, "Shredding", default=0.0)
        )

        # Derived metrics
        avg_ups_pkg = (ups_shipping / ups_packages) if (ups_shipping is not None and ups_packages) else None
        avg_meter_pkg = (meter_sales / ups_packages) if (meter_sales is not None and ups_packages) else None

        # Goals
        monthly_goal = None
        is_6day = False
        if center and center in goal_lookup:
            monthly_goal, is_6day = goal_lookup[center]

        prorated_goal = (
            prorated_goal_exact_calendar(monthly_goal, start_date, end_date, six_day_store=is_6day)
            if (monthly_goal is not None and start_date and end_date)
            else None
        )
        variance = (net_sales - prorated_goal) if (net_sales is not None and prorated_goal is not None) else None

        rows_out.append({
            "Center": center or f"(Report #{idx})",
            "Store": store_name,
            "Date Range": date_range,
            "Workweek": "6-day" if is_6day else "7-day",

            "Total Sales": total_sales,
            "Public Service Payments": psp_income,
            "Net Sales (Sales - PSP)": net_sales,

            "Average Meter Per Package": avg_meter_pkg,
            "Total UPS Shipping": ups_shipping,
            "Average UPS Package": avg_ups_pkg,
            "Total Meter Sales": meter_sales,

            "Packaging/Office Supplies/Service Fees": packaging_bucket,
            "Notary + Public Service Payments": notary_plus_psp,
            "Mailbox Sales": mailbox_sales,
            "Printing & Copies": printing_copies,
            "Shred Sales": shred_sales,

            "Monthly Goal": monthly_goal,
            "Prorated Goal (Exact Calendar)": prorated_goal,
            "Variance vs Prorated Goal": variance,

            # For totals / weighted avgs
            "_ups_packages": ups_packages or 0,
            "_is_6day": 1 if is_6day else 0
        })

    if not rows_out:
        st.error("No reports pasted yet. Paste at least one report and try again.")
        st.stop()

    df = pd.DataFrame(rows_out)

    # Subtotals by workweek group
    df6 = df[df["_is_6day"] == 1].copy()
    df7 = df[df["_is_6day"] == 0].copy()

    def build_totals_row(label: str, dfx: pd.DataFrame):
        pkgs = dfx["_ups_packages"].sum()
        ups_ship = dfx["Total UPS Shipping"].sum(min_count=1)
        meter = dfx["Total Meter Sales"].sum(min_count=1)

        ts = dfx["Total Sales"].sum(min_count=1)
        psp = dfx["Public Service Payments"].sum(min_count=1)
        net = dfx["Net Sales (Sales - PSP)"].sum(min_count=1)

        avg_ups = (ups_ship / pkgs) if pkgs else None
        avg_meter = (meter / pkgs) if pkgs else None

        pror_goal = dfx["Prorated Goal (Exact Calendar)"].sum(min_count=1)
        var = (net - pror_goal) if (pd.notna(net) and pd.notna(pror_goal)) else None

        return {
            "Center": label,
            "Store": "",
            "Date Range": "",
            "Workweek": "",

            "Total Sales": ts,
            "Public Service Payments": psp,
            "Net Sales (Sales - PSP)": net,

            "Average Meter Per Package": avg_meter,
            "Total UPS Shipping": ups_ship,
            "Average UPS Package": avg_ups,
            "Total Meter Sales": meter,

            "Packaging/Office Supplies/Service Fees": dfx["Packaging/Office Supplies/Service Fees"].sum(min_count=1),
            "Notary + Public Service Payments": dfx["Notary + Public Service Payments"].sum(min_count=1),
            "Mailbox Sales": dfx["Mailbox Sales"].sum(min_count=1),
            "Printing & Copies": dfx["Printing & Copies"].sum(min_count=1),
            "Shred Sales": dfx["Shred Sales"].sum(min_count=1),

            "Monthly Goal": dfx["Monthly Goal"].sum(min_count=1),
            "Prorated Goal (Exact Calendar)": pror_goal,
            "Variance vs Prorated Goal": var,
        }

    footer_rows = []
    if len(df6):
        footer_rows.append(build_totals_row("TOTAL (6-day stores)", df6))
    if len(df7):
        footer_rows.append(build_totals_row("TOTAL (7-day stores)", df7))
    footer_rows.append(build_totals_row("TOTAL (All stores)", df))

    df_display = df.drop(columns=["_ups_packages", "_is_6day"], errors="ignore")
    df_display = pd.concat([df_display, pd.DataFrame(footer_rows)], ignore_index=True)

    # Column order
    col_order = [
        "Center", "Store", "Date Range", "Workweek",
        "Total Sales", "Public Service Payments", "Net Sales (Sales - PSP)",
        "Average Meter Per Package", "Total UPS Shipping", "Average UPS Package", "Total Meter Sales",
        "Packaging/Office Supplies/Service Fees", "Notary + Public Service Payments",
        "Mailbox Sales", "Printing & Copies", "Shred Sales",
        "Monthly Goal", "Prorated Goal (Exact Calendar)", "Variance vs Prorated Goal",
    ]
    df_display = df_display[[c for c in col_order if c in df_display.columns]]

    st.subheader("Results (All Stores)")
    st.dataframe(df_display, use_container_width=True)

    # Excel export
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df_display.to_excel(writer, index=False, sheet_name="Recap")

    st.download_button(
        "Download Excel",
        data=buffer.getvalue(),
        file_name="multi_store_recap.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )

    # Quick summary
    st.subheader("Quick Summary")
    lines = []
    for _, r in df.iterrows():
        lines.append(
            f"{r['Center']} {r['Store']} ({r['Workweek']}): "
            f"Net {fmt_money(r['Net Sales (Sales - PSP)'])} | "
            f"UPS {fmt_money(r['Total UPS Shipping'])} (Avg {fmt_money(r['Average UPS Package'])}) | "
            f"Meter {fmt_money(r['Total Meter Sales'])} (Avg {fmt_money(r['Average Meter Per Package'])}) | "
            f"Goal {fmt_money(r['Prorated Goal (Exact Calendar)'])} | Var {fmt_money(r['Variance vs Prorated Goal'])}"
        )

    lines.append("")
    for fr in footer_rows:
        lines.append(
            f"{fr['Center']}: Net {fmt_money(fr['Net Sales (Sales - PSP)'])} | "
            f"Goal {fmt_money(fr['Prorated Goal (Exact Calendar)'])} | Var {fmt_money(fr['Variance vs Prorated Goal'])}"
        )

    st.text_area("Copy/paste summary", "\n".join(lines), height=280)
