# Fall Risk Model + LIME - Final Handover (Logistic Regression)

## macOS setup

Double-click `deploy/setup_and_run.command` (or run `bash deploy/setup_and_run.command` from the project root). The launcher installs the Python dependencies, uses Corepack/project-local pnpm without requiring `sudo`, starts the FastAPI and Vite servers, waits for both health checks, and opens the dashboard.

- Dashboard: `http://127.0.0.1:5173`
- API docs: `http://127.0.0.1:8000/docs`
- Python 3.10+ is required; an existing Python 3.9 virtual environment is recreated automatically.
- Keep the two server Terminal windows open while using the dashboard.

**From:** KWAN Kwan Ip (ML Module) -> Teammate (API Module)

## Model
Logistic Regression (`class_weight='balanced'`, 70/20/10 split).
Test accuracy ~84%.

## Top-3 risk factors (by LIME, global)

| Rank | Feature | Meaning | avg LIME weight |
|------|---------|---------|-----------------|
| 1 | `high_risk_medication` | Uses high-risk medication (0/1) | 0.2256 |
| 2 | `cognitive_impairment` | Cognitive impairment level (0-2) | 0.177 |
| 3 | `past_falls` | Number of past falls | 0.1731 |

> The API can show these to clinicians as the main risk factors.

## Files

| File | Purpose |
|------|---------|
| `fall_risk_model.pkl` | Trained Logistic Regression |
| `train_data.npy` | Training data (LIME needs it to build neighbors) |
| `predict.py` | `predict_fall_risk()` / `explain_patient()` / `get_top3_features()` |
| `top3_features.json` | Top-3 features as JSON |
| `README.md` | This guide |

## FastAPI example

```python
from predict import predict_fall_risk, explain_patient, get_top3_features

@app.post("/predict")
def predict(patient: Patient):
    return {"fall_risk_level": predict_fall_risk(patient.model_dump())}

@app.post("/predict/explain")
def explain(patient: Patient):
    return {"explanation": explain_patient(patient.model_dump())}

@app.get("/risk-factors")
def risk_factors():
    return {"top_3_features": get_top3_features()}
```

## Requirements

```bash
pip install joblib scikit-learn lime numpy pandas
```
