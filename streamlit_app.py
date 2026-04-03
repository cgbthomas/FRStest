# streamlit_app.py
import re
import io
import calendar
from dataclasses import dataclass
from datetime import datetime, date, timedelta

import pandas as pd
import streamlit as st

# ============================================================
# App Config
# ============================================================
st.set_page_config(page_title="Weekly Multi-Store Performance Scorecard", layout="wide")
st.title("Weekly Multi-Store Performance Scorecard")
st.caption(
    "Paste up to 8 'Worker Sales by Product Category' reports. "
    "Calculates Net Sales (Sales - PSP), exact-calendar prorated goals, Air-to-Ground %, "
    "labor budget vs actual, KPI flags, and summary comments."
)

# ============================================================
# Defaults
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

# Add/update these every month going forward
MONTHLY_GOALS = {
    "2026-03": {
        "1504": 88400.0,
        "5027": 85240.0,
        "5052": 54300.0,
        "5255": 73300.0,
        "5778": 63800.0,
        "6176": 71100.0,
        "6769": 59330.0,
        "7261": 49360.0,
    },
    "2026-04": {
        "1504": None,
        "5027": None,
        "5052": None,
        "5255": None,
        "5778": None,
        "6176": None,
        "6769": None,
        "7261": None,
    },
    "2026-05": {
        "1504": None,
        "5027": None,
        "5052": None,
        "5255": None,
        "5778": None,
        "6176": None,
        "6769": None,
        "7261": None,
    },
    "2026-06": {
        "1504": None,
        "5027": None,
        "5052": None,
        "5255": None,
        "5778": None,
        "6176": None,
        "6769": None,
        "7261": None,
    },
    "2026-07": {
        "1504": None,
        "5027": None,
        "5052": None,
        "5255": None,
        "5778": None,
        "6176": None,
        "6769": None,
        "7261": None,
    },
    "2026-08": {
        "1504": None,
        "5027": None,
        "5052": None,
        "5255": None,
        "5778": None,
        "6176": None,
        "6769": None,
        "7261": None,
    },
    "2026-09": {
        "1504": None,
        "5027": None,
        "5052": None,
        "5255": None,
        "5778": None,
        "6176": None,
        "6769": None,
        "7261": None,
    },
    "2026-10": {
        "1504": None,
        "5027": None,
        "5052": None,
        "5255": None,
        "5778": None,
        "6176": None,
        "6769": None,
        "7261": None,
    },
    "2026-11": {
        "1504": None,
        "5027": None,
        "5052": None,
        "5255": None,
        "5778": None,
        "6176": None,
        "6769": None,
        "7261": None,
    },
    "2026-12": {
        "1504": None,
        "5027": None,
        "5052": None,
        "5255": None,
        "5778": None,
        "6176": None,
        "6769": None,
        "7261": None,
    },
}

# Set your 6-day stores here if any
DEFAULT_6_DAY_STORES = set()

# KPI targets / thresholds
KPI_TARGETS = {
    "Average UPS Package": 14.00,
    "Average Meter Per Package": 2.50,
    "Air-to-Ground % (Air/Domestic)": 0.10,
    "Mailbox Sales": 400.0,
    "Printing & Copies": 700.0,
    "Packaging/Office Supplies/Service Fees": 900.0,
}

# Kiosk group assignment (labor tables)
KIOSK_GROUP = {
    "kiosk_1": {"5778", "6176", "6769", "7261"},
    "kiosk_2": {"1504", "5027", "5052", "5255"},
}

# Each row: (sales, budget_hours, labor_pct, budget_labor_dollars)
LABOR_BUDGET_KIOSK_1 = [
    (10000, 175, 0.38, 1700),
    (10500, 176, 0.36, 1785),
    (11000, 177, 0.35, 1870),
    (11500, 178, 0.33, 1955),
    (12000, 179, 0.32, 2040),
    (12500, 180, 0.31, 2125),
    (13000, 181, 0.30, 2210),
    (13500, 182, 0.29, 2295),
    (14000, 183, 0.28, 2380),
    (14500, 184, 0.27, 2465),
    (15000, 185, 0.27, 2550),
    (15500, 186, 0.26, 2635),
    (16000, 187, 0.25, 2720),
    (16500, 188, 0.24, 2805),
    (17000, 189, 0.24, 2890),
    (17500, 190, 0.23, 2975),
    (18000, 191, 0.23, 3060),
    (18500, 192, 0.22, 3145),
    (19000, 193, 0.22, 3230),
    (19500, 194, 0.21, 3315),
    (20000, 195, 0.21, 3400),
    (21000, 196, 0.20, 3570),
    (22000, 197, 0.19, 3740),
    (23000, 198, 0.19, 3910),
    (24000, 199, 0.18, 4080),
    (25000, 200, 0.17, 4250),
]

LABOR_BUDGET_KIOSK_2 = [
    (10000, 168, 0.36, 1700),
    (10500, 169, 0.35, 1785),
    (11000, 170, 0.33, 1870),
    (11500, 171, 0.32, 1955),
    (12000, 172, 0.31, 2040),
    (12500, 173, 0.30, 2125),
    (13000, 174, 0.29, 2210),
    (13500, 175, 0.28, 2295),
    (14000, 176, 0.27, 2380),
    (14500, 177, 0.26, 2465),
    (15000, 178, 0.26, 2550),
    (15500, 179, 0.25, 2635),
    (16000, 180, 0.24, 2720),
    (16500, 181, 0.24, 2805),
    (17000, 182, 0.23, 2890),
    (17500, 183, 0.22, 2975),
    (18000, 184, 0.22, 3060),
    (18500, 185, 0.22, 3145),
    (19000, 186, 0.21, 3230),
    (19500, 187, 0.21, 3315),
    (20000, 188, 0.20, 3400),
    (21000, 189, 0.19, 3570),
    (22000, 190, 0.19, 3740),
    (23000, 191, 0.18, 3910),
    (24000, 192, 0.17, 4080),
    (25000, 193, 0.17, 4250),
]

