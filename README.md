# Transaction Risk Validation & Decision Engine

### 🌐 Live Dashboard: [Click Here to View the Interactive Looker Studio Demo](https://datastudio.google.com/reporting/3ab72ebd-9384-4bd6-bceb-e298c8fb02c2)

A cloud-native data engineering and risk analytics pipeline built inside **Google BigQuery** to process, score, and segment credit card transactions under highly imbalanced real-world conditions.

---

## 📊 Performance & Operational Impact
* **Dataset Size:** 284,807 transactions (Severe **0.17%** baseline fraud rate).
* **System Precision:** **51.39%** (Highly efficient alert targeting).
* **System Recall:** **71.54%** (Catches nearly 3/4 of all fraud).

### Automated Operational Funnel (As seen in the Live Demo):
* **APPROVE (99.15% of volume):** Instantly clears 282,373 legitimate users to completely eliminate customer friction.
* **REVIEW (0.70% of volume):** Funnels 2,005 borderline anomalies into low-overhead manual triage.
* **DECLINE (0.15% of volume):** Automatically blocks the highest-risk 428 transactions—**capturing 67.2% of all actual fraud (331/492 cases)** while impacting almost zero legitimate spend.

---

## 🛠️ Technical Workspace Architecture
The repository is structured to mirror a production engineering environment across three progressive layers:

1. **`feature_engineering_view.sql` (Data Preparation):** Streams raw transaction volumes natively into GCP and utilizes log-amount transformations ($\log(\text{Amount} + 1)$) to flatten extreme variance from major outlier currency sizes.
2. **`exploratory_downsampling.sql` (Analytical Drilldown):** Downsamples the massive majority class to create a balanced 50/50 snapshot table, allowing rapid distribution analysis of hidden behavioral feature dimensions ($V14, V17$).
3. **`decision_engine_rules.sql` (Deployment & Rules Engine):** Authors a weighted risk-scoring engine ($0\text{--}100$) directly inside BigQuery to partition transaction volume into active operational treatment policies.
