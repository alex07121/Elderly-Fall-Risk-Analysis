# LIME Handover — for SHAP comparison
=====================================

**From:** KWAN Kwan Ip (ML Module)
**To:** Teammate (SHAP analysis)

## Goal
Compare two explainable-AI methods (SHAP vs LIME) on the SAME model,
SAME patients, SAME class, so the comparison is fair.

## How to run

```bash
/Users/alex0712/Python_Study/.venv/bin/python lime_analysis.py
```

Requirements: `pip install lime scikit-learn pandas numpy`

## Fair-comparison contract (IMPORTANT)

Both tools MUST use:

| Item | Value |
|------|-------|
| Model | LogisticRegression(max_iter=5000, class_weight="balanced", random_state=42) |
| Data | fall_risk_patients_2000.csv, 10 features (REQUIRED list) |
| Split | 70/20/10, random_state=42, stratify |
| Class | HIGH risk |
| Patient (local) | the FIRST HIGH patient in the test set (script picks it automatically) |

> If your SHAP script trains a different model or picks a different
> patient, the comparison is NOT valid. Use the same settings.

## Outputs of the script

### A) Global top-3 features (LIME)
Expected (from KWAN's run):
1. high_risk_medication (0.2256)
2. cognitive_impairment (0.1770)
3. past_falls (0.1731)

Compare with your SHAP global mean |SHAP value| ranking.
(Both tools showed: high_risk_medication + cognitive_impairment at #1/#2.)

### B) Local explanation of ONE HIGH patient
Compare the top contributors with your SHAP waterfall/beeswarm for the
same patient. KWAN's LIME run gave:
- cognitive_impairment > 1.00  (+0.28 push HIGH)
- mobility_score <= 5.00       (+0.24 push HIGH)
- high_risk_medication = 0     (-0.23 pull away)

## Note on units
- SHAP values are in log-odds (can exceed 1)
- LIME weights are probability-scale (0~1)
Compare the RANKING / direction, not the raw numbers.

## Files
| File | Purpose |
|------|---------|
| `lime_analysis.py` | LIME global + local analysis |
| `README.md` | This guide |
