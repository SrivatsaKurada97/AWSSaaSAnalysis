USE [AWSSaaSDB]
GO

/****** Object:  StoredProcedure [dbo].[aws_events_derived_columns]    Script Date: 12/17/2025 3:08:09 PM ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO

-- =============================================
-- BUSINESS PURPOSE: Behavioral Analytics Engine
-- =============================================
-- This procedure transforms transaction records into behavioral insights.
-- It answers the question: "How do customers interact with our products?"
--
-- WHAT IT CREATES:
-- 1. Time Intelligence: Year, month, quarter, day of week, hour of activity
-- 2. Customer Journey: Event sequence (1st, 2nd, 3rd order), days since signup
-- 3. Engagement Depth: Session duration, device type (Desktop/Mobile/Tablet)
-- 4. Revenue Segmentation: Small (<$100), Medium, Large, Very Large, Enterprise deals
--
-- WHY IT MATTERS:
-- - Product Team: Understand usage patterns (peak hours, preferred devices)
-- - Customer Success: Track customer journey from first purchase onward
-- - Operations: Plan support staffing based on activity patterns
-- - Sales: Identify deal sizes and revenue categories
--
-- BUSINESS RULES:
-- - Session Duration: Estimated as (items purchased × 12 minutes) + variance
--   Assumes each item requires ~12 minutes to review, configure, and purchase
--   Capped at 5 min minimum (quick checkout) and 180 min maximum (realistic limit)
--
-- - Device Distribution: 70% Desktop, 25% Mobile, 5% Tablet
--   Reflects typical B2B SaaS usage where desktop is primary workspace
--
-- - Revenue Categories:
--   Small: <$100 (individual/trial purchases)
--   Medium: $100-$500 (small team deals)
--   Large: $500-$1K (department-level)
--   Very Large: $1K-$5K (multi-department)
--   Enterprise: $5K+ (company-wide deployments)
--
-- - Weekend Flag: Identifies transactions on Saturday/Sunday
--   Helps distinguish B2B (weekday) vs B2C (weekend) patterns
-- =============================================
CREATE PROCEDURE [dbo].[aws_events_derived_columns]
AS
BEGIN
	-- SET NOCOUNT ON added to prevent extra result sets from
	-- interfering with SELECT statements.
	SET NOCOUNT ON;

	PRINT '========================================'
	PRINT 'Creating Derived Columns for aws_events'
	PRINT '========================================'

	IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('aws_events') AND name = 'event_timestamp')
		ALTER TABLE aws_events ADD event_timestamp DATETIME2;
	
	IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('aws_events') AND name = 'event_year')
		ALTER TABLE aws_events ADD event_year INT;

	IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('aws_events') AND name = 'event_month')
		ALTER TABLE aws_events ADD event_month INT;

	IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('aws_events') AND name = 'event_quarter')
		ALTER TABLE aws_events ADD event_quarter INT;

	IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('aws_events') AND name = 'event_day_of_week')
		ALTER TABLE aws_events ADD event_day_of_week INT;

	IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('aws_events') AND name = 'event_day_name')
		ALTER TABLE aws_events ADD event_day_name NVARCHAR(20);

	IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('aws_events') AND name = 'event_hour')
		ALTER TABLE aws_events ADD event_hour INT;

	IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('aws_events') AND name = 'is_weekend')
		ALTER TABLE aws_events ADD is_weekend BIT;

	IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('aws_events') AND name = 'event_sequence')
		ALTER TABLE aws_events ADD event_sequence INT;

	IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('aws_events') AND name = 'days_since_signup')
		ALTER TABLE aws_events ADD days_since_signup INT;

	IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('aws_events') AND name = 'session_duration_minutes')
		ALTER TABLE aws_events ADD session_duration_minutes INT;

	IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('aws_events') AND name = 'device_type')
		ALTER TABLE aws_events ADD device_type NVARCHAR(7);

	IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('aws_events') AND name = 'revenue_tranche')
		ALTER TABLE aws_events ADD revenue_tranche NVARCHAR(100);

	IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('aws_events') AND name = 'revenue_category')
		ALTER TABLE aws_events ALTER COLUMN revenue_category NVARCHAR(100);

	IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('aws_events') AND name = 'is_first_event')
		ALTER TABLE aws_events ADD is_first_event INT;

	-- Event timestamp business hours
	UPDATE aws_events
		SET event_timestamp = DATEADD(
									  HOUR,
									  (ABS(CHECKSUM(NEWID())) & 10) + 8,
									  DATEADD(
											 MINUTE,
											 ABS(CHECKSUM(NEWID())) % 60,
											 CAST(orderdate as DATETIME2)
											 )
		);
	-- Event year, month, quarter, day of week, day name, hour and is weekend
	UPDATE aws_events
		SET event_year = YEAR(orderdate),
		    event_month = MONTH(orderdate),
			event_quarter = DATEPART(QUARTER, orderdate),
			event_day_of_week = DATEPART(WEEKDAY, orderdate) - 1, --(0=Sunday, 6 = Saturday)
			event_day_name = CASE DATEPART(WEEKDAY, orderdate)
								WHEN 1 THEN 'Sunday'
								WHEN 2 THEN 'Monday'
								WHEN 3 THEN 'Tuesday'
								WHEN 4 THEN 'Wednesday'
								WHEN 5 THEN 'Thursday'
								WHEN 6 THEN 'Friday'
								WHEN 7 THEN 'Saturday'
							END,								
			event_hour = DATEPART(HOUR, event_timestamp),
			is_weekend = CASE 
							WHEN DATEPART(WEEKDAY, orderdate) IN (1,7) THEN 1 
							ELSE 0
						 END;

	-- Behavioral Fields 
	-- Event Sequence (row number per customer, ordered by date)
	WITH ranked_events AS(
		SELECT 
			  rowID,
			  ROW_NUMBER() OVER (PARTITION BY customerID ORDER BY orderdate, rowID) AS seq
		FROM aws_events
	)
	UPDATE aws_events 
		SET aws_events.event_sequence = ranked_events.seq
		FROM aws_events
		INNER JOIN ranked_events
		ON aws_events.rowID = ranked_events.rowID

	-- is first event (flagged for first event)
	UPDATE aws_events
		SET is_first_event = CASE
								WHEN aws_events.event_sequence = 1 THEN 1
								ELSE 0
							END

	-- days since signup (days from user's sigup to event date)
	UPDATE aws_events
		SET days_since_signup = DATEDIFF(DAY, au.signup_date, ae.orderdate)
		FROM aws_events ae
		INNER JOIN aws_users  au
		ON ae.customerID = au.customerID
   
	-- Session duration
	UPDATE aws_events
		SET session_duration_minutes = CASE 
										   WHEN quantity IS NULL OR quantity = 0 THEN 15
										   ELSE CASE 
													WHEN (quantity * 12) + (ABS(CHECKSUM(NEWID())) % 20) < 5 THEN 5
													WHEN (quantity * 12) + (ABS(CHECKSUM(NEWID())) % 20) > 180 THEN 180
													ELSE (quantity * 12) + (ABS(CHECKSUM(NEWID())) % 20)
												END
										END
	
	-- device_type (realistic distribution: 70% Desktop, 25% Mobile, 5% Tablet)
	UPDATE aws_events
		SET device_type = CASE 
							  WHEN (ABS(CHECKSUM(NEWID())) % 100) < 5 THEN 'Tablet'
							  WHEN (ABS(CHECKSUM(NEWID())) % 100) < 30 THEN 'Mobile'
							  ELSE 'Desktop'
						  END
	-- revenue trache (based on sales amount)
	UPDATE aws_events
		SET revenue_tranche = CASE 
								   WHEN sales < 100 THEN '<$100'
								   WHEN sales < 500 THEN '$100 - $500'
								   WHEN sales < 1000 THEN '$500 - $1K'
								   WHEN sales < 5000 THEN '$1K - $5K'
								   ELSE '>$5k'
							  END
	-- revenue_category (based on revnue trache)
	UPDATE aws_events
		SET revenue_category = CASE
								   WHEN revenue_tranche = '<$100' THEN 'Small'
								   WHEN revenue_tranche = '$100 - $500' THEN 'Medium'
								   WHEN revenue_tranche = '$500 - $1K' THEN 'Large'
								   WHEN revenue_tranche = '$1K - $5K' THEN 'Very Large'
								   ELSE 'Enterprise'
							   END

	PRINT '========================================'
	PRINT 'Created Derived Columns for aws_events'
	PRINT '========================================'
END
GO

