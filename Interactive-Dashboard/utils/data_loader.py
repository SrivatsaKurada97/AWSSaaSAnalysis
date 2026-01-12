"""Data loading utilities for AWS SaaS analytics from SQL Server.

Provides cached functions to load data from 4 tables:
- aws_users: Customer master data
- aws_events: Transaction/event detail
- aws_features: Product/feature analytics
- aws_milestones: Customer milestone achievements

Functions are decorated with `@st.cache_data` when Streamlit is available.
"""

from __future__ import annotations

import logging
from typing import Optional, List
import os

import pandas as pd

from utils.database import get_connection

try:
    import streamlit as st
    cache_data = st.cache_data
except Exception:
    # Fallback: no-op decorator when streamlit isn't available
    def cache_data(func):
        return func

logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logger.addHandler(handler)
logger.setLevel(os.getenv("LOG_LEVEL", "INFO"))


def _safe_query(query: str, conn) -> pd.DataFrame:
    """Execute SQL query and return DataFrame, with error handling."""
    try:
        df = pd.read_sql_query(query, conn)
        return df
    except Exception as e:
        logger.exception(f"SQL query failed: {query[:100]}...")
        return pd.DataFrame()


# ============================================================================
# TABLE-SPECIFIC LOADING FUNCTIONS
# ============================================================================

@cache_data
def load_users_table() -> pd.DataFrame:
    """Load the aws_users table (customer master data).
    
    Returns:
        DataFrame with customer-level data including demographics, 
        segment, CLV tier, engagement level, tenure, etc.
    """
    try:
        conn = get_connection()
        query = "SELECT * FROM aws_users;"
        df = _safe_query(query, conn)
        conn.close()
        logger.info(f"Loaded {len(df)} rows from aws_users")
        return df
    except Exception as e:
        logger.exception("Failed to load aws_users table")
        return pd.DataFrame()


@cache_data
def load_events_table() -> pd.DataFrame:
    """Load the aws_events table (transaction/event detail).
    
    Returns:
        DataFrame with event-level data including orders, products,
        timestamps, device types, revenue categories, etc.
    """
    try:
        conn = get_connection()
        query = "SELECT * FROM aws_events;"
        df = _safe_query(query, conn)
        conn.close()
        logger.info(f"Loaded {len(df)} rows from aws_events")
        return df
    except Exception as e:
        logger.exception("Failed to load aws_events table")
        return pd.DataFrame()


@cache_data
def load_features_table() -> pd.DataFrame:
    """Load the aws_features table (product/feature analytics).
    
    Returns:
        DataFrame with feature-level data including feature names,
        categories, pricing, adoption rates, usage metrics, etc.
    """
    try:
        conn = get_connection()
        query = "SELECT * FROM aws_features;"
        df = _safe_query(query, conn)
        conn.close()
        logger.info(f"Loaded {len(df)} rows from aws_features")
        return df
    except Exception as e:
        logger.exception("Failed to load aws_features table")
        return pd.DataFrame()


@cache_data
def load_milestones_table() -> pd.DataFrame:
    """Load the aws_milestones table (customer milestone achievements).
    
    Returns:
        DataFrame with milestone data including types, dates,
        revenue/orders at milestone, products used, etc.
    """
    try:
        conn = get_connection()
        query = "SELECT * FROM aws_milestones;"
        df = _safe_query(query, conn)
        conn.close()
        logger.info(f"Loaded {len(df)} rows from aws_milestones")
        return df
    except Exception as e:
        logger.exception("Failed to load aws_milestones table")
        return pd.DataFrame()


# ============================================================================
# COMBINED/JOINED DATA FUNCTIONS
# ============================================================================

