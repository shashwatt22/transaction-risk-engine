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
2. **`exploratory_downsampling.sql` (Analytical Drilldown):** Downsamples the massive majority class to create a balanced 50/50 snapshot table, allowing rapid distribution analysis of hidden behavioral feature dimensions ($V14, V17$). Uses `FARM_FINGERPRINT`-based deterministic ordering rather than `RAND()`, so the sample is reproducible across runs.
3. **`decision_engine_rules.sql` (Deployment & Rules Engine):** Authors a weighted risk-scoring engine ($0\text{--}100$) directly inside BigQuery to partition transaction volume into active operational treatment policies.

---

## 🔬 Extended Validation: Rigorous Train/Test Feature Selection (`src/feature_selection_analysis.py`)

To validate that the BigQuery rule engine's feature and threshold choices weren't arbitrary, this script rebuilds the selection process end-to-end in Python with a methodologically stricter pipeline:

* **Stratified 70/30 train/test split** — all feature ranking, threshold search, and weight derivation happen on the train split only. The test split is touched exactly once, at the end, to report held-out performance. This avoids the classic mistake of tuning rules on the same data used to score them.
* **Effect-size feature ranking** (Cohen's d) over all 28 PCA features plus `Amount`/`log_amount`, instead of raw mean-gap comparison — accounts for feature variance, not just average separation.
* **Auto-detected threshold direction** (does fraud sit above or below the normal mean for this feature) and **automatic threshold scanning** across each feature's own quantiles, rather than manually guessed cutoffs.
* **Redundancy check** using both Pearson and Spearman correlation across every selected feature, to confirm the chosen rules aren't duplicating the same signal.
* **Data-driven rule weights**, derived directly from each feature's standalone precision on the train set (scaled to sum to 100), instead of manually assigned weights.

**Held-out test results (85,443 transactions, 148 fraud cases):**

| Tier | Volume | Volume % | Fraud Caught | % of Total Fraud |
|------|--------|----------|---------------|-------------------|
| APPROVE | 84,747 | 99.19% | 27 | 18.2% |
| REVIEW | 514 | 0.60% | 29 | 19.6% |
| DECLINE | 182 | 0.21% | 92 | 62.2% |

**Decline-tier precision: 50.5%, recall: 62.2%** — closely matching the original BigQuery engine's 51.4% precision, despite being measured on a stricter, never-before-seen 30% test split. This independently validates that the original result reflects a real, generalizable pattern rather than an artifact of the specific dataset slice it was measured on.

Note: the original BigQuery numbers (67.2% fraud caught, 331/492 cases) were measured across the *full* 284,807-row dataset, while this script's numbers are measured on a held-out *test split* (148 fraud cases) that was never used during feature or threshold selection — the two are calculated on different-sized fraud samples and aren't expected to match exactly, but land in the same range, which is the relevant check.

**Known limitation:** the redundancy check (Pearson + Spearman) catches linear and monotonic relationships between features, but not more complex non-monotonic dependencies — mutual information would be needed to fully rule those out, and is left as future work.
