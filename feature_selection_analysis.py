"""
feature_selection_analysis.py
================================
Builds and validates a rule-based, multi-tier fraud decisioning layer on the
Credit Card Fraud Detection dataset. Candidate features: 28 PCA-transformed
behavioral features (V1-V28), raw Amount, and log_amount (log1p of Amount,
matching the SQL feature engineering layer's outlier-flattening transform).

Pipeline
--------
1. Stratified train/test split. ALL feature ranking, threshold search, and
   weight derivation happens on the train split only -- the test split is
   touched exactly once, at the end, to report held-out performance. This
   avoids the classic mistake of choosing rules and thresholds on the same
   data used to report how good they are.

2. Rank candidate features by effect size (Cohen's d) on the train split.

3. For each top-ranked feature, detect automatically whether fraud sits
   above or below the normal mean (no hardcoded assumption about direction),
   then scan threshold candidates drawn from the feature's own quantiles
   (not a manually guessed list) to find the cutoff with the best precision
   at an acceptable recall floor.

4. Check pairwise correlation (Pearson AND Spearman) across ALL selected
   features, not just the top two, to catch redundant rules before they're
   combined.

5. Derive each rule's weight in the scoring engine directly from its
   standalone train-set precision, scaled to sum to 100 -- not assigned by
   hand.

6. Score and bucket the held-out TEST split with the combined multi-feature
   engine, and report tier-level volume/precision/recall. Comparing the
   combined Review+Decline precision/recall against each feature's
   standalone numbers (printed earlier) shows directly whether combining
   features adds real lift over any single rule.

Known limitation: redundancy checks (step 4) use Pearson and Spearman
correlation, which capture linear and monotonic relationships respectively.
Two features could still share fraud-relevant information through a more
complex, non-monotonic relationship that neither method would catch --
mutual information would be needed to fully rule that out, and is out of
scope here.
"""

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

# Resolves relative to this file's own location, not the current working
# directory -- so this script runs correctly whether you call it from the
# project root, from inside src/, or anywhere else.
DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "creditcard.csv"


def rank_features_by_effect_size(df, features):
    """Rank candidate features by Cohen's d between fraud and normal classes."""
    fraud_df = df[df["Class"] == 1]
    normal_df = df[df["Class"] == 0]

    rows = []
    for col in features:
        fraud_vals = fraud_df[col]
        normal_vals = normal_df[col]

        mean_gap = fraud_vals.mean() - normal_vals.mean()
        pooled_std = np.sqrt((fraud_vals.var() + normal_vals.var()) / 2)
        effect_size = abs(mean_gap) / pooled_std

        rows.append((col, round(mean_gap, 3), round(pooled_std, 3), round(effect_size, 3)))

    ranking = pd.DataFrame(rows, columns=["Feature", "Mean_Gap", "Pooled_Std", "Effect_Size"])
    return ranking.sort_values("Effect_Size", ascending=False).reset_index(drop=True)


def determine_direction(df, feature):
    """Detect whether fraud sits below or above the normal mean for this
    feature, instead of assuming every feature behaves the same way."""
    fraud_mean = df.loc[df["Class"] == 1, feature].mean()
    normal_mean = df.loc[df["Class"] == 0, feature].mean()
    return "below" if fraud_mean < normal_mean else "above"


def generate_threshold_candidates(df, feature, direction, n_candidates=30):
    """Generate threshold candidates from the feature's own quantiles rather
    than a hand-picked list. 'below' features scan the lower half of the
    distribution (0.5th-50th percentile); 'above' features scan the upper
    half (50th-99.5th percentile)."""
    if direction == "below":
        q = np.linspace(0.005, 0.50, n_candidates)
    else:
        q = np.linspace(0.50, 0.995, n_candidates)
    return df[feature].quantile(q).unique()