@cache_data
def load_users_with_events() -> pd.DataFrame:
    """Load customers joined with their events.
    
    Returns:
        DataFrame with one row per event, including customer info.
        Useful for event-level analysis while keeping customer context.
    """
    try:
        conn = get_connection()
        query = """
        SELECT 
            u.customerID,
            u.customer,
            u.industry,
            u.segment,
            u.country,
            u.region,
            u.clv_tier,
            u.engagement_level,
            u.tenure_days,
            u.signup_date,
            u.product_count,
            e.rowID as event_rowID,
            e.orderID,
            e.orderdate,
            e.product,
            e.quantity,
            e.sales as event_sales,
            e.profit as event_profit,
            e.discount as event_discount,
            e.event_timestamp,
            e.event_year,
            e.event_month,
            e.event_quarter,
            e.event_day_name,
            e.event_hour,
            e.is_weekend,
            e.session_duration_minutes,
            e.device_type,
            e.revenue_category,
            e.is_first_event
        FROM aws_users u
        LEFT JOIN aws_events e ON u.customerID = e.customerID
        ORDER BY u.customerID, e.event_timestamp;
        """
        df = _safe_query(query, conn)
        conn.close()
        logger.info(f"Loaded {len(df)} rows from users+events join")
        return df
    except Exception as e:
        logger.exception("Failed to load users with events")
        return pd.DataFrame()


@cache_data
def load_users_with_milestones() -> pd.DataFrame:
    """Load customers joined with their milestones.
    
    Returns:
        DataFrame with one row per milestone, including customer info.
        Useful for milestone analysis and progression tracking.
    """
    try:
        conn = get_connection()
        query = """
        SELECT 
            u.customerID,
            u.customer,
            u.segment,
            u.clv_tier,
            u.engagement_level,
            u.tenure_days,
            u.signup_date,
            m.milestoneID,
            m.milestone_type,
            m.milestone_name,
            m.milestone_date,
            m.days_since_signup,
            m.description,
            m.total_orders_at_milestone,
            m.total_revenue_at_milestone,
            m.products_used_at_milestone
        FROM aws_users u
        LEFT JOIN aws_milestones m ON u.customerID = m.customerID
        ORDER BY u.customerID, m.milestone_date;
        """
        df = _safe_query(query, conn)
        conn.close()
        logger.info(f"Loaded {len(df)} rows from users+milestones join")
        return df
    except Exception as e:
        logger.exception("Failed to load users with milestones")
        return pd.DataFrame()


@cache_data
def load_events_with_features() -> pd.DataFrame:
    """Load events joined with feature/product details.
    
    Returns:
        DataFrame with event data enriched with feature analytics.
        Useful for product performance analysis.
    """
    try:
        conn = get_connection()
        query = """
        SELECT 
            e.rowID,
            e.customerID,
            e.orderID,
            e.orderdate,
            e.product,
            e.quantity,
            e.sales,
            e.profit,
            e.discount,
            e.event_timestamp,
            e.device_type,
            e.revenue_category,
            f.featureID,
            f.featurename,
            f.feature_category,
            f.required_plan,
            f.base_price,
            f.adoption_rate_pct,
            f.usage_frequency,
            f.profit_margin_pct
        FROM aws_events e
        LEFT JOIN aws_features f ON e.product = f.featurename
        ORDER BY e.event_timestamp;
        """
        df = _safe_query(query, conn)
        conn.close()
        logger.info(f"Loaded {len(df)} rows from events+features join")
        return df
    except Exception as e:
        logger.exception("Failed to load events with features")
        return pd.DataFrame()

# Add this function to utils/data_loader.py
# Place it after the other load functions

