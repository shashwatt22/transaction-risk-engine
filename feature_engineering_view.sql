-- =========================================================================
-- STEP 1: PRODUCTION FEATURE ENGINEERING LAYER (DATA PREPARATION VIEW)
-- Implements log-scaling to flatten extreme $25k transaction outliers 
-- =========================================================================

CREATE OR REPLACE VIEW `bloodlink-analytics.transaction_risk_analytics.v_engineered_fraud_features` AS
SELECT 
  Time,
  Amount,
  Class,
  
  -- Normalize amount variance to handle heavy machine-learning scaling skew
  ROUND(LOG(Amount + 1), 4) as log_amount,
  
  -- Isolate high-value transactional outlier benchmarks
  CASE WHEN Amount > 500 THEN 1 ELSE 0 END as is_high_value_risk,
  
  -- Retain historical PCA behavioral characteristics
  V1, V2, V3, V4, V5, V6, V7, V8, V9, V10, 
  V11, V12, V13, V14, V15, V16, V17, V18, V19, V20, 
  V21, V22, V23, V24, V25, V26, V27, V28
FROM `bloodlink-analytics.transaction_risk_analytics.fraud_records`;
