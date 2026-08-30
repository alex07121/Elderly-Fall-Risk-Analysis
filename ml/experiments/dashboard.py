"""
Phase 2 Final Dashboard — Elderly Fall Risk Analysis
====================================================
Uses: v2 data (17 cols) + Final Model (LR, Alex 14 features, acc 91.5%, recall 100%)

Run:
    cd ~/Desktop/IA/demo/IA2/P2 && unset PYTHONPATH && /opt/anaconda3/bin/python -m streamlit run dashboard.py
"""
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import joblib, json
from pathlib import Path

# ═══ Load v2 data ═══
@st.cache_data
def load_data():
    df = pd.read_csv("fall_risk_patients_2000_v2.csv")
    for col in ["high_risk_medication", "orthostatic_hypotension"]:
        df[col] = df[col].map({True: 1, False: 0})
    df["sex"] = df["sex"].map({"F": 0, "M": 1})
    df["days_since_last_fall"] = pd.to_numeric(df["days_since_last_fall"], errors="coerce").fillna(-1)
    return df

@st.cache_resource
def load_model():
    mdir = Path("saved")
    if (mdir / "final_model.pkl").exists():
        model = joblib.load(mdir / "final_model.pkl")
        le = joblib.load(mdir / "label_encoder.pkl")
        with open(mdir / "features.json") as f:
            features = json.load(f)
        with open(mdir / "threshold.json") as f:
            thr = json.load(f)
        return model, le, features, thr
    return None, None, None, None

df = load_data()
model, le, FEATURES, THR = load_model()

RISK_ORDER = ["LOW", "MEDIUM", "HIGH"]
RISK_COLOR = {"LOW": "#4CAF50", "MEDIUM": "#FFC107", "HIGH": "#F44336"}

st.set_page_config(page_title="Fall Risk Analysis — Phase 2", layout="wide")
st.title("🏥 Elderly Fall Risk Analysis — Phase 2 Final")
st.caption("Group 3 · 2,000 patients · Final model: LR (14 features) · acc 91.5% · HIGH recall 100%")

# ═══ Sidebar ═══
with st.sidebar:
    st.header("📊 Overview")
    total = len(df)
    c = df["fall_risk_level"].value_counts()
    st.metric("Total Patients", f"{total:,}")
    st.metric("HIGH Risk", f"{c.get('HIGH', 0):,} ({c.get('HIGH', 0)/total:.1%})")
    st.metric("MEDIUM Risk", f"{c.get('MEDIUM', 0):,} ({c.get('MEDIUM', 0)/total:.1%})")
    st.metric("LOW Risk", f"{c.get('LOW', 0):,} ({c.get('LOW', 0)/total:.1%})")
    st.divider()
    if model is not None:
        st.success("✅ Final model loaded")
        st.caption(f"Features: {len(FEATURES)} | Threshold: {THR.get('threshold', 0.5)}")
    else:
        st.warning("⚠️ Model not found — run final_model.py first")

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "🎯 Risk Distribution", "📊 Feature Distribution", "🔥 Correlation", "🧓 Age Analysis", "🤖 Model Evolution", "📋 Summary Table"
])

# ═══════════════════════════════════════════
# Tab 1: Risk Distribution
# ═══════════════════════════════════════════
with tab1:
    st.subheader("🎯 Risk Level Distribution")
    col1, col2 = st.columns(2)
    with col1:
        counts = df["fall_risk_level"].value_counts().reindex(RISK_ORDER)
        fig = px.pie(values=counts.values, names=counts.index, color=counts.index,
                     color_discrete_map=RISK_COLOR, hole=0.4, title="Risk Level Proportion")
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        fig = px.bar(counts, color=counts.index, color_discrete_map=RISK_COLOR, title="Risk Level Counts")
        fig.update_layout(xaxis_title="Risk Level", yaxis_title="Count")
        st.plotly_chart(fig, use_container_width=True)
    st.write("#### Risk Level Counts")
    st.dataframe(pd.DataFrame({
        "Level": counts.index, "Count": counts.values,
        "佔比": [f"{v/total:.1%}" for v in counts.values]}),
        use_container_width=True, hide_index=True)

