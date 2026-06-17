-- =========================================================================
-- TRANSACTION RISK DECISION ENGINE - REVENUE & RISK OPERATIONAL TUNING
-- Target Environment: Google BigQuery
-- Implements multi-tier risk policy (Approve / Review / Decline) 
-- =========================================================================

WITH risk_scoring AS (
  SELECT
    Class,
    Amount,
    -- Calculate a weighted risk score (0 to 100) based on isolated feature anomalies
    (    
      CASE WHEN V17 < -2.5 THEN 45 ELSE 0 END +
      CASE WHEN V14 < -3.0 THEN 35 ELSE 0 END +
      CASE WHEN log_amount > 4.5 THEN 20 ELSE 0 END
    ) as risk_score
  FROM `bloodlink-analytics.transaction_risk_analytics.v_engineered_fraud_features`
),
decision_engine AS (
  SELECT
    *,
    -- Map numerical risk brackets into active cardmember treatment policies
    CASE 
      WHEN risk_score >= 70 THEN 'DECLINE'
      WHEN risk_score >= 30 AND risk_score < 70 THEN 'REVIEW'
      ELSE 'APPROVE'
    END as fraud_decision
  FROM risk_scoring
)

SELECT
  fraud_decision,
  COUNT(*) as transaction_volume,
  SUM(Class) as actual_fraud_caught,
  -- Calculate what % of transactions drop into each operational bucket
  ROUND(COUNT(*) / 284807 * 100, 2) as operational_volume_percentage
FROM decision_engine
GROUP BY fraud_decision
ORDER BY 
  CASE fraud_decision WHEN 'APPROVE' THEN 1 WHEN 'REVIEW' THEN 2 ELSE 3 END;
