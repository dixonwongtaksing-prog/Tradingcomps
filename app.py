import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import yfinance as yf
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings("ignore")

st.set_page_config(
    page_title="Services Sector Comps",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Styling ──────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

.main { background-color: #0f1117; }
section[data-testid="stSidebar"] { background-color: #161b22; border-right: 1px solid #30363d; }

.metric-card {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 10px;
    padding: 16px 20px;
    text-align: center;
}
.metric-label { color: #8b949e; font-size: 12px; font-weight: 500; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 4px; }
.metric-value { color: #e6edf3; font-size: 22px; font-weight: 700; }
.metric-delta-pos { color: #3fb950; font-size: 13px; font-weight: 500; }
.metric-delta-neg { color: #f85149; font-size: 13px; font-weight: 500; }
.metric-delta-neu { color: #8b949e; font-size: 13px; font-weight: 500; }

.section-header {
    font-size: 18px; font-weight: 600; color: #e6edf3;
    border-bottom: 1px solid #30363d; padding-bottom: 8px; margin: 24px 0 16px 0;
}
.sub-header { font-size: 14px; font-weight: 500; color: #8b949e; margin-bottom: 12px; }

.winner-badge { background: #1a3a2a; border: 1px solid #3fb950; color: #3fb950; border-radius: 6px; padding: 2px 8px; font-size: 11px; font-weight: 600; }
.loser-badge  { background: #3a1a1a; border: 1px solid #f85149; color: #f85149; border-radius: 6px; padding: 2px 8px; font-size: 11px; font-weight: 600; }

.stDataFrame { border: 1px solid #30363d; border-radius: 8px; }
div[data-testid="stDataFrame"] table { background: #161b22 !important; }

.tab-content { padding-top: 16px; }

/* Sidebar nav */
.nav-link { padding: 8px 12px; border-radius: 6px; cursor: pointer; }
</style>
""", unsafe_allow_html=True)

# ── Data Loading ──────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def load_universe():
    df = pd.read_excel("expanded_services_universe_us_uk.xlsx")
    df.columns = df.columns.str.strip()
    # Suffix UK tickers for yfinance
    def fix_ticker(row):
        t = str(row["ticker"]).strip()
        if row["listing_country"] == "UK" and "." not in t:
            return t + ".L"
        return t
    df["yf_ticker"] = df.apply(fix_ticker, axis=1)
    return df

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_prices(tickers, period="1y"):
    try:
        raw = yf.download(tickers, period=period, auto_adjust=True, progress=False)
        if isinstance(raw.columns, pd.MultiIndex):
            prices = raw["Close"]
        else:
            prices = raw[["Close"]] if "Close" in raw else raw
            prices.columns = tickers
        return prices
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_fundamentals(tickers):
    rows = []
    prog = st.progress(0, text="Fetching market data…")
    total = len(tickers)
    for i, t in enumerate(tickers):
        try:
            info = yf.Ticker(t).info
            hist = yf.Ticker(t).history(period="1y")
            price = info.get("currentPrice") or info.get("regularMarketPrice") or (hist["Close"].iloc[-1] if not hist.empty else None)
            prev_close = info.get("previousClose") or info.get("regularMarketPreviousClose")
            price_52w_ago = hist["Close"].iloc[0] if len(hist) >= 250 else None
            market_cap = info.get("marketCap")
            rows.append({
                "ticker": t,
                "price": price,
                "prev_close": prev_close,
                "price_52w": price_52w_ago,
                "market_cap": market_cap,
                "ev": info.get("enterpriseValue"),
                "pe_fwd": info.get("forwardPE"),
                "pe_trail": info.get("trailingPE"),
                "ev_ebitda": info.get("enterpriseToEbitda"),
                "ev_rev": info.get("enterpriseToRevenue"),
                "pb": info.get("priceToBook"),
                "revenue_ttm": info.get("totalRevenue"),
                "ebitda_ttm": info.get("ebitda"),
                "gross_margin": info.get("grossMargins"),
                "ebitda_margin": info.get("ebitdaMargins"),
                "net_margin": info.get("profitMargins"),
                "rev_growth": info.get("revenueGrowth"),
                "dividend_yield": info.get("dividendYield"),
                "beta": info.get("beta"),
                "52w_high": info.get("fiftyTwoWeekHigh"),
                "52w_low": info.get("fiftyTwoWeekLow"),
            })
        except Exception:
            rows.append({"ticker": t})
        prog.progress((i + 1) / total, text=f"Fetching {t}… ({i+1}/{total})")
    prog.empty()
    return pd.DataFrame(rows)

# ── Helpers ───────────────────────────────────────────────────────────────────
def fmt_pct(v, decimals=1):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "n/a"
    return f"{v*100:+.{decimals}f}%"

def fmt_x(v, decimals=1):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "n/a"
    return f"{v:.{decimals}f}x"

def fmt_price(v):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "n/a"
    return f"{v:,.2f}"

def fmt_bn(v):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "n/a"
    if abs(v) >= 1e9:
        return f"${v/1e9:.1f}B"
    if abs(v) >= 1e6:
        return f"${v/1e6:.0f}M"
    return f"${v:,.0f}"

def color_pct(v):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return ""
    return "color: #3fb950" if v >= 0 else "color: #f85149"

PLOTLY_LAYOUT = dict(
    paper_bgcolor="#0f1117",
    plot_bgcolor="#0f1117",
    font_color="#e6edf3",
    font_family="Inter",
    xaxis=dict(gridcolor="#21262d", linecolor="#30363d", zerolinecolor="#30363d"),
    yaxis=dict(gridcolor="#21262d", linecolor="#30363d", zerolinecolor="#30363d"),
    legend=dict(bgcolor="#161b22", bordercolor="#30363d", borderwidth=1),
    margin=dict(l=40, r=20, t=40, b=40),
)

# ── Sidebar ───────────────────────────────────────────────────────────────────
universe = load_universe()
sectors = sorted(universe["sector"].unique().tolist())

with st.sidebar:
    st.markdown("## 📊 Services Comps")
    st.markdown("---")
    page = st.radio(
        "Navigate",
        ["Overview", "Segment Comps"],
        label_visibility="collapsed",
    )
    st.markdown("---")
    st.markdown("**Filters**")
    country_filter = st.multiselect(
        "Country", ["US", "UK"], default=["US", "UK"]
    )
    st.markdown("---")
    st.caption(f"Universe: {len(universe)} companies across {len(sectors)} sectors")
    st.caption("Data: Yahoo Finance · Refreshes hourly")

filtered_universe = universe[universe["listing_country"].isin(country_filter)]

# ══════════════════════════════════════════════════════════════════════════════
#  PAGE: OVERVIEW
# ══════════════════════════════════════════════════════════════════════════════
if page == "Overview":
    st.markdown("# Services Sector Overview")
    st.markdown(f"<div class='sub-header'>Market intelligence across {len(filtered_universe)} companies · {datetime.now().strftime('%d %b %Y %H:%M')}</div>", unsafe_allow_html=True)

    # ── Load data ────────────────────────────────────────────────────────────
    tickers_list = filtered_universe["yf_ticker"].dropna().unique().tolist()

    with st.spinner("Loading market data… this may take a moment on first load"):
        fund_df = fetch_fundamentals(tickers_list)

    merged = filtered_universe.merge(fund_df, left_on="yf_ticker", right_on="ticker", how="left")
    merged["chg_1d"] = (merged["price"] - merged["prev_close"]) / merged["prev_close"]
    merged["chg_1y"] = (merged["price"] - merged["price_52w"]) / merged["price_52w"]

    # ── KPI Cards ─────────────────────────────────────────────────────────────
    total_mcap = merged["market_cap"].sum(min_count=1)
    valid = merged.dropna(subset=["chg_1d"])
    gainers_count = (valid["chg_1d"] > 0).sum()
    losers_count  = (valid["chg_1d"] < 0).sum()
    avg_1y = valid["chg_1y"].median()

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""<div class='metric-card'>
            <div class='metric-label'>Total Market Cap</div>
            <div class='metric-value'>{fmt_bn(total_mcap)}</div>
            <div class='metric-delta-neu'>{len(filtered_universe)} companies</div>
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""<div class='metric-card'>
            <div class='metric-label'>Gainers Today</div>
            <div class='metric-value' style='color:#3fb950'>{gainers_count}</div>
            <div class='metric-delta-neu'>of {gainers_count+losers_count} reporting</div>
        </div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""<div class='metric-card'>
            <div class='metric-label'>Losers Today</div>
            <div class='metric-value' style='color:#f85149'>{losers_count}</div>
            <div class='metric-delta-neu'>of {gainers_count+losers_count} reporting</div>
        </div>""", unsafe_allow_html=True)
    with c4:
        delta_class = "metric-delta-pos" if avg_1y >= 0 else "metric-delta-neg"
        st.markdown(f"""<div class='metric-card'>
            <div class='metric-label'>Median 1Y Return</div>
            <div class='metric-value'>{fmt_pct(avg_1y)}</div>
            <div class='{delta_class}'>universe median</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("")

    # ── Tabs: Winners/Losers & Index Performance ──────────────────────────────
    tab1, tab2 = st.tabs(["🏆 Winners & Losers", "📈 Index Performance"])

    with tab1:
        col_a, col_b = st.columns(2)

        # ---- By Name ----
        with col_a:
            st.markdown("<div class='section-header'>Top 10 Winners — Today</div>", unsafe_allow_html=True)
            top10 = valid.nlargest(10, "chg_1d")[["name", "sector", "price", "chg_1d", "chg_1y", "market_cap"]].copy()
            top10["Price"] = top10["price"].apply(fmt_price)
            top10["1D %"] = top10["chg_1d"].apply(fmt_pct)
            top10["1Y %"] = top10["chg_1y"].apply(fmt_pct)
            top10["Mkt Cap"] = top10["market_cap"].apply(fmt_bn)
            st.dataframe(
                top10[["name", "sector", "Price", "1D %", "1Y %", "Mkt Cap"]].rename(columns={"name": "Name", "sector": "Sector"}),
                hide_index=True, use_container_width=True
            )

            st.markdown("<div class='section-header'>Top 10 Losers — Today</div>", unsafe_allow_html=True)
            bot10 = valid.nsmallest(10, "chg_1d")[["name", "sector", "price", "chg_1d", "chg_1y", "market_cap"]].copy()
            bot10["Price"] = bot10["price"].apply(fmt_price)
            bot10["1D %"] = bot10["chg_1d"].apply(fmt_pct)
            bot10["1Y %"] = bot10["chg_1y"].apply(fmt_pct)
            bot10["Mkt Cap"] = bot10["market_cap"].apply(fmt_bn)
            st.dataframe(
                bot10[["name", "sector", "Price", "1D %", "1Y %", "Mkt Cap"]].rename(columns={"name": "Name", "sector": "Sector"}),
                hide_index=True, use_container_width=True
            )

        # ---- By Sector ----
        with col_b:
            st.markdown("<div class='section-header'>Sector Performance — 1Y Return</div>", unsafe_allow_html=True)

            sector_perf = (
                merged.dropna(subset=["chg_1y"])
                .groupby("sector")["chg_1y"]
                .median()
                .sort_values(ascending=True)
                .reset_index()
            )
            sector_perf["color"] = sector_perf["chg_1y"].apply(lambda x: "#3fb950" if x >= 0 else "#f85149")
            sector_perf["label"] = sector_perf["chg_1y"].apply(lambda x: f"{x*100:+.1f}%")

            fig = go.Figure(go.Bar(
                x=sector_perf["chg_1y"] * 100,
                y=sector_perf["sector"],
                orientation="h",
                marker_color=sector_perf["color"].tolist(),
                text=sector_perf["label"],
                textposition="outside",
                textfont_size=11,
            ))
            fig.update_layout(
                **PLOTLY_LAYOUT,
                height=420,
                xaxis_title="Median 1Y Return (%)",
                yaxis_tickfont_size=11,
                showlegend=False,
            )
            st.plotly_chart(fig, use_container_width=True)

            st.markdown("<div class='section-header'>Best & Worst Sectors — Today</div>", unsafe_allow_html=True)
            sector_today = (
                merged.dropna(subset=["chg_1d"])
                .groupby("sector")["chg_1d"]
                .median()
                .sort_values(ascending=False)
                .reset_index()
            )
            sector_today["1D %"] = sector_today["chg_1d"].apply(fmt_pct)
            st.dataframe(
                sector_today[["sector", "1D %"]].rename(columns={"sector": "Sector"}),
                hide_index=True, use_container_width=True, height=280
            )

    with tab2:
        st.markdown("<div class='section-header'>Market-Cap Weighted Sector Indices vs. S&P 500 (L1Y)</div>", unsafe_allow_html=True)

        selected_sectors = st.multiselect(
            "Select sectors to display",
            sectors,
            default=sectors[:4],
            key="idx_sectors"
        )

        if selected_sectors:
            with st.spinner("Fetching price history…"):
                all_tickers = filtered_universe[filtered_universe["sector"].isin(selected_sectors)]["yf_ticker"].dropna().unique().tolist()
                all_tickers_with_spy = all_tickers + ["^GSPC"]
                prices = fetch_prices(all_tickers_with_spy, period="1y")

            if not prices.empty:
                fig = go.Figure()

                # S&P 500
                if "^GSPC" in prices.columns:
                    spy = prices["^GSPC"].dropna()
                    spy_norm = spy / spy.iloc[0] * 100
                    fig.add_trace(go.Scatter(
                        x=spy_norm.index, y=spy_norm.values,
                        name="S&P 500",
                        line=dict(color="#e6edf3", width=2, dash="dash"),
                    ))

                colors = px.colors.qualitative.Vivid
                for ci, sector_name in enumerate(selected_sectors):
                    sector_tickers = filtered_universe[
                        (filtered_universe["sector"] == sector_name) &
                        (filtered_universe["yf_ticker"].isin(prices.columns))
                    ][["yf_ticker", "market_cap"]].copy()

                    # Use fetched market caps from fund_df if available
                    mcaps = fund_df.set_index("ticker")["market_cap"]
                    sector_tickers["mktcap"] = sector_tickers["yf_ticker"].map(mcaps)
                    sector_tickers = sector_tickers.dropna(subset=["mktcap"])

                    valid_tks = [t for t in sector_tickers["yf_ticker"].tolist() if t in prices.columns]
                    if not valid_tks:
                        continue

                    price_sub = prices[valid_tks].dropna(how="all")
                    wts = sector_tickers.set_index("yf_ticker")["mktcap"].reindex(valid_tks).fillna(0)
                    total_w = wts.sum()
                    if total_w == 0:
                        continue
                    wts = wts / total_w

                    # Weighted index
                    idx_series = price_sub.pct_change().fillna(0).dot(wts)
                    idx_level = (1 + idx_series).cumprod() * 100

                    color = colors[ci % len(colors)]
                    fig.add_trace(go.Scatter(
                        x=idx_level.index, y=idx_level.values,
                        name=sector_name,
                        line=dict(color=color, width=2),
                        hovertemplate=f"<b>{sector_name}</b><br>%{{x|%d %b %Y}}<br>Index: %{{y:.1f}}<extra></extra>",
                    ))

                fig.update_layout(
                    **PLOTLY_LAYOUT,
                    height=480,
                    yaxis_title="Indexed (base 100)",
                    hovermode="x unified",
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
                )
                fig.add_hline(y=100, line_dash="dot", line_color="#555", opacity=0.5)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("Could not retrieve price history. Please check your connection.")
        else:
            st.info("Select at least one sector above.")


# ══════════════════════════════════════════════════════════════════════════════
#  PAGE: SEGMENT COMPS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Segment Comps":
    st.markdown("# Segment Trading Comps")
    st.markdown(f"<div class='sub-header'>Valuation multiples and operating metrics · {datetime.now().strftime('%d %b %Y')}</div>", unsafe_allow_html=True)

    sector_tabs = st.tabs([s[:30] for s in sectors])

    for ti, sector_name in enumerate(sectors):
        with sector_tabs[ti]:
            sector_data = filtered_universe[filtered_universe["sector"] == sector_name].copy()
            tickers_sec = sector_data["yf_ticker"].dropna().unique().tolist()

            if not tickers_sec:
                st.info("No companies in this sector for the selected country filter.")
                continue

            with st.spinner(f"Loading {sector_name} data…"):
                fund_sec = fetch_fundamentals(tickers_sec)

            merged_sec = sector_data.merge(fund_sec, left_on="yf_ticker", right_on="ticker", how="left")
            merged_sec["chg_1d"] = (merged_sec["price"] - merged_sec["prev_close"]) / merged_sec["prev_close"]
            merged_sec["chg_1y"] = (merged_sec["price"] - merged_sec["price_52w"]) / merged_sec["price_52w"]

            def build_comps_table(df):
                out = df[["name", "listing_country", "price", "chg_1d", "chg_1y",
                           "market_cap", "ev", "ev_ebitda", "ev_rev", "pe_fwd",
                           "ebitda_margin", "rev_growth"]].copy()
                out.columns = ["Company", "Country", "Price", "1D %", "1Y %",
                                "Mkt Cap", "EV", "EV/EBITDA", "EV/Rev", "Fwd P/E",
                                "EBITDA Mg", "Rev Growth"]
                display = out.copy()
                display["Price"]      = out["Price"].apply(fmt_price)
                display["1D %"]       = out["1D %"].apply(fmt_pct)
                display["1Y %"]       = out["1Y %"].apply(fmt_pct)
                display["Mkt Cap"]    = out["Mkt Cap"].apply(fmt_bn)
                display["EV"]         = out["EV"].apply(fmt_bn)
                display["EV/EBITDA"]  = out["EV/EBITDA"].apply(fmt_x)
                display["EV/Rev"]     = out["EV/Rev"].apply(fmt_x)
                display["Fwd P/E"]    = out["Fwd P/E"].apply(lambda v: fmt_x(v) if v and v < 200 else "n/a")
                display["EBITDA Mg"]  = out["EBITDA Mg"].apply(fmt_pct)
                display["Rev Growth"] = out["Rev Growth"].apply(fmt_pct)
                return display

            def build_summary_row(df, label="Sector Median"):
                numeric = df[["EV/EBITDA", "EV/Rev", "Fwd P/E", "EBITDA Mg", "Rev Growth"]].copy()
                for col in numeric.columns:
                    numeric[col] = pd.to_numeric(
                        numeric[col].astype(str).str.replace("x", "").str.replace("%", "").str.replace("n/a", "").str.strip(),
                        errors="coerce"
                    )
                med = numeric.median()
                return {
                    "Company": f"⟐ {label}",
                    "Country": "",
                    "Price": "",
                    "1D %": "",
                    "1Y %": "",
                    "Mkt Cap": "",
                    "EV": "",
                    "EV/EBITDA": f"{med['EV/EBITDA']:.1f}x" if not np.isnan(med["EV/EBITDA"]) else "n/a",
                    "EV/Rev":    f"{med['EV/Rev']:.1f}x"    if not np.isnan(med["EV/Rev"])    else "n/a",
                    "Fwd P/E":   f"{med['Fwd P/E']:.1f}x"   if not np.isnan(med["Fwd P/E"])   else "n/a",
                    "EBITDA Mg": f"{med['EBITDA Mg']:.1f}%"  if not np.isnan(med["EBITDA Mg"]) else "n/a",
                    "Rev Growth":f"{med['Rev Growth']:.1f}%" if not np.isnan(med["Rev Growth"])else "n/a",
                }

            # ── Sector level KPIs ─────────────────────────────────────────────
            valid_mc = merged_sec["market_cap"].dropna()
            total_mc = valid_mc.sum()
            n_cos = len(merged_sec)
            med_ev_ebitda = merged_sec["ev_ebitda"].median()
            med_ev_rev = merged_sec["ev_rev"].median()

            k1, k2, k3, k4 = st.columns(4)
            k1.markdown(f"<div class='metric-card'><div class='metric-label'>Companies</div><div class='metric-value'>{n_cos}</div></div>", unsafe_allow_html=True)
            k2.markdown(f"<div class='metric-card'><div class='metric-label'>Total Mkt Cap</div><div class='metric-value'>{fmt_bn(total_mc)}</div></div>", unsafe_allow_html=True)
            k3.markdown(f"<div class='metric-card'><div class='metric-label'>Median EV/EBITDA</div><div class='metric-value'>{fmt_x(med_ev_ebitda)}</div></div>", unsafe_allow_html=True)
            k4.markdown(f"<div class='metric-card'><div class='metric-label'>Median EV/Rev</div><div class='metric-value'>{fmt_x(med_ev_rev)}</div></div>", unsafe_allow_html=True)

            st.markdown("")

            # ── Full sector comps table ────────────────────────────────────────
            st.markdown(f"<div class='section-header'>Full Sector Comps — {sector_name}</div>", unsafe_allow_html=True)

            display_df = build_comps_table(merged_sec)
            summary_row = build_summary_row(display_df, "Sector Median")
            display_with_median = pd.concat([display_df, pd.DataFrame([summary_row])], ignore_index=True)

            st.dataframe(display_with_median, hide_index=True, use_container_width=True, height=400)

            # ── Subsector breakdown ────────────────────────────────────────────
            subsectors = sorted(merged_sec["sub_sector"].dropna().unique().tolist())
            if len(subsectors) > 1:
                st.markdown(f"<div class='section-header'>Subsector Breakdown</div>", unsafe_allow_html=True)

                sub_tabs = st.tabs([s[:28] for s in subsectors])
                for si, sub in enumerate(subsectors):
                    with sub_tabs[si]:
                        sub_df = merged_sec[merged_sec["sub_sector"] == sub]
                        if sub_df.empty:
                            continue

                        n_sub = len(sub_df)
                        med_sub_ev_eb = sub_df["ev_ebitda"].median()
                        med_sub_ev_rv = sub_df["ev_rev"].median()

                        sc1, sc2, sc3 = st.columns(3)
                        sc1.markdown(f"<div class='metric-card'><div class='metric-label'>Companies</div><div class='metric-value'>{n_sub}</div></div>", unsafe_allow_html=True)
                        sc2.markdown(f"<div class='metric-card'><div class='metric-label'>Median EV/EBITDA</div><div class='metric-value'>{fmt_x(med_sub_ev_eb)}</div></div>", unsafe_allow_html=True)
                        sc3.markdown(f"<div class='metric-card'><div class='metric-label'>Median EV/Rev</div><div class='metric-value'>{fmt_x(med_sub_ev_rv)}</div></div>", unsafe_allow_html=True)

                        st.markdown("")
                        sub_display = build_comps_table(sub_df)
                        sub_median = build_summary_row(sub_display, "Subsector Median")
                        sub_with_median = pd.concat([sub_display, pd.DataFrame([sub_median])], ignore_index=True)
                        st.dataframe(sub_with_median, hide_index=True, use_container_width=True)

                        # Bubble chart: EV/EBITDA vs Rev Growth, sized by mkt cap
                        chart_data = sub_df.dropna(subset=["ev_ebitda", "rev_growth", "market_cap"])
                        if len(chart_data) >= 3:
                            fig_bub = go.Figure(go.Scatter(
                                x=chart_data["rev_growth"] * 100,
                                y=chart_data["ev_ebitda"],
                                mode="markers+text",
                                marker=dict(
                                    size=np.sqrt(chart_data["market_cap"] / 1e7).clip(8, 60),
                                    color=chart_data["ev_ebitda"],
                                    colorscale="Teal",
                                    showscale=True,
                                    colorbar=dict(title="EV/EBITDA"),
                                    opacity=0.8,
                                    line=dict(color="#30363d", width=1),
                                ),
                                text=chart_data["name"].apply(lambda x: x.split()[0]),
                                textposition="top center",
                                textfont=dict(size=9),
                                hovertemplate="<b>%{text}</b><br>EV/EBITDA: %{y:.1f}x<br>Rev Growth: %{x:.1f}%<extra></extra>",
                            ))
                            fig_bub.update_layout(
                                **PLOTLY_LAYOUT,
                                height=360,
                                xaxis_title="Revenue Growth (%)",
                                yaxis_title="EV/EBITDA (x)",
                                title=dict(text=f"{sub} — Valuation vs. Growth", font_size=13, x=0),
                            )
                            st.plotly_chart(fig_bub, use_container_width=True)