@st.cache_data
def load_milestone_data_from_events():
    """Calculate milestone data from event data with actual dates.
    
    This fixes the issue where milestone table has all dates set to same value.
    Instead, we calculate milestones from events to get accurate timeline data.
    
    Returns:
        DataFrame with columns:
        - customerID
        - milestone_date (actual date milestone was reached)
        - milestone_type (first_10k, first_20k, first_30k)
        - total_revenue_at_milestone
        - clv_tier, engagement_level, segment (from users table)
        - days_since_signup
    """
    conn = get_connection()
    query = """
    WITH cumulative_events AS (
        -- Calculate running total of revenue per customer
        SELECT 
            e.customerID,
            e.event_timestamp,
            e.product,
            e.sales,
            SUM(e.sales) OVER (
                PARTITION BY e.customerID 
                ORDER BY e.event_timestamp, e.rowID
                ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
            ) as cumulative_revenue,
            COUNT(e.product) OVER (
                PARTITION BY e.customerID
                ORDER BY e.event_timestamp
                ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
            ) as products_count,
            ROW_NUMBER() OVER (
                PARTITION BY e.customerID 
                ORDER BY e.event_timestamp, e.rowID
            ) as event_sequence
        FROM aws_events e
    ),
    milestone_crossings AS (
        -- Identify when each threshold is crossed
        SELECT 
            customerID,
            event_timestamp,
            cumulative_revenue,
            products_count,
            event_sequence,
            -- Flag when customer crosses each threshold for FIRST time
            CASE 
                WHEN cumulative_revenue >= 10000 
                     AND (LAG(cumulative_revenue) OVER (PARTITION BY customerID ORDER BY event_timestamp, event_sequence) < 10000 
                          OR LAG(cumulative_revenue) OVER (PARTITION BY customerID ORDER BY event_timestamp, event_sequence) IS NULL)
                THEN 'first_10k'
                WHEN cumulative_revenue >= 20000 
                     AND (LAG(cumulative_revenue) OVER (PARTITION BY customerID ORDER BY event_timestamp, event_sequence) < 20000 
                          OR LAG(cumulative_revenue) OVER (PARTITION BY customerID ORDER BY event_timestamp, event_sequence) IS NULL)
                THEN 'first_20k'
                WHEN cumulative_revenue >= 30000 
                     AND (LAG(cumulative_revenue) OVER (PARTITION BY customerID ORDER BY event_timestamp, event_sequence) < 30000 
                          OR LAG(cumulative_revenue) OVER (PARTITION BY customerID ORDER BY event_timestamp, event_sequence) IS NULL)
                THEN 'first_30k'
                ELSE NULL
            END as milestone_type
        FROM cumulative_events
    ),
    first_event_per_customer AS (
        -- Get signup milestone (first event)
        SELECT 
            customerID,
            MIN(event_timestamp) as event_timestamp,
            'account_created' as milestone_type,
            0 as cumulative_revenue,
            0 as products_count
        FROM aws_events
        GROUP BY customerID
    ),
    all_milestones AS (
        -- Combine signup milestones with threshold milestones
        SELECT 
            customerID,
            event_timestamp as milestone_date,
            milestone_type,
            cumulative_revenue as total_revenue_at_milestone,
            products_count as products_used_at_milestone
        FROM milestone_crossings
        WHERE milestone_type IS NOT NULL
        
        UNION ALL
        
        SELECT 
            customerID,
            event_timestamp as milestone_date,
            milestone_type,
            cumulative_revenue as total_revenue_at_milestone,
            products_count as products_used_at_milestone
        FROM first_event_per_customer
    )
    -- Join with user data for additional context
    SELECT 
        m.customerID,
        m.milestone_date,
        m.milestone_type,
        m.total_revenue_at_milestone,
        m.products_used_at_milestone,
        u.customer,
        u.clv_tier,
        u.engagement_level,
        u.segment,
        u.industry,
        DATEDIFF(day, 
            (SELECT MIN(event_timestamp) FROM aws_events e2 WHERE e2.customerID = m.customerID),
            m.milestone_date
        ) as days_since_signup,
        -- Add milestone sequence number
        ROW_NUMBER() OVER (PARTITION BY m.customerID ORDER BY m.milestone_date) as milestone_sequence
    FROM all_milestones m
    INNER JOIN aws_users u ON m.customerID = u.customerID
    ORDER BY m.customerID, m.milestone_date
    """
    
    try:
        df = _safe_query(query, conn)
        conn.close()
        if df is not None and not df.empty:
            # Convert date column to datetime
            df['milestone_date'] = pd.to_datetime(df['milestone_date'])
            
            # Log success
            import logging
            logging.info(f"✅ Loaded {len(df)} milestone records calculated from events")
            logging.info(f"   Unique customers: {df['customerID'].nunique()}")
            logging.info(f"   Date range: {df['milestone_date'].min()} to {df['milestone_date'].max()}")
            
        return df
    except Exception as e:
        import logging
        logging.error(f"❌ Error loading milestone data from events: {e}")
        return pd.DataFrame()


