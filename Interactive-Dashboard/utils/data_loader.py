import pandas as pd
import streamlit as st
from pathlib import Path

# Base path for data files
DATA_DIR = Path(__file__).parent.parent / "data"

@st.cache_data
def load_customer_summary():
    """Load customer data from CSV"""
    try:
        file_path = DATA_DIR / "aws_users.csv"
        df = pd.read_csv(file_path)
        return df
    except FileNotFoundError:
        st.error(f"❌ Data file not found: {file_path}")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"❌ Error loading data: {e}")
        return pd.DataFrame()

@st.cache_data
def load_event_data():
    """Load event data from CSV"""
    try:
        file_path = DATA_DIR / "aws_events.csv"
        df = pd.read_csv(file_path)
        # Convert timestamp column
        if 'event_timestamp' in df.columns:
            df['event_timestamp'] = pd.to_datetime(df['event_timestamp'])
        return df
    except Exception as e:
        st.error(f"❌ Error loading events: {e}")
        return pd.DataFrame()

@st.cache_data
def load_milestone_data_from_events():
    """Load milestone data from CSV"""
    try:
        file_path = DATA_DIR / "aws_milestones.csv"
        if file_path.exists():
            df = pd.read_csv(file_path)
            if 'milestone_date' in df.columns:
                df['milestone_date'] = pd.to_datetime(df['milestone_date'])
            return df
        else:
            # Calculate from events if milestones file doesn't exist
            return calculate_milestones_from_events()
    except Exception as e:
        st.error(f"❌ Error loading milestones: {e}")
        return pd.DataFrame()
