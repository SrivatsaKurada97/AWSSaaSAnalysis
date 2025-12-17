-- =============================================
-- Index Definitions
-- Purpose: Optimize query performance
-- =============================================

USE AWSSaaSDB;
GO

-- =============================================
-- INDEXES ON aws_events (Fact Table)
-- =============================================

-- Most common: Filter by customer
CREATE INDEX idx_events_customer 
    ON aws_events(customerID);
GO

-- Time-series analysis
CREATE INDEX idx_events_date 
    ON aws_events(orderdate);
GO

-- Product analysis
CREATE INDEX idx_events_product 
    ON aws_events(product);
GO

-- Customer journey analysis (composite)
CREATE INDEX idx_events_customer_sequence 
    ON aws_events(customerID, event_sequence);
GO

PRINT '✅ Indexes created on aws_events';
GO

-- =============================================
-- INDEXES ON aws_users (Dimension Table)
-- =============================================

-- Segmentation queries
CREATE INDEX idx_users_segment 
    ON aws_users(segment);
GO

CREATE INDEX idx_users_engagement 
    ON aws_users(engagement_level);
GO

CREATE INDEX idx_users_clv 
    ON aws_users(clv_tier);
GO

-- Cohort analysis
CREATE INDEX idx_users_cohort 
    ON aws_users(signup_cohort);
GO

PRINT '✅ Indexes created on aws_users';
GO

-- =============================================
-- INDEXES ON aws_milestones (Fact Table)
-- =============================================

-- Filter by customer
CREATE INDEX idx_milestones_customer 
    ON aws_milestones(customerID);
GO

-- Filter by milestone type
CREATE INDEX idx_milestones_type 
    ON aws_milestones(milestone_type);
GO

-- Time-based analysis
CREATE INDEX idx_milestones_date 
    ON aws_milestones(milestone_date);
GO

PRINT '✅ Indexes created on aws_milestones';
GO

-- =============================================
-- INDEXES ON aws_features (Dimension Table)
-- =============================================

-- Category analysis
CREATE INDEX idx_features_category 
    ON aws_features(feature_category);
GO

-- Adoption analysis
CREATE INDEX idx_features_adoption 
    ON aws_features(adoption_rate_pct);
GO

PRINT '✅ Indexes created on aws_features';
GO

PRINT '✅ All indexes created successfully';
GO
