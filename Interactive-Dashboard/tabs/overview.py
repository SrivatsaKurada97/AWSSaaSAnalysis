import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import Optional


def _find_column(df: pd.DataFrame, candidates):
    for c in candidates:
        if c in df.columns:
            return c
    return None


def _format_currency(x: float) -> str:
    try:
        return f"${x:,.2f}"
    except Exception:
        return str(x)


def render_overview(df: pd.DataFrame):
    """Render the Overview tab.

    df: main dataset containing customer-level or transaction-level rows.
    The function is defensive about column names and will try common alternatives.
    """

    # Discover likely column names
    cust_col = _find_column(df, ["customerID", "customer", "cust_id"])
    revenue_col = _find_column(df, ["saletotal_event_sales", "user_table_sales", "sales", "revenue"])
    products_col = _find_column(df, ["product_count", "num_products", "products"])
    clv_col = _find_column(df, ["clv_tier", "tier", "customer_tier"])
    engagement_col = _find_column(df, ["engagement_level", "engagement", "engagement_tier"])
    segment_col = _find_column(df, ["segment", "customer_segment"])

    # Section header
    st.subheader("Overview")

    # --- Section 1: Key Metrics (polished cards) ---
    st.subheader("Key Metrics")

    # compute metrics
    total_customers = int(df[cust_col].nunique()) if cust_col else int(len(df))
    total_revenue = float(df[revenue_col].sum()) if revenue_col else 0.0
    avg_rev_per_cust = total_revenue / total_customers if total_customers else 0.0
    if products_col:
        if cust_col:
            avg_products = float(df.groupby(cust_col)[products_col].mean().mean())
        else:
            avg_products = float(df[products_col].mean())
    else:
        avg_products = 0.0

    # CSS for polished metric cards
    st.markdown(
        """
    <style>
      .metric-row { display:flex; gap:16px; width:100%; }
      .metric-card {
        flex:1;
        background: linear-gradient(180deg,#ffffff,#f8fafc);
        border-radius:12px;
        padding:16px 18px;
        box-shadow: 0 6px 18px rgba(15,23,42,0.06);
        border: 1px solid rgba(15,23,42,0.04);
      }
      .metric-top { display:flex; align-items:center; gap:12px; }
      .metric-icon {
        width:44px; height:44px; border-radius:10px;
        display:inline-flex; align-items:center; justify-content:center;
        background:#eef2ff; font-size:20px;
      }
      .metric-value { font-size:28px; font-weight:700; color:#0f172a; }
      .metric-label { font-size:13px; color:#475569; margin-top:6px; }
    </style>
    """,
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4 = st.columns([1, 1, 1, 1], gap="small")

    with c1:
        st.markdown(
            f"""
        <div class="metric-card">
          <div class="metric-top">
            <div class="metric-icon">👥</div>
            <div>
              <div class="metric-value">{total_customers:,}</div>
              <div class="metric-label">Total Customers</div>
            </div>
          </div>
        </div>
        """,
            unsafe_allow_html=True,
        )

    with c2:
        st.markdown(
            f"""
        <div class="metric-card">
          <div class="metric-top">
            <div class="metric-icon">💰</div>
            <div>
              <div class="metric-value">{_format_currency(total_revenue)}</div>
              <div class="metric-label">Total Revenue</div>
            </div>
          </div>
        </div>
        """,
            unsafe_allow_html=True,
        )

    with c3:
        st.markdown(
            f"""
        <div class="metric-card">
          <div class="metric-top">
            <div class="metric-icon">📈</div>
            <div>
              <div class="metric-value">{_format_currency(avg_rev_per_cust)}</div>
              <div class="metric-label">Avg Revenue / Customer</div>
            </div>
          </div>
        </div>
        """,
            unsafe_allow_html=True,
        )

    with c4:
        st.markdown(
            f"""
        <div class="metric-card">
          <div class="metric-top">
            <div class="metric-icon">🧩</div>
            <div>
              <div class="metric-value">{avg_products:.2f}</div>
              <div class="metric-label">Avg Products / Customer</div>
            </div>
          </div>
        </div>
        """,
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # --- Section 2: Distribution Charts ---
    st.subheader("Distribution Charts")
    left_col, right_col = st.columns(2)

    # CLV Tier Distribution (left)
    with left_col:
        st.info(
            "What: Horizontal bar chart of customer counts by CLV tier.\n"
            "Business question: Which CLV tiers contain the largest share of customers?\n"
            "Insight: Large concentrations in lower tiers may indicate growth opportunity via upgrades."
        )
        st.markdown("#### CLV Tier Distribution")
        if clv_col and not df[clv_col].isna().all():
            clv_counts = df[clv_col].value_counts(dropna=True)
            clv_df = clv_counts.rename_axis(clv_col).reset_index(name="count")
            clv_df["percent"] = clv_df["count"] / clv_df["count"].sum() * 100

            # Color mapping
            color_map = {
                "Platinum": "gold",
                "Gold": "silver",
                "Silver": "peru",
                "Bronze": "gray",
            }
            clv_df["color"] = clv_df[clv_col].map(lambda x: color_map.get(x, "#636EFA"))

            fig_clv = go.Figure(
                data=go.Bar(
                    x=clv_df["count"],
                    y=clv_df[clv_col],
                    orientation="h",
                    marker_color=clv_df["color"],
                    text=clv_df.apply(lambda r: f"{int(r['count'])} ({r['percent']:.1f}%)", axis=1),
                    hovertemplate="%{y}: %{x} customers<br>%{text}<extra></extra>",
                )
            )
            fig_clv.update_layout(template="plotly_white", height=320, margin=dict(l=80, r=10, t=30, b=30))
            st.plotly_chart(fig_clv, use_container_width=True)
        else:
            st.info(f"No CLV tier column found. Expected one of: 'clv_tier','tier','customer_tier'.")

    # Engagement Level Distribution (right)
    with right_col:
        st.info(
            "What: Donut chart showing distribution of engagement levels (High/Medium/Low).\n"
            "Business question: What share of customers are highly engaged vs at risk?\n"
            "Insight: A high Low-engagement share signals churn risk and re-engagement priority."
        )
        st.markdown("#### Engagement Level Distribution")
        if engagement_col and not df[engagement_col].isna().all():
            eng_counts = df[engagement_col].value_counts(dropna=True)
            eng_df = eng_counts.rename_axis(engagement_col).reset_index(name="count")
            eng_df["percent"] = eng_df["count"] / eng_df["count"].sum() * 100

            eng_color_map = {"High": "green", "Medium": "orange", "Low": "red"}
            eng_df["color"] = eng_df[engagement_col].map(lambda x: eng_color_map.get(x, None))

            fig_eng = go.Figure(
                go.Pie(
                    labels=eng_df[engagement_col],
                    values=eng_df["count"],
                    hole=0.4,
                    marker_colors=eng_df["color"].tolist(),
                    hovertemplate="%{label}: %{value} (<b>%{percent}</b>)<extra></extra>",
                )
            )
            fig_eng.update_layout(template="plotly_white", height=320, margin=dict(t=10, b=10))
            st.plotly_chart(fig_eng, use_container_width=True)
        else:
            st.info(f"No engagement column found. Expected one of: 'engagement_level','engagement','engagement_tier'.")

    st.markdown("---")

    # --- Section 3: Revenue Analysis ---
    st.subheader("Revenue Analysis")

    # Revenue by CLV Tier
    if revenue_col and clv_col and not df[clv_col].isna().all():
        st.info(
            "What: Horizontal bar chart of revenue contributed by each CLV tier.\n"
            "Business question: Which tiers drive the majority of revenue?\n"
            "Insight: If revenue is concentrated in one tier, prioritize retention/expansion on that tier."
        )
        rev_by_tier = df.groupby(clv_col)[revenue_col].sum().reset_index()
        rev_by_tier = rev_by_tier.sort_values(by=revenue_col, ascending=False)

        fig_rev_tier = px.bar(
            rev_by_tier,
            x=revenue_col,
            y=clv_col,
            orientation="h",
            text=revenue_col,
            labels={revenue_col: "Revenue", clv_col: "CLV Tier"},
            template="plotly_white",
        )
        fig_rev_tier.update_traces(hovertemplate="%{y}: %{x:$,.2f}<extra></extra>")
        fig_rev_tier.update_layout(height=420, margin=dict(l=120, r=20, t=30, b=30))
        st.plotly_chart(fig_rev_tier, use_container_width=True)
    else:
        st.info("Revenue-by-tier chart requires both revenue and CLV tier columns.")

    # Revenue by segment (if exists)
    if revenue_col and segment_col and not df[segment_col].isna().all():
        st.info(
            "What: Bar chart showing revenue by customer segment.\n"
            "Business question: Which customer segments generate the most revenue?\n"
            "Insight: High-revenue segments are prime candidates for targeted upsell programs."
        )
        st.markdown("#### Revenue by Segment")
        rev_by_seg = df.groupby(segment_col)[revenue_col].sum().reset_index()
        rev_by_seg = rev_by_seg.sort_values(by=revenue_col, ascending=False)

        fig_seg = px.bar(
            rev_by_seg,
            x=segment_col,
            y=revenue_col,
            labels={revenue_col: "Revenue", segment_col: "Segment"},
            template="plotly_white",
        )
        fig_seg.update_traces(hovertemplate="%{x}: %{y:$,.2f}<extra></extra>")
        fig_seg.update_layout(height=360, margin=dict(l=20, r=20, t=20, b=80))
        st.plotly_chart(fig_seg, use_container_width=True)
    else:
        if not segment_col:
            st.info("No 'segment' column detected; skipping Revenue by Segment.")