# ═══════════════════════════════════════════
# Tab 2: Feature Distribution
# ═══════════════════════════════════════════
with tab2:
    st.subheader("📊 Feature Distribution (by Risk Level)")
    feat_options = {
        "sex": "Sex", "age": "Age", "night_bed_exits": "Night Bed Exits",
        "night_activity_duration_min": "Night Activity (min)", "past_falls": "Past Falls",
        "mobility_score": "Mobility Score", "polypharmacy_count": "Polypharmacy Count",
        "tug_seconds": "TUG Seconds", "days_since_last_fall": "Days Since Last Fall",
        "cognitive_impairment": "Cognitive Impairment", "high_risk_medication": "High-Risk Medication",
        "orthostatic_hypotension": "Orthostatic Hypotension",
        "syncopal_fall": "Syncopal Fall", "fall_cluster_30d": "Fall Cluster 30d",
    }
    sel = st.selectbox("Select Feature", list(feat_options.keys()), format_func=lambda k: feat_options[k])
    col1, col2 = st.columns(2)
    with col1:
        fig = px.box(df, x="fall_risk_level", y=sel, color="fall_risk_level",
                     color_discrete_map=RISK_COLOR, category_orders={"fall_risk_level": RISK_ORDER},
                     title=f"{feat_options[sel]} Distribution (Box Plot)")
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        fig = px.histogram(df, x=sel, color="fall_risk_level", nbins=20,
                           color_discrete_map=RISK_COLOR, marginal="box",
                           category_orders={"fall_risk_level": RISK_ORDER},
                           title=f"{feat_options[sel]} Histogram")
        st.plotly_chart(fig, use_container_width=True)
    st.write(f"#### {feat_options[sel]} Statistics by Risk Level")
    stat = df.groupby("fall_risk_level")[sel].describe().loc[RISK_ORDER][["mean", "std", "min", "max"]]
    st.dataframe(stat.round(2), use_container_width=True)

# ═══════════════════════════════════════════
# Tab 3: 相關性
# ═══════════════════════════════════════════
with tab3:
    st.subheader("🔥 Feature Correlation Matrix")
    num_cols = ["age", "night_bed_exits", "night_activity_duration_min", "past_falls",
                "mobility_score", "polypharmacy_count", "tug_seconds", "days_since_last_fall",
                "cognitive_impairment", "high_risk_medication",
                "orthostatic_hypotension", "syncopal_fall", "fall_cluster_30d"]
    corr = df[num_cols].corr()
    fig = px.imshow(corr, text_auto=".2f", color_continuous_scale="RdBu_r",
                    zmin=-1, zmax=1, aspect="auto", title="Feature Correlation (Pearson)")
    fig.update_layout(height=500)
    st.plotly_chart(fig, use_container_width=True)
    st.markdown("""
    **Observations:**
    - `tug_seconds` ↔ `mobility_score` 強負相關 — TUG 越慢，行動分數越低
    - `night_bed_exits` ↔ `night_activity_duration_min` 正相關 — 離床越多，活動越久
    - `polypharmacy_count``polypharmacy_count` ↔ `high_risk_medication` related (r≈0.4) — polypharmacy & high-risk drugs
    """)

# ═══════════════════════════════════════════
# Tab 4: Age Analysis
# ═══════════════════════════════════════════
with tab4:
    st.subheader("🧓 Age Analysis")
    fig = px.histogram(df, x="age", color="fall_risk_level", nbins=15,
                       color_discrete_map=RISK_COLOR, marginal="violin",
                       category_orders={"fall_risk_level": RISK_ORDER}, title="Age Distribution (by Risk Level)")
    st.plotly_chart(fig, use_container_width=True)
    fig = px.box(df, x="fall_risk_level", y="age", color="fall_risk_level",
                 color_discrete_map=RISK_COLOR, category_orders={"fall_risk_level": RISK_ORDER},
                 title="Age Range by Risk Level")
    st.plotly_chart(fig, use_container_width=True)
    df["age_group"] = pd.cut(df["age"], bins=[0, 70, 80, 90, 200], labels=["<70", "70-79", "80-89", "90+"])
    age_risk = pd.crosstab(df["age_group"], df["fall_risk_level"]).reindex(["<70", "70-79", "80-89", "90+"])[RISK_ORDER]
    st.write("#### Age Group × Risk Level")
    st.dataframe(age_risk, use_container_width=True)

