# Web dashboard address: 127.0.0.1:8000
# Interactive API control panel: 127.0.0.1:8000/docs
# username: admin_clinician
# password: password123

# Download library
from backend.libAuto import libmain
libmain()

import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
import hashlib
import secrets
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import jwt
from pydantic import BaseModel, Field
# This imports code and loads the models automatically
from ml.predict import predict_fall_risk, explain_patient, recommend_intervention
import gradio as gr
import pandas as pd
import random

from backend.models import PatientRecord
from backend.database import Base, engine, get_db, AsyncSessionLocal

# Project paths (backend/ sits one level below the project root)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi.middleware.cors import CORSMiddleware
from typing import Literal

SECRET_KEY = "SUPER_SECRET_SECURITY_KEY_CHANGE_THIS_IN_PRODUCTION"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# hashlib.sha256(b"password123").hexdigest()
ADMIN_PASSWORD_HASH = "ef92b778bafe771e89245b89ecbc08a44a4e166c06659911881f383d4473e94f"

MOCK_USERS_DB = {
    "admin_clinician": {
        "username": "admin_clinician",
        "hashed_password": ADMIN_PASSWORD_HASH,
        "disabled": False,
    }
}

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

class Token(BaseModel):
    access_token: str
    token_type: str

def verify_password(plain_password: str, correct_hash: str) -> bool:
    input_hash = hashlib.sha256(plain_password.encode('utf-8')).hexdigest()
    return secrets.compare_digest(input_hash, correct_hash)

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# Dependency validation check ensuring route protection
async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception
        
    user = MOCK_USERS_DB.get(username)
    if user is None:
        raise credentials_exception
    return user


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Shutdown
    await engine.dispose()

# Initialize the API
app = FastAPI(title="Fall Risk Assessment API", lifespan=lifespan)

# Define the 10 inputs exactly as requested in the README
class PatientData(BaseModel):
    sex: Literal['M', 'F']
    age: int = Field(..., ge=60, le=100)
    night_bed_exits: int = Field(..., ge=0, le=8)
    night_activity_duration_min: float = Field(..., ge=0, le=120)
    past_falls: int = Field(..., ge=0, le=5)
    mobility_score: int = Field(..., ge=1, le=10)
    high_risk_medication: int = Field(..., ge=0, le=1)
    cognitive_impairment: int = Field(..., ge=0, le=2)
    polypharmacy_count: int = Field(..., ge=0, le=14)
    orthostatic_hypotension: int = Field(..., ge=0, le=1)
    tug_seconds: float = Field(..., ge=8.0, le=31.9)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = MOCK_USERS_DB.get(form_data.username)
    if not user or not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["username"]}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/predict")