# Category alias map
CATEGORY_ALIASES = {
    "Shipping Charges (UPS)": [
        "Shipping Charges (UPS)",
        "Shipping Charges - UPS",
        "UPS Shipping Charges",
        "Shipping Charges UPS",
    ],
    "Public Service Payments": [
        "Public Service Payments",
        "Public Svcs Payments",
        "PSP",
    ],
    "Mailbox Service": [
        "Mailbox Service",
        "Mailbox",
        "Mailboxes",
    ],
    "Meter Mail": [
        "Meter Mail",
        "Meter",
        "Postage Meter",
    ],
    "Packaging Service Fee": [
        "Packaging Service Fee",
        "Packing Service Fee",
        "Packaging Service Fees",
        "Packing Service Fees",
    ],
    "Packaging Materials": [
        "Packaging Materials",
        "Packing Materials",
    ],
    "Retail Shipping Supplies": [
        "Retail Shipping Supplies",
        "Shipping Supplies",
        "Retail Supplies",
    ],
    "Office Supplies": [
        "Office Supplies",
        "Supplies",
    ],
    "Printing": [
        "Printing",
        "Print",
    ],
    "Copies": [
        "Copies",
        "Copy",
    ],
    "Color Copies": [
        "Color Copies",
        "Colour Copies",
    ],
    "Notary": [
        "Notary",
        "Notary Service",
    ],
    "Shred": [
        "Shred",
        "Shredding",
        "Shred Sales",
        "Shredding Sales",
    ],
}

UPS_AIR_KEYWORDS = [
    "nda",
    "next day air",
    "next-day air",
    "2da",
    "2nd day air",
    "second day air",
    "2-day air",
    "3 day",
    "3day",
    "3-day",
    "3 day select",
    "3ds",
]

UPS_GROUND_KEYWORDS = [
    "ground",
    "gnd",
]

# ============================================================
# Data Structures
# ============================================================
@dataclass
class ParsedReport:
    center: str | None
    date_range_str: str | None
    start_date: date | None
    end_date: date | None
    rows: dict
    totals: dict | None
    raw_text: str