# ═══════════════════════════════════════════
# Tab 5: Model Evolution (4-step process)
# ═══════════════════════════════════════════
with tab5:
    st.subheader("🤖 Model Evolution — Why LR is the Final Choice")

    # Step 1: 3-Model Comparison — Kero AND Alex versions
    st.markdown("#### Step 1 — 3-Model Comparison: LR is best in BOTH versions")
    c1, c2 = st.columns(2)

    # Kero version (17 features) — from phase2_model.py
    with c1:
        st.markdown("**Kero (17 features) — phase2_model.py**")
        step1_k = pd.DataFrame({
            "Model": ["LR", "XGBoost", "Random Forest"],
            "HIGH Recall": [0.9427, 0.8282, 0.7155],
            "Accuracy": [0.8990, 0.8740, 0.8275],
        })
        figk = px.bar(step1_k, x="Model", y="HIGH Recall",
                      color="Model", color_discrete_map={"LR": "#2E7D32", "XGBoost": "#F57C00", "Random Forest": "#C62828"},
                      text=step1_k["HIGH Recall"].apply(lambda x: f"{x:.4f}"))
        figk.update_layout(height=260, showlegend=False, title="5-fold CV — HIGH Recall (LR wins 0.9427)")
        st.plotly_chart(figk, use_container_width=True)
        figk_acc = px.bar(step1_k, x="Model", y="Accuracy",
                          color="Model", color_discrete_map={"LR": "#2E7D32", "XGBoost": "#F57C00", "Random Forest": "#C62828"},
                          text=step1_k["Accuracy"].apply(lambda x: f"{x:.4f}"))
        figk_acc.update_layout(height=260, showlegend=False, title="5-fold CV — Accuracy (LR wins 0.8990)")
        st.plotly_chart(figk_acc, use_container_width=True)

    # Alex version (14 features) — from P2Alex ml train sanity
    with c2:
        st.markdown("**Alex (14 features) — P2Alex/ml**")
        step1_a = pd.DataFrame({
            "Model": ["LR", "XGBoost", "Random Forest"],
            "HIGH Recall": [0.9447, 0.8493, 0.7155],
            "Accuracy": [0.9045, 0.8795, 0.8380],
        })
        figa = px.bar(step1_a, x="Model", y="HIGH Recall",
                      color="Model", color_discrete_map={"LR": "#2E7D32", "XGBoost": "#F57C00", "Random Forest": "#C62828"},
                      text=step1_a["HIGH Recall"].apply(lambda x: f"{x:.4f}"))
        figa.update_layout(height=260, showlegend=False, title="5-fold CV — HIGH Recall (LR wins 0.9447)")
        st.plotly_chart(figa, use_container_width=True)
        figa_acc = px.bar(step1_a, x="Model", y="Accuracy",
                          color="Model", color_discrete_map={"LR": "#2E7D32", "XGBoost": "#F57C00", "Random Forest": "#C62828"},
                          text=step1_a["Accuracy"].apply(lambda x: f"{x:.4f}"))
        figa_acc.update_layout(height=260, showlegend=False, title="5-fold CV — Accuracy (LR wins 0.9045)")
        st.plotly_chart(figa_acc, use_container_width=True)

    st.success("✅ LR is the best model in BOTH feature sets — then we test adding features")

    # Step 2: Combo (swapped — was Step 3)
    st.markdown("#### Step 2 — Combo Attempt (combo_model.py): RESULT GOT WORSE")
    step3 = pd.DataFrame({
        "Model": ["Alex (14 feat)", "Combo (18 feat)"],
        "Accuracy": [0.9170, 0.9120],
        "HIGH Recall": [0.9940, 0.9870],
    })
    fig3 = go.Figure()
    fig3.add_trace(go.Bar(name="Accuracy", x=step3["Model"], y=step3["Accuracy"],
                          marker_color=["#2E7D32", "#C62828"],
                          text=[f"{v:.1%}" for v in step3["Accuracy"]]))
    fig3.add_trace(go.Bar(name="HIGH Recall", x=step3["Model"], y=step3["HIGH Recall"],
                          marker_color=["#00A896", "#E57373"],
                          text=[f"{v:.1%}" for v in step3["HIGH Recall"]]))
    fig3.update_layout(barmode="group", height=280,
                       title="Adding 4 features made it WORSE — Alex 91.7%/99.4% → Combo 91.2%/98.7%")
    st.plotly_chart(fig3, use_container_width=True)
    st.error("❌ WORSE: -0.5% acc, -0.7% recall, 1 HIGH patient MISSED (Alex 0 → Combo 1)")
    st.markdown("**Why: multicollinearity (polypharmacy r=0.75 with med_poly_interaction) — redundant features = NOISE**")

    # Step 3: Fair Comparison (swapped — was Step 2)
    st.markdown("#### Step 3 — Fair Comparison (fair_compare.py): Alex 14 wins")
    step2 = pd.DataFrame({
        "Model": ["Kero (17 feat)", "Alex (14 feat)"],
        "Accuracy": [0.9100, 0.9150],
        "HIGH Recall": [0.9811, 1.0000],
    })
    fig2 = go.Figure()
    fig2.add_trace(go.Bar(name="Accuracy", x=step2["Model"], y=step2["Accuracy"], marker_color="#4DA8DA", text=[f"{v:.1%}" for v in step2["Accuracy"]]))
    fig2.add_trace(go.Bar(name="HIGH Recall", x=step2["Model"], y=step2["HIGH Recall"], marker_color="#00D4AA", text=[f"{v:.1%}" for v in step2["HIGH Recall"]]))
    fig2.update_layout(barmode="group", height=280, title="Same test set — Alex 14 features wins (missed 0 HIGH)")
    st.plotly_chart(fig2, use_container_width=True)
    st.markdown("**→ Decision: Alex 14 features + Kero validation = FINAL MODEL**")

    # Step 4: Final
    st.markdown("#### Step 4 — Final Model (final_model.py)")
    m1, m2, m3 = st.columns(3)
    m1.metric("🏆 Accuracy", "91.5%")
    m2.metric("🎯 HIGH Recall", "100%")
    m3.metric("✅ HIGH Missed", "0 (53/53)")
    st.success("Alex 14 features + Kero validation (5-fold + threshold + overfit check) = FINAL MODEL")

