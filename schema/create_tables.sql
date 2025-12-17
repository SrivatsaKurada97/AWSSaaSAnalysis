-- =============================================
-- AWS SaaS Analytics Database Schema
-- Purpose: Star schema for customer behavioral analytics
-- Author: Srivatsa Kurada
-- =============================================

USE AWSSaaSDB;
GO

-- =============================================
-- TABLE 1: aws_users (Customer Dimension)
-- Purpose: One row per customer with aggregated metrics
-- =============================================

CREATE TABLE aws_users (
    -- Primary Key
    customerID NVARCHAR(50) NOT NULL PRIMARY KEY,
    
    -- Customer Information
    customer NVARCHAR(255),
    segment NVARCHAR(50),
    industry NVARCHAR(100),
    region NVARCHAR(10),
    
    -- Aggregated Metrics (from raw data)
    orderID INT,                    -- Total number of orders
    sales DECIMAL(12,2),            -- Lifetime revenue
    profit DECIMAL(12,2),           -- Lifetime profit
    discount DECIMAL(5,4),          -- Average discount rate
    
    -- Derived Columns (calculated by stored procedure)
    signup_date DATE,
    signup_month NVARCHAR(7),
    signup_cohort NVARCHAR(7),
    tenure_days INT,
    engagement_level NVARCHAR(50),  -- New, Active, High Value, Strategic, At Risk
    clv_tier NVARCHAR(20),          -- Platinum, Gold, Silver, Bronze
    product_count INT,              -- Number of unique products used
    
    -- Audit
    created_at DATETIME2 DEFAULT GETDATE()
);
GO

-- =============================================
-- TABLE 2: aws_events (Behavioral Fact Table)
-- Purpose: One row per transaction/event
-- =============================================

CREATE TABLE aws_events (
    -- Primary Key
    rowID INT NOT NULL PRIMARY KEY,
    
    -- Foreign Key (links to aws_users)
    customerID NVARCHAR(50) NOT NULL,
    
    -- Transaction Details
    orderID NVARCHAR(50),
    orderdate DATE,
    product NVARCHAR(255),
    quantity INT,
    sales DECIMAL(12,2),
    profit DECIMAL(12,2),
    discount DECIMAL(5,4),
    
    -- Derived Temporal Columns
    event_timestamp DATETIME2,
    event_year INT,
    event_month INT,
    event_quarter INT,
    event_day_of_week INT,          -- 0=Sunday, 6=Saturday
    event_day_name NVARCHAR(20),
    event_hour INT,
    is_weekend BIT,
    
    -- Derived Behavioral Columns
    event_sequence INT,             -- 1st, 2nd, 3rd event per customer
    is_first_event INT,
    days_since_signup INT,
    session_duration_minutes INT,
    device_type NVARCHAR(7),        -- Desktop, Mobile, Tablet
    
    -- Derived Revenue Columns
    revenue_tranche NVARCHAR(100),  -- <$100, $100-$500, etc.
    revenue_category NVARCHAR(100), -- Small, Medium, Large, Very Large, Enterprise
    
    -- Audit
    created_at DATETIME2 DEFAULT GETDATE()
);
GO

-- =============================================
-- TABLE 3: aws_features (Product Dimension)
-- Purpose: One row per product/feature
-- =============================================

CREATE TABLE aws_features (
    -- Primary Key
    feature_id INT NOT NULL PRIMARY KEY IDENTITY(1,1),
    
    -- Feature Information
    featurename NVARCHAR(255) NOT NULL UNIQUE,
    feature_category NVARCHAR(50),  -- Core, Standard, Advanced, Premium
    required_plan NVARCHAR(50),     -- Free, Starter, Professional, Enterprise
    
    -- Pricing Metrics
    base_price DECIMAL(10,2),
    avg_discount_pct DECIMAL(8,2),
    
    -- Adoption Metrics
    adoption_rate_pct DECIMAL(9,2), -- % of total customers using this
    unique_users INT,
    total_usage_count INT,
    usage_frequency DECIMAL(8,2),   -- Avg times used per customer
    
    -- Financial Metrics
    total_revenue DECIMAL(12,2),
    total_profit DECIMAL(12,2),
    profit_margin_pct DECIMAL(8,2),
    
    -- Engagement Metrics
    avg_session_duration INT,
    
    -- Temporal
    first_used_date DATE,
    last_used_date DATE,
    
    -- Audit
    created_at DATETIME2 DEFAULT GETDATE()
);
GO

-- =============================================
-- TABLE 4: aws_milestones (Lifecycle Fact Table)
-- Purpose: One row per customer milestone event
-- =============================================

CREATE TABLE aws_milestones (
    -- Primary Key
    milestone_id INT NOT NULL PRIMARY KEY IDENTITY(1,1),
    
    -- Foreign Key (links to aws_users)
    customerID NVARCHAR(50) NOT NULL,
    
    -- Milestone Information
    milestone_type NVARCHAR(50) NOT NULL,    -- account_created, first_purchase, active_user, power_user, high_value
    milestone_name NVARCHAR(255),
    milestone_date DATE NOT NULL,
    days_since_signup INT,
    description NVARCHAR(500),
    
    -- Metrics at Milestone
    total_orders_at_milestone INT,
    total_revenue_at_milestone DECIMAL(12,2),
    products_used_at_milestone INT,
    
    -- Audit
    created_at DATETIME2 DEFAULT GETDATE()
);
GO

PRINT '✅ All tables created successfully';
GO