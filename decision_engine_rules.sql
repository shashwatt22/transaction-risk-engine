WITH risk_scoring AS (

    SELECT
        Class,
        Amount,
        (
            CASE WHEN V17 < -2.5 THEN 45 ELSE 0 END +
            CASE WHEN V14 < -3.0 THEN 35 ELSE 0 END +
            CASE WHEN log_amount > 4.5 THEN 20 ELSE 0 END
        ) AS risk_score

    FROM `bloodlink-analytics.transaction_risk_analytics.v_engineered_fraud_features`

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
    ROUND(
        COUNT(*) / 284807 * 100,
        2
    ) AS operational_volume_percentage

FROM decision_engine

GROUP BY fraud_decision

ORDER BY
    CASE
        WHEN fraud_decision = 'APPROVE' THEN 1
        WHEN fraud_decision = 'REVIEW' THEN 2
        ELSE 3
    END;