# OPTIONAL: Keep old function but rename it
@st.cache_data
def load_milestone_data_from_table():
    """Load milestone data from aws_milestones table (original broken version).
    
    NOTE: This has issues with all dates being the same.
    Use load_milestone_data_from_events() instead.
    """
    query = """
    SELECT 
        u.*,
        m.*
    FROM aws_users u
    LEFT JOIN aws_milestones m ON u.customerID = m.customerID
    """
    try:
        conn = get_connection()
        df = _safe_query(query, conn)
        conn.close()
        if df is not None and not df.empty:
            # Convert date column to datetime
            df['milestone_date'] = pd.to_datetime(df['milestone_date'])
            # Log success
            import logging
            logging.info(f"✅ Loaded {len(df)} milestone records calculated from events")
            logging.info(f"   Unique customers: {df['customerID'].nunique()}")
            logging.info(f"   Date range: {df['milestone_date'].min()} to {df['milestone_date'].max()}")
        return df
    except Exception as e:
        import logging
        logging.error(f"❌ Error loading milestone data from events: {e}")
        return pd.DataFrame()

# ============================================================================
# LEGACY/COMPATIBILITY FUNCTION
# ============================================================================

@cache_data
def load_all_data(table_name: str = "aws_users") -> pd.DataFrame:
    """Legacy function for backward compatibility.
    
    DEPRECATED: Use specific table loading functions instead.
    This function exists for backward compatibility with existing code.
    
    Args:
        table_name: Name of table to load (default: aws_users)
    
    Returns:
        DataFrame from specified table
    """
    logger.warning(f"load_all_data() is deprecated. Use load_{table_name}_table() instead.")
    
    if table_name == "aws_users":
        return load_users_table()
    elif table_name == "aws_events":
        return load_events_table()
    elif table_name == "aws_features":
        return load_features_table()
    elif table_name == "aws_milestones":
        return load_milestones_table()
    else:
        # Fallback to generic query
        try:
            conn = get_connection()
            query = f"SELECT * FROM {table_name};"
            df = _safe_query(query, conn)
            conn.close()
            return df
        except Exception:
            logger.exception(f"Failed to load table '{table_name}'")
            return pd.DataFrame()


# ============================================================================
# SUMMARY/AGGREGATION FUNCTIONS
# ============================================================================

@cache_data
def get_customer_summary() -> pd.DataFrame:
    """Get customer-level summary aggregating from all tables.
    
    Returns:
        DataFrame with one row per customer, including:
        - Basic info from aws_users
        - Event counts and totals from aws_events
        - Milestone counts from aws_milestones
    """
    try:
        conn = get_connection()
        query = """
        SELECT 
            u.customerID,
            u.customer,
            u.industry,
            u.segment,
            u.country,
            u.region,
            u.clv_tier,
            u.engagement_level,
            u.tenure_days,
            u.product_count,
            u.signup_date,
            u.sales as user_table_sales,
            u.profit as user_table_profit,
            
            -- Event aggregations
            COUNT(DISTINCT e.rowID) as total_events,
            COUNT(DISTINCT e.orderID) as total_orders,
            COUNT(DISTINCT e.product) as unique_products_purchased,
            SUM(e.sales) as total_event_sales,
            SUM(e.profit) as total_event_profit,
            AVG(e.session_duration_minutes) as avg_session_duration,
            MAX(e.event_timestamp) as last_event_date,
            MIN(e.event_timestamp) as first_event_date,
            
            -- Milestone aggregations
            COUNT(DISTINCT m.milestoneID) as total_milestones_achieved,
            MAX(m.milestone_date) as last_milestone_date
            
        FROM aws_users u
        LEFT JOIN aws_events e ON u.customerID = e.customerID
        LEFT JOIN aws_milestones m ON u.customerID = m.customerID
        GROUP BY 
            u.customerID, u.customer, u.industry, u.segment, u.country, 
            u.region, u.clv_tier, u.engagement_level, u.tenure_days,
            u.product_count, u.signup_date, u.sales, u.profit
        ORDER BY u.customerID;
        """
        df = _safe_query(query, conn)
        conn.close()
        logger.info(f"Generated customer summary for {len(df)} customers")
        return df
    except Exception as e:
        logger.exception("Failed to generate customer summary")
        return pd.DataFrame()


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    # Individual table loaders
    "load_users_table",
    "load_events_table",
    "load_features_table",
    "load_milestones_table",
    
    # Combined data loaders
    "load_users_with_events",
    "load_users_with_milestones",
    "load_events_with_features",
    
    # Summary/aggregation
    "get_customer_summary",
    
    # Legacy (deprecated)
    "load_all_data",
]