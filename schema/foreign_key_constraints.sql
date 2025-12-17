-- =============================================
-- Foreign Key Constraints (Table Relationships)
-- Purpose: Enforce data integrity and show relationships
-- =============================================

USE AWSSaaSDB;
GO

-- =============================================
-- aws_events → aws_users
-- =============================================
ALTER TABLE aws_events
ADD CONSTRAINT fk_events_customer 
    FOREIGN KEY (customerID) 
    REFERENCES aws_users(customerID)
    ON DELETE CASCADE
    ON UPDATE CASCADE;
GO

PRINT '✅ Foreign key: aws_events → aws_users';
GO

-- =============================================
-- aws_milestones → aws_users
-- =============================================
ALTER TABLE aws_milestones
ADD CONSTRAINT fk_milestones_customer 
    FOREIGN KEY (customerID) 
    REFERENCES aws_users(customerID)
    ON DELETE CASCADE
    ON UPDATE CASCADE;
GO

PRINT '✅ Foreign key: aws_milestones → aws_users';
GO

-- =============================================
-- Note: aws_events → aws_features relationship
-- =============================================
-- This is a logical relationship, not enforced by FK constraint
-- Reason: product names may not perfectly match featurename
-- JOIN condition: aws_events.product = aws_features.featurename

PRINT '✅ All foreign keys created successfully';
GO