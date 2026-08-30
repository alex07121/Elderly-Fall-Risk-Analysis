# LR Tuning on Validation Set — Kero version (70/20/10)
# cd ~/Desktop/IA/demo/IA && unset PYTHONPATH && /opt/anaconda3/bin/python tune_lr_validation.py
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, recall_score, precision_score, classification_report

# ── Load + engineer (same as Kero v2) ──
df = pd.read_csv("fall_risk_patients_2000.csv")
for col in ["high_risk_medication", "orthostatic_hypotension"]:
    df[col] = df[col].map({True: 1, False: 0})

df["mobility_tug_ratio"]     = df["tug_seconds"] / (df["mobility_score"] + 1)
df["night_falls_interaction"] = df["night_bed_exits"] * df["past_falls"]
df["med_poly_interaction"]   = df["high_risk_medication"] * df["polypharmacy_count"]
df["age_mobility_risk"]      = df["age"] * (10 - df["mobility_score"])

REQUIRED = ["age","night_bed_exits","night_activity_duration_min",
            "past_falls","mobility_score","high_risk_medication",
            "cognitive_impairment","orthostatic_hypotension","tug_seconds"]
ENGINEERED = ["mobility_tug_ratio","night_falls_interaction",
              "med_poly_interaction","age_mobility_risk"]
FEATURES = REQUIRED + ENGINEERED

X = df[FEATURES]
y = df["fall_risk_level"]

le = LabelEncoder()
y_num = le.fit_transform(y)
HIGH_IDX = list(le.classes_).index("HIGH")   # index of "HIGH" in encoded labels

scaler = StandardScaler()
X_s = scaler.fit_transform(X)

# ── 70/20/10 split ──
X_train, X_temp, y_train, y_temp = train_test_split(
    X_s, y, test_size=0.30, random_state=42, stratify=y)
X_val, X_test, y_val, y_test = train_test_split(
    X_temp, y_temp, test_size=0.333, random_state=42, stratify=y_temp)

print(f"Train {len(X_train)} | Val {len(X_val)} | Test {len(X_test)}")

# ── STEP 1: Tune C on validation (accuracy + recall_macro) ──
print("\n" + "=" * 55)
print("STEP 1 — TUNE C (regularization) ON VALIDATION")
print("=" * 55)
best_c, best_c_score = None, -1
for C in [0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0]:
    m = LogisticRegression(max_iter=5000, C=C, class_weight="balanced", random_state=42)
    m.fit(X_train, y_train)
    p = m.predict(X_val)
    acc = accuracy_score(y_val, p)
    rec = recall_score(y_val, p, labels=["HIGH"], average=None, zero_division=0)[0]
    # score = 0.5*acc + 0.5*rec (balanced target: acc 90%, recall 95%)
    score = 0.5 * acc + 0.5 * rec
    print(f"C={C:<5} acc={acc:.4f}  HIGH recall={rec:.4f}  score={score:.4f}")
    if score > best_c_score:
        best_c, best_c_score = C, score
print(f"→ Best C = {best_c} (score {best_c_score:.4f})")

# ── STEP 2: Tune HIGH threshold on validation (with best C) ──
print("\n" + "=" * 55)
print("STEP 2 — TUNE HIGH THRESHOLD ON VALIDATION")
print("=" * 55)
model = LogisticRegression(max_iter=5000, C=best_c, class_weight="balanced", random_state=42)
model.fit(X_train, y_train)

proba_val = model.predict_proba(X_val)
proba_test = model.predict_proba(X_test)

def predict_with_threshold(proba, thr):
    """HIGH if P(HIGH) >= thr, else fall back to argmax of remaining."""
    preds = []
    for row in proba:
        if row[HIGH_IDX] >= thr:
            preds.append("HIGH")
        else:
            # pick best among LOW/MEDIUM
            others = [(c, row[i]) for i, c in enumerate(le.classes_) if c != "HIGH"]
            preds.append(max(others, key=lambda x: x[1])[0])
    return np.array(preds)

best_thr, best_thr_score = None, -1
for thr in [0.50, 0.45, 0.40, 0.35, 0.30, 0.25, 0.20]:
    p = predict_with_threshold(proba_val, thr)
    acc = accuracy_score(y_val, p)
    rec = recall_score(y_val, p, labels=["HIGH"], average=None, zero_division=0)[0]
    prec = precision_score(y_val, p, labels=["HIGH"], average=None, zero_division=0)[0]
    score = 0.5 * acc + 0.5 * rec
    print(f"thr={thr:<5} acc={acc:.4f}  HIGH recall={rec:.4f}  precision={prec:.4f}  score={score:.4f}")
    if score > best_thr_score:
        best_thr, best_thr_score = thr, score
print(f"→ Best threshold = {best_thr} (score {best_thr_score:.4f})")

# ── FINAL: evaluate best config on TEST ──
print("\n" + "=" * 55)
print(f"FINAL — C={best_c}, threshold={best_thr} on TEST SET")
print("=" * 55)
test_pred = predict_with_threshold(proba_test, best_thr)
print(classification_report(y_test, test_pred, target_names=le.classes_, zero_division=0))
test_acc = accuracy_score(y_test, test_pred)
test_rec = recall_score(y_test, test_pred, labels=["HIGH"], average=None, zero_division=0)[0]
print(f"\nTest accuracy: {test_acc:.4f} | HIGH recall: {test_rec:.4f}")
