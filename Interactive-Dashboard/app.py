import streamlit as st
import logging
import os

from utils.data_loader import (
    load_customer_summary,
    load_event_data,
    load_milestone_data_from_events
)

# Import tab render functions
from tabs.overview import render_overview
from tabs.users_events import render_users_events
from tabs.milestones import render_milestones      
from tabs.ai_chat import render_ai_chat            


def _inject_css() -> None:
    css = """
    <style>
    /* Modern, professional container */
    .stApp {
        background: #0E1117;
        color: #0FAFAFA;
        font-family: Inter, system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', Arial;
    }
    .sidebar .sidebar-content {
        background: #ffffff;
        padding: 1rem 1rem 2rem 1rem;
        border-radius: 8px;
        box-shadow: 0 6px 18px rgba(15,23,42,0.06);
    }
    .stButton>button {
        background-color: #0ea5a4;
        color: white;
        border: none;
        border-radius: 6px;
        padding: 0.5rem 1rem;
        font-weight: 500;
        transition: background-color 0.2s;
    }
    .stButton>button:hover {
        background-color: #0d9190;
    }
    .connection-dot {
        height: 10px; 
        width: 10px; 
        border-radius: 50%; 
        display:inline-block; 
        margin-right:8px;
    }
    /* Metric cards styling */
    [data-testid="stMetricValue"] {
        font-size: 2rem;
        font-weight: 600;
    }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)


def main():
    st.set_page_config(
        page_title="SaaS Product Adoption Analytics", 
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    _inject_css()

    # Sidebar
    with st.sidebar:
        st.markdown("## SaaS Product Adoption Analytics")
        st.markdown("Analyze user, revenue, and engagement metrics for your SaaS product.")
        st.markdown("---")

        # Refresh button
        if st.button("Refresh data", key="refresh_button"):
            st.cache_data.clear()
            st.rerun()

    # Header
    st.title("SaaS Product Adoption Analytics Dashboard")
    
    # Load data with spinner - DIFFERENT DATA FOR EACH TAB
    with st.spinner("Loading data from database..."):
        try:
            # Tab 1: Overview - needs customer summary
            df_summary = load_customer_summary()
            
            # Tab 2: Users & Events - needs event detail
            df_events = load_event_data()
            
            # Tab 3: Milestones - needs milestone data
            df_milestones = load_milestone_data_from_events()
            
            # Tab 4: AI Chat - will need access to all data
            # We'll pass df_summary for now, can expand later
            
        except Exception as e:
            st.error(f"Failed to load data: {e}")
            logging.exception("Data loading error")
            st.stop()

        st.success("✅ Data loaded successfully")

    # Check if data is empty
    if df_summary.empty:
        st.warning("⚠️ No data found in database. Please verify the tables contain data.")
        st.stop()

    # Show data info in sidebar
    with st.sidebar:
        st.markdown("---")
        st.markdown("### Dataset Info")
        st.metric("Total Customers", len(df_summary))
        st.metric("Total Events", len(df_events) if not df_events.empty else 0)
        st.metric("Total Milestones", len(df_milestones) if not df_milestones.empty else 0)
        st.caption(f"Summary columns: {len(df_summary.columns)}")

    # Create tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Overview", 
        "👥 Users & Events", 
        "🎯 Milestones", 
        "💬 AI Chat"
    ])

    # Render tabs with error handling and APPROPRIATE DATA
    try:
        with tab1:
            # Overview uses customer summary data
            render_overview(df_summary)

        with tab2:
            # Users & Events uses event-level data
            render_users_events(df_events)

        with tab3:                       
            # Milestones uses milestone data
            render_milestones(df_milestones)

        with tab4:
            # AI Chat feature 
            render_ai_chat(df_summary)

    except Exception as exc:
        st.error(f"An error occurred while rendering the dashboard: {exc}")
        logging.exception("Dashboard rendering error")
        
        # Show detailed error in expander for debugging
        with st.expander("🔍 Error Details (for debugging)"):
            st.exception(exc)


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    

    main()


