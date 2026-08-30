# ============================================================
# LIME Analysis - for SHAP comparison
# Handover: KWAN Kwan Ip -> teammate (who does SHAP)
# ============================================================
# IMPORTANT - to compare fairly, both tools must use:
#   1) the SAME model  (Logistic Regression, the team's final model)
#   2) the SAME patient (picked from the same test split)
#   3) the SAME class  (HIGH risk)
#
# This script outputs:
#   A) Global top-3 features (by LIME)   -> compare with SHAP global
#   B) One HIGH patient's explanation    -> compare with SHAP local
# ============================================================

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
import lime
import lime.lime_tabular

DATA = "/Users/alex0712/Downloads/IA/fall_risk_patients_2000.csv"
LABELS = ['LOW', 'MEDIUM', 'HIGH']
REQUIRED = ["age", "night_bed_exits", "night_activity_duration_min",
            "past_falls", "mobility_score", "high_risk_medication",
            "cognitive_impairment", "polypharmacy_count",
            "orthostatic_hypotension", "tug_seconds"]

# ---- 1. load + preprocess ----
df = pd.read_csv(DATA, encoding="utf-8-sig")
X = df[REQUIRED].copy()
for col in ['high_risk_medication', 'orthostatic_hypotension']:
    X[col] = X[col].map({True: 1, False: 0})
y = df["fall_risk_level"]

# ---- 2. train/test split (SAME split seed as team's 13.py) ----
X_train, X_temp, y_train, y_temp = train_test_split(
    X, y, test_size=0.30, random_state=42, stratify=y)
X_val, X_test, y_val, y_test = train_test_split(
    X_temp, y_temp, test_size=0.333, random_state=42, stratify=y_temp)

# ---- 3. train the SAME Logistic Regression ----
model = LogisticRegression(max_iter=5000, class_weight='balanced', random_state=42)
model.fit(X_train, y_train)

# ---- 4. LIME explainer ----
explainer = lime.lime_tabular.LimeTabularExplainer(
    training_data=X_train.values,
    feature_names=REQUIRED,
    class_names=LABELS,
    discretize_continuous=True,
    random_state=42,
)
HIGH_IDX = list(model.classes_).index('HIGH')   # explicit, not a hardcoded guess

# ============================================================
# A) GLOBAL: top-3 features by LIME (average |weight|, HIGH class)
#    -> compare with SHAP's global mean |SHAP value|
# ============================================================
print("=" * 64)
print("A) LIME GLOBAL top features (HIGH class)")
print("   compare with SHAP's global mean |SHAP| ranking")
print("=" * 64)

X_sample = X_test.iloc[:60].values
agg = np.zeros(len(REQUIRED))
for row in X_sample:
    exp = explainer.explain_instance(
        data_row=row, predict_fn=model.predict_proba,
        num_features=10, labels=[HIGH_IDX])
    for feat_text, weight in exp.as_list(label=HIGH_IDX):
        for j, name in enumerate(REQUIRED):
            if name in feat_text:
                agg[j] += abs(weight)
                break
rank = pd.Series(agg / len(X_sample), index=REQUIRED).sort_values(ascending=False)
print(rank.round(4).to_string())
print("\nLIME Top-3:", list(rank.index[:3]))

# ============================================================
# B) LOCAL: explain ONE HIGH patient (from the test set)
#    -> compare with SHAP's explanation of the SAME patient
# ============================================================
print("\n" + "=" * 64)
print("B) LIME LOCAL explanation (one HIGH patient)")
print("   compare with SHAP on the SAME patient")
print("=" * 64)

y_test_arr = np.asarray(y_test)
high_pos = int(np.where(y_test_arr == 'HIGH')[0][0])
patient = X_test.values[high_pos]

print("\nPatient features (SAME patient for both tools):")
print(pd.DataFrame([patient], columns=REQUIRED).T.to_string())

exp = explainer.explain_instance(
    data_row=patient, predict_fn=model.predict_proba,
    num_features=10, labels=[HIGH_IDX])
print(f"\nLIME explanation (HIGH):")
for feat_text, weight in exp.as_list(label=HIGH_IDX)[:5]:
    direction = "push HIGH" if weight > 0 else "pull away"
    print(f"  {feat_text:45s} {weight:+.4f}  {direction}")
