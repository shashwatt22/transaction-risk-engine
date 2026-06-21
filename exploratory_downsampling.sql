CREATE OR REPLACE TABLE `bloodlink-analytics.transaction_risk_analytics.balanced_fraud_snapshot` AS
WITH fraud_cases AS (
  SELECT * FROM `bloodlink-analytics.transaction_risk_analytics.v_engineered_fraud_features`
  WHERE Class = 1
),
normal_cases AS (
  SELECT * FROM `bloodlink-analytics.transaction_risk_analytics.v_engineered_fraud_features`
  WHERE Class = 0
  ORDER BY FARM_FINGERPRINT(CAST(Time AS STRING))
  LIMIT 492
)
SELECT * FROM fraud_cases
UNION ALL
SELECT * FROM normal_cases;