def evaluate_thresholds(df, feature, direction, candidates, total_fraud):
    """Compute precision/recall for every candidate cutoff."""
    results = []
    for t in candidates:
        flagged = df[df[feature] < t] if direction == "below" else df[df[feature] > t]
        caught = flagged["Class"].sum()
        precision = caught / len(flagged) if len(flagged) else 0
        recall = caught / total_fraud if total_fraud else 0
        results.append({"threshold": t, "precision": precision, "recall": recall})
    return pd.DataFrame(results)


def select_best_threshold(results_df, min_recall=0.5):
    """Pick the cutoff with the highest precision among options that still
    retain at least `min_recall` recall. Falls back to the highest-recall
    row if nothing clears the bar."""
    eligible = results_df[results_df["recall"] >= min_recall]
    if eligible.empty:
        return results_df.sort_values("recall", ascending=False).iloc[0]
    return eligible.sort_values("precision", ascending=False).iloc[0]


def check_redundancy(df, features, corr_threshold=0.5):
    """Pairwise Pearson and Spearman correlation across every selected
    feature (not just the top two), flagging any pair that looks redundant."""
    pearson = df[features].corr(method="pearson")
    spearman = df[features].corr(method="spearman")

    print("\nPairwise Pearson correlation among selected features:")
    print(pearson.round(3).to_string())
    print("\nPairwise Spearman correlation (catches monotonic relationships "
          "Pearson can miss):")
    print(spearman.round(3).to_string())

    flagged_pairs = []
    for i, f1 in enumerate(features):
        for f2 in features[i + 1:]:
            p, s = pearson.loc[f1, f2], spearman.loc[f1, f2]
            if abs(p) > corr_threshold or abs(s) > corr_threshold:
                flagged_pairs.append((f1, f2, p, s))

    if flagged_pairs:
        print(f"\nPairs exceeding |corr| > {corr_threshold} (possible redundancy):")
        for f1, f2, p, s in flagged_pairs:
            print(f"  {f1}-{f2}: pearson={p:.3f}, spearman={s:.3f}")
    else:
        print(f"\nNo pair exceeds |corr| > {corr_threshold} -- selected features "
              "appear to capture independent signal.")


