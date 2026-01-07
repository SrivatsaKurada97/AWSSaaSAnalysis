import io
from typing import List, Optional

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


def render_users_events(df: pd.DataFrame):
    """Render Users & Events deepdive tab.

    Sidebar filters (CLV Tier, Engagement, Segment) with Apply button.
    Sections:
      1) User Segmentation Matrix (heatmap: CLV x Engagement)
      2) Behavioral Analysis (histograms: product_count, tenure_days)
      3) Customer Deep Dive table with CSV download
    """

    if df is None or not isinstance(df, pd.DataFrame):
        st.error("No dataframe provided to Users & Events tab.")
        return

    if df.empty:
        st.warning("⚠️ Dataframe is empty. No data to display.")
        return

    # Discover columns (flexible names)
    custid_col = _find_column(df, ["customerID", "customerid", "cust_id", "id"])
    customer_col = _find_column(df, ["customer", "name", "company"])
    segment_col = _find_column(df, ["segment", "customer_segment", "market_segment"])
    clv_col = _find_column(df, ["clv_tier", "tier", "customer_tier", "clv"])
    engagement_col = _find_column(df, ["engagement_level", "engagement", "engagement_tier", "engagement_score"])
    revenue_col = _find_column(df, ["revenue", "sales", "amount", "total_revenue", "spend"])
    products_col = _find_column(df, ["products_count", "product_count", "num_products", "products"])
    tenure_col = _find_column(df, ["tenure_days", "tenure", "days_active"])

    # Debug: Show what columns were found
    # st.caption(f"Debug - Columns found: CLV={clv_col}, Engagement={engagement_col}, Products={products_col}, Tenure={tenure_col}")

    st.sidebar.markdown("---")
    st.sidebar.header("🔍 Filters — Users & Events")

    # Prepare filter options from the full dataset
    clv_options = []
    if clv_col and clv_col in df.columns and not df[clv_col].isna().all():
        clv_options = sorted(df[clv_col].dropna().astype(str).unique().tolist())

    eng_options = []
    if engagement_col and engagement_col in df.columns and not df[engagement_col].isna().all():
        eng_options = sorted(df[engagement_col].dropna().astype(str).unique().tolist())

    seg_options = []
    if segment_col and segment_col in df.columns and not df[segment_col].isna().all():
        seg_options = sorted(df[segment_col].dropna().astype(str).unique().tolist())

    # Session-backed selections: store 'applied' filter values
    if "ue_filters" not in st.session_state:
        st.session_state["ue_filters"] = {"clv": [], "eng": [], "seg": []}

    with st.sidebar.form(key="ue_filter_form"):
        st.caption("💡 Leave empty to show all records")
        
        selected_clv = st.multiselect(
            "CLV Tier", 
            options=clv_options, 
            default=st.session_state["ue_filters"]["clv"],
            help="Select one or more CLV tiers to filter"
        )
        selected_eng = st.multiselect(
            "Engagement Level", 
            options=eng_options, 
            default=st.session_state["ue_filters"]["eng"],
            help="Select one or more engagement levels to filter"
        )
        if seg_options:
            selected_seg = st.multiselect(
                "Segment", 
                options=seg_options, 
                default=st.session_state["ue_filters"]["seg"],
                help="Select one or more segments to filter"
            )
        else:
            selected_seg = []

        col1, col2 = st.columns(2)
        with col1:
            apply_button = st.form_submit_button("Apply Filters", use_container_width=True)
        with col2:
            reset_button = st.form_submit_button("Reset All", use_container_width=True)

    if apply_button:
        st.session_state["ue_filters"] = {"clv": selected_clv, "eng": selected_eng, "seg": selected_seg}
        st.rerun()

    if reset_button:
        st.session_state["ue_filters"] = {"clv": [], "eng": [], "seg": []}
        st.rerun()

    # Create filtered dataframe
    df_active = df.copy()
    f = st.session_state["ue_filters"]
    
    # Apply filters
    if clv_col and f.get("clv"):
        df_active = df_active[df_active[clv_col].astype(str).isin([str(x) for x in f.get("clv")])]
    if engagement_col and f.get("eng"):
        df_active = df_active[df_active[engagement_col].astype(str).isin([str(x) for x in f.get("eng")])]
    if segment_col and f.get("seg"):
        df_active = df_active[df_active[segment_col].astype(str).isin([str(x) for x in f.get("seg")])]

    # Show filter status and record count
    st.subheader("Users & Events Deepdive")
    
    active_filters = []
    if f.get("clv"):
        active_filters.append(f"CLV: {', '.join(f['clv'])}")
    if f.get("eng"):
        active_filters.append(f"Engagement: {', '.join(f['eng'])}")
    if f.get("seg"):
        active_filters.append(f"Segment: {', '.join(f['seg'])}")
    
    if active_filters:
        st.info(f"🔍 Active Filters: {' | '.join(active_filters)} | Showing {len(df_active):,} of {len(df):,} records")
    else:
        st.info(f"📊 Showing all {len(df):,} records (no filters applied)")

    if df_active.empty:
        st.warning("⚠️ No data matches the selected filters. Try adjusting your filter criteria.")
        return

    st.markdown("---")

    # Section 1: User Segmentation Matrix
    st.subheader("User Segmentation Matrix")

    st.info(
        "What:\n"
        "- Counts of customers by CLV Tier (rows) and Engagement Level (columns).\n\n"
        "\n"
        "- Where are customers concentrated across CLV and engagement; which segments need attention?\n\n"
        "Insight:\n"
        "- High counts in high-CLV & high-engagement cells indicate healthy segments; high-CLV but low-engagement cells may be churn risks or upsell opportunities."
    )
    if not clv_col or not engagement_col:
        st.info("Heatmap requires both CLV tier and Engagement columns.")
    else:
        # pivot counts using full active (filtered) dataset
        pivot = (
            df_active[[clv_col, engagement_col]]
            .dropna()
            .assign(**{clv_col: df_active[clv_col].astype(str), engagement_col: df_active[engagement_col].astype(str)})
            .groupby([clv_col, engagement_col])
            .size()
            .reset_index(name="count")
        )

        if pivot.empty:
            st.warning("No data available for the selected filters to build the heatmap.")
        else:
            # ensure consistent ordering
            row_order = sorted(pivot[clv_col].unique().tolist())
            col_order = sorted(pivot[engagement_col].unique().tolist())

            heat_df = pivot.pivot(index=clv_col, columns=engagement_col, values="count").fillna(0)
            heat_df = heat_df.reindex(index=row_order, columns=col_order, fill_value=0)

            fig = go.Figure(
                data=go.Heatmap(
                    z=heat_df.values,
                    x=heat_df.columns.astype(str),
                    y=heat_df.index.astype(str),
                    colorscale="Blues",
                    hovertemplate="CLV: %{y}<br>Engagement: %{x}<br>Count: %{z}<extra></extra>",
                )
            )
            # add annotations
            annotations = []
            for i, yi in enumerate(heat_df.index):
                for j, xj in enumerate(heat_df.columns):
                    val = heat_df.iloc[i, j]
                    annotations.append(
                        dict(
                            x=str(xj),
                            y=str(yi),
                            text=str(int(val)),
                            showarrow=False,
                            font=dict(
                                color="black" if val < heat_df.values.max() * 0.6 else "white",
                                size=14
                            ),
                        )
                    )
            fig.update_layout(
                template="plotly_white", 
                annotations=annotations, 
                xaxis_title="Engagement Level", 
                yaxis_title="CLV Tier", 
                height=420,
                margin=dict(l=100, r=20, t=40, b=80)
            )
            st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # Section 2: Behavioral Analysis (2 columns)
    st.subheader("Behavioral Analysis")
    left, right = st.columns(2)

    # Left: Product Count Distribution
    with left:
        st.markdown("#### Product Count Distribution")
        st.info(
            "What:\n"
            "- Distribution of the number of products each customer uses, with the average highlighted.\n\n"
            "\n"
            "- Are customers primarily single-product or multi-product users (opportunity for cross-sell)?\n\n"
            "Insight:\n"
            "- A higher average product count suggests stronger cross-sell / product adoption; many single-product customers indicate bundling opportunities."
        )
        if products_col and products_col in df_active.columns and not df_active[products_col].dropna().empty:
            prod_series = pd.to_numeric(df_active[products_col], errors="coerce").dropna()
            
            if prod_series.empty:
                st.info("No valid product count data in filtered dataset.")
            else:
                avg_prod = prod_series.mean()
                fig = px.histogram(
                    prod_series, 
                    nbins=30, 
                    labels={"value": "Product Count"}, 
                    template="plotly_white"
                )
                fig.update_layout(
                    yaxis_title="Number of Customers", 
                    xaxis_title="Product Count", 
                    height=360,
                    showlegend=False
                )
                # add vertical avg line
                fig.add_vline(
                    x=avg_prod, 
                    line_dash="dash", 
                    line_color="red", 
                    annotation_text=f"Avg: {avg_prod:.1f}", 
                    annotation_position="top right"
                )
                st.plotly_chart(fig, use_container_width=True)
                st.caption(f"📊 Average products per customer: **{avg_prod:.2f}**")
        else:
            st.info("No product count column found or no data available.")

    # Right: Tenure Analysis
    with right:
        st.markdown("#### Tenure Analysis")
        st.info(
                "What:\n"
                "- Distribution of customer tenure (in days) with summary metrics (mean, median, 90th percentile).\n\n"
                "\n"
                "- How long do customers typically remain active and where are retention risks concentrated?\n\n"
                "Insight:\n"
                "- A short median tenure indicates potential churn pressure; a long tail of high-tenure customers suggests a loyal cohort worth studying."
            )
        if tenure_col and tenure_col in df_active.columns and not df_active[tenure_col].dropna().empty:
            tenure_series = pd.to_numeric(df_active[tenure_col], errors="coerce").dropna()
            
            if tenure_series.empty:
                st.info("No valid tenure data in filtered dataset.")
            else:
                mean_t = tenure_series.mean()
                median_t = tenure_series.median()
                p90 = tenure_series.quantile(0.9)

                fig_t = px.histogram(
                    tenure_series, 
                    nbins=40, 
                    labels={"value": "Tenure (days)"}, 
                    template="plotly_white"
                )
                fig_t.update_layout(
                    yaxis_title="Number of Customers", 
                    xaxis_title="Tenure (days)", 
                    height=360,
                    showlegend=False
                )
                st.plotly_chart(fig_t, use_container_width=True)

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Mean", f"{mean_t:.0f} days")
                with col2:
                    st.metric("Median", f"{median_t:.0f} days")
                with col3:
                    st.metric("90th percentile", f"{p90:.0f} days")
        else:
            st.info("No tenure column found or no data available.")

    st.markdown("---")

    # Section 3: Customer Deep Dive Table
    st.subheader("Customer Deep Dive")
    st.info(
        "What:\n"
        "- Row-level customer details (ID, name, CLV tier, engagement, revenue, products, tenure).\n\n"
        "\n"
        "- Which individual customers should be prioritized for outreach, retention, or expansion?\n\n"
        "Insight:\n"
        "- Sort and filter to find high-revenue but low-engagement customers for targeted re-engagement campaigns."
    )
    
    # desired column order
    desired = [custid_col, customer_col, segment_col, clv_col, engagement_col, revenue_col, products_col, tenure_col]
    col_names = [c for c in desired if c and c in df_active.columns]

    if not col_names:
        st.info("No customer columns found to display in the deep dive table.")
        return

    sub = df_active[col_names].copy()
    
    # rename to friendly labels
    rename_map = {}
    if custid_col and custid_col in sub.columns:
        rename_map[custid_col] = "Customer ID"
    if customer_col and customer_col in sub.columns:
        rename_map[customer_col] = "Customer Name"
    if segment_col and segment_col in sub.columns:
        rename_map[segment_col] = "Segment"
    if clv_col and clv_col in sub.columns:
        rename_map[clv_col] = "CLV Tier"
    if engagement_col and engagement_col in sub.columns:
        rename_map[engagement_col] = "Engagement"
    if revenue_col and revenue_col in sub.columns:
        rename_map[revenue_col] = "Revenue"
    if products_col and products_col in sub.columns:
        rename_map[products_col] = "Products"
    if tenure_col and tenure_col in sub.columns:
        rename_map[tenure_col] = "Tenure (days)"

    sub = sub.rename(columns=rename_map)
    
    # Show table
    with st.expander(f"📋 View Customer Table ({len(sub):,} records)", expanded=True):
        st.dataframe(sub, use_container_width=True, height=400)

        # CSV download
        to_download = sub.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="⬇️ Download as CSV", 
            data=to_download, 
            file_name="customers_deepdive.csv", 
            mime="text/csv",
            use_container_width=True
        )

    st.markdown("---")

    # SECTION 4: Cohort Analysis (tenure buckets)
    st.subheader("Cohort Analysis — Tenure Buckets")

    st.info(
        "What:\n"
        "- Average revenue and/or product counts for customers grouped into tenure buckets (0-90, 91-180, 181-365, 365+ days).\n\n"
        "\n"
        "- How do customer value metrics evolve as customers age?\n\n"
        "Insight:\n"
        "- If average sales rise with tenure, accelerate onboarding to realize value earlier; flat or declining trends suggest retention or monetization issues."
    )

    # Define tenure buckets
    if tenure_col and tenure_col in df_active.columns:
        try:
            tenure_vals = pd.to_numeric(df_active[tenure_col], errors="coerce")
            bins = [0, 90, 180, 365, float('inf')]
            labels = ["0-90", "91-180", "181-365", "365+"]
            df_active = df_active.assign(_tenure_bucket=pd.cut(tenure_vals, bins=bins, labels=labels, right=True))

            # SAFE conditional aggregation: only include columns that exist
            cohort_source = df_active.dropna(subset=["_tenure_bucket"])
            agg_dict = {}
            if revenue_col and revenue_col in cohort_source.columns:
                agg_dict["avg_sales"] = (revenue_col, lambda s: pd.to_numeric(s, errors="coerce").fillna(0).mean())
            if products_col and products_col in cohort_source.columns:
                agg_dict["avg_products"] = (products_col, lambda s: pd.to_numeric(s, errors="coerce").fillna(0).mean())

            if not agg_dict:
                st.info("Not enough columns (revenue/products) to compute cohort metrics for the selected filters.")
                cohort_grp = pd.DataFrame(columns=["_tenure_bucket"])
            else:
                cohort_grp = cohort_source.groupby(["_tenure_bucket"]).agg(**agg_dict).reset_index()

            if cohort_grp.empty:
                st.info("Not enough data to compute cohort metrics for the selected filters.")
            else:
                # Melt for grouped bar chart
                plot_df = cohort_grp.melt(id_vars=["_tenure_bucket"], value_vars=[c for c in ["avg_sales","avg_products"] if c in cohort_grp.columns], var_name="metric", value_name="value")
                plot_df["metric_label"] = plot_df["metric"].map({"avg_sales": "Avg Sales", "avg_products": "Avg Products"})

                colors = {"Avg Sales": "#0ea5a4", "Avg Products": "#3b82f6"}
                fig_cohort = px.bar(
                    plot_df,
                    x="_tenure_bucket",
                    y="value",
                    color="metric_label",
                    barmode="group",
                    color_discrete_map=colors,
                    labels={"_tenure_bucket": "Tenure Bucket", "value": "Average"},
                    template="plotly_white",
                )
                fig_cohort.update_traces(hovertemplate="%{x} — %{fullData.name}: %{y:.2f}<extra></extra>")
                fig_cohort.update_layout(height=420, margin=dict(l=40, r=20, t=30, b=80))
                st.plotly_chart(fig_cohort, use_container_width=True)
        except Exception as exc:
            st.error(f"Error computing cohort analysis: {exc}")
    else:
        st.info("Tenure column not found; cohort analysis requires `tenure_days` or equivalent.")

    st.markdown("---")

    # SECTION 5: Engagement Score Analysis
    st.subheader("Engagement Score Analysis")

    st.info(
        "What:\n"
        "- Distribution of an aggregated engagement score overall or broken down by CLV tier (mean, median, 75th, 90th percentiles).\n\n"
        "\n"
        "- How does engagement vary across CLV tiers and which tiers show potential for upsell or churn?\n\n"
        "Insight:\n"
        "- Higher CLV tiers usually show higher engagement; lower tiers with relatively strong engagement are good targets for expansion."
    )

    # Compute engagement score if ingredients exist (products, tenure, sales)
    score_components = []
    temp = df_active.copy()
    if products_col and products_col in temp.columns:
        temp["_prod"] = pd.to_numeric(temp[products_col], errors="coerce").fillna(0)
        score_components.append("_prod")
    if tenure_col and tenure_col in temp.columns:
        temp["_tenure"] = pd.to_numeric(temp[tenure_col], errors="coerce").fillna(0)
        score_components.append("_tenure")
    if revenue_col and revenue_col in temp.columns:
        temp["_sales"] = pd.to_numeric(temp[revenue_col], errors="coerce").fillna(0)
        score_components.append("_sales")

    if not score_components:
        st.info("Not enough columns to compute engagement score (need products, tenure, or sales).")
    else:
        # Min-max normalize each component, avoid division by zero
        for c in score_components:
            mn = temp[c].min()
            mx = temp[c].max()
            if mx - mn > 0:
                temp[c + "_norm"] = (temp[c] - mn) / (mx - mn)
            else:
                temp[c + "_norm"] = 0.0

        norm_cols = [c + "_norm" for c in score_components]
        # engagement score = mean of normalized components
        temp["engagement_score"] = temp[norm_cols].mean(axis=1)

        # Interpretation guide
        st.info("0–0.33 = Low engagement | 0.34–0.66 = Medium engagement | 0.67–1.0 = High engagement\n\nHigher CLV tiers typically show higher engagement scores across all metrics.")

        # Ensure engagement_score exists (compute with formula if needed)
        # Formula: (products * 0.3) + (tenure_days/365 * 0.3) + (revenue/10000 * 0.4)
        if "engagement_score" not in temp.columns:
            # compute components safely
            prod = pd.to_numeric(temp[products_col], errors="coerce").fillna(0) if products_col and products_col in temp.columns else pd.Series(0, index=temp.index)
            ten = pd.to_numeric(temp[tenure_col], errors="coerce").fillna(0) if tenure_col and tenure_col in temp.columns else pd.Series(0, index=temp.index)
            rev = pd.to_numeric(temp[revenue_col], errors="coerce").fillna(0) if revenue_col and revenue_col in temp.columns else pd.Series(0, index=temp.index)

            temp["engagement_score"] = (prod * 0.3) + ((ten / 365.0) * 0.3) + ((rev / 10000.0) * 0.4)
            temp["engagement_score"] = temp["engagement_score"].clip(lower=0.0, upper=1.0).round(2)

        # Validate clv_col exists for grouping
        if not (clv_col and clv_col in temp.columns):
            st.info("CLV tier column not available; showing overall engagement distribution.")
            overall = temp["engagement_score"].dropna()
            if overall.empty:
                st.info("No engagement score data available.")
            else:
                fig_over = px.histogram(overall, nbins=40, title="Engagement Score Distribution", labels={"value": "Engagement Score"}, template="plotly_white")
                fig_over.update_layout(height=360)
                st.plotly_chart(fig_over, use_container_width=True)
        else:
            # Group by CLV tier and compute statistics
            grp = temp.dropna(subset=[clv_col, "engagement_score"]).groupby(temp[clv_col].astype(str))["engagement_score"]
            if grp.size().sum() == 0:
                st.info("No engagement score data available for CLV tiers.")
            else:
                engagement_stats = grp.agg(["mean", "median", lambda x: x.quantile(0.75), lambda x: x.quantile(0.90)])
                engagement_stats = engagement_stats.rename(columns={"<lambda_0>": "75th", "<lambda_1>": "90th"}, errors="ignore")
                # Ensure consistent CLV order if common tiers present
                preferred = ["Bronze", "Silver", "Gold", "Platinum"]
                tiers = [t for t in preferred if t in engagement_stats.index] + [t for t in engagement_stats.index if t not in preferred]
                engagement_stats = engagement_stats.reindex(tiers)

                # Prepare for grouped bar chart
                engagement_stats = engagement_stats.rename(columns={"mean": "Mean", "median": "Median", "75th": "75th Percentile", "90th": "90th Percentile"})
                plot_df = engagement_stats.reset_index().melt(id_vars=clv_col, var_name="Statistic", value_name="Value")

                color_map = {"Mean": "#3B82F6", "Median": "#10B981", "75th Percentile": "#F59E0B", "90th Percentile": "#EF4444"}
                fig_bar = px.bar(
                    plot_df,
                    x=clv_col,
                    y="Value",
                    color="Statistic",
                    barmode="group",
                    color_discrete_map=color_map,
                    labels={clv_col: "CLV Tier", "Value": "Engagement Score"},
                    template="plotly_white",
                    title="Engagement Score Distribution by CLV Tier",
                )
                fig_bar.update_layout(height=450, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1), yaxis=dict(range=[0, 1]), hovermode="x unified")
                st.plotly_chart(fig_bar, use_container_width=True)

                # Expandable detailed stats table
                with st.expander("View Detailed Statistics by CLV Tier"):
                    # format to 3 decimals
                    display_stats = engagement_stats.rename_axis("CLV Tier").copy()
                    display_stats = display_stats[["Mean", "Median", "75th Percentile", "90th Percentile"]]
                    display_stats = display_stats.round(3)
                    st.dataframe(display_stats, use_container_width=True)
