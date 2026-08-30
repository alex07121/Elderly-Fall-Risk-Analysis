# 📁 IA2 Project — File Inventory & Functions

> **Location:** `~/Desktop/IA/demo/IA2/`
> **Structure:** `P1/` (Phase 1 + Jim) · `P2/` (Phase 2 - Kero) · `P2/P2Alex/` (Phase 2 - Alex)

---

## 🗂️ P1/ — Phase 1 Files (Kero + Jim)

| File | 用途 (Function) | 點 run |
|------|----------------|--------|
| `generate_data.py` | **Jim 嘅 data generator** — 生成 2,000 個 v2 病人記錄 (17 cols) | `python generate_data.py` |
| `real_data_pipeline.py` | **Kero 主 pipeline** — load data → 10 features → 70/20/10 → train LR | `python real_data_pipeline.py` |
| `real_data_pipeline_k_fold.py` | **Kero 5-fold CV 版** — LR/RF/XGB + HIGH recall scoring | `python real_data_pipeline_k_fold.py` |
| `real_data_pipeline_kfold.py` | 早期 k-fold 版本（可以忽略，被上面取代） | — |
| `real_data_pipeline_Alex.py` | **Alex Phase 1 版** — 80/20 + StandardScaler + C=100 | `python real_data_pipeline_Alex.py` |
| `compare_models.py` | **Kero vs Alex 比較** — 5 個 sections（per-model winner, best acc, average, verdict） | `python compare_models.py` |
| `tune_lr_validation.py` | **LR tuning** — C + threshold 喺 validation 度 tune | `python tune_lr_validation.py` |
| `xgb_threshold_tuning.py` | **XGB + threshold tuning** — 8 個 threshold + overfit check | `python xgb_threshold_tuning.py` |
| `xgb_smote_tuning.py` | **XGB + SMOTE** — oversampling HIGH class + threshold | `python xgb_smote_tuning.py` |
| `class_balance.py` | Class balance 圖（LOW/MEDIUM/HIGH + balanced weights） | `python class_balance.py` |
| `risk_distribution.py` | 2,000 病人 3 色 dot 分佈圖 | `python risk_distribution.py` |
| `shap_analysis.py` | SHAP 基本圖（beeswarm, bar, waterfall, heatmap） | `.venv_shap/bin/python shap_analysis.py` |
| `pprof_shap.py` | SHAP 專業圖（4 張, dpi=200, 拉闊 x-axis） | `.venv_shap/bin/python pprof_shap.py` |
| `dashboard.py` | **Streamlit dashboard** — 5 tabs 互動圖表 | `streamlit run dashboard.py` |

---

## 🗂️ P2/ — Phase 2 Files (Kero)

| File | 用途 (Function) | 點 run |
|------|----------------|--------|
| `fall_risk_patients_2000_v2.csv` | **Jim 新 data** — 17 cols (加 sex + fall-detail) | 輸入 data |
| `phase2_model.py` | **P2 model (17 features)** — Kero 4 engineered + sex + 3 clinical bg | `python phase2_model.py` |
| `fair_compare.py` | **公平比較** — Kero 17 vs Alex 14（同 folds、同 split、同 test） | `python fair_compare.py` |
| `combo_model.py` | **Combo (18 features)** — Kero engineered + Alex polypharmacy/-1 | `python combo_model.py` |
| `final_model.py` | ⭐ **FINAL MODEL** — Alex 14 features + Kero 驗證方法（acc 91.5%, recall 100%） | `python final_model.py` |
| `shap_overfit_test.py` | **SHAP 5-fold 穩定性測試** — 證明冇 overfit + feature balance | `.venv_shap/bin/python shap_overfit_test.py` |
| `shap_stacked_bar.py` | **Multi-class SHAP stacked bar** — 每個 feature 對 3 class 影響 | `.venv_shap/bin/python shap_stacked_bar.py` |
| `saved/` | **Final model artifacts** — final_model.pkl, label_encoder.pkl, features.json, threshold.json | 部署用 |

### 圖表輸出 (P2)
| File | 內容 |
|------|------|
| `phase2_feature_balance.png` | Feature 分佈 by risk level |
| `phase2_shap_stacked_bar.png` | Multi-class SHAP importance |
| `phase2_shap_overfit_report.txt` | SHAP stability 報告 |

---

## 🗂️ P2/P2Alex/ — Phase 2 Files (Alex)

### ml/ module
| File | 用途 (Function) |
|------|----------------|
| `train.py` | **Retrain LR** — 14 features, class_weight='balanced', sanity acc 92.2%, 生成 model.pkl + top3_features.json |
| `predict.py` | **Prediction + LIME + Counterfactual** — `predict_fall_risk()`, `explain_patient()`, `get_top3_features()`, `get_minimal_change()`, `recommend_intervention()` |
| `fall_risk_model.pkl` | 已訓練 model |
| `train_data.npy` | Training X（LIME explainer 用） |
| `top3_features.json` | Top-3 risk factors（high_risk_medication, past_falls, orthostatic_hypotension） |

### backend/ module（FastAPI）
| File | 用途 |
|------|------|
| `main.py` | FastAPI 主入口 |
| `models.py` | Pydantic data models |
| `database.py` | Database 連接 |
| `libAuto.py` | 自動化 helper |

### full-version/（Vue dashboard）
完整前端 dashboard（fall-risk-dashboard.vue 等）

### deploy/
| File | 用途 |
|------|------|
| `setup_and_run.bat` | Windows 一鍵部署 script |
| `README.md` | 部署說明 |

---

## 📌 最常用 Commands

```bash
# Kero — Final model（最重要！）
cd ~/Desktop/IA/demo/IA2/P2 && unset PYTHONPATH && /opt/anaconda3/bin/python final_model.py

# Kero — SHAP overfit test
cd ~/Desktop/IA/demo/IA2/P2 && unset PYTHONPATH && ../IA/.venv_shap/bin/python shap_overfit_test.py

# Alex — train + predict
cd ~/Desktop/IA/demo/IA2/P2/P2Alex/ml && unset PYTHONPATH && /opt/anaconda3/bin/python train.py
cd ~/Desktop/IA/demo/IA2/P2/P2Alex/ml && unset PYTHONPATH && /opt/anaconda3/bin/python predict.py
```

---

## 🏆 最終版本狀態

| Item | 狀態 |
|------|------|
| **FINAL MODEL** | `P2/final_model.py` — acc 91.5%, recall 100%, no overfit ✅ |
| **Artifacts** | `P2/saved/` (model.pkl + threshold.json) — 可交俾 Lai 部署 |
| **Presentation** | `P2/Phase2_Final_Presentation.pptx` (12 slides) |
| **Alex intervention** | `P2Alex/ml/predict.py` — counterfactual 建議 |