def compute_data_driven_weights(selected, total_points=100):
    """Weight each selected feature's rule proportionally to its standalone
    train-set precision, scaled to sum to `total_points`. If every feature
    came back with zero precision, split the weight evenly instead of
    dividing by zero."""
    precisions = np.array([s["precision"] for s in selected], dtype=float)
    if precisions.sum() == 0:
        weights = np.full(len(selected), total_points // len(selected))
    else:
        raw = precisions / precisions.sum() * total_points
        weights = np.round(raw).astype(int)
        weights[0] += total_points - weights.sum()  # fix rounding drift
    return weights


def main():
    df = pd.read_csv(DATA_PATH)

    # log_amount mirrors the SQL feature engineering layer: log-scaling
    # flattens the heavy right-skew in raw transaction amounts.
    df["log_amount"] = np.log1p(df["Amount"])

    # Full candidate pool now matches the original project scope: all 28
    # PCA features plus Amount and log_amount, not just V1-V28.
    v_features = [f"V{i}" for i in range(1, 29)] + ["Amount", "log_amount"]

    # --- Stratified train/test split -- feature selection, threshold
    # search, and weight derivation all happen on TRAIN only -------------
    train_df, test_df = train_test_split(
        df, test_size=0.3, stratify=df["Class"], random_state=42
    )
    print(f"Train set: {len(train_df):,} rows ({train_df['Class'].sum()} fraud)")
    print(f"Test set:  {len(test_df):,} rows ({test_df['Class'].sum()} fraud)")

    # --- Rank features on train ------------------------------------------
    ranking = rank_features_by_effect_size(train_df, v_features)
    print("\nFeature ranking by effect size, train set (top 10):\n")
    print(ranking.head(10).to_string(index=False))

    top_n = 3
    selected_features = ranking.head(top_n)["Feature"].tolist()
    train_total_fraud = train_df["Class"].sum()

    selected = []
    for feat in selected_features:
        direction = determine_direction(train_df, feat)
        candidates = generate_threshold_candidates(train_df, feat, direction)
        results = evaluate_thresholds(train_df, feat, direction, candidates, train_total_fraud)
        best = select_best_threshold(results, min_recall=0.5)
        selected.append({
            "feature": feat,
            "direction": direction,
            "threshold": best["threshold"],
            "precision": best["precision"],
            "recall": best["recall"],
        })
        symbol = "<" if direction == "below" else ">"
        print(f"\n{feat} ({direction} threshold, scanned {len(candidates)} candidates): "
              f"cutoff {symbol} {best['threshold']:.3f}, "
              f"train precision={best['precision']*100:.1f}%, "
              f"train recall={best['recall']*100:.1f}%")

    # --- Redundancy check across ALL selected features ------------------
    check_redundancy(train_df, selected_features)

    # --- Derive weights from standalone precision, not human judgment ---
    weights = compute_data_driven_weights(selected)
    for s, w in zip(selected, weights):
        s["weight"] = int(w)

    print("\nData-driven rule weights (proportional to standalone train precision):")
    for s in selected:
        symbol = "<" if s["direction"] == "below" else ">"
        print(f"  {s['feature']} {symbol} {s['threshold']:.3f}: weight={s['weight']}")

    # --- Score and bucket the HELD-OUT TEST set with the combined engine -
    test_df = test_df.copy()
    test_df["risk_score"] = 0
    for s in selected:
        mask = test_df[s["feature"]] < s["threshold"] if s["direction"] == "below" \
            else test_df[s["feature"]] > s["threshold"]
        test_df.loc[mask, "risk_score"] += s["weight"]

    review_cutoff, decline_cutoff = 30, 70
    test_df["fraud_decision"] = np.select(
        [test_df["risk_score"] >= decline_cutoff, test_df["risk_score"] >= review_cutoff],
        ["DECLINE", "REVIEW"],
        default="APPROVE",
    )

    test_total_fraud = test_df["Class"].sum()
    print(f"\nHeld-out test set results ({len(test_df):,} transactions, "
          f"{test_total_fraud} fraud):")

    summary = test_df.groupby("fraud_decision").agg(
        volume=("Class", "size"), fraud_caught=("Class", "sum")
    ).reindex(["APPROVE", "REVIEW", "DECLINE"]).fillna(0)
    summary["volume_pct"] = (summary["volume"] / len(test_df) * 100).round(2)
    if test_total_fraud:
        summary["fraud_caught_pct_of_total_fraud"] = (
            summary["fraud_caught"] / test_total_fraud * 100
        ).round(1)
    else:
        summary["fraud_caught_pct_of_total_fraud"] = 0
    print(summary.to_string())

    decline = test_df[test_df["fraud_decision"] == "DECLINE"]
    decline_precision = decline["Class"].sum() / len(decline) if len(decline) else 0
    decline_recall = decline["Class"].sum() / test_total_fraud if test_total_fraud else 0
    print(f"\nDecline-tier precision: {decline_precision*100:.1f}%  "
          f"recall: {decline_recall*100:.1f}%")

    flagged = test_df[test_df["fraud_decision"].isin(["REVIEW", "DECLINE"])]
    flagged_precision = flagged["Class"].sum() / len(flagged) if len(flagged) else 0
    flagged_recall = flagged["Class"].sum() / test_total_fraud if test_total_fraud else 0
    print(f"Review+Decline combined precision: {flagged_precision*100:.1f}%  "
          f"recall: {flagged_recall*100:.1f}%")

    print("\nCombined-vs-individual check: compare the Review+Decline precision/"
          "recall above against each feature's standalone train precision/recall "
          "printed earlier. If the combined numbers beat every individual "
          "feature's standalone numbers, the multi-feature engine is adding real "
          "lift over any single rule -- if not, reconsider whether the weaker "
          "feature(s) earn their place.")


if __name__ == "__main__":
    main()