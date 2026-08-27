# ml/experiments — Model Experiments & Validation (KS 的 Phase-2 工作)

呢個資料夾放 **KS（Kero）** 寫嘅模型實驗 / 驗證 scripts。佢哋係「搵出 FINAL MODEL」過程嘅完整證據鏈：
fair comparison → combo 實驗 → 5-fold stability（overfit 證明）→ SHAP 圖 → 最終模型輸出。

> 註：呢啲 scripts 原本由 KS 直接 upload 咗去 repo 根目錄（GitHub "Add files via upload"），
> 為咗保持專案結構整潔，已移入 `ml/experiments/`（用 `git mv`，commit history 冇斷）。
> 唯一改動：data path 由 `"fall_risk_patients_2000_v2.csv"`（靠 CWD）改為 `__file__` 相對路徑
> `../../data/fall_risk_patients_2000_v2.csv`，所以而家喺 repo 任何位置 run 都得。

## File 一覽

| File | 用途（KS 原描述） | 輸出 |
|------|-------------------|------|
| `final_model.py` | **FINAL MODEL** — Alex 14 features + Kero 驗證（70/20/10 + 5-fold + threshold tuning + overfit check），LR `class_weight='balanced'` → **acc ~91.5%, HIGH recall ~100%** | `saved/`（俾 Lai 部署用） |
| `phase2_model.py` | **17 features 版** — Kero engineered (4) + sex + 3 clinical background；threshold tuning + overfit check（P2 改進版） | console metrics |
| `fair_compare.py` | **公平比較 Kero (17 features) vs Alex (14 features)** — same split / same test set / same metrics / same protocol，threshold 兩邊都係 0.5（冇 unfair advantage） | console metrics |
| `combo_model.py` | **18 features combo** — Kero engineered + Alex 保留 `polypharmacy_count` + Alex `days_since_last_fall=-1` 處理 | console metrics |
| `shap_overfit_test.py` | **SHAP 5-fold 穩定性** — feature ranking 每個 fold 一致 → 證明模型冇 overfit；另附 feature balance 圖 | `phase2_shap_overfit_report.txt` + PNG figures |
| `shap_stacked_bar.py` | **Multi-class SHAP 圖** — mean(\|SHAP\|) per feature，按 HIGH / MEDIUM / LOW 拆開 stacked bar | PNG figure |

## 點樣 Run（喺 repo root）

```bash
# 一般 script（只需要 pandas / numpy / scikit-learn / joblib）
python ml/experiments/final_model.py
python ml/experiments/phase2_model.py
python ml/experiments/fair_compare.py
python ml/experiments/combo_model.py

# SHAP scripts（需要 SHAP venv：pip install shap matplotlib）
python ml/experiments/shap_overfit_test.py
python ml/experiments/shap_stacked_bar.py
```

## 部署輸出（Lai 用）

`final_model.py` run 完之後會喺 **repo root** 產生 `saved/`：

| File | 內容 |
|------|------|
| `saved/final_model.pkl` | 訓練好嘅 Logistic Regression（14 features, balanced） |
| `saved/label_encoder.pkl` | LabelEncoder（LOW/MEDIUM/HIGH 編碼） |
| `saved/features.json` | 14 個 feature 名稱（順序必須一致） |
| `saved/threshold.json` | `{"threshold", "high_idx", "classes"}` — 部署時用 threshold 決定 HIGH |

> 呢批 artifacts 係俾 Lai 接落 API 部署用（對應 `deploy/` + `backend/` 嘅 predict 流程）。
