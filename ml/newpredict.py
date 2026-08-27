"""
Production 14-Feature Inference Engine
=====================================
Loads artifacts directly from KS's Phase-2 final_model output.
Applies dynamic threshold tuning for 100% HIGH risk recall.
"""
import os
import json
import numpy as np
import joblib

# Setup path boundaries to read from the 'saved' folder
_DIR = os.path.dirname(os.path.abspath(__file__))
_SAVED_DIR = os.path.join("saved")

# 1. Load the brand new Phase-2 Model Artifacts
_model = joblib.load(os.path.join(_SAVED_DIR, "final_model.pkl"))
_le = joblib.load(os.path.join(_SAVED_DIR, "label_encoder.pkl"))

with open(os.path.join(_SAVED_DIR, "features.json"), "w" if not os.path.exists(os.path.join(_SAVED_DIR, "features.json")) else "r") as f:
    # Read the strict 14 feature sequence:
    # ["sex", "age", "night_bed_exits", "night_activity_duration_min", "past_falls", 
    #  "mobility_score", "high_risk_medication", "cognitive_impairment", "polypharmacy_count", 
    #  "orthostatic_hypotension", "tug_seconds", "days_since_last_fall", "syncopal_fall", "fall_cluster_30d"]
    REQUIRED_FEATURES = json.load(f) if os.path.exists(os.path.join(_SAVED_DIR, "features.json")) else []

with open(os.path.join(_SAVED_DIR, "threshold.json"), "r") as f:
    _threshold_data = json.load(f)
    OPTIMIZED_THRESHOLD = _threshold_data["threshold"]
    HIGH_IDX = _threshold_data["high_idx"]
    LABELS = _threshold_data["classes"]

# "Safe direction" dictionary mapping for counterfactual suggestions
# -1 = decrease makes safer, +1 = increase makes safer
SAFE_DIRECTION = {
    "night_bed_exits": -1,
    "night_activity_duration_min": -1,
    "mobility_score": +1,
    "high_risk_medication": -1,
    "polypharmacy_count": -1,
    "orthostatic_hypotension": -1,
    "tug_seconds": -1,
    "days_since_last_fall": +1, # More days since a fall = safer
    "syncopal_fall": -1,
    "fall_cluster_30d": -1
}

# Unchangeable non-modifiable background flags
UNCHANGEABLE = {"sex", "age", "past_falls", "cognitive_impairment"}

def _to_tensor_row(features: dict) -> np.ndarray:
    """Encodes frontend dictionary payloads into a strict 1x14 array tensor row."""
    row = []
    for name in REQUIRED_FEATURES:
        v = features.get(name, 0)
        
        # Handle string gender parsing safely
        if name == "sex" and isinstance(v, str):
            v = 0 if v.strip().upper().startswith("F") else 1
            
        # Handle Alex's -1 fix for patients who never fell
        elif name == "days_since_last_fall":
            if v is None or str(v).strip() == "" or float(v) < 0:
                v = -1
                
        elif isinstance(v, bool):
            v = int(v)
            
        row.append(float(v))
    return np.asarray(row)

def predict_fall_risk(features: dict) -> str:
    """Predicts fall risk level using the optimized custom threshold settings."""
    row = _to_tensor_row(features).reshape(1, -1)
    probabilities = _model.predict_proba(row)[0]
    
    # Check high risk probability against the tuned json cutoff threshold
    if probabilities[HIGH_IDX] >= OPTIMIZED_THRESHOLD:
        return "HIGH"
    
    # Fallback default sorting loop for lower tiers (LOW vs MEDIUM)
    other_classes = [(c, probabilities[i]) for i, c in enumerate(LABELS) if c != "HIGH"]
    return max(other_classes, key=lambda x: x[1])[0]

def explain_patient(features: dict, max_features: int = 5) -> list:
    """Simulates localized feature reasoning profiles."""
    row = _to_tensor_row(features)
    predicted_class = predict_fall_risk(features)
    
    # Extract structural logistic regression parameters coefficients
    coefficients = _model.coef_[LABELS.index(predicted_class)]
    
    explanations = []
    for i, name in enumerate(REQUIRED_FEATURES):
        weight = coefficients[i] * row[i]
        direction = f"push HIGH" if (predicted_class == "HIGH" and weight > 0) else "pull away"
        explanations.append({
            "condition": f"{name.upper()} state baseline",
            "weight": round(float(weight), 4),
            "direction": direction
        })
        
    # Sort by absolute weight impact magnitude and return top 5 for the Vue UI
    explanations.sort(key=lambda x: abs(x["weight"]), reverse=True)
    return explanations[:max_features]

def get_minimal_change(features: dict) -> list:
    """Calculates counterfactual paths using the strict 14 feature array grid layout."""
    current_prediction = predict_fall_risk(features)
    if current_prediction != "HIGH":
        return []
        
    row = _to_tensor_row(features)
    results = []
    
    for i, feat in enumerate(REQUIRED_FEATURES):
        if feat in UNCHANGEABLE:
            continue
            
        current_val = int(round(row[i]))
        direction = SAFE_DIRECTION.get(feat, -1)
        
        # Simulate an incremental therapeutic change tweak
        trial_features = features.copy()
        target_val = current_val + direction
        
        # Bound binary states securely between 0 and 1
        if feat in ["high_risk_medication", "orthostatic_hypotension", "syncopal_fall", "fall_cluster_30d"]:
            target_val = max(0, min(1, target_val))
            
        trial_features[feat] = target_val
        new_prediction = predict_fall_risk(trial_features)
        
        if new_prediction != "HIGH":
            results.append({
                "feature": feat,
                "from": current_val,
                "to": target_val,
                "can_flip": True
            })
        else:
            results.append({
                "feature": feat,
                "from": current_val,
                "to": current_val,
                "can_flip": False
            })
            
    return results

def recommend_intervention(features: dict) -> dict:
    """Formats human-readable response payloads for the Vue template suggestions box."""
    risk = predict_fall_risk(features)
    options = get_minimal_change(features)
    return {
        "risk_level": risk,
        "all_options": options
    }
