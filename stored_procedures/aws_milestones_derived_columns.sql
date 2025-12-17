USE [AWSSaaSDB]
GO

/****** Object:  StoredProcedure [dbo].[aws_milestones_derived_columns]    Script Date: 12/17/2025 3:14:37 PM ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO

-- =============================================
-- Author:		<Author,,Name>
-- Create date: <Create Date,,>
-- Description:	<Description,,>
-- =============================================
CREATE PROCEDURE [dbo].[aws_milestones_derived_columns]
AS
BEGIN
	-- SET NOCOUNT ON added to prevent extra result sets from
	-- interfering with SELECT statements.
	SET NOCOUNT ON;

	TRUNCATE TABLE [dbo].[aws_milestones]

	INSERT INTO aws_milestones(
	[customerID],
	[milestone_type],
	[milestone_name],
	[milestone_date],
	[days_since_signup],
	[description],
	[total_orders_at_milestone],
	[total_revenue_at_milestone],
	[products_used_at_milestone]
	)
	-- MILESTONE 1: Account Created
	SELECT 
		[customerID],
		'account_created' AS [milestone_type],
		'Account Created' AS [milestone_name],
		signup_date AS [milestone_date],
		0 AS [days_since_signup],
		'User signed up for ' + segment + ' account' AS [description],
		0 AS [total_orders_at_milestone],
		0 AS [total_revenue_at_milestone],
		0 AS [products_used_at_milestone]
	FROM aws_users

	UNION ALL
	-- MILESTONE 2: First Purchase (Activation)
	SELECT 
		au.[customerID],
		'first_purchase' AS [milestone_type],
		'First Purchase' AS [milestone_name],
		au.signup_date AS [milestone_date],
		0 AS [days_since_signup],
		'Made first purchase' AS [description],
		0 AS [total_orders_at_milestone],
		(SELECT MIN(sales) FROM aws_events e WHERE e.customerID = au.customerID) AS [total_revenue_at_milestone],
		1 AS [products_used_at_milestone]
	FROM aws_users au

	UNION ALL
	-- MILESTONE 3: Active User (5+ orders)
	SELECT 
		[customerID],
		'active_user' AS [milestone_type],
		'Active User' AS [milestone_name],
		signup_date AS [milestone_date],
		CAST(tenure_days * 0.4 AS INT) AS [days_since_signup], -- Estimated 40% of tenure
		'Reached 5+ orders' AS [description],
		orderID AS [total_orders_at_milestone],
		CAST(sales * 0.5 AS DECIMAL(12,2)) AS [total_revenue_at_milestone], --Estimated 50% of sales
		product_count AS [products_used_at_milestone]
	FROM aws_users
	WHERE orderID >= 5

	UNION ALL
	-- MILESTONE 4: Power User (10+ orders)
	SELECT 
		[customerID],
		'power_user' AS [milestone_type],
		'Power User' AS [milestone_name],
		signup_date AS [milestone_date],
		CAST(tenure_days * 0.7 AS INT) AS [days_since_signup], -- Estimated 70% of tenure
		'Achieved Power User status' AS [description],
		orderID AS [total_orders_at_milestone],
		CAST(sales * 0.75 AS DECIMAL(12,2)) AS [total_revenue_at_milestone], --Estimated 75% of sales
		product_count AS [products_used_at_milestone]
	FROM aws_users
	WHERE orderID >= 10

	UNION ALL
	-- MILESTONE 5: High-value Customer (Top 25% revenue)
	SELECT 
		[customerID],
		'high_value' AS [milestone_type],
		'High Value' AS [milestone_name],
		signup_date AS [milestone_date],
		CAST(tenure_days * 0.6 AS INT) AS [days_since_signup], -- Estimated 60% of tenure
		'Achieved High Value status' AS [description],
		orderID AS [total_orders_at_milestone],
		sales AS [total_revenue_at_milestone],
		product_count AS [products_used_at_milestone]
	FROM aws_users
	WHERE clv_tier = 'Platinum'

END
GO

