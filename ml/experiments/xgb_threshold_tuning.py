# XGB + Threshold Tuning on Validation — Kero v2 features
# cd ~/Desktop/IA/demo/IA && unset PYTHONPATH && /opt/anaconda3/bin/python xgb_threshold_tuning.py
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler
from xgboost import XGBClassifier
from sklearn.metrics import accuracy_score, recall_score, precision_score, classification_report

# ── Load + engineer (same as Kero v2) ──
df = pd.read_csv("fall_risk_patients_2000.csv")
for col in ["high_risk_medication", "orthostatic_hypotension"]:
    df[col] = df[col].map({True: 1, False: 0})

df["mobility_tug_ratio"]      = df["tug_seconds"] / (df["mobility_score"] + 1)
df["night_falls_interaction"] = df["night_bed_exits"] * df["past_falls"]
df["med_poly_interaction"]    = df["high_risk_medication"] * df["polypharmacy_count"]
df["age_mobility_risk"]       = df["age"] * (10 - df["mobility_score"])

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
HIGH_IDX = list(le.classes_).index("HIGH")

# ── 70/20/10 split ──
X_train, X_temp, y_train, y_temp = train_test_split(
    X, y, test_size=0.30, random_state=42, stratify=y)
X_val, X_test, y_val, y_test = train_test_split(
    X_temp, y_temp, test_size=0.333, random_state=42, stratify=y_temp)

print(f"Train {len(X_train)} | Val {len(X_val)} | Test {len(X_test)}")

# ── Train XGB on train ──
xgb_model = XGBClassifier(
    n_estimators=200, max_depth=6, learning_rate=0.1,
    random_state=42, eval_metric='mlogloss'
)
# encode train y with matching split
_, _, y_num_train, _ = train_test_split(
    X, y_num, test_size=0.30, random_state=42, stratify=y_num)
xgb_model.fit(X_train, y_num_train)

proba_val = xgb_model.predict_proba(X_val)   # columns = le.classes_ order
proba_test = xgb_model.predict_proba(X_test)

def predict_with_threshold(proba, thr):
    preds = []
    for row in proba:
        if row[HIGH_IDX] >= thr:
            preds.append("HIGH")
        else:
            others = [(c, row[i]) for i, c in enumerate(le.classes_) if c != "HIGH"]
            preds.append(max(others, key=lambda x: x[1])[0])
    return np.array(preds)

# ── Threshold search on VALIDATION ──
print("\n" + "=" * 60)
print("THRESHOLD SEARCH (on VALIDATION only)")
print("=" * 60)
print(f"{'thr':<6}{'acc':<10}{'HIGH recall':<14}{'precision':<12}{'score'}")
results = []
for thr in [0.50, 0.45, 0.40, 0.35, 0.30, 0.25, 0.20, 0.15]:
    p = predict_with_threshold(proba_val, thr)
    acc = accuracy_score(y_val, p)
    rec = recall_score(y_val, p, labels=["HIGH"], average=None, zero_division=0)[0]
    prec = precision_score(y_val, p, labels=["HIGH"], average=None, zero_division=0)[0]
    # target: acc >= 0.90, recall >= 0.95 → score = min(acc, 0.90)/0.90*0.5 + min(rec,0.95)/0.95*0.5
    score = min(acc/0.90, 1.0)*0.5 + min(rec/0.95, 1.0)*0.5
    results.append((thr, acc, rec, prec, score))
    print(f"{thr:<6.2f}{acc:<10.4f}{rec:<14.4f}{prec:<12.4f}{score:.4f}")

# pick best by target score
best_thr, best_acc, best_rec, best_prec, best_score = max(results, key=lambda r: r[4])
print(f"\n→ Best threshold = {best_thr:.2f} (acc={best_acc:.4f}, recall={best_rec:.4f})")

# ── Overfit check: evaluate same threshold on TEST ──
print("\n" + "=" * 60)
print(f"OVERFIT CHECK — threshold={best_thr:.2f} on TEST")
print("=" * 60)
val_acc = best_acc
val_rec = best_rec
test_pred = predict_with_threshold(proba_test, best_thr)
test_acc = accuracy_score(y_test, test_pred)
test_rec = recall_score(y_test, test_pred, labels=["HIGH"], average=None, zero_division=0)[0]

print(f"Validation: acc={val_acc:.4f}  HIGH recall={val_rec:.4f}")
print(f"Test:       acc={test_acc:.4f}  HIGH recall={test_rec:.4f}")
print(f"Gap:        acc diff={abs(val_acc-test_acc):.4f}  recall diff={abs(val_rec-test_rec):.4f}")

if abs(val_acc - test_acc) < 0.03 and abs(val_rec - test_rec) < 0.03:
    print("\n✅ NO OVERFITTING — validation and test are consistent")
else:
    print("\n⚠️ WATCH OUT — gap > 3%, possible overfitting")

print("\n" + "=" * 60)
print(f"FINAL RESULT (test, thr={best_thr:.2f})")
print("=" * 60)
print(classification_report(y_test, test_pred, target_names=le.classes_, zero_division=0))
print(f"\nTarget check: acc≥90%? {'✅' if test_acc>=0.90 else '❌ '+f'{test_acc:.1%}'} | recall≥95%? {'✅' if test_rec>=0.95 else '❌ '+f'{test_rec:.1%}'}")
