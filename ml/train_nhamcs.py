"""Reproducible research-only baseline evaluation on CDC NHAMCS 2022 ED data."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from importlib.metadata import version

import joblib
import numpy as np
import pandas as pd
import pyreadstat
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

TARGET = "IMMEDR"
NUMERIC = ["AGE", "TEMPF", "PULSE", "RESPR", "BPSYS", "BPDIAS", "POPCT", "PAINSCALE"]
CATEGORICAL = ["RFV1", "RFV2", "RFV3", "RFV4", "RFV5"]
CLASSES = [1, 2, 3, 4, 5]
CLASS_NAMES = {1: "immediate", 2: "emergent", 3: "urgent", 4: "semi_urgent", 5: "nonurgent"}


def prepare_frame(path: Path) -> tuple[pd.DataFrame, pd.Series, pd.Series, dict]:
    frame, metadata = pyreadstat.read_sas7bdat(path)
    frame.columns = [str(column).upper() for column in frame.columns]
    needed = [TARGET, "PATWT", *NUMERIC, *CATEGORICAL]
    missing_columns = sorted(set(needed) - set(frame.columns))
    if missing_columns:
        raise ValueError(f"Required NHAMCS columns are absent: {missing_columns}")

    raw_target = pd.to_numeric(frame[TARGET], errors="coerce")
    valid = raw_target.isin(CLASSES)
    target = raw_target.loc[valid].astype(int)
    data = frame.loc[valid, [*NUMERIC, *CATEGORICAL, "PATWT"]].copy()
    weights = pd.to_numeric(data.pop("PATWT"), errors="coerce")
    weights = weights.where(weights > 0, np.nan).fillna(1.0)

    for column in NUMERIC:
        data[column] = pd.to_numeric(data[column], errors="coerce")
        data.loc[data[column] < 0, column] = np.nan
        data.loc[data[column] == 998, column] = np.nan
    for column in CATEGORICAL:
        values = pd.to_numeric(data[column], errors="coerce")
        data[column] = values.where(values >= 0).map(lambda value: str(int(value)) if pd.notna(value) else np.nan)

    missingness = {column: round(float(data[column].isna().mean()), 4) for column in [*NUMERIC, *CATEGORICAL]}
    metadata_summary = {
        "source_url": "https://ftp.cdc.gov/pub/Health_Statistics/NCHS/Dataset_Documentation/NHAMCS/sas/ed2022_sas.zip",
        "source_file": path.name,
        "rows_in_source": int(len(frame)),
        "columns_in_source": int(len(frame.columns)),
        "known_triage_rows": int(valid.sum()),
        "excluded_target_rows": int((~valid).sum()),
        "target_raw_value_counts": {str(key): int(value) for key, value in raw_target.value_counts(dropna=False).sort_index().items()},
        "target_class_names": {str(key): value for key, value in CLASS_NAMES.items()},
        "class_counts_known_target": {str(key): int(value) for key, value in target.value_counts().sort_index().items()},
        "class_percent_known_target": {str(key): round(float(value / len(target) * 100), 2) for key, value in target.value_counts().sort_index().items()},
        "feature_missing_fraction_known_target": missingness,
        "features": {"numeric": NUMERIC, "categorical": CATEGORICAL},
        "survey_weights_used": "PATWT passed to model fitting and reported weighted metrics; rows with absent/nonpositive PATWT receive weight 1 for this prototype.",
        "split": "stratified random 70/15/15 train/validation/test, random_state=42/43; final candidate models refit on train+validation; no patient-level linkage fields used.",
        "python_libraries": {name: version(name) for name in ("pandas", "scikit-learn", "pyreadstat", "joblib")},
    }
    return data, target, weights, metadata_summary


def make_preprocessor() -> ColumnTransformer:
    numeric = Pipeline([("impute", SimpleImputer(strategy="median", add_indicator=True)), ("scale", StandardScaler())])
    categorical = Pipeline([("impute", SimpleImputer(strategy="constant", fill_value="missing")), ("onehot", OneHotEncoder(handle_unknown="ignore", min_frequency=2))])
    return ColumnTransformer([("numeric", numeric, NUMERIC), ("reason_codes", categorical, CATEGORICAL)])


def metric_block(y_true: pd.Series, y_pred: np.ndarray, weights: pd.Series) -> dict:
    return {
        "unweighted_accuracy": float(accuracy_score(y_true, y_pred)),
        "unweighted_balanced_accuracy": float(balanced_accuracy_score(y_true, y_pred)),
        "unweighted_macro_f1": float(f1_score(y_true, y_pred, labels=CLASSES, average="macro", zero_division=0)),
        "survey_weighted_accuracy": float(accuracy_score(y_true, y_pred, sample_weight=weights)),
        "survey_weighted_balanced_accuracy": float(balanced_accuracy_score(y_true, y_pred, sample_weight=weights)),
        "survey_weighted_macro_f1": float(f1_score(y_true, y_pred, labels=CLASSES, average="macro", sample_weight=weights, zero_division=0)),
        "per_class": classification_report(y_true, y_pred, labels=CLASSES, target_names=[CLASS_NAMES[c] for c in CLASSES], output_dict=True, zero_division=0),
        "confusion_matrix_labels_1_to_5": confusion_matrix(y_true, y_pred, labels=CLASSES).tolist(),
        "survey_weighted_confusion_matrix_labels_1_to_5": confusion_matrix(y_true, y_pred, labels=CLASSES, sample_weight=weights).tolist(),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True, help="Path to the CDC 2022 NHAMCS ED SAS7BDAT file")
    parser.add_argument("--output", type=Path, required=True, help="Output directory for metrics and local model artifacts")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    X, y, weights, summary = prepare_frame(args.input)
    indices = np.arange(len(y))
    train_ids, held_ids = train_test_split(indices, test_size=0.30, stratify=y, random_state=42)
    validation_ids, test_ids = train_test_split(held_ids, test_size=0.50, stratify=y.iloc[held_ids], random_state=43)
    X_train, y_train, train_weights = X.iloc[train_ids], y.iloc[train_ids], weights.iloc[train_ids]
    X_validation, y_validation, validation_weights = X.iloc[validation_ids], y.iloc[validation_ids], weights.iloc[validation_ids]
    X_test, y_test, test_weights = X.iloc[test_ids], y.iloc[test_ids], weights.iloc[test_ids]

    candidates = {
        "logistic_regression": LogisticRegression(max_iter=1500, solver="newton-cg"),
        "random_forest": RandomForestClassifier(n_estimators=250, min_samples_leaf=5, max_features="sqrt", n_jobs=-1, random_state=42),
    }
    validation_scores = {}
    for name, estimator in candidates.items():
        pipeline = Pipeline([("features", make_preprocessor()), ("model", estimator)])
        pipeline.fit(X_train, y_train, model__sample_weight=train_weights)
        predictions = pipeline.predict(X_validation)
        validation_scores[name] = float(f1_score(y_validation, predictions, labels=CLASSES, average="macro", sample_weight=validation_weights, zero_division=0))

    winner = max(validation_scores, key=validation_scores.get)
    refit_X = pd.concat([X_train, X_validation])
    refit_y = pd.concat([y_train, y_validation])
    refit_weights = pd.concat([train_weights, validation_weights])
    evaluations = {}
    for name, estimator in candidates.items():
        pipeline = Pipeline([("features", make_preprocessor()), ("model", estimator)])
        pipeline.fit(refit_X, refit_y, model__sample_weight=refit_weights)
        evaluations[name] = metric_block(y_test, pipeline.predict(X_test), test_weights)
        joblib.dump(pipeline, args.output / f"{name}.joblib")

    result = {
        "status": "research_only_not_clinically_validated",
        "target": "NHAMCS IMMEDR provider-recorded triage level, original 1-5 labels; only visits with known level 1-5 are modeled.",
        "target_semantics": CLASS_NAMES,
        "selection_rule": "Highest survey-weighted macro-F1 on validation split; final test split remains held out. This is a prototype comparison, not production selection.",
        "validation_survey_weighted_macro_f1": validation_scores,
        "provisional_top_candidate": winner,
        "train_rows": int(len(train_ids)),
        "validation_rows": int(len(validation_ids)),
        "final_model_fit_rows": int(len(train_ids) + len(validation_ids)),
        "test_rows": int(len(test_ids)),
        "split_class_counts_train": {str(k): int(v) for k, v in y_train.value_counts().sort_index().items()},
        "split_class_counts_test": {str(k): int(v) for k, v in y_test.value_counts().sort_index().items()},
        "dataset": summary,
        "evaluations": evaluations,
        "limitations": [
            "Predicts provider-assigned historical triage labels, not a patient's true need, diagnosis, or outcome.",
            "NHAMCS is a complex survey of US ED visits; this stratified split is not an external or temporal validation and does not estimate deployment performance.",
            "2022 was the final NHAMCS collection year; hospital practice and this population differ from CURE users.",
            "Features are limited to patient age, initial vitals, pain score, and chief-reason codes. Visit reasons are proxy inputs and the mapping to CURE questions is imperfect.",
            "No calibration, subgroup fairness, external validation, prospective evaluation, or clinician approval was performed.",
            "Artifacts must not be loaded into the clinical app or used to route real patients.",
        ],
    }
    (args.output / "evaluation.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(args.output), "train_rows": result["train_rows"], "validation_rows": result["validation_rows"], "test_rows": result["test_rows"], "known_target_counts": summary["class_counts_known_target"], "class_percentages": summary["class_percent_known_target"], "missingness": summary["feature_missing_fraction_known_target"], "validation_weighted_macro_f1": validation_scores, "heldout_candidate_metrics": {name: {key: values[key] for key in ("unweighted_macro_f1", "survey_weighted_macro_f1", "survey_weighted_balanced_accuracy")} for name, values in evaluations.items()}, "provisional_top_candidate": winner}, indent=2))


if __name__ == "__main__":
    main()