# ============================================================
# Helpers
# ============================================================
def normalize_report_text(text: str) -> str:
    if text is None:
        return ""
    text = text.replace("\t", " ")
    text = re.sub(r"[–—]", "-", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = "\n".join(re.sub(r"[ ]{2,}", " ", line).strip() for line in text.splitlines())
    return text.strip()


def split_reports(raw: str) -> list[str]:
    raw = (raw or "").strip()
    if not raw:
        return []

    seps = ["\n-----\n", "\n—\n", "\n=====\n", "\n---\n"]
    for sep in seps:
        if sep in raw:
            parts = [p.strip() for p in raw.split(sep) if p.strip()]
            if len(parts) > 1:
                return parts

    header_pat = re.compile(r"(Worker Sales by Product Category)", re.IGNORECASE)
    hits = list(header_pat.finditer(raw))
    if len(hits) <= 1:
        return [raw]

    parts = []
    for i, h in enumerate(hits):
        start = h.start()
        end = hits[i + 1].start() if i + 1 < len(hits) else len(raw)
        parts.append(raw[start:end].strip())
    return [p for p in parts if p]


def money_to_float(s: str) -> float:
    return float(s.replace(",", "").replace("$", "").strip())


def parse_date_any(s: str):
    s = (s or "").strip()
    for fmt in ("%m/%d/%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    return None


def find_field_block_value(text: str, field_name: str) -> str | None:
    pattern = re.compile(rf"^{re.escape(field_name)}\s*:\s*$", re.IGNORECASE | re.MULTILINE)
    m = pattern.search(text)
    if not m:
        return None

    after = text[m.end():].splitlines()
    for line in after:
        if line.strip():
            return line.strip()
    return None


def parse_worker_sales_by_category(text: str) -> ParsedReport:
    text = normalize_report_text(text)

    center = None
    center_line = find_field_block_value(text, "Center")
    if center_line and re.fullmatch(r"\d{3,5}", center_line):
        center = center_line.strip()
    else:
        m = re.search(r"Center:\s*(\d+)", text, flags=re.IGNORECASE)
        if m:
            center = m.group(1).strip()

    start_date = end_date = None
    date_range_str = None

    m = re.search(
        r"Date Range:\s*\n([0-9/]+)\s*\n(?:to|-)\s*\n([0-9/]+)",
        text,
        flags=re.IGNORECASE,
    )
    if m:
        start_date = parse_date_any(m.group(1))
        end_date = parse_date_any(m.group(2))
    else:
        m2 = re.search(r"Date Range:\s*([0-9/]+)\s*(?:to|-)\s*([0-9/]+)", text, flags=re.IGNORECASE)
        if m2:
            start_date = parse_date_any(m2.group(1))
            end_date = parse_date_any(m2.group(2))

    if start_date and end_date:
        date_range_str = f"{start_date.month}/{start_date.day}/{start_date.year} to {end_date.month}/{end_date.day}/{end_date.year}"
    elif m:
        date_range_str = f"{m.group(1).strip()} to {m.group(2).strip()}"

    row_re = re.compile(
        r"^[\+\-]\s*(.+?)\s+(\d+)\s+(\d+)\s+\$([\d,]+\.\d{2})\s+\$([\d,]+\.\d{2})\s+\$([\d,]+\.\d{2})\s*$",
        flags=re.MULTILINE,
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

    totals = None
    m = re.search(
        r"^Totals\s+(\d+)\s+(\d+)\s+\$([\d,]+\.\d{2})\s+\$([\d,]+\.\d{2})\s+\$([\d,]+\.\d{2})\s*$",
        text,
        flags=re.MULTILINE | re.IGNORECASE,
    )
    if m:
        totals = {
            "customer_count": int(m.group(1)),
            "item_count": int(m.group(2)),
            "income": money_to_float(m.group(3)),
            "customer_avg": money_to_float(m.group(4)),
            "item_avg": money_to_float(m.group(5)),
        }

    return ParsedReport(
        center=center,
        date_range_str=date_range_str,
        start_date=start_date,
        end_date=end_date,
        rows=rows,
        totals=totals,
        raw_text=text,
    )


def fmt_money(x):
    return "—" if x is None or pd.isna(x) else f"${x:,.2f}"


def fmt_pct(x):
    return "—" if x is None or pd.isna(x) else f"{x:.1%}"


def fmt_num(x, decimals=1):
    return "—" if x is None or pd.isna(x) else f"{x:,.{decimals}f}"


def daterange_inclusive(d1: date, d2: date):
    cur = d1
    while cur <= d2:
        yield cur
        cur += timedelta(days=1)


def is_sunday(d: date) -> bool:
    return d.weekday() == 6


def month_days(year: int, month: int):
    return calendar.monthrange(year, month)[1]


def count_sundays_in_month(year: int, month: int) -> int:
    sundays = 0
    dim = month_days(year, month)
    for day in range(1, dim + 1):
        if is_sunday(date(year, month, day)):
            sundays += 1
    return sundays


def prorated_goal_exact_calendar(monthly_goal: float, start: date, end: date, six_day_store: bool) -> float | None:
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


def get_kiosk_type(center: str) -> str | None:
    if center in KIOSK_GROUP["kiosk_1"]:
        return "kiosk_1"
    if center in KIOSK_GROUP["kiosk_2"]:
        return "kiosk_2"
    return None


def labor_budget_table(center: str):
    kt = get_kiosk_type(center)
    if kt == "kiosk_1":
        return LABOR_BUDGET_KIOSK_1
    if kt == "kiosk_2":
        return LABOR_BUDGET_KIOSK_2
    return None


def pick_labor_budget(center: str, projected_sales: float | None):
    table = labor_budget_table(center)
    if not table or projected_sales is None or pd.isna(projected_sales):
        return {"budget_hours": None, "budget_labor_dollars": None, "budget_labor_pct": None}

    ps = float(projected_sales)

    for sales, hrs, pct, dollars in table:
        if ps <= sales:
            return {"budget_hours": float(hrs), "budget_labor_dollars": float(dollars), "budget_labor_pct": float(pct)}

    sales, hrs, pct, dollars = table[-1]
    return {"budget_hours": float(hrs), "budget_labor_dollars": float(dollars), "budget_labor_pct": float(pct)}


def find_row_key(rows: dict, canonical: str) -> str | None:
    if canonical in rows:
        return canonical

    for alias in CATEGORY_ALIASES.get(canonical, []):
        if alias in rows:
            return alias

    canon_low = canonical.lower()
    for k in rows.keys():
        if canon_low in k.lower():
            return k

    return None


def find_income(rows: dict, canonical: str, default=0.0):
    k = find_row_key(rows, canonical)
    if k is None:
        return default
    return rows.get(k, {}).get("income", default)


def find_customer_count(rows: dict, canonical: str, default=0):
    k = find_row_key(rows, canonical)
    if k is None:
        return default
    return int(rows.get(k, {}).get("customer_count", default) or 0)


def classify_ups_domestic_service(category: str) -> str | None:
    if not category:
        return None
    c = category.lower()

    if "ups" not in c and "shipping" not in c:
        return None

    if "international" in c:
        return None

    if any(k in c for k in UPS_AIR_KEYWORDS):
        return "air"
    if any(k in c for k in UPS_GROUND_KEYWORDS):
        return "ground"

    return None


def compute_air_ground_counts(rows: dict) -> dict:
    air_pkgs = 0
    ground_pkgs = 0
    found_service_lines = False

    for cat, payload in rows.items():
        svc = classify_ups_domestic_service(cat)
        if svc is None:
            continue
        found_service_lines = True
        cnt = int(payload.get("customer_count", 0) or 0)
        if svc == "air":
            air_pkgs += cnt
        elif svc == "ground":
            ground_pkgs += cnt

    if not found_service_lines:
        return {"air_pkgs": None, "ground_pkgs": None, "domestic_pkgs": None, "air_to_ground_pct": None}

    domestic = air_pkgs + ground_pkgs
    air_pct = (air_pkgs / domestic) if domestic else None
    return {"air_pkgs": air_pkgs, "ground_pkgs": ground_pkgs, "domestic_pkgs": domestic, "air_to_ground_pct": air_pct}


def kpi_status(actual, target, higher_is_better=True, tolerance=0.05):
    if actual is None or pd.isna(actual) or target is None or pd.isna(target):
        return "N/A"

    if higher_is_better:
        if actual >= target:
            return "Good"
        elif actual >= target * (1 - tolerance):
            return "Watch"
        return "Low"
    else:
        if actual <= target:
            return "Good"
        elif actual <= target * (1 + tolerance):
            return "Watch"
        return "High"


def build_store_comment(row):
    comments = []

    var_pct = row.get("Variance %")
    labor_dollar_var = row.get("Labor $ Variance (Est Actual - Budget)")
    avg_ups = row.get("Average UPS Package")
    avg_meter = row.get("Average Meter Per Package")
    mailbox = row.get("Mailbox Sales")
    printing = row.get("Printing & Copies")
    packaging = row.get("Packaging/Office Supplies/Service Fees")
    air_pct = row.get("Air-to-Ground % (Air/Domestic)")

    if pd.notna(var_pct):
        if var_pct >= 0.05:
            comments.append("Sales ahead of goal")
        elif var_pct >= 0:
            comments.append("Slightly ahead of goal")
        else:
            comments.append("Sales behind goal")

    if pd.notna(labor_dollar_var):
        if labor_dollar_var > 0:
            comments.append("Labor over budget")
        elif labor_dollar_var < 0:
            comments.append("Labor under budget")

    if pd.notna(avg_ups):
        if avg_ups >= KPI_TARGETS["Average UPS Package"]:
            comments.append("Strong UPS avg")
        else:
            comments.append("UPS avg low")

    if pd.notna(avg_meter):
        if avg_meter >= KPI_TARGETS["Average Meter Per Package"]:
            comments.append("Strong meter avg")
        else:
            comments.append("Meter avg soft")

    if pd.notna(mailbox) and mailbox < KPI_TARGETS["Mailbox Sales"]:
        comments.append("Mailbox sales soft")

    if pd.notna(printing) and printing < KPI_TARGETS["Printing & Copies"]:
        comments.append("Print/copy sales soft")

    if pd.notna(packaging) and packaging < KPI_TARGETS["Packaging/Office Supplies/Service Fees"]:
        comments.append("Packaging attachment soft")

    if pd.notna(air_pct):
        if air_pct >= KPI_TARGETS["Air-to-Ground % (Air/Domestic)"]:
            comments.append("Air mix healthy")
        else:
            comments.append("Air mix low")

    return "; ".join(comments) if comments else "Stable week"


def color_status(val):
    if val == "Good":
        return "background-color: #d9ead3; color: #000000;"
    if val == "Watch":
        return "background-color: #fff2cc; color: #000000;"
    if val in ("Low", "High"):
        return "background-color: #f4cccc; color: #000000;"
    return ""


def color_positive_negative(val, positive_good=True):
    if val is None or pd.isna(val):
        return ""
    if positive_good:
        if val > 0:
            return "background-color: #d9ead3; color: #000000;"
        if val < 0:
            return "background-color: #f4cccc; color: #000000;"
        return ""
    else:
        if val < 0:
            return "background-color: #d9ead3; color: #000000;"
        if val > 0:
            return "background-color: #f4cccc; color: #000000;"
        return ""


def style_scorecard(df: pd.DataFrame):
    styler = df.style

    if "Variance vs Prorated Goal" in df.columns:
        styler = styler.map(
            lambda v: color_positive_negative(v, positive_good=True),
            subset=["Variance vs Prorated Goal"],
        )
    if "Variance %" in df.columns:
        styler = styler.map(
            lambda v: color_positive_negative(v, positive_good=True),
            subset=["Variance %"],
        )
    if "Labor Hours Variance (Actual - Budget)" in df.columns:
        styler = styler.map(
            lambda v: color_positive_negative(v, positive_good=False),
            subset=["Labor Hours Variance (Actual - Budget)"],
        )
    if "Labor $ Variance (Est Actual - Budget)" in df.columns:
        styler = styler.map(
            lambda v: color_positive_negative(v, positive_good=False),
            subset=["Labor $ Variance (Est Actual - Budget)"],
        )

    status_cols = [c for c in df.columns if c.endswith("Status")]
    for col in status_cols:
        styler = styler.map(color_status, subset=[col])

    return styler


def dataframe_for_export(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    money_cols = [
        "Total Sales",
        "Public Service Payments",
        "Net Sales (Sales - PSP)",
        "Total UPS Shipping",
        "Average UPS Package",
        "Total Meter Sales",
        "Average Meter Per Package",
        "Packaging/Office Supplies/Service Fees",
        "Notary + Public Service Payments",
        "Mailbox Sales",
        "Printing & Copies",
        "Shred Sales",
        "Monthly Goal",
        "Prorated Goal (Exact Calendar)",
        "Variance vs Prorated Goal",
        "Labor Budget $",
        "Est. Hourly Rate (from chart)",
        "Est. Actual Labor $",
        "Labor $ Variance (Est Actual - Budget)",
    ]

    pct_cols = [
        "Variance %",
        "Air-to-Ground % (Air/Domestic)",
        "Labor Budget %",
        "Est. Actual Labor %",
    ]

    for col in money_cols:
        if col in out.columns:
            out[col] = out[col].apply(fmt_money)

    for col in pct_cols:
        if col in out.columns:
            out[col] = out[col].apply(fmt_pct)

    num_cols_1 = [
        "Labor Budget Hours",
        "Actual Labor Hours",
        "Labor Hours Variance (Actual - Budget)",
        "UPS Air Packages (NDA/2DA/3Day)",
        "UPS Ground Packages",
        "UPS Domestic Packages (Air+Ground)",
    ]
    for col in num_cols_1:
        if col in out.columns:
            out[col] = out[col].apply(lambda x: fmt_num(x, 1))

    return out


# ============================================================
# Month Setup
# ============================================================
st.subheader("1) Monthly Setup")

available_months = sorted(MONTHLY_GOALS.keys())
default_index = available_months.index("2026-03") if "2026-03" in available_months else 0
selected_month = st.selectbox("Select reporting month", available_months, index=default_index)

selected_goals = MONTHLY_GOALS.get(selected_month, {})

prefill_rows = []
for c in CENTER_ORDER:
    prefill_rows.append(
        {
            "Center": c,
            "Store": CENTER_NAMES.get(c, ""),
            "Monthly Goal ($)": selected_goals.get(c, None),
            "6-Day Store (Closed Sundays)": c in DEFAULT_6_DAY_STORES,
        }
    )

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
    key="goals_editor",
)

st.divider()

# ============================================================
# Report Input
# ============================================================
st.subheader("2) Paste Reports (up to 8)")

with st.expander("Optional: Paste ALL reports in one box (auto-split)", expanded=False):
    big_paste = st.text_area(
        "Paste multiple reports here. Separate with ----- or paste them back-to-back.",
        height=250,
        placeholder="Paste multiple full reports here...",
        key="big_paste",
    )

cols = st.columns(2, gap="large")
report_texts = []
for i in range(8):
    with cols[i % 2]:
        report_texts.append(
            st.text_area(
                f"Store Report #{i+1}",
                height=200,
                placeholder="Paste one full 'Worker Sales by Product Category' report here...",
                key=f"report_{i+1}",
            )
        )

st.divider()

# ============================================================
# Labor Input
# ============================================================
st.subheader("3) Labor (Budget vs Actual)")

labor_sales_basis = st.radio(
    "Which sales number should drive the labor chart lookup?",
    options=["Total Sales", "Net Sales (Sales - PSP)"],
    horizontal=True,
)

labor_input_rows = []
for c in CENTER_ORDER:
    labor_input_rows.append(
        {
            "Center": c,
            "Store": CENTER_NAMES.get(c, ""),
            "Kiosk Table": get_kiosk_type(c) or "",
            "Actual Labor Hours": None,
        }
    )

labor_df = pd.DataFrame(labor_input_rows)

labor_df = st.data_editor(
    labor_df,
    use_container_width=True,
    num_rows="fixed",
    column_config={
        "Center": st.column_config.TextColumn(disabled=True),
        "Store": st.column_config.TextColumn(disabled=True),
        "Kiosk Table": st.column_config.TextColumn(disabled=True),
        "Actual Labor Hours": st.column_config.NumberColumn(min_value=0),
    },
    key="labor_editor",
)

st.caption(
    "Budget $ and % come from your kiosk labor chart brackets. "
    "Estimated actual labor $ uses the chart's implied hourly rate (Budget$ / BudgetHours)."
)

st.divider()

process = st.button("Process All Reports", type="primary", use_container_width=True)

# ============================================================
# Processing
# ============================================================
if process:
    goal_lookup = {}
    for _, r in goals_df.iterrows():
        c = str(r.get("Center") or "").strip()
        g = r.get("Monthly Goal ($)")
        s6 = bool(r.get("6-Day Store (Closed Sundays)") or False)
        if c:
            goal_lookup[c] = (float(g) if pd.notna(g) else None, s6)

    actual_hours_lookup = {}
    for _, r in labor_df.iterrows():
        c = str(r.get("Center") or "").strip()
        ah = r.get("Actual Labor Hours")
        if c and pd.notna(ah):
            actual_hours_lookup[c] = float(ah)

    sources = []
    if (big_paste or "").strip():
        sources = split_reports(big_paste)[:8]
        if len(sources) < 8:
            for t in report_texts:
                if t.strip():
                    sources.append(t)
                if len(sources) >= 8:
                    break
    else:
        sources = report_texts

    diagnostics = []
    rows_out = []

    for idx, text in enumerate(sources, start=1):
        if not (text or "").strip():
            continue

        report = parse_worker_sales_by_category(text)
        center = (report.center or "").strip()
        store_name = CENTER_NAMES.get(center, "")
        date_range = report.date_range_str or ""
        start_date = report.start_date
        end_date = report.end_date
        rows = report.rows
        totals = report.totals

        if not center:
            diagnostics.append(f"Report #{idx}: Could not detect Center.")
        if not (start_date and end_date):
            diagnostics.append(f"Report #{idx} ({center or 'Unknown'}): Could not detect Date Range.")
        if not totals:
            diagnostics.append(f"Report #{idx} ({center or 'Unknown'}): Could not detect Totals row.")

        total_sales = totals["income"] if totals else None
        ups_shipping = find_income(rows, "Shipping Charges (UPS)", default=None)
        ups_packages = find_customer_count(rows, "Shipping Charges (UPS)", default=0) or 0

        air_ground = compute_air_ground_counts(rows)
        ups_domestic_pkgs = air_ground["domestic_pkgs"] if air_ground["domestic_pkgs"] is not None else None
        pkgs_for_avgs = ups_packages if ups_packages > 0 else (ups_domestic_pkgs or 0)
        pkgs_for_avgs = pkgs_for_avgs if pkgs_for_avgs > 0 else None

        meter_sales = find_income(rows, "Meter Mail", default=None)
        mailbox_sales = find_income(rows, "Mailbox Service", default=None)

        notary_income = find_income(rows, "Notary", default=0.0)
        psp_income = find_income(rows, "Public Service Payments", default=0.0)
        notary_plus_psp = notary_income + psp_income

        net_sales = (total_sales - psp_income) if (total_sales is not None) else None

        printing_copies = (
            find_income(rows, "Printing", default=0.0)
            + find_income(rows, "Copies", default=0.0)
            + find_income(rows, "Color Copies", default=0.0)
        )

        packaging_bucket = (
            find_income(rows, "Office Supplies", default=0.0)
            + find_income(rows, "Packaging Materials", default=0.0)
            + find_income(rows, "Packaging Service Fee", default=0.0)
            + find_income(rows, "Retail Shipping Supplies", default=0.0)
        )

        shred_sales = find_income(rows, "Shred", default=0.0)

        avg_ups_pkg = (ups_shipping / pkgs_for_avgs) if (ups_shipping is not None and pkgs_for_avgs) else None
        avg_meter_pkg = (meter_sales / pkgs_for_avgs) if (meter_sales is not None and pkgs_for_avgs) else None

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
        variance_pct = (variance / prorated_goal) if (variance is not None and prorated_goal) else None

        projected_sales_for_labor = total_sales if labor_sales_basis == "Total Sales" else net_sales
        lb = pick_labor_budget(center, projected_sales_for_labor)

        budget_hours = lb["budget_hours"]
        budget_labor_dollars = lb["budget_labor_dollars"]
        budget_labor_pct = lb["budget_labor_pct"]

        actual_hours = actual_hours_lookup.get(center)

        hourly_rate_est = None
        actual_labor_dollars_est = None

        if budget_hours and budget_labor_dollars:
            hourly_rate_est = float(budget_labor_dollars) / float(budget_hours)

        if actual_hours is not None and hourly_rate_est is not None:
            actual_labor_dollars_est = actual_hours * hourly_rate_est

        labor_hours_var = (actual_hours - budget_hours) if (actual_hours is not None and budget_hours is not None) else None
        labor_dollars_var = (
            (actual_labor_dollars_est - budget_labor_dollars)
            if (actual_labor_dollars_est is not None and budget_labor_dollars is not None)
            else None
        )
        actual_labor_pct_est = (
            (actual_labor_dollars_est / projected_sales_for_labor)
            if (actual_labor_dollars_est is not None and projected_sales_for_labor)
            else None
        )

        avg_ups_status = kpi_status(avg_ups_pkg, KPI_TARGETS["Average UPS Package"], higher_is_better=True)
        avg_meter_status = kpi_status(avg_meter_pkg, KPI_TARGETS["Average Meter Per Package"], higher_is_better=True)
        air_mix_status = kpi_status(air_ground["air_to_ground_pct"], KPI_TARGETS["Air-to-Ground % (Air/Domestic)"], higher_is_better=True)
        mailbox_status = kpi_status(mailbox_sales, KPI_TARGETS["Mailbox Sales"], higher_is_better=True)
        printing_status = kpi_status(printing_copies, KPI_TARGETS["Printing & Copies"], higher_is_better=True)
        packaging_status = kpi_status(packaging_bucket, KPI_TARGETS["Packaging/Office Supplies/Service Fees"], higher_is_better=True)

        row_payload = {
            "Center": center or f"(Report #{idx})",
            "Store": store_name,
            "Date Range": date_range,
            "Workweek": "6-day" if is_6day else "7-day",
            "Total Sales": total_sales,
            "Public Service Payments": psp_income,
            "Net Sales (Sales - PSP)": net_sales,
            "Prorated Goal (Exact Calendar)": prorated_goal,
            "Variance vs Prorated Goal": variance,
            "Variance %": variance_pct,
            "Total UPS Shipping": ups_shipping,
            "Average UPS Package": avg_ups_pkg,
            "Average UPS Package Status": avg_ups_status,
            "UPS Air Packages (NDA/2DA/3Day)": air_ground["air_pkgs"],
            "UPS Ground Packages": air_ground["ground_pkgs"],
            "UPS Domestic Packages (Air+Ground)": air_ground["domestic_pkgs"],
            "Air-to-Ground % (Air/Domestic)": air_ground["air_to_ground_pct"],
            "Air Mix Status": air_mix_status,
            "Total Meter Sales": meter_sales,
            "Average Meter Per Package": avg_meter_pkg,
            "Average Meter Per Package Status": avg_meter_status,
            "Packaging/Office Supplies/Service Fees": packaging_bucket,
            "Packaging Status": packaging_status,
            "Notary + Public Service Payments": notary_plus_psp,
            "Mailbox Sales": mailbox_sales,
            "Mailbox Status": mailbox_status,
            "Printing & Copies": printing_copies,
            "Printing Status": printing_status,
            "Shred Sales": shred_sales,
            "Monthly Goal": monthly_goal,
            "Kiosk Type": get_kiosk_type(center),
            "Labor Sales Basis": labor_sales_basis,
            "Labor Budget Hours": budget_hours,
            "Labor Budget $": budget_labor_dollars,
            "Labor Budget %": budget_labor_pct,
            "Actual Labor Hours": actual_hours,
            "Est. Hourly Rate (from chart)": hourly_rate_est,
            "Est. Actual Labor $": actual_labor_dollars_est,
            "Labor Hours Variance (Actual - Budget)": labor_hours_var,
            "Labor $ Variance (Est Actual - Budget)": labor_dollars_var,
            "Est. Actual Labor %": actual_labor_pct_est,
            "_pkgs_for_avgs": pkgs_for_avgs or 0,
            "_is_6day": 1 if is_6day else 0,
        }

        row_payload["Store Comment"] = build_store_comment(row_payload)
        rows_out.append(row_payload)

    if not rows_out:
        st.error("No reports found. Paste at least one report and try again.")
        st.stop()

    df = pd.DataFrame(rows_out)

    df6 = df[df["_is_6day"] == 1].copy()
    df7 = df[df["_is_6day"] == 0].copy()

    def build_totals_row(label: str, dfx: pd.DataFrame):
        pkgs = dfx["_pkgs_for_avgs"].sum()
        ups_ship = dfx["Total UPS Shipping"].sum(min_count=1)
        meter = dfx["Total Meter Sales"].sum(min_count=1)

        ts = dfx["Total Sales"].sum(min_count=1)
        psp = dfx["Public Service Payments"].sum(min_count=1)
        net = dfx["Net Sales (Sales - PSP)"].sum(min_count=1)

        avg_ups = (ups_ship / pkgs) if pkgs else None
        avg_meter = (meter / pkgs) if pkgs else None

        pror_goal = dfx["Prorated Goal (Exact Calendar)"].sum(min_count=1)
        var = (net - pror_goal) if (pd.notna(net) and pd.notna(pror_goal)) else None
        var_pct = (var / pror_goal) if (var is not None and pror_goal) else None

        air_pkgs = dfx["UPS Air Packages (NDA/2DA/3Day)"].sum(min_count=1)
        ground_pkgs = dfx["UPS Ground Packages"].sum(min_count=1)
        domestic_pkgs = dfx["UPS Domestic Packages (Air+Ground)"].sum(min_count=1)

        air_pkgs = None if pd.isna(air_pkgs) else float(air_pkgs)
        ground_pkgs = None if pd.isna(ground_pkgs) else float(ground_pkgs)
        domestic_pkgs = None if pd.isna(domestic_pkgs) else float(domestic_pkgs)
        air_pct = (air_pkgs / domestic_pkgs) if (air_pkgs is not None and domestic_pkgs) else None

        labor_budget_hours = dfx["Labor Budget Hours"].sum(min_count=1)
        labor_budget_dollars = dfx["Labor Budget $"].sum(min_count=1)
        actual_hours = dfx["Actual Labor Hours"].sum(min_count=1)
        est_actual_dollars = dfx["Est. Actual Labor $"].sum(min_count=1)

        labor_budget_hours = None if pd.isna(labor_budget_hours) else float(labor_budget_hours)
        labor_budget_dollars = None if pd.isna(labor_budget_dollars) else float(labor_budget_dollars)
        actual_hours = None if pd.isna(actual_hours) else float(actual_hours)
        est_actual_dollars = None if pd.isna(est_actual_dollars) else float(est_actual_dollars)

        labor_hours_var = (actual_hours - labor_budget_hours) if (actual_hours is not None and labor_budget_hours is not None) else None
        labor_dollars_var = (
            (est_actual_dollars - labor_budget_dollars)
            if (est_actual_dollars is not None and labor_budget_dollars is not None)
            else None
        )
        actual_labor_pct_est = (
            (est_actual_dollars / net)
            if (est_actual_dollars is not None and net and labor_sales_basis == "Net Sales (Sales - PSP)")
            else ((est_actual_dollars / ts) if (est_actual_dollars is not None and ts and labor_sales_basis == "Total Sales") else None)
        )

        total_row = {
            "Center": label,
            "Store": "",
            "Date Range": "",
            "Workweek": "",
            "Total Sales": ts,
            "Public Service Payments": psp,
            "Net Sales (Sales - PSP)": net,
            "Prorated Goal (Exact Calendar)": pror_goal,
            "Variance vs Prorated Goal": var,
            "Variance %": var_pct,
            "Total UPS Shipping": ups_ship,
            "Average UPS Package": avg_ups,
            "Average UPS Package Status": "",
            "UPS Air Packages (NDA/2DA/3Day)": air_pkgs,
            "UPS Ground Packages": ground_pkgs,
            "UPS Domestic Packages (Air+Ground)": domestic_pkgs,
            "Air-to-Ground % (Air/Domestic)": air_pct,
            "Air Mix Status": "",
            "Total Meter Sales": meter,
            "Average Meter Per Package": avg_meter,
            "Average Meter Per Package Status": "",
            "Packaging/Office Supplies/Service Fees": dfx["Packaging/Office Supplies/Service Fees"].sum(min_count=1),
            "Packaging Status": "",
            "Notary + Public Service Payments": dfx["Notary + Public Service Payments"].sum(min_count=1),
            "Mailbox Sales": dfx["Mailbox Sales"].sum(min_count=1),
            "Mailbox Status": "",
            "Printing & Copies": dfx["Printing & Copies"].sum(min_count=1),
            "Printing Status": "",
            "Shred Sales": dfx["Shred Sales"].sum(min_count=1),
            "Monthly Goal": dfx["Monthly Goal"].sum(min_count=1),
            "Kiosk Type": "",
            "Labor Sales Basis": labor_sales_basis,
            "Labor Budget Hours": labor_budget_hours,
            "Labor Budget $": labor_budget_dollars,
            "Labor Budget %": None,
            "Actual Labor Hours": actual_hours,
            "Est. Hourly Rate (from chart)": None,
            "Est. Actual Labor $": est_actual_dollars,
            "Labor Hours Variance (Actual - Budget)": labor_hours_var,
            "Labor $ Variance (Est Actual - Budget)": labor_dollars_var,
            "Est. Actual Labor %": actual_labor_pct_est,
            "Store Comment": "",
        }
        return total_row

    footer_rows = []
    if len(df6):
        footer_rows.append(build_totals_row("TOTAL (6-day stores)", df6))
    if len(df7):
        footer_rows.append(build_totals_row("TOTAL (7-day stores)", df7))
    footer_rows.append(build_totals_row("TOTAL (All stores)", df))

    df_display = df.drop(columns=["_pkgs_for_avgs", "_is_6day"], errors="ignore")
    df_display = pd.concat([df_display, pd.DataFrame(footer_rows)], ignore_index=True)

    col_order = [
        "Center",
        "Store",
        "Date Range",
        "Workweek",
        "Net Sales (Sales - PSP)",
        "Prorated Goal (Exact Calendar)",
        "Variance vs Prorated Goal",
        "Variance %",
        "Total Sales",
        "Public Service Payments",
        "Total UPS Shipping",
        "Average UPS Package",
        "Average UPS Package Status",
        "UPS Air Packages (NDA/2DA/3Day)",
        "UPS Ground Packages",
        "UPS Domestic Packages (Air+Ground)",
        "Air-to-Ground % (Air/Domestic)",
        "Air Mix Status",
        "Total Meter Sales",
        "Average Meter Per Package",
        "Average Meter Per Package Status",
        "Packaging/Office Supplies/Service Fees",
        "Packaging Status",
        "Notary + Public Service Payments",
        "Mailbox Sales",
        "Mailbox Status",
        "Printing & Copies",
        "Printing Status",
        "Shred Sales",
        "Monthly Goal",
        "Kiosk Type",
        "Labor Sales Basis",
        "Labor Budget Hours",
        "Actual Labor Hours",
        "Labor Hours Variance (Actual - Budget)",
        "Labor Budget $",
        "Est. Actual Labor $",
        "Labor $ Variance (Est Actual - Budget)",
        "Labor Budget %",
        "Est. Actual Labor %",
        "Est. Hourly Rate (from chart)",
        "Store Comment",
    ]
    df_display = df_display[[c for c in col_order if c in df_display.columns]]

    # ============================================================
    # Dashboard KPIs
    # ============================================================
    st.subheader("4) Weekly Dashboard")

    total_net = df["Net Sales (Sales - PSP)"].sum(min_count=1)
    total_goal = df["Prorated Goal (Exact Calendar)"].sum(min_count=1)
    total_var = (total_net - total_goal) if pd.notna(total_net) and pd.notna(total_goal) else None
    total_var_pct = (total_var / total_goal) if total_var is not None and total_goal else None
    total_labor_var = df["Labor $ Variance (Est Actual - Budget)"].sum(min_count=1)

    kpi_cols = st.columns(4)
    with kpi_cols[0]:
        st.metric("Total Net Sales", fmt_money(total_net))
    with kpi_cols[1]:
        st.metric("Prorated Goal", fmt_money(total_goal))
    with kpi_cols[2]:
        st.metric("Variance vs Goal", fmt_money(total_var), fmt_pct(total_var_pct))
    with kpi_cols[3]:
        st.metric("Labor $ Variance", fmt_money(total_labor_var))

    st.divider()

    # ============================================================
    # Results
    # ============================================================
    st.subheader("5) Results Table")

    styled = style_scorecard(df_display)
    st.dataframe(styled, use_container_width=True)

    if diagnostics:
        with st.expander("Diagnostics (Parsing / Missing Fields)", expanded=False):
            for msg in diagnostics:
                st.write(f"- {msg}")
            st.write("")
            st.write("Tip: Air-to-Ground requires service-level UPS lines (NDA/2DA/3 Day/Ground). If not present, those fields will show blank.")

    # ============================================================
    # Export
    # ============================================================
    export_df = dataframe_for_export(df_display)

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        export_df.to_excel(writer, index=False, sheet_name="Scorecard")

    st.download_button(
        "Download Excel",
        data=buffer.getvalue(),
        file_name=f"weekly_multi_store_scorecard_{selected_month}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )

    # ============================================================
    # Quick Summary
    # ============================================================
    st.subheader("6) Quick Summary")

    lines = []
    for _, r in df.iterrows():
        lines.append(
            f"{r['Center']} {r['Store']} ({r['Workweek']}): "
            f"Net {fmt_money(r['Net Sales (Sales - PSP)'])} | "
            f"Goal {fmt_money(r['Prorated Goal (Exact Calendar)'])} | "
            f"Var {fmt_money(r['Variance vs Prorated Goal'])} ({fmt_pct(r.get('Variance %'))}) | "
            f"UPS {fmt_money(r['Total UPS Shipping'])} (Avg {fmt_money(r['Average UPS Package'])}) | "
            f"Meter Avg {fmt_money(r['Average Meter Per Package'])} | "
            f"Mailbox {fmt_money(r['Mailbox Sales'])} | "
            f"Print {fmt_money(r['Printing & Copies'])} | "
            f"Labor Hrs {fmt_num(r.get('Actual Labor Hours'), 1)} vs Bud {fmt_num(r.get('Labor Budget Hours'), 1)} | "
            f"{r.get('Store Comment', '')}"
        )

    lines.append("")
    for fr in footer_rows:
        lines.append(
            f"{fr['Center']}: "
            f"Net {fmt_money(fr.get('Net Sales (Sales - PSP)'))} | "
            f"Goal {fmt_money(fr.get('Prorated Goal (Exact Calendar)'))} | "
            f"Var {fmt_money(fr.get('Variance vs Prorated Goal'))} ({fmt_pct(fr.get('Variance %'))}) | "
            f"Labor $ Var {fmt_money(fr.get('Labor $ Variance (Est Actual - Budget)'))}"
        )

    st.text_area("Copy/paste summary", "\n".join(lines), height=320)

    # ============================================================
    # Leadership Notes View
    # ============================================================
    st.subheader("7) Store Notes Snapshot")

    notes_df = df[[
        "Center",
        "Store",
        "Net Sales (Sales - PSP)",
        "Prorated Goal (Exact Calendar)",
        "Variance vs Prorated Goal",
        "Labor $ Variance (Est Actual - Budget)",
        "Average UPS Package",
        "Average Meter Per Package",
        "Mailbox Sales",
        "Printing & Copies",
        "Packaging/Office Supplies/Service Fees",
        "Store Comment",
    ]].copy()

    notes_df["Net Sales (Sales - PSP)"] = notes_df["Net Sales (Sales - PSP)"].apply(fmt_money)
    notes_df["Prorated Goal (Exact Calendar)"] = notes_df["Prorated Goal (Exact Calendar)"].apply(fmt_money)
    notes_df["Variance vs Prorated Goal"] = notes_df["Variance vs Prorated Goal"].apply(fmt_money)
    notes_df["Labor $ Variance (Est Actual - Budget)"] = notes_df["Labor $ Variance (Est Actual - Budget)"].apply(fmt_money)
    notes_df["Average UPS Package"] = notes_df["Average UPS Package"].apply(fmt_money)
    notes_df["Average Meter Per Package"] = notes_df["Average Meter Per Package"].apply(fmt_money)
    notes_df["Mailbox Sales"] = notes_df["Mailbox Sales"].apply(fmt_money)
    notes_df["Printing & Copies"] = notes_df["Printing & Copies"].apply(fmt_money)
    notes_df["Packaging/Office Supplies/Service Fees"] = notes_df["Packaging/Office Supplies/Service Fees"].apply(fmt_money)

    st.dataframe(notes_df, use_container_width=True)
