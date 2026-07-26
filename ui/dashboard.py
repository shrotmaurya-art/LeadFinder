# TODO: T10.1 preflight_check not yet implemented.
# When scripts/preflight_check.py is built, uncomment and enable the block below:
#
#   from scripts.preflight_check import run as preflight_run
#   import streamlit as st
#   ok, msg = preflight_run()
#   if not ok:
#       st.error(f"Environment check failed: {msg}")
#       st.stop()

import streamlit as st
from crm.database import Database
from utils.timeutil import today_local

st.set_page_config(page_title="LeadFinder Dashboard", layout="wide")

# ── Sidebar filters ──────────────────────────────────────────────

db = Database()


@st.cache_data(ttl=30)
def _fetch_filter_options() -> tuple[list[str], list[str]]:
    leads = db.get_leads()
    cities = sorted({r["city"] for r in leads if r.get("city")})
    categories = sorted({r["category"] for r in leads if r.get("category")})
    return cities, categories


cities, categories = _fetch_filter_options()

with st.sidebar:
    st.header("Filters")
    city_selection = st.selectbox("City", ["all"] + cities, index=0)
    category_selection = st.multiselect("Category", ["all"] + categories, default=["all"])

# Resolve filter values: "all" → None (no filter)
city_filter = None if city_selection == "all" else city_selection
cat_filter = None if "all" in category_selection else category_selection

# ── Data fetching (cached) ───────────────────────────────────────


@st.cache_data(ttl=30)
def _fetch_counts(for_date: str, city: str | None, cats: tuple[str, ...] | None) -> dict:
    cats_list = list(cats) if cats else None
    return db.get_dashboard_counts(for_date, city=city, categories=cats_list)


for_date = today_local()
counts = _fetch_counts(for_date, city_filter, tuple(cat_filter) if cat_filter else None)

# ── Metric cards ─────────────────────────────────────────────────

st.title("LeadFinder Dashboard")

card_defs = [
    ("Businesses Found Today", counts["businesses_found_today"]),
    ("New Leads", counts["new_leads"]),
    ("Messages Ready", counts["messages_ready"]),
    ("Sent Today", counts["sent_today"]),
    ("Replies", counts["replies"]),
    ("Meetings", counts["meetings"]),
    ("Clients", counts["clients"]),
]

cols = st.columns(7)
for col, (label, value) in zip(cols, card_defs):
    with col:
        st.metric(label=label, value=value)
