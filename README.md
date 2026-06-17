# Transaction Risk Engine
A cloud-based credit card fraud decision engine built in Google BigQuery using SQL. Implements log-transformations, exploratory downsampling, and automated Approve/Review/Decline workflows achieving 51.39% precision and 71.54% recall.

# Transaction Risk Validation & Decision Engine

A cloud-native data engineering and risk analytics pipeline built inside **Google BigQuery** to process and segment credit card transactions under highly imbalanced real-world conditions.

## 📊 Performance & Operational Impact
* **Dataset Size:** 284,807 transactions (Severe **0.17%** baseline fraud rate).
* **System Precision:** **51.39%** (Highly efficient alert targeting).
* **System Recall:** **71.54%** (Catches nearly 3/4 of all fraud).

### Automated Operational Funnel:
* **APPROVE (99.15% of volume):** Instantly clears legitimate users to eliminate customer friction.
* **REVIEW (0.70% of volume):** Funnels borderline anomalies into low-overhead manual triage.
* **DECLINE (0.15% of volume):** Automatically blocks highest-risk transactions—**capturing 67.2% of all actual fraud** while impacting almost zero legitimate spend.

## 🛠️ Technical Implementation
1. **Data Ingestion:** Streamed compressed raw transaction volumes natively into GCP.
2. **Feature Engineering:** Built a robust SQL View utilizing log-amount scaling ($\log(\text{Amount} + 1)$) to flatten massive skew from outlier transaction sizes.
3. **Exploratory Downsampling:** Engineered a balanced 50/50 analytical snapshot table to isolate and analyze anomalous behavioral dimensions ($V14, V17$).
4. **Decision Logic:** Authored a weighted risk-scoring engine to execute real-time policy tiering.
