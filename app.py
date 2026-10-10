"""
app.py — Brand Visibility Intelligence Dashboard
Streamlit application with 6 tabs, sidebar filters (backed by SQLite).
"""

import os
import subprocess
import sys
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

import db_utils as db

# ─── Page config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Brand Visibility Intelligence Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Custom CSS ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

  html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

  .main { background: #0d0f1a; }
  .block-container { padding: 1.5rem 2rem; }

  /* Sidebar */
  [data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0f1629 0%, #1a1f35 100%);
    border-right: 1px solid rgba(99,102,241,0.2);
  }
  [data-testid="stSidebar"] .stMarkdown h2 { color: #a5b4fc; font-size: 1.1rem; }
  [data-testid="stSidebar"] label { color: #94a3b8 !important; font-size: 0.85rem; }

  /* KPI Cards */
  .kpi-card {
    background: linear-gradient(135deg, #1e2340 0%, #252b45 100%);
    border: 1px solid rgba(99,102,241,0.25);
    border-radius: 16px;
    padding: 1.25rem 1.5rem;
    text-align: center;
    box-shadow: 0 4px 20px rgba(0,0,0,0.3);
    transition: transform 0.2s ease, box-shadow 0.2s ease;
  }
  .kpi-card:hover {
    transform: translateY(-3px);
    box-shadow: 0 8px 30px rgba(99,102,241,0.2);
    border-color: rgba(99,102,241,0.5);
  }
  .kpi-value {
    font-size: 2rem;
    font-weight: 800;
    background: linear-gradient(135deg, #6366f1, #a78bfa);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    line-height: 1.1;
  }
  .kpi-label {
    color: #64748b;
    font-size: 0.78rem;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-top: 0.4rem;
  }
  .kpi-icon { font-size: 1.5rem; margin-bottom: 0.4rem; }

  /* Section headers */
  .section-header {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    margin-bottom: 1rem;
    padding-bottom: 0.6rem;
    border-bottom: 2px solid rgba(99,102,241,0.3);
  }
  .section-header h3 {
    color: #e2e8f0;
    font-size: 1.1rem;
    font-weight: 600;
    margin: 0;
  }

  /* Tab styling */
  [data-testid="stTabs"] [data-baseweb="tab-list"] {
    background: #1a1f35;
    border-radius: 12px;
    padding: 4px;
    gap: 4px;
  }
  [data-testid="stTabs"] [data-baseweb="tab"] {
    background: transparent;
    color: #64748b;
    border-radius: 8px;
    padding: 0.5rem 1.2rem;
    font-weight: 500;
    font-size: 0.85rem;
    border: none;
  }
  [data-testid="stTabs"] [aria-selected="true"] {
    background: linear-gradient(135deg, #6366f1, #7c3aed) !important;
    color: white !important;
  }

  /* Table styling */
  .stDataFrame { border-radius: 12px; overflow: hidden; }

  /* Divider */
  hr { border-color: rgba(99,102,241,0.15); }

  /* Alert / info boxes */
  .setup-box {
    background: linear-gradient(135deg, #1e3a5f, #1e2f5f);
    border: 1px solid #3b82f6;
    border-radius: 16px;
    padding: 2rem;
    text-align: center;
    color: #93c5fd;
  }
  .setup-box h2 { color: #60a5fa; margin-bottom: 0.5rem; }
</style>
""", unsafe_allow_html=True)


# ─── Plotly theme ─────────────────────────────────────────────────────────────
PLOT_THEME = "plotly_dark"
COLORS     = px.colors.qualitative.Vivid
PRIMARY    = "#6366f1"
GRADIENT   = ["#6366f1", "#8b5cf6", "#a78bfa", "#c4b5fd"]

PLOT_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter", color="#94a3b8", size=12),
    margin=dict(l=10, r=10, t=40, b=10),
    legend=dict(
        bgcolor="rgba(30,35,64,0.8)",
        bordercolor="rgba(99,102,241,0.3)",
        borderwidth=1,
        font=dict(color="#94a3b8", size=11),
    ),
    xaxis=dict(gridcolor="rgba(99,102,241,0.1)", linecolor="rgba(99,102,241,0.2)"),
    yaxis=dict(gridcolor="rgba(99,102,241,0.1)", linecolor="rgba(99,102,241,0.2)"),
)


def apply_layout(fig, title=""):
    fig.update_layout(**PLOT_LAYOUT, title=dict(text=title, font=dict(color="#e2e8f0", size=14)))
    return fig


# ─── Helpers ──────────────────────────────────────────────────────────────────
def fmt_num(val, prefix="", suffix="", decimals=0):
    """Format number for KPI display."""
    try:
        v = float(val)
        if decimals == 0:
            return f"{prefix}{int(v):,}{suffix}"
        return f"{prefix}{v:,.{decimals}f}{suffix}"
    except Exception:
        return str(val) if val is not None else "N/A"


def kpi_card(icon, label, value):
    return f"""
    <div class="kpi-card">
      <div class="kpi-icon">{icon}</div>
      <div class="kpi-value">{value}</div>
      <div class="kpi-label">{label}</div>
    </div>
    """


def section_header(icon, title):
    st.markdown(f"""
    <div class="section-header">
      <span style="font-size:1.2rem">{icon}</span>
      <h3>{title}</h3>
    </div>
    """, unsafe_allow_html=True)


# ─── DB Check / Setup ─────────────────────────────────────────────────────────
def run_etl():
    """Run ETL pipeline and rerun app."""
    with st.spinner("⚙️ Running ETL pipeline — this may take a minute..."):
        result = subprocess.run(
            [sys.executable, "etl_pipeline.py"],
            cwd=os.path.dirname(os.path.abspath(__file__)),
            capture_output=True, text=True
        )
        if result.returncode != 0:
            st.error(f"ETL failed:\n```\n{result.stderr}\n```")
        else:
            st.success("✅ Pipeline complete! Refreshing dashboard...")
            st.rerun()


# ─── Sidebar ──────────────────────────────────────────────────────────────────
def render_sidebar():
    with st.sidebar:
        st.markdown("""
        <div style="text-align:center;padding:1rem 0 1.5rem;">
          <div style="font-size:2.5rem">📊</div>
          <div style="font-weight:700;font-size:1rem;color:#a5b4fc;">Brand Visibility</div>
          <div style="font-size:0.75rem;color:#475569;">Intelligence Dashboard</div>
        </div>
        """, unsafe_allow_html=True)

        st.divider()
        st.markdown("## 🔍 Filters")

        opts = db.get_filter_options()
        if not opts:
            st.warning("No data loaded yet.")
            return {}, opts

        filters = {}

        filters["keywords"] = st.multiselect(
            "🔑 Keywords",
            options=opts.get("keywords", []),
            default=[],
            placeholder="All keywords",
        )
        filters["platforms"] = st.multiselect(
            "🏪 Platforms",
            options=opts.get("platforms", []),
            default=[],
            placeholder="All platforms",
        )
        filters["brands"] = st.multiselect(
            "🏷️ Brands",
            options=opts.get("brands", []),
            default=[],
            placeholder="All brands",
        )
        filters["price_ranges"] = st.multiselect(
            "💰 Price Range",
            options=opts.get("price_ranges", []),
            default=[],
            placeholder="All ranges",
        )

        r_col1, r_col2 = st.columns(2)
        with r_col1:
            filters["rating_min"] = st.number_input("⭐ Min Rating", 0.0, 5.0, 0.0, 0.5)
        with r_col2:
            filters["rating_max"] = st.number_input("⭐ Max Rating", 0.0, 5.0, 5.0, 0.5)

        st.divider()

        st.markdown("## ⚙️ Pipeline")
        if st.button("🔄 Re-run ETL Pipeline", use_container_width=True, type="secondary"):
            run_etl()

        st.divider()
        st.markdown("""
        <div style="text-align:center;color:#334155;font-size:0.7rem;">
          Brand Visibility Intelligence<br>Built with Streamlit + SQLite
        </div>
        """, unsafe_allow_html=True)

    return filters, opts


# ─── Tab 1: Overview ──────────────────────────────────────────────────────────
def tab_overview(where, params):
    st.markdown("### 🌐 Executive Overview")

    kpis = db.get_overview_kpis(where, params)

    col1, col2, col3, col4, col5 = st.columns(5)
    cards = [
        (col1, "📦", "Total Products",    fmt_num(kpis.get("total_products", 0))),
        (col2, "💵", "Avg Price (₹)",     fmt_num(kpis.get("avg_price", 0), "₹", decimals=0)),
        (col3, "⭐", "Avg Rating",         fmt_num(kpis.get("avg_rating", 0), decimals=2)),
        (col4, "💬", "Total Reviews",      fmt_num(kpis.get("total_reviews", 0))),
        (col5, "👁️", "Avg Visibility",    fmt_num(kpis.get("avg_visibility", 0), decimals=1)),
    ]
    for col, icon, label, value in cards:
        with col:
            st.markdown(kpi_card(icon, label, value), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    row1_c1, row1_c2 = st.columns([6, 4])

    with row1_c1:
        section_header("📈", "Price Distribution")
        price_df = db.get_price_distribution(where, params)
        if not price_df.empty:
            fig = px.histogram(price_df, x="price", nbins=40,
                               color_discrete_sequence=[PRIMARY])
            fig.update_traces(opacity=0.85)
            apply_layout(fig, "Price Distribution (₹)")
            st.plotly_chart(fig, use_container_width=True)

    with row1_c2:
        section_header("🏪", "Platform Share")
        plat_df = db.get_platform_share(where, params)
        if not plat_df.empty:
            fig = px.pie(plat_df, names="platform", values="count",
                         color_discrete_sequence=COLORS, hole=0.45)
            fig.update_traces(textposition='inside', textinfo='percent+label',
                              marker=dict(line=dict(color='#1a1f35', width=2)))
            apply_layout(fig, "Platform Share")
            st.plotly_chart(fig, use_container_width=True)

    section_header("🔑", "Products per Keyword")
    kw_df = db.get_products_per_keyword(where, params)
    if not kw_df.empty:
        fig = px.bar(kw_df, x="keyword", y="product_count",
                     color="product_count",
                     color_continuous_scale=["#4338ca", "#a78bfa"],
                     text="product_count")
        fig.update_traces(textposition='outside', marker_line_width=0)
        apply_layout(fig, "Products per Keyword")
        fig.update_coloraxes(showscale=False)
        st.plotly_chart(fig, use_container_width=True)


# ─── Tab 2: Brand Insights ────────────────────────────────────────────────────
def tab_brand(where, params):
    st.markdown("### 🏷️ Brand Insights")

    brand_kpis = db.get_brand_kpis(where, params)
    col1, col2, col3, col4 = st.columns(4)
    cards = [
        (col1, "🏢", "Total Brands",       fmt_num(brand_kpis.get("total_brands", 0))),
        (col2, "🥇", "Top Brand",          str(brand_kpis.get("top_brand", "N/A"))),
        (col3, "⭐", "Highest Rated Brand", str(brand_kpis.get("highest_rated_brand", "N/A"))),
        (col4, "👁️", "Best Visibility",   str(brand_kpis.get("best_visibility_brand", "N/A"))),
    ]
    for col, icon, label, value in cards:
        with col:
            st.markdown(kpi_card(icon, label, value), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    c1, c2 = st.columns(2)

    with c1:
        section_header("📊", "Brand vs Product Count")
        df = db.get_brand_product_count(where, params)
        if not df.empty:
            fig = px.bar(df.head(15), x="product_count", y="brand",
                         orientation="h",
                         color="product_count",
                         color_continuous_scale=["#312e81", "#6366f1"],
                         text="product_count")
            fig.update_traces(textposition='outside', marker_line_width=0)
            apply_layout(fig, "")
            fig.update_layout(yaxis=dict(autorange="reversed"))
            fig.update_coloraxes(showscale=False)
            st.plotly_chart(fig, use_container_width=True)

    with c2:
        section_header("⭐", "Brand vs Avg Rating")
        df = db.get_brand_avg_rating(where, params)
        if not df.empty:
            fig = px.bar(df.head(15), x="avg_rating", y="brand",
                         orientation="h",
                         color="avg_rating",
                         color_continuous_scale=["#7c3aed", "#f59e0b"],
                         text="avg_rating")
            fig.update_traces(textposition='outside', marker_line_width=0)
            apply_layout(fig, "")
            fig.update_layout(yaxis=dict(autorange="reversed"))
            fig.update_coloraxes(showscale=False)
            st.plotly_chart(fig, use_container_width=True)

    c3, c4 = st.columns(2)

    with c3:
        section_header("🏆", "Top Brands in Top-10 Positions")
        df = db.get_top_brands_in_top10(where, params)
        if not df.empty:
            fig = px.bar(df.head(12), x="brand", y="top10_count",
                         color="top10_count",
                         color_continuous_scale=["#1e3a8a", "#60a5fa"],
                         text="top10_count")
            fig.update_traces(textposition='outside', marker_line_width=0)
            apply_layout(fig, "")
            fig.update_coloraxes(showscale=False)
            st.plotly_chart(fig, use_container_width=True)

    with c4:
        section_header("👁️", "Brand Visibility Score")
        df = db.get_brand_visibility(where, params)
        if not df.empty:
            fig = px.bar(df.head(12), x="avg_visibility", y="brand",
                         orientation="h",
                         color="avg_visibility",
                         color_continuous_scale=["#374151", "#a78bfa"],
                         text="avg_visibility")
            fig.update_traces(textposition='outside', marker_line_width=0)
            apply_layout(fig, "")
            fig.update_layout(yaxis=dict(autorange="reversed"))
            fig.update_coloraxes(showscale=False)
            st.plotly_chart(fig, use_container_width=True)


# ─── Tab 3: Pricing Analysis ──────────────────────────────────────────────────
def tab_pricing(where, params):
    st.markdown("### 💰 Pricing Analysis")

    p_kpis = db.get_pricing_kpis(where, params)
    col1, col2, col3, col4 = st.columns(4)
    cards = [
        (col1, "📊", "Avg Price (₹)",        fmt_num(p_kpis.get("avg_price", 0), "₹", decimals=0)),
        (col2, "🔺", "Highest Price (₹)",    fmt_num(p_kpis.get("max_price", 0), "₹", decimals=0)),
        (col3, "🔻", "Lowest Price (₹)",     fmt_num(p_kpis.get("min_price", 0), "₹", decimals=0)),
        (col4, "🏷️", "% Discounted",         fmt_num(p_kpis.get("pct_discounted", 0), suffix="%", decimals=1)),
    ]
    for col, icon, label, value in cards:
        with col:
            st.markdown(kpi_card(icon, label, value), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    c1, c2 = st.columns(2)

    with c1:
        section_header("📈", "Price Distribution by Brand")
        df = db.get_price_by_brand(where, params)
        if not df.empty:
            fig = px.bar(df.head(15), x="brand", y="avg_price",
                         color="avg_price",
                         color_continuous_scale=["#1d4ed8", "#38bdf8"],
                         text=df.head(15)["avg_price"].apply(lambda x: f"₹{x:,.0f}"))
            fig.update_traces(textposition='outside', marker_line_width=0)
            apply_layout(fig, "")
            fig.update_coloraxes(showscale=False)
            st.plotly_chart(fig, use_container_width=True)

    with c2:
        section_header("🗂️", "Price Range Distribution")
        df = db.get_price_range_distribution(where, params)
        if not df.empty:
            fig = px.pie(df, names="price_range", values="count",
                         color_discrete_sequence=COLORS, hole=0.45)
            fig.update_traces(textposition='inside', textinfo='percent+label',
                              marker=dict(line=dict(color='#1a1f35', width=2)))
            apply_layout(fig, "")
            st.plotly_chart(fig, use_container_width=True)

    section_header("🔵", "Price vs Ranking (Scatter)")
    df = db.get_price_vs_ranking(where, params)
    if not df.empty:
        fig = px.scatter(df, x="price", y="position",
                         color="brand", size_max=12,
                         hover_data=["title", "rating"],
                         opacity=0.75,
                         color_discrete_sequence=COLORS)
        apply_layout(fig, "")
        fig.update_layout(
            yaxis=dict(autorange="reversed", title="Position (rank)",
                       gridcolor="rgba(99,102,241,0.1)"),
            xaxis=dict(title="Price (₹)", gridcolor="rgba(99,102,241,0.1)"),
        )
        st.plotly_chart(fig, use_container_width=True)

    c3, c4 = st.columns(2)
    with c3:
        section_header("🏷️", "Discount % by Brand")
        df = db.get_discount_by_brand(where, params)
        if not df.empty:
            fig = px.bar(df.head(15), x="brand", y="avg_discount",
                         color="avg_discount",
                         color_continuous_scale=["#064e3b", "#34d399"],
                         text=df.head(15)["avg_discount"].apply(lambda x: f"{x:.1f}%"))
            fig.update_traces(textposition='outside', marker_line_width=0)
            apply_layout(fig, "")
            fig.update_coloraxes(showscale=False)
            st.plotly_chart(fig, use_container_width=True)

    with c4:
        section_header("🏪", "Discount % by Platform")
        df = db.get_discount_by_platform(where, params)
        if not df.empty:
            fig = px.bar(df, x="avg_discount", y="platform",
                         orientation="h",
                         color="avg_discount",
                         color_continuous_scale=["#065f46", "#6ee7b7"],
                         text=df["avg_discount"].apply(lambda x: f"{x:.1f}%"))
            fig.update_traces(textposition='outside', marker_line_width=0)
            apply_layout(fig, "")
            fig.update_layout(yaxis=dict(autorange="reversed"))
            fig.update_coloraxes(showscale=False)
            st.plotly_chart(fig, use_container_width=True)


# ─── Tab 4: Platform Analysis ─────────────────────────────────────────────────
def tab_platform(where, params):
    st.markdown("### 🏪 Platform Analysis")

    plat_count  = db.get_platform_product_count(where, params)
    plat_rating = db.get_platform_avg_rating(where, params)
    plat_price  = db.get_platform_avg_price(where, params)

    total_platforms = len(plat_count)
    best_platform   = plat_rating.iloc[0]["platform"]    if not plat_rating.empty else "N/A"
    cheapest        = plat_price.iloc[-1]["platform"]    if not plat_price.empty else "N/A"
    most_products   = plat_count.iloc[0]["platform"]     if not plat_count.empty else "N/A"

    col1, col2, col3, col4 = st.columns(4)
    for col, icon, label, value in [
        (col1, "🏪", "Total Platforms",        str(total_platforms)),
        (col2, "🌟", "Best Avg Rating",        best_platform),
        (col3, "💸", "Cheapest Platform",      cheapest),
        (col4, "📦", "Most Products",          most_products),
    ]:
        with col:
            st.markdown(kpi_card(icon, label, value), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    c1, c2 = st.columns(2)

    with c1:
        section_header("📦", "Products per Platform")
        if not plat_count.empty:
            fig = px.bar(plat_count, x="platform", y="product_count",
                         color="product_count",
                         color_continuous_scale=["#1e3a5f", "#3b82f6"],
                         text="product_count")
            fig.update_traces(textposition='outside', marker_line_width=0)
            apply_layout(fig, "")
            fig.update_coloraxes(showscale=False)
            st.plotly_chart(fig, use_container_width=True)

    with c2:
        section_header("⭐", "Avg Rating per Platform")
        if not plat_rating.empty:
            fig = px.bar(plat_rating, x="platform", y="avg_rating",
                         color="avg_rating",
                         color_continuous_scale=["#713f12", "#fbbf24"],
                         text=plat_rating["avg_rating"].apply(lambda x: f"{x:.2f}"))
            fig.update_traces(textposition='outside', marker_line_width=0)
            apply_layout(fig, "")
            fig.update_coloraxes(showscale=False)
            st.plotly_chart(fig, use_container_width=True)

    c3, _ = st.columns([1, 1])
    with c3:
        section_header("💰", "Avg Price per Platform")
        if not plat_price.empty:
            fig = px.bar(plat_price, x="platform", y="avg_price",
                         color="avg_price",
                         color_continuous_scale=["#0c4a6e", "#38bdf8"],
                         text=plat_price["avg_price"].apply(lambda x: f"₹{x:,.0f}"))
            fig.update_traces(textposition='outside', marker_line_width=0)
            apply_layout(fig, "")
            fig.update_coloraxes(showscale=False)
            st.plotly_chart(fig, use_container_width=True)


# ─── Tab 5: Visibility & Ranking ─────────────────────────────────────────────
def tab_visibility(where, params):
    st.markdown("### 👁️ Visibility & Ranking Analysis")

    v_kpis = db.get_visibility_kpis(where, params)

    col1, col2, col3, col4 = st.columns(4)
    for col, icon, label, value in [
        (col1, "⭐", "Avg Rating",           fmt_num(v_kpis.get("avg_rating", 0), decimals=2)),
        (col2, "👁️", "Avg Visibility Score", fmt_num(v_kpis.get("avg_visibility", 0), decimals=1)),
        (col3, "🥇", "Best Ranked Product",  str(v_kpis.get("best_ranked", "N/A"))[:40] + "..."),
        (col4, "🏆", "% in Top 10",          fmt_num(v_kpis.get("pct_top10", 0), suffix="%", decimals=1)),
    ]:
        with col:
            st.markdown(kpi_card(icon, label, value), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    c1, c2 = st.columns(2)

    with c1:
        section_header("📊", "Ranking Distribution")
        df = db.get_ranking_distribution(where, params)
        if not df.empty:
            fig = px.bar(df, x="position", y="count",
                         color="count",
                         color_continuous_scale=["#312e81", "#818cf8"])
            fig.update_traces(marker_line_width=0)
            apply_layout(fig, "")
            fig.update_coloraxes(showscale=False)
            st.plotly_chart(fig, use_container_width=True)

    with c2:
        section_header("👁️", "Visibility Score by Brand")
        df = db.get_visibility_by_brand(where, params)
        if not df.empty:
            fig = px.bar(df.head(15), x="avg_visibility", y="brand",
                         orientation="h",
                         color="avg_visibility",
                         color_continuous_scale=["#2e1065", "#c4b5fd"],
                         text=df.head(15)["avg_visibility"].apply(lambda x: f"{x:.1f}"))
            fig.update_traces(textposition='outside', marker_line_width=0)
            apply_layout(fig, "")
            fig.update_layout(yaxis=dict(autorange="reversed"))
            fig.update_coloraxes(showscale=False)
            st.plotly_chart(fig, use_container_width=True)

    section_header("🔵", "Rating vs Ranking (Bubble Chart)")
    df = db.get_rating_vs_ranking(where, params)
    if not df.empty:
        df["reviews_scaled"] = df["reviews"].clip(upper=10000)
        fig = px.scatter(df, x="rating", y="position",
                         size="reviews_scaled", color="brand",
                         hover_data=["title", "price"],
                         color_discrete_sequence=COLORS,
                         opacity=0.75, size_max=30)
        apply_layout(fig, "")
        fig.update_layout(
            yaxis=dict(autorange="reversed", title="Search Position",
                       gridcolor="rgba(99,102,241,0.1)"),
            xaxis=dict(title="Rating (out of 5)", gridcolor="rgba(99,102,241,0.1)"),
        )
        st.plotly_chart(fig, use_container_width=True)


# ─── Tab 6: Product Explorer ──────────────────────────────────────────────────
def tab_products(where, params):
    st.markdown("### 🔍 Product Explorer")

    all_df = db.get_all_products(where, params)

    col1, col2, col3 = st.columns(3)
    for col, icon, label, value in [
        (col1, "📦", "Total Products",   fmt_num(len(all_df))),
        (col2, "💵", "Avg Price (₹)",    fmt_num(all_df["price"].mean() if not all_df.empty else 0, "₹", decimals=0)),
        (col3, "⭐", "Avg Rating",        fmt_num(all_df["rating"].mean() if not all_df.empty else 0, decimals=2)),
    ]:
        with col:
            st.markdown(kpi_card(icon, label, value), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Search
    search = st.text_input("🔎 Search product title or brand", placeholder="Type to search...")
    if search and not all_df.empty:
        mask = all_df["title"].str.contains(search, case=False, na=False) | \
               all_df["brand"].str.contains(search, case=False, na=False)
        all_df = all_df[mask]

    section_header("🏆", "Top 10 Products by Visibility")
    top10 = db.get_top_products(where, params, limit=10)
    if not top10.empty:
        st.dataframe(
            top10,
            use_container_width=True,
            hide_index=True,
            column_config={
                "price":            st.column_config.NumberColumn("Price (₹)", format="₹%.0f"),
                "rating":           st.column_config.NumberColumn("Rating", format="%.1f ⭐"),
                "reviews":          st.column_config.NumberColumn("Reviews", format="%d 💬"),
                "discount":         st.column_config.NumberColumn("Discount %", format="%.1f%%"),
                "visibility_score": st.column_config.ProgressColumn("Visibility", min_value=0, max_value=100),
            }
        )

    st.markdown("<br>", unsafe_allow_html=True)
    section_header("📋", f"All Products ({len(all_df)} shown)")

    if not all_df.empty:
        st.dataframe(
            all_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "price":            st.column_config.NumberColumn("Price (₹)", format="₹%.0f"),
                "rating":           st.column_config.NumberColumn("Rating", format="%.1f ⭐"),
                "reviews":          st.column_config.NumberColumn("Reviews", format="%d 💬"),
                "discount":         st.column_config.NumberColumn("Discount %", format="%.1f%%"),
                "visibility_score": st.column_config.ProgressColumn("Visibility", min_value=0, max_value=100),
            }
        )

        csv_data = all_df.to_csv(index=False)
        st.download_button(
            "⬇️ Download as CSV",
            data=csv_data,
            file_name="filtered_products.csv",
            mime="text/csv",
            use_container_width=False,
        )

    # Scatter of all products
    if not all_df.empty and "price" in all_df.columns and "rating" in all_df.columns:
        c1, c2 = st.columns(2)
        with c1:
            section_header("🔵", "Rating vs Price")
            fig = px.scatter(all_df.dropna(subset=["rating", "price"]),
                             x="price", y="rating",
                             color="brand",
                             hover_data=["title"],
                             color_discrete_sequence=COLORS,
                             opacity=0.7)
            apply_layout(fig, "")
            st.plotly_chart(fig, use_container_width=True)

        with c2:
            section_header("💬", "Reviews vs Price")
            fig = px.scatter(all_df.dropna(subset=["reviews", "price"]),
                             x="price", y="reviews",
                             color="platform",
                             hover_data=["title", "brand"],
                             color_discrete_sequence=COLORS,
                             opacity=0.7)
            apply_layout(fig, "")
            st.plotly_chart(fig, use_container_width=True)


# ─── Setup / Welcome screen ───────────────────────────────────────────────────
def show_setup_screen():
    st.markdown("""
    <div class="setup-box">
      <h2>🚀 Welcome to Brand Visibility Intelligence Dashboard</h2>
      <p style="font-size:1.05rem;margin:1rem 0">
        No data found. You need to run the ETL pipeline to get started.
      </p>
      <p>Steps:<br>
        <b>1.</b> Drop your <code>brand_dirty_dataset.csv</code> inside the <code>data/</code> folder.<br>
        <b>2.</b> (Optional) Add your SerpAPI key to <code>.env</code> → <code>SERPAPI_KEY=your_key</code><br>
        <b>3.</b> Click the button below to run the pipeline.
      </p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([2, 2, 2])
    with col2:
        if st.button("▶️ Run ETL Pipeline Now", type="primary", use_container_width=True):
            run_etl()


# ─── Main App ─────────────────────────────────────────────────────────────────
def main():
    # Header
    st.markdown("""
    <div style="display:flex;align-items:center;gap:1rem;margin-bottom:0.5rem;">
      <div style="font-size:2.8rem;">📊</div>
      <div>
        <h1 style="margin:0;font-size:1.8rem;font-weight:800;
                   background:linear-gradient(135deg,#6366f1,#a78bfa,#f472b6);
                   -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                   background-clip:text;">
          Brand Visibility Intelligence Dashboard
        </h1>
        <p style="margin:0;color:#475569;font-size:0.9rem;">
          E-commerce Analytics · Search Rankings · Pricing Strategy · Competitive Intelligence
        </p>
      </div>
    </div>
    """, unsafe_allow_html=True)
    st.divider()

    if not db.db_exists():
        show_setup_screen()
        return

    filters, opts = render_sidebar()
    where, params = db.build_where_clause(
        keywords     = filters.get("keywords") or None,
        platforms    = filters.get("platforms") or None,
        brands       = filters.get("brands") or None,
        price_ranges = filters.get("price_ranges") or None,
        rating_min   = filters.get("rating_min") if filters.get("rating_min", 0) > 0 else None,
        rating_max   = filters.get("rating_max") if filters.get("rating_max", 5) < 5 else None,
    )

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "🌐 Overview",
        "🏷️ Brand Insights",
        "💰 Pricing",
        "🏪 Platform",
        "👁️ Visibility",
        "🔍 Explorer",
    ])

    with tab1: tab_overview(where, params)
    with tab2: tab_brand(where, params)
    with tab3: tab_pricing(where, params)
    with tab4: tab_platform(where, params)
    with tab5: tab_visibility(where, params)
    with tab6: tab_products(where, params)


if __name__ == "__main__":
    main()
