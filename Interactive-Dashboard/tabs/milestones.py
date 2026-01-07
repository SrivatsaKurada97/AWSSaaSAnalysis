from typing import Optional, List

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


def _find_column(df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
    if df is None:
        return None
    cols = list(df.columns)
    lower_map = {c.lower(): c for c in cols}
    for cand in candidates:
        if cand is None:
            continue
        key = cand.lower()
        if key in lower_map:
            return lower_map[key]
    return None


def _format_currency(x: float) -> str:
    try:
        return f"${x:,.0f}"
    except Exception:
        return str(x)


def _assign_revenue_tier(amount: float) -> str:
    if pd.isna(amount):
        return "Unknown"
    a = float(amount)
    if a < 10_000:
        return "Tier 1 (<10K)"
    if 10_000 <= a < 20_000:
        return "Tier 2 (10K-20K)"
    if 20_000 <= a < 30_000:
        return "Tier 3 (20K-30K)"
    return "Tier 4 (30K+)"


def generate_milestone_insights(df: pd.DataFrame) -> List[str]:
    """Generate 4-6 short data-driven insights for the milestones tab.

    Returns a list of markdown-ready strings (with bold numbers and emojis).
    """
    insights: List[str] = []
    if df is None or df.empty:
        return ["No data available to generate insights."]

    # find likely columns
    cust_col = _find_column(df, ["customerID", "customer_id", "cust_id", "id"])
    revenue_col = _find_column(df, ["total_revenue_at_milestone", "revenue", "sales", "amount", "total_revenue", "spend", "cumulative_revenue"])
    clv_col = _find_column(df, ["clv_tier", "tier", "customer_tier", "clv"])
    engagement_col = _find_column(df, ["engagement_level", "engagement", "engagement_tier"])
    date_col = _find_column(df, ["milestone_date", "date", "orderdate", "purchase_date", "created_at"])

    # build per-customer revenue
    try:
        if cust_col and cust_col in df.columns:
            cust_rev = df.groupby(cust_col)[revenue_col].sum().reset_index().rename(columns={revenue_col: "total_revenue"})
        else:
            cust_rev = df[[revenue_col]].rename(columns={revenue_col: "total_revenue"}).reset_index(drop=True)
    except Exception:
        return ["Could not compute revenue aggregates for insights."]

    cust_rev["total_revenue"] = pd.to_numeric(cust_rev["total_revenue"], errors="coerce").fillna(0)
    total_customers = len(cust_rev)
    total_revenue = cust_rev["total_revenue"].sum() if total_customers else 0

    # Insight 1: % reached 30K+
    reached_30k = (cust_rev["total_revenue"] >= 30_000).sum()
    pct_30k = (reached_30k / total_customers * 100) if total_customers else 0
    insights.append(f"🔥 **{pct_30k:.1f}%** of customers have reached the **$30K+** revenue milestone ({reached_30k}/{total_customers}).")

    # Insight 2: CLV tier contributions
    if clv_col and clv_col in df.columns:
        try:
            # aggregate by customer to get unique CLV assignments
            cust_clv = df.groupby(cust_col).agg({clv_col: "first", revenue_col: "sum"}).reset_index()
            cust_clv[revenue_col] = pd.to_numeric(cust_clv[revenue_col], errors="coerce").fillna(0)

            tier_summary = []
            for tier in ["Platinum", "Gold", "Silver"]:
                tier_data = cust_clv[cust_clv[clv_col].astype(str).str.lower() == tier.lower()]
                if not tier_data.empty:
                    count = len(tier_data)
                    pct_cust = (count / total_customers * 100) if total_customers else 0
                    tier_rev = tier_data[revenue_col].sum()
                    pct_rev = (tier_rev / total_revenue * 100) if total_revenue else 0
                    tier_summary.append({
                        'tier': tier,
                        'pct_customers': pct_cust,
                        'pct_revenue': pct_rev
                    })

            parts = []
            for r in tier_summary:
                tier = r['tier']
                parts.append(f"{tier}: **{r['pct_customers']:.1f}%** of customers, **{r['pct_revenue']:.1f}%** of revenue")

            if parts:
                insights.append("\n ⭐ CLV tier contributions — " + "; ".join(parts) + ".")
        except Exception:
            pass

    # Insight 3: typical days to milestones (requires transaction-level dates)
    if cust_col and date_col and date_col in df.columns:
        try:
            tx = df[[cust_col, revenue_col, date_col]].copy()
            tx[date_col] = pd.to_datetime(tx[date_col], errors="coerce")
            tx[revenue_col] = pd.to_numeric(tx[revenue_col], errors="coerce").fillna(0)
            tx = tx.dropna(subset=[date_col])
            tx = tx.sort_values([cust_col, date_col])

            def first_cross_days(group, threshold):
                # If revenue in the source appears already cumulative (milestone rows),
                # find the first row where revenue >= threshold and subtract the start date.
                vals = group[revenue_col].values
                is_cumulative = False
                if len(vals) > 1:
                    # simple heuristic: non-decreasing series likely cumulative
                    is_cumulative = all(vals[i] >= vals[i - 1] for i in range(1, len(vals)))
                    # also treat column name hints as cumulative
                    if "total" in revenue_col.lower() or "at_milestone" in revenue_col.lower():
                        is_cumulative = True

                if is_cumulative:
                    crossed = group[group[revenue_col] >= threshold]
                    if crossed.empty:
                        return None
                    return (crossed.iloc[0][date_col] - group.iloc[0][date_col]).days

                # otherwise treat values as incremental transactions and use running sum
                running = group[revenue_col].cumsum()
                crossed = running[running >= threshold]
                if crossed.empty:
                    return None
                idx = crossed.index[0]
                return (group.loc[idx, date_col] - group.iloc[0][date_col]).days

            groups = [g for _, g in tx.groupby(cust_col)]
            import numpy as np
            days_10 = [first_cross_days(g, 10_000) for g in groups]
            days_20 = [first_cross_days(g, 20_000) for g in groups]
            days_30 = [first_cross_days(g, 30_000) for g in groups]
            def _mean_days(arr):
                vals = [d for d in arr if d is not None]
                return int(np.nanmean(vals)) if vals else None

            m10 = _mean_days(days_10)
            m20 = _mean_days(days_20)
            m30 = _mean_days(days_30)
            insights.append(f"\n ⏱️ Customers typically take **{m10 if m10 is not None else 'N/A'}d** / **{m20 if m20 is not None else 'N/A'}d** / **{m30 if m30 is not None else 'N/A'}d** to reach **10K/20K/30K** respectively.")
        except Exception:
            pass

    # Insight 4: revenue concentration by top tier
    try:
        top_tier = cust_rev.sort_values("total_revenue", ascending=False).head(max(1, int(max(1, total_customers * 0.01)) ))
        top_sum = top_tier["total_revenue"].sum()
        pct_top = (top_sum / total_revenue * 100) if total_revenue else 0
        insights.append(f"\n 💡 Top customers (top 1) contribute **{pct_top:.1f}%** of revenue — consider targeted retention/expansion." )
    except Exception:
        pass

    # ensure 4-6 bullets; trim or expand with simple stats
    if len(insights) < 4:
        insights.append(f"\n 📊 Total customers: **{total_customers}**, Total revenue: **{_format_currency(total_revenue)}**.")

    return insights


def render_milestones(df: pd.DataFrame):
    """Render Milestones Deepdive: revenue tiers, distribution, funnel, and metrics.

    Expects a DataFrame with revenue per row and (preferably) a customer identifier.
    The function is defensive and will show informative messages when required
    columns are missing.
    """

    st.subheader("Milestones Deepdive")

    if df is None or not isinstance(df, pd.DataFrame):
        st.error("No DataFrame provided to Milestones tab.")
        return

    if df.empty:
        st.warning("DataFrame is empty — nothing to show.")
        return

    # SECTION 0: Key Insights (AI-generated)
    try:
        insights = generate_milestone_insights(df)
        left_col, right_col = st.columns([0.92, 0.08])
    
        with left_col:
            st.info("\n".join([f"• {i}" for i in insights]))
    
        with right_col:
            if st.button("🔄", key="regen_insights", help="Regenerate Insights"):
                insights = generate_milestone_insights(df)
                st.rerun()
        
            # Close container
            st.markdown('</div>', unsafe_allow_html=True)

    except Exception:
        st.warning("Could not generate insights for this dataset.")

    st.markdown("---")

    
    # find key columns
    cust_col = _find_column(df, ["customerID", "customer_id", "cust_id", "id"])
    revenue_col = _find_column(df, ["total_revenue_at_milestone", "revenue", "sales", "amount", "total_revenue", "spend"])
    clv_col = _find_column(df, ["clv_tier", "tier", "customer_tier", "clv"])
    engagement_col = _find_column(df, ["engagement_level", "engagement", "engagement_tier"])
    products_col = _find_column(df, ["products_used_at_milestone", "product_count", "products"])
    tenure_col = _find_column(df, ["tenure_days", "days_since_signup", "customer_age_days"])

    # build per-customer revenue summary
    if not revenue_col or revenue_col not in df.columns:
        st.error(f"Could not find a revenue column. Looked for: total_revenue_at_milestone, revenue, sales, etc.")
        return

    try:
        if cust_col and cust_col in df.columns:
            cust_rev = df.groupby(cust_col)[revenue_col].sum().reset_index().rename(columns={revenue_col: "total_revenue"})
        else:
            cust_rev = df[[revenue_col]].rename(columns={revenue_col: "total_revenue"}).reset_index(drop=True)
    except Exception as e:
        st.error(f"Error aggregating revenue by customer: {e}")
        return

    # merge additional columns if they exist
    if cust_col:
        for col_name in [clv_col, engagement_col, products_col, tenure_col]:
            if col_name and col_name in df.columns:
                try:
                    agg_col = df.groupby(cust_col)[col_name].first().reset_index()
                    cust_rev = cust_rev.merge(agg_col, on=cust_col, how="left")
                except Exception:
                    pass

    cust_rev["total_revenue"] = pd.to_numeric(cust_rev["total_revenue"], errors="coerce").fillna(0)
    cust_rev["revenue_tier"] = cust_rev["total_revenue"].apply(_assign_revenue_tier)

    st.subheader("Revenue Tier Distribution")
    st.info(
        "What: Shows customer counts and revenue share across revenue tiers.\n"
        "Which customer segments (by revenue tier) drive most of our revenue?\n"
        "AI insight: Highlight top tier contributions to prioritize retention/expansion."
    )
    tier_counts = cust_rev["revenue_tier"].value_counts().reindex(["Tier 4 (30K+)", "Tier 3 (20K-30K)", "Tier 2 (10K-20K)", "Tier 1 (<10K)"], fill_value=0)

    col1, col2 = st.columns([1, 1])
    with col1:
        fig_pie = px.pie(values=tier_counts.values, names=tier_counts.index, title="Customer Count by Revenue Tier", template="plotly_white", color_discrete_sequence=px.colors.sequential.Teal)
        fig_pie.update_layout(height=360)
        st.plotly_chart(fig_pie, use_container_width=True)

    with col2:
        # revenue % by tier
        tier_rev_map = {}
        for tier in tier_counts.index:
            tier_rev_map[tier] = cust_rev[cust_rev["revenue_tier"] == tier]["total_revenue"].sum()
        fig_pie_rev = px.pie(values=list(tier_rev_map.values()), names=list(tier_rev_map.keys()), title="Revenue % by Tier", template="plotly_white", color_discrete_sequence=px.colors.sequential.Teal)
        fig_pie_rev.update_layout(height=360)
        st.plotly_chart(fig_pie_rev, use_container_width=True)

    st.markdown("---")

    # PART 1: REVENUE FUNNEL
    st.subheader("Revenue Milestone Funnel")
    st.info(
        "What: Funnel showing counts of customers reaching revenue milestones.\n"
        "How efficiently do customers progress to higher revenue milestones?\n"
        "AI insight: Conversion drops between steps highlight where to focus growth programs."
    )

    funnel_data = {
        "Stage": ["All Customers", "Reached $10K+", "Reached $20K+", "Reached $30K+"],
        "Count": [
            len(cust_rev),
            (cust_rev["total_revenue"] >= 10_000).sum(),
            (cust_rev["total_revenue"] >= 20_000).sum(),
            (cust_rev["total_revenue"] >= 30_000).sum(),
        ]
    }
    funnel_df = pd.DataFrame(funnel_data)
    funnel_df["Percentage"] = (funnel_df["Count"] / funnel_df["Count"].iloc[0] * 100).round(1)

    fig_funnel = go.Figure(go.Funnel(
        y=funnel_df["Stage"],
        x=funnel_df["Count"],
        textinfo="value+percent initial",
        marker=dict(color=["#0EA5A4", "#10B981", "#F59E0B", "#EF4444"]),
        connector=dict(line=dict(color="gray", width=2))
    ))
    fig_funnel.update_layout(title="Revenue Milestone Funnel", template="plotly_white", height=400)
    st.plotly_chart(fig_funnel, use_container_width=True)

    # metrics
    metrics_data = {
        "Metric": ["Avg Revenue", "Median Revenue", "Top 10% Threshold"],
        "Value": [
            cust_rev["total_revenue"].mean(),
            cust_rev["total_revenue"].median(),
            cust_rev["total_revenue"].quantile(0.9)
        ]
    }
    metrics_df = pd.DataFrame(metrics_data)
    metrics_df["Value"] = metrics_df["Value"].apply(_format_currency)

    fig_metrics = go.Figure(go.Bar(x=metrics_df["Metric"], y=[100] * len(metrics_df), text=metrics_df["Value"], textposition="inside"))
    fig_metrics.update_traces(marker_color=["#3B82F6", "#10B981", "#F59E0B"], textfont_size=16, textfont_color="white")
    fig_metrics.update_layout(
        title="Key Revenue Metrics",
        template="plotly_white",
        showlegend=False,
        height=320,
        margin=dict(l=40, r=20, t=30, b=40),
        xaxis=dict(range=[0, 100])
    )
    st.info(
        "What: Key revenue metrics (avg, median, top decile).\n"
        "What are central tendencies and thresholds to target for expansion?\n"
        "AI insight: If average >> median, revenue is skewed by a small set of high-value customers."
    )
    st.plotly_chart(fig_metrics, use_container_width=True)

    st.markdown("---")

    # PART 2: CUSTOMER LIFECYCLE STAGES
    st.subheader("Customer Lifecycle Stages")

    # Require CLV and engagement to compute stages
    if not (clv_col and clv_col in cust_rev.columns and engagement_col and engagement_col in cust_rev.columns):
        st.info("Lifecycle stage analysis requires `clv_tier` and `engagement` columns per customer.")
    else:
        # normalize strings
        cust_rev[clv_col] = cust_rev[clv_col].astype(str)
        cust_rev[engagement_col] = cust_rev[engagement_col].astype(str)

        # assign stages based on rules
        def _assign_stage(row):
            clv = str(row.get(clv_col, "")).strip()
            eng = str(row.get(engagement_col, "")).strip()
            tenure = pd.to_numeric(row.get(tenure_col, 0), errors="coerce") if tenure_col in row.index else 0
            # At Risk: low engagement + high tenure (>365 days)
            if eng.lower() == "low" and pd.notna(tenure) and tenure > 365:
                return "At Risk"
            # Mature: Platinum + High
            if clv.lower() == "platinum" and eng.lower() == "high":
                return "Mature"
            # Growing: Gold + Medium/High OR Silver + High
            if (clv.lower() == "gold" and eng.lower() in ["medium", "high"]) or (clv.lower() == "silver" and eng.lower() == "high"):
                return "Growing"
            # Developing: Bronze/Silver + Low/Medium
            if clv.lower() in ["bronze", "silver"] and eng.lower() in ["low", "medium"]:
                return "Developing"
            # default
            return "Developing"

        cust_rev["lifecycle_stage"] = cust_rev.apply(_assign_stage, axis=1)

        # SECTION 4: Lifecycle Stage Distribution (Sankey)
        st.subheader("Lifecycle Stage Flow (CLV → Engagement → Stage)")
        st.info(
            "What: Sankey flow mapping CLV tier → engagement → lifecycle stage.\n"
            "How do customers flow from tier and engagement into lifecycle stages?\n"
            "AI insight: Identify large flows into 'At Risk' to prioritize recovery campaigns."
        )
        # nodes: CLV tiers, engagement, stages
        clv_nodes = list(cust_rev[clv_col].dropna().astype(str).unique())
        eng_nodes = list(cust_rev[engagement_col].dropna().astype(str).unique())
        stage_nodes = list(cust_rev["lifecycle_stage"].dropna().astype(str).unique())
        nodes = clv_nodes + eng_nodes + stage_nodes
        node_idx = {n: i for i, n in enumerate(nodes)}

        # links CLV -> Engagement
        links_src = []
        links_tgt = []
        links_val = []
        for key, g in cust_rev.groupby([clv_col, engagement_col]):
            # key is a tuple (clv_value, engagement_value)
            clv_val = str(key[0])
            eng_val = str(key[1])
            count = len(g)
            # guard against missing nodes
            if clv_val in node_idx and eng_val in node_idx:
                links_src.append(node_idx[clv_val])
                links_tgt.append(node_idx[eng_val])
                links_val.append(count)

        # links Engagement -> Stage
        for key, g in cust_rev.groupby([engagement_col, "lifecycle_stage"]):
            eng_val = str(key[0])
            stg_val = str(key[1])
            count = len(g)
            if eng_val in node_idx and stg_val in node_idx:
                links_src.append(node_idx[eng_val])
                links_tgt.append(node_idx[stg_val])
                links_val.append(count)

        # stage colors
        stage_colors = {"Developing": "#93C5FD", "Growing": "#60A5FA", "Mature": "#FBBF24", "At Risk": "#FB7185"}
        # node colors: CLV gray, engagement light, stage by mapping
        node_colors = []
        for n in nodes:
            if n in stage_colors:
                node_colors.append(stage_colors[n])
            elif n in clv_nodes:
                node_colors.append("#9CA3AF")
            else:
                node_colors.append("#A7F3D0")

        fig_sankey = go.Figure(data=[
            go.Sankey(
                node=dict(label=nodes, color=node_colors, pad=15, thickness=20),
                link=dict(source=links_src, target=links_tgt, value=links_val)
            )
        ])
        fig_sankey.update_layout(title_text="CLV → Engagement → Lifecycle Stage", font_size=10, height=520)
        st.plotly_chart(fig_sankey, use_container_width=True)

        st.markdown("---")

        # SECTION 5: Stage Performance Comparison
        st.subheader("Stage Performance Comparison")
        st.info(
            "What: Compares average revenue and product counts by lifecycle stage.\n"
            "Which stages deliver highest revenue per customer and product adoption?\n"
            "AI insight: Stages with below-average revenue but high product usage may be upsell opportunities."
        )
        left, right = st.columns(2)

        overall_avg_rev = cust_rev["total_revenue"].mean()
        overall_avg_prod = pd.to_numeric(cust_rev.get(products_col, pd.Series(dtype=float)), errors="coerce").fillna(0).mean()

        with left:
            rev_by_stage = cust_rev.groupby("lifecycle_stage")["total_revenue"].mean().reset_index().sort_values(by="total_revenue", ascending=False)
            fig_stage_rev = px.bar(rev_by_stage, x="lifecycle_stage", y="total_revenue", labels={"lifecycle_stage": "Stage", "total_revenue": "Avg Revenue"}, template="plotly_white")
            fig_stage_rev.add_hline(y=overall_avg_rev, line_dash="dash", line_color="red", annotation_text="Overall avg", annotation_position="top right")
            fig_stage_rev.update_layout(height=360)
            st.plotly_chart(fig_stage_rev, use_container_width=True)

        with right:
            if products_col and products_col in cust_rev.columns:
                prod_by_stage = cust_rev.groupby("lifecycle_stage")[products_col].mean().reset_index().sort_values(by=products_col, ascending=False)
                fig_stage_prod = px.bar(prod_by_stage, x="lifecycle_stage", y=products_col, labels={"lifecycle_stage": "Stage", products_col: "Avg Products"}, template="plotly_white")
                fig_stage_prod.add_hline(y=overall_avg_prod, line_dash="dash", line_color="red", annotation_text="Overall avg", annotation_position="top right")
                fig_stage_prod.update_layout(height=360)
                st.plotly_chart(fig_stage_prod, use_container_width=True)
            else:
                st.info("Products data not available to show stage product comparison.")

        st.markdown("---")

        # SECTION 6: Stage Transition Opportunities
        st.subheader("Stage Transition Opportunities")
        st.info(
            "What: Heuristic list of customers close to the next CLV tier or with rising engagement.\n"
            "Which customers are the best targets for one-step upsell or retention interventions?\n"
            "AI insight: Customers near the next revenue threshold and with medium engagement are high-value outreach targets."
        )
        # Heuristic: customers close to next CLV tier by revenue (>=90% of next threshold) or engagement one level below high
        opportunities = []
        clv_rank = ["Bronze", "Silver", "Gold", "Platinum"]
        next_threshold = {"Bronze": 10000, "Silver": 20000, "Gold": 30000}

        for _, r in cust_rev.iterrows():
            cid = r.get(cust_col) if cust_col else None
            name = r.get(cust_col) if not cid else None
            clv = str(r.get(clv_col, "")).title() if clv_col in r.index else None
            eng = str(r.get(engagement_col, "")).title() if engagement_col in r.index else None
            rev = float(r.get("total_revenue", 0))
            tenure = float(r.get(tenure_col, 0)) if tenure_col in r.index else None
            reason = []
            recommend = []
            if clv in clv_rank and clv != "Platinum":
                thresh = next_threshold.get(clv)
                if thresh and rev >= 0.9 * thresh:
                    reason.append(f"Revenue close to {thresh}")
                    recommend.append("Run targeted upsell campaign")
            if eng and eng.lower() == "medium":
                reason.append("Engagement near High")
                recommend.append("Nudge with feature highlights")

            if reason:
                opportunities.append({
                    "customer_id": cid,
                    "clv": clv,
                    "engagement": eng,
                    "total_revenue": rev,
                    "tenure_days": tenure,
                    "reasons": "; ".join(reason),
                    "recommended_actions": "; ".join(recommend)
                })

        if not opportunities:
            st.info("No clear 1-tier transition opportunities detected with current heuristic.")
        else:
            opp_df = pd.DataFrame(opportunities)
            with st.expander(f"View {len(opp_df)} Opportunities"):
                st.dataframe(opp_df, use_container_width=True)
                csv_bytes = opp_df.to_csv(index=False).encode("utf-8")
                st.download_button("Export Opportunities", data=csv_bytes, file_name="opportunities.csv", mime="text/csv")