async def get_prediction(data: PatientData, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    try:
        # Convert incoming JSON data into a clean Python dictionary
        features_dict = data.model_dump()
        
        # Run model function
        result = predict_fall_risk(features_dict)
        lime_explanations = explain_patient(features_dict, max_features=3)
        suggestion = recommend_intervention(features_dict)

        # Save feature profile & prediction output to database
        db_record = PatientRecord(
            age=features_dict["age"],
            night_bed_exits=features_dict["night_bed_exits"],
            night_activity_duration_min=features_dict["night_activity_duration_min"],
            past_falls=features_dict["past_falls"],
            mobility_score=features_dict["mobility_score"],
            high_risk_medication=features_dict["high_risk_medication"],
            cognitive_impairment=features_dict["cognitive_impairment"],
            polypharmacy_count=features_dict["polypharmacy_count"],
            orthostatic_hypotension=features_dict["orthostatic_hypotension"],
            tug_seconds=features_dict["tug_seconds"],
            fall_risk_level=result
        )
        db.add(db_record)
        await db.commit()
        
        # Return the exact JSON structure your friend asked for
        return {
            "fall_risk_level": result,
            "lime_explanations": lime_explanations,
            "suggestion": suggestion
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")
    
# Gradio Prediction Logic
async def predict_gradio(
        inputSex,
        inputAge, 
        inputPastFalls, 
        inputMobilityScore, 
        inputNightBedExits, 
        inputNightActivityDurationMin, 
        inputHighRiskMed, 
        inputCognitiveImpairment,
        inputPolypharmacyCount,
        inputOrthostaticHypotension,
        inputTugSeconds
    ):
    profile = PatientData(
        sex=_to_sex(inputSex),
        age=int(inputAge),
        night_bed_exits=int(inputNightBedExits),
        night_activity_duration_min=int(inputNightActivityDurationMin),
        past_falls=int(inputPastFalls),
        mobility_score=int(inputMobilityScore),
        high_risk_medication=1 if inputHighRiskMed else 0,
        cognitive_impairment=int(inputCognitiveImpairment), 
        polypharmacy_count=int(inputPolypharmacyCount), 
        orthostatic_hypotension=1 if inputOrthostaticHypotension else 0, 
        tug_seconds=float(inputTugSeconds)
    )

    async with AsyncSessionLocal() as session:
        response = await get_prediction(data=profile, db=session)
        
    risk_level = response["fall_risk_level"]
    explanations = response["lime_explanations"]
    suggestion = response["suggestion"]

    # Format output for the user interface textboxes
    output_text = f"Risk Level: {risk_level}\n"
    output_text += "primary factors:\n"
    for i, exp in enumerate(explanations, start=1):
        output_text += f" {i}. {exp['condition']} | Weight: {exp['weight']} ({exp['direction']})\n"
    output_text += f"Suggestions:\n"
    if risk_level == "HIGH":
        for item in suggestion["all_options"]:
            if item["can_flip"]:
                # Perfect Sentence Generation matching your UI requirements
                output_text += f"  • {item['feature']} need to change from {item['from']} to {item['to']}.\n"
            else:
                # Gracefully handle features that cannot drop the risk level independently
                output_text += f"  • [Restricted] Altering '{item['feature']}' alone is insufficient.\n"
    else:
        output_text += f"{suggestion["note"]}\n"
    return output_text

def random_gradio():
    df = pd.read_csv(os.path.join(DATA_DIR, "fall_risk_patients_2000_v2.csv"))
    X = df.drop(columns=["fall_risk_score", "fall_risk_level", "patient_id", "sex"])    # feature
    first_row = X.iloc[random.randint(0, len(df) - 1)].to_dict()
    return (
        first_row.get("age"),
        first_row.get("night_bed_exits"),
        first_row.get("night_activity_duration_min"),
        first_row.get("past_falls"),
        first_row.get("mobility_score"),
        first_row.get("high_risk_medication"),
        first_row.get("cognitive_impairment"),
        first_row.get("polypharmacy_count"),
        first_row.get("orthostatic_hypotension"),
        first_row.get("tug_seconds"),
    )


# 中文列名 -> 英文特征名（养老院 Excel 模板用中文列名，后端自动映射）
COLUMN_MAP = {
    "姓名": "name", "性别": "sex", "年龄": "age",
    "夜间离床次数": "night_bed_exits",
    "夜间活动时长(分钟)": "night_activity_duration_min",
    "夜间活动时长": "night_activity_duration_min",
    "过去跌倒次数": "past_falls", "活动能力评分": "mobility_score",
    "是否使用高风险药物": "high_risk_medication",
    "认知障碍程度": "cognitive_impairment", "多重用药数量": "polypharmacy_count",
    "是否有体位性低血压": "orthostatic_hypotension",
    "起立行走测试(秒)": "tug_seconds", "起立行走测试": "tug_seconds",
}

FEATURE_CN = {
    "sex": "性别", "age": "年龄", "night_bed_exits": "夜间离床次数",
    "night_activity_duration_min": "夜间活动时长", "past_falls": "过去跌倒次数",
    "mobility_score": "活动能力评分", "high_risk_medication": "高风险药物",
    "cognitive_impairment": "认知障碍", "polypharmacy_count": "多重用药",
    "orthostatic_hypotension": "体位性低血压", "tug_seconds": "起立行走测试(秒)",
}


def _cn(text):
    for en, cn in FEATURE_CN.items():
        text = text.replace(en, cn)
    return text


def _to_sex(v):
    """男/女/M/F/male/female/1/0 -> 'M'/'F'"""
    if isinstance(v, (int, float)) and not pd.isna(v):
        return "M" if int(v) == 1 else "F"
    s = str(v).strip().lower()
    if s in ("男", "m", "male"):
        return "M"
    if s in ("女", "f", "female"):
        return "F"
    raise ValueError(f"性别无法识别：{v}（请填 男 或 女）")


def _to_bool(v):
    """是/否/有/无/yes/no/true/false/1/0 -> 1/0"""
    if isinstance(v, bool):
        return int(v)
    if isinstance(v, (int, float)) and not pd.isna(v):
        return int(v)
    s = str(v).strip().lower()
    if s in ("是", "有", "yes", "y", "true", "1"):
        return 1
    if s in ("否", "不是", "没有", "无", "no", "n", "false", "0"):
        return 0
    raise ValueError(f"无法识别：{v}（请填 是 或 否）")


def _build_excel_template(path):
    """Generate the Excel template (English column names + dropdowns)."""
    import openpyxl
    from openpyxl.styles import Font, PatternFill
    from openpyxl.worksheet.datavalidation import DataValidation

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Fall Risk Assessment"

    headers = ["sex", "age", "night_bed_exits", "night_activity_duration_min",
               "past_falls", "mobility_score", "high_risk_medication",
               "cognitive_impairment", "polypharmacy_count",
               "orthostatic_hypotension", "tug_seconds"]
    ws.append(headers)

    for cell in ws[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="4472C4")

    dv_sex = DataValidation(type="list", formula1='"Male,Female"', allow_blank=True)
    dv_yesno = DataValidation(type="list", formula1='"Yes,No"', allow_blank=True)
    dv_cog = DataValidation(type="list", formula1='"0,1,2"', allow_blank=True)
    for dv in (dv_sex, dv_yesno, dv_cog):
        ws.add_data_validation(dv)
    dv_sex.add("A2:A2000")
    dv_yesno.add("G2:G2000")
    dv_cog.add("H2:H2000")
    dv_yesno.add("J2:J2000")

    widths = {"A": 10, "B": 8, "C": 16, "D": 24, "E": 12, "F": 16,
              "G": 20, "H": 18, "I": 18, "J": 22, "K": 14}
    for col, w in widths.items():
        ws.column_dimensions[col].width = w

    wb.save(path)


def batch_predict_file(file):
    """Batch prediction: read an uploaded Excel(.xlsx) or CSV, predict each
    resident, and return a results table + summary.
    """
    if file is None:
        raise gr.Error("Please upload an Excel / CSV file first")

    required = ["sex", "age", "night_bed_exits", "night_activity_duration_min",
                "past_falls", "mobility_score", "high_risk_medication",
                "cognitive_impairment", "polypharmacy_count",
                "orthostatic_hypotension", "tug_seconds"]

    RANGE = {
        "age": (60, 100), "night_bed_exits": (0, 8),
        "night_activity_duration_min": (0, 120), "past_falls": (0, 5),
        "mobility_score": (1, 10), "high_risk_medication": (0, 1),
        "cognitive_impairment": (0, 2), "polypharmacy_count": (0, 14),
        "orthostatic_hypotension": (0, 1), "tug_seconds": (8.0, 31.9),
    }

    fname = file.name.lower()
    if fname.endswith((".xlsx", ".xlsm")):
        df = pd.read_excel(file.name, engine="openpyxl")
    elif fname.endswith(".csv"):
        df = None
        for enc in ("utf-8-sig", "gbk", "utf-8"):
            try:
                df = pd.read_csv(file.name, encoding=enc)
                break
            except Exception:
                continue
        if df is None:
            raise gr.Error("Could not read this CSV. Please check the format.")
    else:
        raise gr.Error("Please upload a .xlsx or .csv file (download the template below)")

    df = df.rename(columns={k: v for k, v in COLUMN_MAP.items() if k in df.columns})

    missing = [c for c in required if c not in df.columns]
    if missing:
        raise gr.Error("Missing columns: " + ", ".join(missing) +
                       ". Please use the template below.")

    if "sex" in df.columns:
        df["sex"] = df["sex"].apply(lambda v: _to_sex(v) if not pd.isna(v) else v)
    for c in ("high_risk_medication", "orthostatic_hypotension"):
        df[c] = df[c].apply(lambda v: _to_bool(v) if not pd.isna(v) else v)

    rows = []
    n_high = n_medium = n_low = n_err = 0
    for idx, r in df.iterrows():
        pid = f"P{idx + 1:05d}"
        try:
            feats = {}
            for c in required:
                v = r[c]
                if pd.isna(v):
                    raise ValueError(f"{c} is empty")
                if c in RANGE:
                    try:
                        fv = float(v)
                    except (TypeError, ValueError):
                        raise ValueError(f"{c} is not a number: {v}")
                    lo, hi = RANGE[c]
                    if not (lo <= fv <= hi):
                        raise ValueError(f"{c}={v} out of range {lo}~{hi}")
                feats[c] = v

            level = predict_fall_risk(feats)
            expl = explain_patient(feats, max_features=3)
            reasons = "; ".join(e["condition"] for e in expl)
            inter = recommend_intervention(feats)

            if level == "HIGH":
                best = inter.get("easiest_intervention", {})
                feat = best.get("feature", "")
                to_val = best.get("to")
                if to_val is None:
                    advice = f"{feat}: single change insufficient, needs combined intervention"
                else:
                    advice = f"{feat}: {best.get('from', '')} -> {to_val}"
                n_high += 1
            elif level == "MEDIUM":
                advice = "Increase monitoring, reassess regularly"
                n_medium += 1
            else:
                advice = "No intervention needed"
                n_low += 1

            rows.append({"ID": pid, "Risk Level": level,
                         "Top Risk Factors": reasons, "Intervention": advice})
        except Exception as e:
            n_err += 1
            rows.append({"ID": pid, "Risk Level": "Data Error",
                         "Top Risk Factors": str(e), "Intervention": ""})

    out = pd.DataFrame(rows)
    total = len(out)
    summary = (f"### Batch prediction complete\n\n"
               f"- Total residents: **{total}**\n"
               f"- HIGH risk: **{n_high}**\n"
               f"- MEDIUM risk: **{n_medium}**\n"
               f"- LOW risk: **{n_low}**\n"
               f"- Data errors: **{n_err}**")
    if n_err:
        summary += ("\n\n> Rows with errors are marked as \"Data Error\" in the "
                    "results table. Please check the values are within range and not empty.")
    return out, summary


# Build Gradio UI (single Blocks with two Tabs: single + batch)
with gr.Blocks() as interface:
    gr.Markdown("# 跌倒风险评估系统")
    TEMPLATE_PATH = os.path.join(DATA_DIR, "import_template.xlsx")
    if not os.path.exists(TEMPLATE_PATH):
        _build_excel_template(TEMPLATE_PATH)

    with gr.Tab("单条预测"):
        with gr.Row():
            with gr.Column():
                inputSex = gr.Radio(
                    choices=["男", "女"], 
                    label="性别",
                    value="男"
                )
                inputAge = gr.Number(
                    minimum=60, 
                    maximum=100, 
                    label="年龄", 
                    value=65
                )
                inputPastFalls = gr.Number(
                    minimum=0, 
                    label="过去跌倒次数", 
                    value=0
                )
                inputMobilityScore = gr.Slider(
                    minimum=1, 
                    maximum=10, 
                    step=1, 
                    label="活动能力评分", 
                    value=5
                )
                inputNightBedExits = gr.Number(
                    minimum=0, 
                    label="夜间离床次数",
                    value=0
                )
                inputNightActivityDurationMin = gr.Number(
                    minimum=0, 
                    label="夜间活动时长(分钟)",
                    value=0
                )
                inputHighRiskMed = gr.Checkbox(
                    label="高风险药物"
                )
                inputCognitiveImpairment = gr.Number(
                    minimum=0, 
                    maximum=2, 
                    label="认知障碍程度", 
                    value=0
                )
                inputPolypharmacyCount = gr.Number(
                    minimum=0, 
                    label="多重用药数量",
                    value=0
                )
                inputOrthostaticHypotension = gr.Checkbox(
                    label="体位性低血压"
                )
                inputTugSeconds = gr.Number(
                    minimum=8, 
                    label="起立行走测试(秒)", 
                    value=8.0
                )
                random_btn = gr.Button("随机生成示例老人资料")
                submit_btn = gr.Button("提交预测")

            with gr.Column():
                output = gr.Textbox(label="预测结果", lines=4)

        random_btn.click(
            fn=random_gradio, 
            inputs=[], 
            outputs=[
                inputAge, inputNightBedExits, inputNightActivityDurationMin, 
                inputPastFalls, inputMobilityScore, inputHighRiskMed, inputCognitiveImpairment,
                inputPolypharmacyCount, inputOrthostaticHypotension, inputTugSeconds
            ]
        )

        submit_btn.click(
            fn=predict_gradio, 
            inputs=[
                inputSex, inputAge, inputPastFalls, inputMobilityScore, inputNightBedExits, 
                inputNightActivityDurationMin, inputHighRiskMed, inputCognitiveImpairment,
                inputPolypharmacyCount, inputOrthostaticHypotension, inputTugSeconds
            ], 
            outputs=output
        )

    with gr.Tab("Batch Prediction"):
        gr.Markdown("""
# Batch Fall Risk Assessment

**Three steps:**

1. Click "Download Excel Template" below and open it in Excel
2. Fill in the data (one resident per row)
3. Save, upload above, and click "Run Batch Prediction"

**Column guide:**

| Column | How to fill |
|--------|-------------|
| sex | Select "Male" or "Female" |
| age | Number, 60–100 |
| night_bed_exits | Number, 0–8 |
| night_activity_duration_min | Number, 0–120 |
| past_falls | Number, 0–5 |
| mobility_score | Number, 1–10 (higher = better mobility) |
| high_risk_medication | Select "Yes" or "No" |
| cognitive_impairment | 0 / 1 / 2 (0=none, 1=mild, 2=moderate/severe) |
| polypharmacy_count | Number, 0–14 |
| orthostatic_hypotension | Select "Yes" or "No" |
| tug_seconds | Number, 8–31.9 (seconds) |

> Values out of range are marked as "Data Error". Please fill within range.
""")
        gr.DownloadButton(label="Download Excel Template", value=TEMPLATE_PATH)
        batch_file = gr.File(label="Upload filled Excel file (.xlsx)")
        batch_btn = gr.Button("Run Batch Prediction", variant="primary")
        batch_summary = gr.Markdown()
        batch_output = gr.Dataframe(label="Prediction Results", wrap=True)
        batch_btn.click(fn=batch_predict_file, inputs=batch_file,
                        outputs=[batch_output, batch_summary])

# Mount Gradio inside FastAPI application context properly
app = gr.mount_gradio_app(app, interface, path="/")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)