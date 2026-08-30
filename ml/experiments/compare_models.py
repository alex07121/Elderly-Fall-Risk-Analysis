
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier
from sklearn.metrics import accuracy_score, recall_score

df = pd.read_csv("fall_risk_patients_2000.csv")

# boolean -> 0/1
for col in ["high_risk_medication", "orthostatic_hypotension"]:
    df[col] = df[col].map({True: 1, False: 0})

# 10 blueprint features
REQUIRED = ["age", "night_bed_exits", "night_activity_duration_min",
            "past_falls", "mobility_score", "high_risk_medication",
            "cognitive_impairment", "polypharmacy_count",
            "orthostatic_hypotension", "tug_seconds"]

y = df["fall_risk_level"]

print("Loaded", df.shape)

def high_recall(y_true, y_pred):
    return recall_score(y_true, y_pred, average=None, zero_division=0)[0]


# --- Alex version: 80/20 split, StandardScaler, LR C=100 ---
def run_alex():
    X = df[REQUIRED]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y)

    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s = scaler.transform(X_test)

    #LR (scaled)
    lr = LogisticRegression(C=100, max_iter=5000, random_state=42)
    lr.fit(X_train_s, y_train)
    lr_pred = lr.predict(X_test_s)

    #RF
    rf = RandomForestClassifier(n_estimators=200, random_state=42)
    rf.fit(X_train,y_train)
    rf_pred = rf.predict(X_test)

    #XGB (numeric y)
    y_num_train = y_train.map({"LOW": 0, "MEDIUM": 1, "HIGH": 2})
    xgb = XGBClassifier(n_estimators=200, learning_rate=0.1, max_depth=6, random_state=42, eval_metric='mlogloss')
    xgb.fit(X_train, y_num_train)
    xgb_pred  = pd.Series(xgb.predict(X_test)).map({0: "LOW", 1: "MEDIUM", 2: "HIGH"}).values

    return {
        "LR" :(lr_pred, y_test),
        "RF" :(rf_pred, y_test),
        "XGB" :(xgb_pred, y_test),
    }

# --- Kero version: 70/20/10 split, class_weight='balanced' ---
def run_kero():
    X = df[REQUIRED]

    # 70% train, 30% temp
    X_train, X_temp, y_train, y_temp = train_test_split(
        X, y , test_size=0.30, random_state=42, stratify=y)
    #temp -> 20% val, 10% test
    X_val, X_test, y_val, y_test = train_test_split(
        X_temp, y_temp, test_size=0.333, random_state=42, stratify=y_temp)

    #LR (balanced)
    lr = LogisticRegression(max_iter=5000, class_weight='balanced', random_state=42)
    lr.fit(X_train, y_train)
    lr_pred = lr.predict(X_val)

    #RF (balanced)
    rf = RandomForestClassifier(n_estimators=200, max_depth=6, random_state=42)
    rf.fit(X_train, y_train)
    rf_pred = rf.predict(X_val)

    #XGB (needs numeric y)
    le = LabelEncoder()
    yt = le.fit_transform(y_train)
    xgb = XGBClassifier(n_estimators=200, max_depth=6, random_state=42)
    xgb.fit(X_train, yt)
    xgb_pred = le.inverse_transform(xgb.predict(X_val))

    return{
        "LR": (lr_pred, y_val),
        "RF": (rf_pred, y_val),
        "XGB": (xgb_pred, y_val),
    }
print("=== ALEX ===")
alex = run_alex()
for n, (p, yt) in alex.items():
    print(f"{n}: acc={accuracy_score(yt,p):.2f} HIGH recall={high_recall(yt,p):.4f}")

print("=== Kero ===")
kero = run_kero()
for n, (p, yt) in kero.items():
    print(f"{n}: acc={accuracy_score(yt,p):.2f} HIGH recall={high_recall(yt,p):.4f}")

# Comprehensive Comparison
# part 1
results = {"Kero": {}, "Alex": {}}
for name, out in [("Kero", kero), ("Alex", alex)]:
    for model, (p, yt) in out.items():
        results[name][model] = {
            "acc": accuracy_score(yt, p),
            "recall": high_recall(yt, p),
        }

print ("\n" + "=" * 55)
print ("1. PER-MODEL WINNER (HIGH recall)")
print("=" *  55)
for model in ["LR", "RF", "XGB"]:
    k = results["Kero"][model]["recall"]
    a = results["Alex"][model]["recall"]
    winner = "Kero" if k > a else ("Alex" if a > k else "Tie")
    print(f" {model}: Kero={k:.4f} vs Alex={a:.4f} -> {winner}")

# part 2: Overall best model (HIGH recall)
print ("\n" + "=" * 55)
print("2. OVERALL BEST MODEL (HIGH recall)")
print("=" * 55)

# put the KERO + ALEX all model's recall data
all_models = []
for ver in ["Kero", "Alex"]:
    for model in ["LR", "RF", "XGB"]:
        all_models.append((f"{ver}-{model}", results[ver][model]["recall"]))

# find the highest
best_model = max(all_models, key=lambda x:x[1])
print(f" Best: {best_model[0]} (HIGH rcall = {best_model[1]:.4f})")

# part 3: overall best model (Accuracy)
print("\n" + "=" * 55)
print("3. OVERALL BEST MODEL (Accuracy")
print ("=" * 55)

# collect Kero + Alex all model accuracy
all_acc = []
for ver in ["Kero", "Alex"]:
    for model in ["LR", "RF", "XGB"]:
        all_acc.append((f"{ver}-{model}", results[ver][model]["acc"]))
best_acc = max(all_acc, key=lambda x:x[1])
print(f" Best accuracy: {best_acc[0]} (acc = {best_acc[1]:.2%})")

# part 4: average across 3 models
print("\n" + "=" * 55)
print("4. AVERAGE across 3 models")
print("=" * 55)

for ver in ["Kero", "Alex"]:
    accs = [results[ver][m]["acc"] for m in ["LR", "RF", "XGB"]]
    recs = [results[ver][m]["recall"] for m in ["LR", "RF", "XGB"]]
    print(f"    {ver}: avg acc={sum(accs)/3:.2%} | avg HIGH recall={sum(recs)/3:.4%}")

# Part 5: Verdict
print("\n" + "=" * 55)
print("5. VERDICT")
print("=" * 55)

k_lr = results["Kero"]["LR"]["recall"]
a_lr = results["Alex"]["LR"]["recall"]
print(f"  Kero's balanced LR vs Alex's C=100 LR: {k_lr:.2f} vs {a_lr:.2f}")
print(f"  → class_weight='balanced' is the most effective for HIGH recall")
print(f"     no balanced: HIGH recall = {a_lr:.4f}")
print(f"     balanced:    HIGH recall = {k_lr:.4f}")
print(f"     difference:  {k_lr - a_lr:+.4f}")
