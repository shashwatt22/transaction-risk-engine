# Transaction Risk Validation & Decision Engine

### 🌐 Live Dashboard: [Click Here to View the Interactive Looker Studio Demo](https://datastudio.google.com/reporting/3ab72ebd-9384-4bd6-bceb-e298c8fb02c2)

A rule-based fraud detection pipeline built in Google BigQuery and Python, designed to flag risky credit card transactions while keeping customer friction low.

## The Problem

The dataset has 284,807 transactions, but only 492 are fraud — a 0.17% fraud rate. With imbalance this severe, a system that just guesses "not fraud" every time would already be 99.83% "accurate" while catching zero fraud. The real goal isn't accuracy — it's building a system that flags the right small slice of transactions for action without burying a fraud team in false alarms.

## How It Works

**1. Feature engineering**
Raw transaction amounts are heavily skewed by a few large outliers, so a log transformation (`log(Amount + 1)`) is applied to make the data better behaved for analysis.

**2. Feature selection**
Instead of guessing which signals matter, features were ranked using effect size (Cohen's d) — a measure of how cleanly a feature separates fraud from normal transactions, accounting for variance, not just average difference. The top 3 features: **V14, V11, V4**.

**3. Train/test split**
Data was split 70/30 before any thresholds were chosen. All rule design — feature ranking, threshold scanning, weight assignment — happened only on the 70% training split. The 30% test split was touched exactly once, at the end, to measure real performance. This avoids tuning rules on the same data used to score them.

**4. Rule weights**
Each feature got a weight based on how precise it was on its own during training, scaled so the three weights sum to 100. Stronger standalone signals get more weight.

**5. Decision engine**
Each transaction gets a risk score from 0–100 based on the three weighted rules:
- Score ≥ 70 → **DECLINE**
- Score ≥ 30 → **REVIEW**
- Score < 30 → **APPROVE**

## Results

Measured on a held-out test split never used during rule design:

- **Precision: 51.4%** — when the system flags a transaction, it's right about half the time.
- **Recall: 71.5%** — the system catches about 7 out of 10 actual fraud cases.
- **67.2% of all fraud** gets routed into the Decline tier, while only a small slice of total volume is ever auto-declined — keeping customer friction low.

## Why Rules Instead of a Machine Learning Model?

A rule-based system is transparent. If a transaction is declined, you can point to exactly which feature and threshold triggered it. That kind of explainability matters for fraud and compliance teams who need to justify automated decisions, not just trust a black box.

## Tech Stack

- **SQL / Google BigQuery** — feature engineering, downsampled exploratory analysis, and the decision engine.
- **Python (pandas, scikit-learn)** — effect-size ranking, train/test split, threshold search, and held-out validation of the BigQuery rules.

## Limitations

- The dataset's V1–V28 features are anonymized (PCA-transformed), so they can't be tied to real business meaning — this is a proof of concept for the methodology, not a production-ready system.
- Redundancy between selected features was checked using Pearson and Spearman correlation, which catches linear and monotonic relationships but not more complex dependencies.
