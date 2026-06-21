CREATE OR REPLACE VIEW `bloodlink-analytics.transaction_risk_analytics.v_engineered_fraud_features` AS

SELECT
    Time,
    Amount,
    Class,

    ROUND(LOG(Amount + 1), 4) AS log_amount,

    CASE
        WHEN Amount > 500 THEN 1
        ELSE 0
    END AS is_high_value_risk,

    V1, V2, V3, V4, V5, V6, V7, V8, V9, V10,
    V11, V12, V13, V14, V15, V16, V17, V18, V19, V20,
    V21, V22, V23, V24, V25, V26, V27, V28

FROM `bloodlink-analytics.transaction_risk_analytics.fraud_records`;
