"""
Fall Risk Prediction + LIME explanation
=======================================
Model: Logistic Regression (team's final model)
- predict_fall_risk(features)   -> 'LOW' / 'MEDIUM' / 'HIGH'
- explain_patient(features)     -> LIME explanation (why + which way)
- get_top3_features()           -> Top-3 risk factors (by LIME)
"""
import os
import json
import numpy as np
import joblib
import lime
import lime.lime_tabular

_DIR = os.path.dirname(os.path.abspath(__file__))
LABELS = ["LOW", "MEDIUM", "HIGH"]
REQUIRED = ["age", "night_bed_exits", "night_activity_duration_min", "past_falls", "mobility_score", "high_risk_medication", "cognitive_impairment", "polypharmacy_count", "orthostatic_hypotension", "tug_seconds"]
TOP_3_FEATURES = [
  {
    "feature": "high_risk_medication",
    "meaning": "Uses high-risk medication (0/1)",
    "lime_weight": 0.2256
  },
  {
    "feature": "cognitive_impairment",
    "meaning": "Cognitive impairment level (0-2)",
    "lime_weight": 0.177
  },
  {
    "feature": "past_falls",
    "meaning": "Number of past falls",
    "lime_weight": 0.1731
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


def predict_fall_risk(features: dict) -> str:
    """features: dict with keys = REQUIRED -> 'LOW'/'MEDIUM'/'HIGH'"""
    X = [[features[name] for name in REQUIRED]]
    return str(_model.predict(X)[0])


def explain_patient(features: dict, max_features: int = 5) -> list:
    """LIME explanation for ONE patient.
    Returns: list of [condition, weight, direction]
    weight > 0 -> pushes toward predicted class
    weight < 0 -> pulls away
    """
    row = np.asarray([features[name] for name in REQUIRED])
    pred = str(_model.predict(row.reshape(1, -1))[0])
    label_idx = list(_model.classes_).index(pred)

    exp = _explainer.explain_instance(
        data_row=row, predict_fn=_model.predict_proba,
        num_features=10, labels=[label_idx])

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
    test = {"age": 92, "night_bed_exits": 2, "night_activity_duration_min": 39,
             "past_falls": 0, "mobility_score": 2, "high_risk_medication": 0,
             "cognitive_impairment": 2, "polypharmacy_count": 3,
             "orthostatic_hypotension": 0, "tug_seconds": 25.0}
    print("Prediction:", predict_fall_risk(test))
    print("Top-3 features:", [t["feature"] for t in get_top3_features()])
    print("LIME explanation:")
    for e in explain_patient(test):
        print("  ", e)