# ═══════════════════════════════════════════
# Tab 6: Summary Table (units + sex + min/max/mean)
# ═══════════════════════════════════════════
with tab6:
    st.subheader("📋 Feature Summary — Units, Sex, Min/Max/Mean")

    # Feature metadata: unit + description
    feat_meta = {
        "sex": ("0=F, 1=M", "Gender"),
        "age": ("years", "Age"),
        "night_bed_exits": ("times/night", "Night bed exits"),
        "night_activity_duration_min": ("minutes", "Night activity duration"),
        "past_falls": ("count", "Past falls"),
        "mobility_score": ("score 1-10", "Mobility score"),
        "high_risk_medication": ("0/1", "High-risk medication"),
        "cognitive_impairment": ("0/1/2", "Cognitive impairment"),
        "polypharmacy_count": ("count", "Polypharmacy count"),
        "orthostatic_hypotension": ("0/1", "Orthostatic hypotension"),
        "tug_seconds": ("seconds", "TUG test"),
        "days_since_last_fall": ("days", "Days since last fall"),
        "syncopal_fall": ("0/1", "Syncopal fall"),
        "fall_cluster_30d": ("0/1", "Fall cluster 30d"),
    }

    summary_rows = []
    for feat, (unit, desc) in feat_meta.items():
        s = df[feat]
        row = {
            "Feature": desc,
            "Unit": unit,
            "Mean": round(s.mean(), 2),
            "Min": s.min(),
            "Max": s.max(),
            "Std": round(s.std(), 2),
        }
        # per-sex stats for age (and numeric)
        if df["sex"].nunique() == 2:
            male_vals = df.loc[df["sex"] == 1, feat]
            female_vals = df.loc[df["sex"] == 0, feat]
            if male_vals.nunique() > 1 and female_vals.nunique() > 1:
                row["Male Mean"] = round(male_vals.mean(), 2)
                row["Female Mean"] = round(female_vals.mean(), 2)
            else:
                row["Male Mean"] = male_vals.mode().iloc[0] if len(male_vals) else "-"
                row["Female Mean"] = female_vals.mode().iloc[0] if len(female_vals) else "-"
        summary_rows.append(row)

    summary_df = pd.DataFrame(summary_rows)
    st.dataframe(summary_df, use_container_width=True, hide_index=True)

    st.markdown("""
    **Notes:**
    - `sex`: F=0, M=1 (57% female in dataset)
    - `days_since_last_fall`: -1 = never fell
    - `mobility_score`: 10 = fully independent, 1 = severely limited
    - `tug_seconds`: ≥13.5s = fall-risk cutoff (CDC STEADI)
    """)

    # Age by sex breakdown
    st.markdown("#### Age by Sex")
    age_sex = df.groupby("sex")["age"].agg(["count", "mean", "min", "max", "std"]).round(1)
    age_sex.index = ["Female", "Male"]
    st.dataframe(age_sex, use_container_width=True)
