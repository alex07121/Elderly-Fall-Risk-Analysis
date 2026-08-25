"""
Fall Risk Prediction + LIME explanation
=======================================
Model: Logistic Regression (trained on v2 feature data, 2026-08-20)
- predict_fall_risk(features)      -> 'LOW' / 'MEDIUM' / 'HIGH'
- explain_patient(features)        -> LIME explanation (why + which way)
- get_top3_features()              -> Top-3 risk factors (by LIME)

Input features (11): sex ('F'/'M' or 0/1) + the original 10.
"""
import os
import json
import numpy as np
import joblib
import lime
import lime.lime_tabular

_DIR = os.path.dirname(os.path.abspath(__file__))
LABELS = ["LOW", "MEDIUM", "HIGH"]
REQUIRED = ["sex", "age", "night_bed_exits", "night_activity_duration_min",
            "past_falls", "mobility_score", "high_risk_medication",
            "cognitive_impairment", "polypharmacy_count",
            "orthostatic_hypotension", "tug_seconds",
            "days_since_last_fall", "syncopal_fall", "fall_cluster_30d"]

TOP_3_FEATURES = [
  {
    "feature": "tug_seconds",
    "meaning": "TUG test time (seconds)",
    "lime_weight": 0.3637
  },
  {
    "feature": "past_falls",
    "meaning": "Number of past falls",
    "lime_weight": 0.1366
  },
  {
    "feature": "high_risk_medication",
    "meaning": "Uses high-risk medication (0/1)",
    "lime_weight": 0.1185
  }
]

_model = joblib.load(os.path.join(_DIR, "fall_risk_model.pkl"))
_train = np.load(os.path.join(_DIR, "train_data.npy"))

_explainer = lime.lime_tabular.LimeTabularExplainer(
    training_data=_train,
    feature_names=REQUIRED,
    class_names=LABELS,
    discretize_continuous=True,
    random_state=42,
)


def _to_row(features: dict) -> np.ndarray:
    """Encode a feature dict into a model-ready row.
    sex: 'F'/'M' (or 0/1); booleans: True/False (or 0/1);
    days_since_last_fall: None/'' -> -1 means 'never fell'.
    """
    row = []
    for name in REQUIRED:
        v = features[name]
        if name == "sex" and isinstance(v, str):
            v = 0 if v.strip().upper().startswith("F") else 1
        elif name == "days_since_last_fall" and (v is None or v == ""):
            v = -1
        elif isinstance(v, bool):
            v = int(v)
        row.append(float(v))
    return np.asarray(row)


def predict_fall_risk(features: dict) -> str:
    """features: dict with keys = REQUIRED -> 'LOW'/'MEDIUM'/'HIGH'"""
    X = _to_row(features).reshape(1, -1)
    return str(_model.predict(X)[0])


def explain_patient(features: dict, max_features: int = 5) -> list:
    """LIME explanation for ONE patient.
    Returns: list of {condition, weight, direction}
    weight > 0 -> pushes toward predicted class
    weight < 0 -> pulls away
    """
    row = _to_row(features)
    pred = str(_model.predict(row.reshape(1, -1))[0])
    label_idx = list(_model.classes_).index(pred)

    exp = _explainer.explain_instance(
        data_row=row, predict_fn=_model.predict_proba,
        num_features=len(REQUIRED), labels=[label_idx])

    out = []
    for feat_text, weight in exp.as_list(label=label_idx)[:max_features]:
        direction = f"push {pred}" if weight > 0 else "pull away"
        out.append({"condition": feat_text, "weight": round(weight, 4),
                     "direction": direction})
    return out


def get_top3_features() -> list:
    """Top-3 risk factors (global, by LIME) for the API."""
    return TOP_3_FEATURES


if __name__ == "__main__":
    test = {"sex": "M", "age": 85, "night_bed_exits": 2,
            "night_activity_duration_min": 31.7, "past_falls": 2,
            "mobility_score": 3, "high_risk_medication": 1,
            "cognitive_impairment": 1, "polypharmacy_count": 1,
            "orthostatic_hypotension": 0, "tug_seconds": 24.4,
            "days_since_last_fall": 60, "syncopal_fall": 0, "fall_cluster_30d": 0}
    print("=" * 62)
    print("Fall Risk Model Output (self-test)")
    print("=" * 62)
    print(f"\n[1] PREDICTION         : {predict_fall_risk(test)}")
    print(f"[2] TOP-3 RISK FACTORS : "
          f"{[t['feature'] for t in get_top3_features()]}")
    print(f"\n[3] WHY this patient is HIGH (LIME explanation):")
    for e in explain_patient(test):
        print(f"      {e}")
    print("\n" + "=" * 62)
    print("Note:  [1]-[3] explain the prediction (level, top-3 factors, LIME).")
    print("=" * 62)
