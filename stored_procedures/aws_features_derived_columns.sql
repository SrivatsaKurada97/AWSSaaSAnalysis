USE [AWSSaaSDB]
GO

/****** Object:  StoredProcedure [dbo].[aws_features_derived_columns]    Script Date: 12/17/2025 3:09:33 PM ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO

-- =============================================
-- Author:		<Author,,Name>
-- Create date: <Create Date,,>
-- Description:	<Description,,>
-- =============================================
CREATE PROCEDURE [dbo].[aws_features_derived_columns] 
AS
BEGIN
	-- SET NOCOUNT ON added to prevent extra result sets from
	-- interfering with SELECT statements.
	SET NOCOUNT ON;
	TRUNCATE TABLE aws_features;

	WITH sales_percentiles AS(
		SELECT DISTINCT
			PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY sales) OVER() AS p75,
		    PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY sales) OVER() AS p50,
	        PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY sales) OVER() AS p25
		FROM aws_events
	)
	--Inserting aggregated feature data into the table.
	INSERT INTO aws_features(
	featurename,
	feature_category,
	required_plan,
	base_price,
	adoption_rate_pct,
	unique_users,
	total_usage_count,
	total_revenue,
	total_profit,
	profit_margin_pct,
	[avg_discount_pct],
	[usage_frequency],
	[avg_session_duration],
	[first_used_date],
	[last_used_date]
	)
	SELECT
		 product as featurename,
    -- Category based on revenue quartiles
		 CASE
			WHEN AVG(ae.sales) >= (SELECT p75 FROM sales_percentiles) THEN 'Premium'
			WHEN AVG(ae.sales) >= (SELECT p50 FROM sales_percentiles) THEN 'Advanced'
			WHEN AVG(ae.sales) >= (SELECT p25 FROM sales_percentiles) THEN 'Standard'
			ELSE 'Core'
		END AS feature_category,
	-- Required plan based on sales
		CASE 
			WHEN AVG(ae.sales) >= 1000 THEN 'Enterprise'
			WHEN AVG(ae.sales) >= 500 THEN 'Professional'
			WHEN AVG(ae.sales) >= 100 THEN 'Starter'
			ELSE 'Free'
		END AS required_plan,
		-- Base Price
		AVG(ae.sales) AS base_price,
		-- Adoption rate (% of total users who use this feature)
		CAST(COUNT(DISTINCT customerID) * 100 / (SELECT COUNT(*) FROM aws_users) AS DECIMAL(9,2)) AS adoption_rate_pct,
		-- Unique users
		COUNT(DISTINCT customerID) AS unique_users,
		-- Total usage count
		COUNT(*) AS total_usage_count,
		-- Total Revenue
		sum(ae.sales) AS total_revenue,
		-- Total Profit
		sum(profit) AS total_profit,
		-- Profit margin Percentage
		CASE 
			WHEN SUM(sales) > 0 THEN CAST(SUM(profit) * 100 / SUM(sales) AS DECIMAL(8,2)) 
			ELSE 0
		END AS profit_margin_pct,
		-- Average Discount Percentage
		CAST(AVG(discount) * 100 AS DECIMAL(8,2)) AS avg_discount_pct,
		-- Engagement Metrics
		CAST(COUNT(*) / COUNT(DISTINCT customerID) AS DECIMAL(8,2)) AS usage_frequency,
		AVG(session_duration_minutes) AS [avg_session_duration],
		-- Temporal
		MIN(orderdate) AS first_used_date,
		MAX(orderdate) AS last_used_date
	
	FROM aws_events ae
	CROSS JOIN sales_percentiles
	GROUP BY ae.product;

	-- Updating feature category based on feature name for better accuracy
	UPDATE aws_features
		SET feature_category = CASE
								   WHEN featurename LIKE '%Suite%' OR featurename LIKE '%Marketing%' THEN 'Premium'
								   WHEN featurename LIKE '%Analytics%' OR featurename LIKE '%Business%' THEN 'Advanced'
								   WHEN featurename LIKE '%Contact%' OR featurename LIKE '%CRM%' THEN 'Standard'
								   WHEN featurename LIKE '%Storage%' OR featurename LIKE '%Basics%' THEN 'Core'
								   ELSE feature_category
								END; 
								

END
GO

