WITH risk_scoring AS (
    SELECT
        Class,
        Amount,
        (
            CASE WHEN V14 < -3.410 THEN 51 ELSE 0 END +
            CASE WHEN V11 > 2.606 THEN 41 ELSE 0 END +
            CASE WHEN V4 > 3.647 THEN 8 ELSE 0 END
        ) AS risk_score
    FROM `bloodlink-analytics.transaction_risk_analytics.test_split_records`
),
decision_engine AS (
    SELECT *,
        CASE
            WHEN risk_score >= 70 THEN 'DECLINE'
            WHEN risk_score >= 30 THEN 'REVIEW'
            ELSE 'APPROVE'
        END AS fraud_decision
    FROM risk_scoring
)
SELECT
    fraud_decision,
    COUNT(*) AS transaction_volume,
    SUM(Class) AS actual_fraud_caught,
    ROUND(COUNT(*) / 85443 * 100, 2) AS operational_volume_percentage
FROM decision_engine
GROUP BY fraud_decision
ORDER BY
    CASE WHEN fraud_decision = 'APPROVE' THEN 1
         WHEN fraud_decision = 'REVIEW' THEN 2
         ELSE 3 END;
