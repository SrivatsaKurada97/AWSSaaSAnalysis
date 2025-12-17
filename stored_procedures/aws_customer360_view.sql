USE [AWSSaaSDB]
GO

/****** Object:  StoredProcedure [dbo].[aws_customer360_view]    Script Date: 12/17/2025 3:07:38 PM ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO



-- =============================================
-- Author:		<Author,,Name>
-- Create date: <Create Date,,>
-- Description:	<Description,,>
-- =============================================
CREATE PROCEDURE [dbo].[aws_customer360_view] 
AS
BEGIN
	-- SET NOCOUNT ON added to prevent extra result sets from
	-- interfering with SELECT statements.
	SET NOCOUNT ON;

	-- =============================================
-- BUSINESS PURPOSE: Customer 360° Profile Builder
-- =============================================
-- This procedure transforms raw transaction data into actionable customer intelligence.
-- It answers the question: "Who are our customers and how engaged are they?"
--
-- WHAT IT CREATES:
-- 1. Customer Timeline: When did they join? How long have they been with us?
-- 2. Engagement Scoring: Are they New, Active, High-Value, Strategic, or At Risk?
-- 3. Lifetime Value Tiers: Platinum, Gold, Silver, or Bronze based on spending
-- 4. Product Adoption: How many different products does each customer use?
--
-- WHY IT MATTERS:
-- - Sales: Identify high-value customers worth extra attention
-- - Customer Success: Flag at-risk customers before they churn
-- - Marketing: Target campaigns based on engagement level
-- - Finance: Forecast revenue by analyzing customer spending tiers
--
-- BUSINESS RULES:
-- - "At Risk" = No purchase in 365+ days (potential churn)
-- - "Strategic (VIP)" = Enterprise/Strategic segment with positive profit
-- - "High Value (Core)" = Top 25% spenders OR using 3+ products
-- - "Retained (Active)" = Made purchase within last year, 2+ orders
-- - "New" = Only made 1 order so far
--
-- - Platinum Tier = Top 10% of spenders (highest value)
-- - Gold Tier = 40-90th percentile
-- - Silver Tier = 10-40th percentile
-- - Bronze Tier = Bottom 10% of spenders
-- =============================================
	
	PRINT '========================================'
	PRINT 'Creating Derived Columns for aws_users'
	PRINT '========================================'

	-- Checking if columns exist if not add them
	IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('aws_users') AND name = 'signup_date')
		ALTER TABLE aws_users ADD signup_date DATE;

	IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('aws_users') AND name = 'signup_month')
		ALTER TABLE aws_users ADD signup_month NVARCHAR(7);

	IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('aws_users') AND name = 'signup_cohort')
		ALTER TABLE aws_users ADD signup_cohort NVARCHAR(7);

	IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('aws_users') AND name = 'tenure_days')
		ALTER TABLE aws_users ADD tenure_days INT;

	IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('aws_users') AND name = 'engagement_level')
		ALTER TABLE aws_users ADD engagement_level NVARCHAR(50);

	IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('aws_users') AND name = 'clv_tier')
		ALTER TABLE aws_users ADD clv_tier NVARCHAR(20);

	IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('aws_users') AND name = 'product_count')
		ALTER TABLE aws_users ADD product_count INT;

	PRINT 'Columns added'

	-- Populating derived columns
	PRINT 'Calculating derived columns'

	DECLARE @Referencedate DATE;

	--signup date = orderdate (first order date)
	UPDATE aws_users
	SET signup_date = orderdate;

	-- signup month and signup cohort
	UPDATE aws_users
	SET signup_month = FORMAT(signup_date, 'MM'),
		signup_cohort = FORMAT(signup_date,'yyyy-MM');

	-- tenure days (days from signup to latest date)
	UPDATE aws_users
	SET tenure_days = DATEDIFF(day, signup_date, @Referencedate);

	--  Product count (unique number of products)
	UPDATE u
	SET product_count = (
						SELECT COUNT(DISTINCT e.product) 
						FROM aws_events e WHERE 
						u.[customerID] = e.customerID
						) FROM aws_users u

	-- engagement level and clv tier
	;WITH params AS(
		SELECT MAX(orderdate) AS maxdate FROM aws_users
	),
	customer_metrics AS(
		SELECT 
			[customerID],
			MAX(customer) as customername,
			MAX(segment) as segment,

			COUNT(DISTINCT orderID) as total_orders,
			COUNT(DISTINCT product) as unique_products,

			SUM(sales) as lifetime_sales,
			PERCENT_RANK() OVER (ORDER BY sum(sales)) as sales_percentile, --To determine high value engagement level
			SUM(profit) as lifetime_profit,
			NTILE(10) OVER (ORDER BY sum(sales) ASC) as spend_per_customer,

			MAX(orderdate) as last_purchased_date

		FROM aws_users
		GROUP BY customerID
	)
	,labeled_data AS(
	SELECT 
		metrics.customerID,
		metrics.customername,
		metrics.segment,
		metrics.lifetime_sales,
		metrics.last_purchased_date,
		DATEDIFF(day, metrics.last_purchased_date, p.maxdate) AS days_inactive,
		CASE
			WHEN DATEDIFF(day, metrics.last_purchased_date, p.maxdate) > 365 THEN 'At Risk'
			WHEN metrics.segment IN ('Strategic','Enterprise') AND metrics.lifetime_profit > 0 THEN 'Strategic (VIP)'
			WHEN metrics.sales_percentile >= 0.75 OR metrics.unique_products > 2 THEN 'High Value (Core)'
			WHEN DATEDIFF(day, metrics.last_purchased_date, p.maxdate) <= 365 AND metrics.total_orders > 1 THEN 'Retained (Active)'
			WHEN metrics.total_orders = 1 THEN 'New'
		END AS engagement_level,
		CASE 
			WHEN metrics.spend_per_customer >= 9 THEN 'Platinum'
			WHEN metrics.spend_per_customer BETWEEN 4 AND 8 THEN 'Gold'
			WHEN metrics.spend_per_customer BETWEEN 1 AND 3 THEN 'Silver'
			ELSE 'Bronze'
		END AS clv_tier
	FROM customer_metrics metrics 
	CROSS JOIN params p 
	)

	UPDATE aws_users 
	SET engagement_level = labeled_data.engagement_level,
		clv_tier = labeled_data.clv_tier
	FROM aws_users
	JOIN labeled_data 
	ON aws_users.customerID = labeled_data.customerID;
	
	PRINT '========================================'
	PRINT 'Created Derived Columns for aws_users'
	PRINT '========================================'


END
GO

