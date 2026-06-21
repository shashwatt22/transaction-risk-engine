from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "creditcard.csv"


def rank_features_by_effect_size(df, features):
    fraud = df[df["Class"] == 1]
    normal = df[df["Class"] == 0]
    rows = []

    for col in features:
        f_vals, n_vals = fraud[col], normal[col]
        mean_gap = f_vals.mean() - n_vals.mean()
        pooled_std = np.sqrt((f_vals.var() + n_vals.var()) / 2)
        effect_size = abs(mean_gap) / pooled_std
        rows.append((col, mean_gap, pooled_std, effect_size))

    return pd.DataFrame(
        rows, columns=["Feature", "Mean_Gap", "Pooled_Std", "Effect_Size"]
    ).sort_values("Effect_Size", ascending=False).reset_index(drop=True)


def evaluate_thresholds(df, feature, direction, total_fraud, n_candidates=30):
    if direction == "below":
        q = np.linspace(0.005, 0.50, n_candidates)
    else:
        q = np.linspace(0.50, 0.995, n_candidates)

    candidates = df[feature].quantile(q).unique()
    results = []

    for t in candidates:
        flagged = df[df[feature] < t] if direction == "below" else df[df[feature] > t]
        caught = flagged["Class"].sum()
        precision = caught / len(flagged) if len(flagged) else 0
        recall = caught / total_fraud if total_fraud else 0
        results.append({"threshold": t, "precision": precision, "recall": recall})

    return pd.DataFrame(results)


def select_best_threshold(results_df, min_recall=0.5):
    eligible = results_df[results_df["recall"] >= min_recall]
    if eligible.empty:
        return results_df.sort_values("recall", ascending=False).iloc[0]
    return eligible.sort_values("precision", ascending=False).iloc[0]


def main():
    df = pd.read_csv(DATA_PATH)
    df["log_amount"] = np.log1p(df["Amount"])

    features = [f"V{i}" for i in range(1, 29)] + ["Amount", "log_amount"]

    train_df, test_df = train_test_split(
        df, test_size=0.3, stratify=df["Class"], random_state=42
    )
    train_total_fraud = train_df["Class"].sum()

    ranking = rank_features_by_effect_size(train_df, features)
    top_features = ranking.head(3)["Feature"].tolist()

    selected_rules = []
    for feat in top_features:
        direction = "below" if train_df.loc[train_df["Class"] == 1, feat].mean() < train_df.loc[train_df["Class"] == 0, feat].mean() else "above"
        results = evaluate_thresholds(train_df, feat, direction, train_total_fraud)
        best = select_best_threshold(results, min_recall=0.5)

        selected_rules.append({
            "feature": feat,
            "direction": direction,
            "threshold": best["threshold"],
            "precision": best["precision"]
        })

    precisions = np.array([r["precision"] for r in selected_rules])
    if precisions.sum() == 0:
        weights = np.full(len(selected_rules), 33)
    else:
        weights = np.round(precisions / precisions.sum() * 100).astype(int)
        weights[0] += 100 - weights.sum()

    for rule, w in zip(selected_rules, weights):
        rule["weight"] = int(w)

    test_df = test_df.copy()
    test_df["risk_score"] = 0
    for rule in selected_rules:
        mask = test_df[rule["feature"]] < rule["threshold"] if rule["direction"] == "below" else test_df[rule["feature"]] > rule["threshold"]
        test_df.loc[mask, "risk_score"] += rule["weight"]

    test_df["fraud_decision"] = np.select(
        [test_df["risk_score"] >= 70, test_df["risk_score"] >= 30],
        ["DECLINE", "REVIEW"],
        default="APPROVE"
    )

    test_total_fraud = test_df["Class"].sum()
    summary = test_df.groupby("fraud_decision").agg(
        volume=("Class", "size"), 
        fraud_caught=("Class", "sum")
    ).reindex(["APPROVE", "REVIEW", "DECLINE"]).fillna(0)

    print(summary)

    flagged = test_df[test_df["fraud_decision"].isin(["REVIEW", "DECLINE"])]
    combined_precision = flagged["Class"].sum() / len(flagged) if len(flagged) else 0
    combined_recall = flagged["Class"].sum() / test_total_fraud if test_total_fraud else 0

    print(f"\nReview+Decline Precision: {combined_precision*100:.2f}%")
    print(f"Review+Decline Recall: {combined_recall*100:.2f}%")
    print("\nSending 30% stratified test split dataset to Google BigQuery...")
    try:
        import pandas_gbq
        
        destination_table = "transaction_risk_analytics.test_split_records"
        project_id = "bloodlink-analytics"
        
        pandas_gbq.to_gbq(
            test_df,
            destination_table,
            project_id=project_id,
            if_exists="replace"
        )
        print("Upload successful! Table 'test_split_records' is live in BigQuery.")
    except Exception as e:
        print(f"Error uploading to BigQuery: {str(e)}")


if __name__ == "__main__":
    main()
