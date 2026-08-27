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
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse, Response
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import jwt
from pydantic import BaseModel, Field, model_validator
# This imports code and loads the models automatically
from ml.newpredict import predict_fall_risk, explain_patient
import gradio as gr
import pandas as pd
import random
import json
import re
import math
import asyncio
import tempfile
import zipfile
from types import SimpleNamespace
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from xml.sax.saxutils import escape as _xml_escape

from backend.models import PatientRecord
from backend.database import Base, engine, get_db, AsyncSessionLocal

# Project paths (backend/ sits one level below the project root)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi.middleware.cors import CORSMiddleware
from typing import Literal, Optional

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

# Define the deployed model's 14 inputs (11 base fields plus 3 fall-detail fields).
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
    # Extended fall-detail fields are model inputs and are also retained for
    # the caregiver-facing explanation.  Blank means "no fall recorded".
    days_since_last_fall: Optional[int] = Field(None, ge=0)
    syncopal_fall: int = Field(0, ge=0, le=1)
    fall_cluster_30d: int = Field(0, ge=0, le=1)
    resident_id: Optional[str] = None  # optional, links repeated assessments of the same resident

    @model_validator(mode="after")
    def normalise_fall_date(self):
        """Keep the template's empty ``0`` value from becoming a real fall.

        A value of zero remains valid when ``past_falls`` is positive (a fall
        today).  Only the contradictory no-history/zero-days combination is
        converted to the model's missing-value sentinel.
        """
        if self.past_falls == 0 and self.days_since_last_fall == 0:
            self.days_since_last_fall = None
        return self


# ---------- Evidence-backed, LIME-ranked suggestions for ages 60-74 ----------
# Priority is not a second clinical score.  It is assigned from the relative
# absolute LIME contribution among the actionable factors for this assessment:
# 1 = high model influence, 2 = medium, 3 = lower.  Caregivers should still
# follow the resident's care plan and escalate urgent symptoms regardless of rank.

SUGGESTION_PRIORITIES = {
    1: "High",
    2: "Medium",
    3: "Low",
}

MODEL_FEATURES = (
    "sex", "age", "night_bed_exits", "night_activity_duration_min",
    "past_falls", "mobility_score", "high_risk_medication",
    "cognitive_impairment", "polypharmacy_count",
    "orthostatic_hypotension", "tug_seconds", "days_since_last_fall",
    "syncopal_fall", "fall_cluster_30d",
)

FEATURE_LABELS = {
    "sex": "Sex",
    "age": "Age",
    "night_bed_exits": "Night-time bed exits",
    "night_activity_duration_min": "Night-time activity duration",
    "past_falls": "Falls in the past year",
    "mobility_score": "Mobility score",
    "high_risk_medication": "Medicine linked to falls",
    "cognitive_impairment": "Cognitive impairment",
    "polypharmacy_count": "Number of medicines",
    "orthostatic_hypotension": "Postural hypotension",
    "tug_seconds": "Timed Up & Go (TUG)",
    "days_since_last_fall": "Time since the last fall",
    "syncopal_fall": "Fall with loss of consciousness",
    "fall_cluster_30d": "Two or more falls within 30 days",
}

FEATURE_LABELS_ZH = {
    "sex": "性别",
    "age": "年龄",
    "night_bed_exits": "夜间离床次数",
    "night_activity_duration_min": "夜间活动时长",
    "past_falls": "过去一年跌倒次数",
    "mobility_score": "活动能力评分",
    "high_risk_medication": "高风险药物",
    "cognitive_impairment": "认知障碍程度",
    "polypharmacy_count": "多重用药数量",
    "orthostatic_hypotension": "体位性低血压",
    "tug_seconds": "起立行走测试（TUG）",
    "days_since_last_fall": "距上次跌倒天数",
    "syncopal_fall": "晕厥跌倒",
    "fall_cluster_30d": "30天内连续跌倒",
}

# These are screening flags used to decide which observed inputs deserve a
# caregiver's attention.  They are deliberately labelled as system/setting
# rules unless an external guideline supplies the value (currently TUG >= 12s).
ATTENTION_RULES_ZH = {
    "age": "系统关注条件：年龄 ≥75 岁（本页的行动建议只覆盖 60–74 岁）",
    "night_bed_exits": "系统关注条件：≥2 次/夜（机构可按护理计划调整）",
    "night_activity_duration_min": "系统关注条件：夜间活动 >30 分钟（机构可按护理计划调整）",
    "past_falls": "系统关注条件：过去一年有跌倒记录（机构可按护理计划调整）",
    "mobility_score": "系统关注条件：活动能力评分 ≤4/10（机构可按护理计划调整）",
    "high_risk_medication": "资料标记为与跌倒相关的药物；请由护士、药师或开药医生核对",
    "cognitive_impairment": "系统关注条件：记录为轻度或以上认知障碍（机构可按护理计划调整）",
    "polypharmacy_count": "系统关注条件：记录 4 种或以上药物（机构可按护理计划调整）",
    "orthostatic_hypotension": "资料标记为体位性低血压；请按机构流程复核症状和血压",
    "tug_seconds": "CDC STEADI 关注条件：TUG ≥12 秒",
    "days_since_last_fall": "系统关注条件：最近 30 天内发生过跌倒（机构可按护理计划调整）",
    "syncopal_fall": "资料标记为晕厥或意识丧失相关跌倒；按机构急症/跌倒流程处理",
    "fall_cluster_30d": "系统关注条件：30 天内连续跌倒（机构可按护理计划调整）",
}

# Authoritative sources are returned with every care suggestion so the UI can
# show the exact source instead of presenting an unsupported AI-generated claim.
REFERENCE_LIBRARY = {
    "nice_falls": {
        "id": "NICE-NG249",
        "title": "NICE NG249: Falls assessment and prevention",
        "title_zh": "NICE NG249：跌倒评估与预防建议",
        "publisher": "National Institute for Health and Care Excellence (NICE)",
        "url": "https://www.nice.org.uk/guidance/ng249/chapter/Recommendations",
    },
    "cdc_tug": {
        "id": "CDC-STEADI-TUG",
        "title": "CDC STEADI: Timed Up & Go (TUG) Assessment",
        "title_zh": "CDC STEADI：起立行走测试（TUG）评估",
        "publisher": "Centers for Disease Control and Prevention (CDC)",
        "url": "https://www.cdc.gov/steadi/media/pdfs/STEADI-Assessment-TUG-508.pdf",
    },
    "cdc_care_plan": {
        "id": "CDC-STEADI-CARE-PLAN",
        "title": "CDC STEADI: Coordinated Care Plan to Prevent Older Adult Falls",
        "title_zh": "CDC STEADI：老年人防跌倒协同护理计划",
        "publisher": "Centers for Disease Control and Prevention (CDC)",
        "url": "https://www.cdc.gov/steadi/pdf/Steadi-Coordinated-Care-Plan.pdf",
    },
    "cdc_postural": {
        "id": "CDC-STEADI-POSTURAL",
        "title": "CDC STEADI: Postural Hypotension - What It Is and How to Manage It",
        "title_zh": "CDC STEADI：体位性低血压及处理方法",
        "publisher": "Centers for Disease Control and Prevention (CDC)",
        "url": "https://stacks.cdc.gov/view/cdc/49080",
    },
    "nice_tloc": {
        "id": "NICE-CG109",
        "title": "NICE CG109: Transient loss of consciousness (blackouts)",
        "title_zh": "NICE CG109：短暂意识丧失（晕厥/黑蒙）评估与转诊",
        "publisher": "National Institute for Health and Care Excellence (NICE)",
        "url": "https://www.nice.org.uk/guidance/cg109/chapter/Recommendations",
    },
    "cdc_medicines": {
        "id": "CDC-STEADI-MEDS",
        "title": "CDC STEADI: Medications Linked to Falls",
        "title_zh": "CDC STEADI：与跌倒相关的药物",
        "publisher": "Centers for Disease Control and Prevention (CDC)",
        "url": "https://www.cdc.gov/steadi/media/pdfs/steadi-factsheet-medslinkedtofalls-508.pdf",
    },
    "cdc_home_safety": {
        "id": "CDC-STEADI-HOME-SAFETY",
        "title": "CDC STEADI: Check for Safety Home Fall Prevention Checklist",
        "title_zh": "CDC STEADI：居家防跌倒安全检查清单",
        "publisher": "Centers for Disease Control and Prevention (CDC)",
        "url": "https://stacks.cdc.gov/view/cdc/59197",
    },
    "ags_beers": {
        "id": "AGS-BEERS-2023",
        "title": "2023 AGS Beers Criteria for Potentially Inappropriate Medication Use",
        "title_zh": "2023 AGS Beers 标准：潜在不适当用药",
        "publisher": "American Geriatrics Society",
        "url": "https://doi.org/10.1111/jgs.18372",
    },
}

# The English ``action`` field is kept for existing clients.  ``action_zh`` is
# the caregiver-facing copy used by the redesigned detail view; each sentence
# names a concrete next step and defers measurements/medication changes to the
# facility protocol or a qualified clinician.
ACTION_ZH = {
    "syncopal_fall": "如果老人尚未倒下且感到晕厥，协助其坐下或躺下；如果已经跌倒或疑似受伤，不要自行搬动，按机构跌倒/急症流程立即通知护士或医生并记录经过。评估前不要让老人独自行走，请医生评估意识丧失的原因。",
    "fall_cluster_30d": "尽快通知护士或医生；记录每次跌倒的时间、活动、症状和受伤情况，并请求进行全面跌倒评估、更新护理计划。",
    "past_falls": "写下每次跌倒发生的情况并交给护士或医生；请求全面评估步态、平衡、血压、视力、认知、鞋具和用药。",
    "days_since_last_fall": "按近期跌倒处理：通知护士或医生，依机构跌倒后流程检查受伤情况并记录经过；护理计划复核前陪同老人转移。",
    "tug_seconds": "测试和转移时站在老人身旁，只使用护理计划指定的助行器；请物理治疗师或其他合资格人员评估步态，并制定个人化的力量与平衡训练计划。",
    "mobility_score": "按护理计划使用指定的助行器并陪同步行；请物理治疗或职业治疗人员评估步态、平衡、肌力和转移安全。",
    "high_risk_medication": "不要自行停药或改药；尽快把完整用药清单交给护士、药师或开药医生，请他们审核可能造成嗜睡、头晕、混乱或低血压的药物。",
    "polypharmacy_count": "把最新的处方药和非处方药清单交给护士或药师，请他们逐项进行用药审核；没有处方变更时不要自行漏服。",
    "orthostatic_hypotension": "老人头晕时先让其坐下或躺下，不要让其行走；协助其慢慢起身，按机构流程测量卧位和站立血压，并向护士或医生报告。",
    "cognitive_impairment": "遵循老人的个别护理计划，按计划的陪同程度协助转移和离床；保持通道清楚、照明充足，若出现新发混乱或异常嗜睡立即报告护士。",
    "night_bed_exits": "睡前确认呼叫铃、照明、安全鞋具和清楚的通道都可用；按护理计划陪同夜间转移、记录每次离床，并请护士评估如厕或排泄需要。",
    "night_activity_duration_min": "记录老人何时醒来及需要什么；检查通道、照明、疼痛和如厕需要，如变化新出现、反复发生或伴随混乱/头晕，告知护士。",
}


def _number(value):
    """Return a stable JSON-friendly number where possible."""
    try:
        number = float(value)
        if number != number:  # NaN
            return None
        return int(number) if number.is_integer() else round(number, 2)
    except (TypeError, ValueError):
        return value


def _feature_from_condition(condition: str) -> Optional[str]:
    """Extract an exact model feature token from a LIME condition string."""
    for feature in sorted(MODEL_FEATURES, key=len, reverse=True):
        if re.search(rf"(?<![A-Za-z0-9_]){re.escape(feature)}(?![A-Za-z0-9_])", condition):
            return feature
    return None


def _normalise_lime(lime_explanations) -> list[dict]:
    """Validate stored/caller-provided LIME data without trusting its shape."""
    if isinstance(lime_explanations, str):
        try:
            lime_explanations = json.loads(lime_explanations)
        except (TypeError, ValueError, json.JSONDecodeError):
            return []
    if not isinstance(lime_explanations, list):
        return []

    out = []
    for explanation in lime_explanations:
        if not isinstance(explanation, dict):
            continue
        condition = str(explanation.get("condition") or "").strip()
        feature = explanation.get("feature") or _feature_from_condition(condition)
        if feature not in MODEL_FEATURES:
            continue
        try:
            weight = float(explanation.get("weight", 0))
        except (TypeError, ValueError):
            continue
        if weight != weight:  # NaN
            continue
        out.append({
            "feature": feature,
            "condition": condition,
            "weight": round(weight, 4),
            "direction": str(explanation.get("direction") or ""),
        })
    return out


def _complete_lime_explanations(features: dict, lime_explanations=None) -> list[dict]:
    """Use all 14 LIME terms; transparently upgrade older rows that stored only 3."""
    supplied = _normalise_lime(lime_explanations)
    supplied_features = {entry["feature"] for entry in supplied}
    if len(supplied_features) == len(MODEL_FEATURES):
        return supplied
    try:
        generated = _normalise_lime(explain_patient(features, max_features=len(MODEL_FEATURES)))
        return generated or supplied
    except Exception:
        # Old/imported rows may be incomplete.  Returning the valid stored values
        # is safer than failing the assessment detail endpoint.
        return supplied


def _predicted_level(features: dict, predicted_level: Optional[str] = None) -> str:
    if predicted_level in ("LOW", "MEDIUM", "HIGH"):
        return predicted_level
    try:
        return predict_fall_risk(features)
    except Exception:
        return "UNKNOWN"


def _lime_by_feature(lime_explanations: list[dict]) -> dict[str, dict]:
    result = {}
    for explanation in _normalise_lime(lime_explanations):
        feature = explanation["feature"]
        if feature not in result or abs(explanation["weight"]) > abs(result[feature]["weight"]):
            result[feature] = explanation
    return result


def _display_value(feature: str, value, features: Optional[dict] = None):
    value = _number(value)
    if value is None:
        return "Not recorded"
    if feature in {"high_risk_medication", "orthostatic_hypotension", "syncopal_fall", "fall_cluster_30d"}:
        return "Yes" if value == 1 else "No"
    if feature == "sex":
        return "Female" if str(value).upper().startswith("F") else "Male"
    if feature == "cognitive_impairment":
        return {
            0: "None",
            1: "Mild",
            2: "Moderate-to-severe",
        }.get(value, value)
    if feature == "tug_seconds" and value is not None:
        return f"{value} seconds"
    if feature == "night_activity_duration_min" and value is not None:
        return f"{value} minutes"
    if feature == "days_since_last_fall":
        # Some legacy rows used 0 as the form's empty value.  Do not show that
        # as "0 days" when the resident has no fall history; zero is only a
        # meaningful day count when at least one fall is recorded.
        past_falls = _number((features or {}).get("past_falls", 0)) or 0
        if past_falls == 0:
            return "Not recorded"
        return f"{value} days"
    return value


def _caregiver_label(feature: str, label: str, value, features: Optional[dict] = None) -> str:
    """Add the observed value to a plain-language Chinese feature label."""
    base = FEATURE_LABELS_ZH.get(feature, label)
    shown = _display_value(feature, value, features)
    if shown in (None, "Not recorded", "—"):
        return base
    if feature == "cognitive_impairment":
        shown = {
            "None": "无",
            "Mild": "轻度",
            "Moderate-to-severe": "中重度",
        }.get(shown, shown)
    if isinstance(shown, str):
        shown = (
            shown.replace("seconds", "秒")
            .replace("minutes", "分钟")
            .replace("days", "天")
            .replace("Yes", "是")
            .replace("No", "否")
        )
    return f"{base}（当前：{shown}）"


def _is_elevated_feature(feature: str, value, features: Optional[dict] = None) -> bool:
    """Whether the observed value is clinically actionable in this model.

    These are deliberately broad screening flags, not diagnoses or new risk
    cut-offs.  They let the caregiver card distinguish an observed risk signal
    from a demographic/protective LIME term (for example ``syncopal_fall=0``).
    """
    number = _number(value)
    if feature in {"high_risk_medication", "orthostatic_hypotension", "syncopal_fall", "fall_cluster_30d"}:
        return number == 1
    if feature == "age":
        return isinstance(number, (int, float)) and number >= 75
    if feature == "night_bed_exits":
        return isinstance(number, (int, float)) and number >= 2
    if feature == "night_activity_duration_min":
        return isinstance(number, (int, float)) and number > 30
    if feature == "past_falls":
        return isinstance(number, (int, float)) and number >= 1
    if feature == "mobility_score":
        return isinstance(number, (int, float)) and number <= 4
    if feature == "cognitive_impairment":
        return isinstance(number, (int, float)) and number >= 1
    if feature == "polypharmacy_count":
        return isinstance(number, (int, float)) and number >= 4
    if feature == "tug_seconds":
        return isinstance(number, (int, float)) and number >= 12
    if feature == "days_since_last_fall":
        past_falls = _number((features or {}).get("past_falls", 0)) or 0
        return isinstance(number, (int, float)) and past_falls >= 1 and 0 <= number < 30
    return False


def build_risk_drivers(
    features: dict,
    lime_explanations=None,
    predicted_level: Optional[str] = None,
) -> list[dict]:
    """Turn technical LIME terms into a caregiver-readable ranked driver list.

    LIME explains the class requested by the model, not a medical diagnosis.
    For HIGH and LOW results we can orient the sign toward/away from the
    predicted risk class.  For MEDIUM results we explicitly say “supports” or
    “away from” the current class because a negative term could point toward
    either LOW or HIGH.  The raw signed weight and condition stay available
    for auditability.
    """
    level = _predicted_level(features, predicted_level)
    explanations = _complete_lime_explanations(features, lime_explanations)
    drivers = []
    for explanation in explanations:
        weight = explanation["weight"]
        # LIME is explained for the predicted class.  For LOW predictions a
        # negative term pulls away from LOW and is therefore the risk-oriented
        # direction.  MEDIUM is intentionally described as current-class
        # support/away rather than as a monotonic increase/decrease in risk.
        risk_weight = -weight if level == "LOW" else weight
        if risk_weight > 0:
            impact = "risk"
        elif risk_weight < 0:
            impact = "protective"
        else:
            impact = "neutral"
        if weight == 0:
            model_effect = "neutral"
            model_effect_zh = "影响很小"
        elif level == "MEDIUM":
            model_effect = "supports_current_level" if weight > 0 else "away_from_current_level"
            model_effect_zh = "支持当前中风险分级" if weight > 0 else "远离当前中风险分级（不等于更高或更低）"
        else:
            model_effect = "risk_direction" if risk_weight > 0 else "protective_direction"
            model_effect_zh = "推高当前分级" if risk_weight > 0 else "拉离当前分级"
        elevated = _is_elevated_feature(
            explanation["feature"], features.get(explanation["feature"]), features
        )
        drivers.append({
            "feature": explanation["feature"],
            "label": FEATURE_LABELS[explanation["feature"]],
            "label_zh": FEATURE_LABELS_ZH[explanation["feature"]],
            "value": _display_value(
                explanation["feature"],
                features.get(explanation["feature"]),
                features,
            ),
            "condition": explanation["condition"],
            "weight": weight,
            "lime_weight": weight,
            "risk_weight": round(risk_weight, 4),
            "direction": explanation["direction"],
            "model_effect": model_effect,
            "model_effect_zh": model_effect_zh,
            "impact": impact,
            "risk_signal": "elevated" if elevated else "not_elevated",
            "is_elevated": elevated,
            "attention_rule_zh": ATTENTION_RULES_ZH.get(explanation["feature"]),
            "lime_available": True,
            "score": round(abs(weight), 4),
        })

    # Rank by the local LIME magnitude first.  The observed-value attention
    # flag is displayed separately, so a project screening rule cannot silently
    # override the contribution-based ordering requested by the caregiver.
    drivers.sort(key=lambda item: (
        item["impact"] != "risk",
        -item["score"],
        not item["is_elevated"],
        item["feature"],
    ))
    risk_scores = [item["score"] for item in drivers if item["impact"] == "risk"]
    max_risk_score = max(risk_scores, default=0)
    for rank, item in enumerate(drivers, 1):
        item["rank"] = rank
        if item["impact"] == "risk" and max_risk_score > 0:
            ratio = item["score"] / max_risk_score
            item["lime_priority"] = 1 if ratio >= 0.67 else 2 if ratio >= 0.33 else 3
        else:
            item["lime_priority"] = None
    return drivers


def _suggest_60_74(
    features: dict,
    lime_explanations=None,
    predicted_level: Optional[str] = None,
) -> list[dict]:
    """Create practical care steps, then rank them by LIME contribution."""
    explanations = _complete_lime_explanations(features, lime_explanations)
    level = _predicted_level(features, predicted_level)
    lime_map = _lime_by_feature(explanations)
    items = []

    def add(feature: str, label: str, action: str, reference_keys: list[str]):
        explanation = lime_map.get(feature, {})
        lime_available = feature in lime_map
        raw_weight = float(explanation.get("weight", 0)) if lime_available else 0.0
        # Positive supports HIGH/MEDIUM; negative pulls away from LOW.  The
        # absolute value is used for priority; the direction is shown only as
        # model context so it cannot be mistaken for a clinical diagnosis.
        risk_weight = -raw_weight if level == "LOW" else raw_weight
        # AGS Beers is intended for adults 65+; do not present it as an
        # unconditional source for the 60-64 part of this age band.
        age = _number(features.get("age"))
        usable_reference_keys = [
            key for key in reference_keys
            if not (key == "ags_beers" and isinstance(age, (int, float)) and age < 65)
        ]
        references = [dict(REFERENCE_LIBRARY[key]) for key in usable_reference_keys]
        if level == "MEDIUM":
            model_effect_zh = (
                "支持当前中风险分级" if raw_weight > 0
                else "远离当前中风险分级（不等于更高或更低）" if raw_weight < 0
                else "影响很小"
            )
            risk_direction = (
                "supports current level" if raw_weight > 0
                else "away from current level" if raw_weight < 0
                else "neutral"
            )
        else:
            model_effect_zh = (
                "推高当前分级" if risk_weight > 0
                else "拉离当前分级" if risk_weight < 0
                else "影响很小"
            )
            risk_direction = (
                "increases current risk class" if risk_weight > 0
                else "pulls away from current risk class" if risk_weight < 0
                else "neutral"
            )
        items.append({
            "feature": feature,
            "label": label,
            "label_zh": _caregiver_label(feature, label, features.get(feature), features),
            "value": _display_value(feature, features.get(feature), features),
            "action": action,
            "action_zh": ACTION_ZH.get(feature, action),
            "weight": round(raw_weight, 4),
            "lime_weight": round(raw_weight, 4),
            "risk_weight": round(risk_weight, 4),
            "risk_direction": risk_direction,
            "model_effect_zh": model_effect_zh,
            "direction": explanation.get("direction", "not available"),
            "condition": explanation.get("condition", ""),
            "reference": references[0] if references else None,
            "references": references,
            "reference_title": references[0]["title"] if references else None,
            "reference_title_zh": references[0].get("title_zh", references[0]["title"]) if references else None,
            "reference_url": references[0]["url"] if references else None,
            "attention_rule_zh": ATTENTION_RULES_ZH.get(feature),
            "lime_available": lime_available,
            "priority_basis": "lime_absolute_contribution" if lime_available else "clinical_attention_without_lime",
            "clinical_override": (not lime_available) or risk_weight <= 0,
            # These are care-process flags, not diagnoses or a replacement for
            # the facility's clinical urgency policy.
            "clinical_attention": feature in {"syncopal_fall", "fall_cluster_30d", "days_since_last_fall"},
            "_score": abs(raw_weight),
        })

    past_falls = _number(features.get("past_falls", 0)) or 0
    tug = _number(features.get("tug_seconds"))
    mobility = _number(features.get("mobility_score"))
    cognitive = _number(features.get("cognitive_impairment", 0)) or 0
    night_activity = _number(features.get("night_activity_duration_min"))
    bed_exits = _number(features.get("night_bed_exits"))
    days_since_fall = _number(features.get("days_since_last_fall"))
    medicine_count = _number(features.get("polypharmacy_count"))

    if _number(features.get("syncopal_fall")) == 1:
        add(
            "syncopal_fall",
            "Fall with loss of consciousness recorded",
            "If the resident feels faint before falling, help them sit or lie down; if they have fallen or may be injured, do not move them yourself. Follow the facility fall/emergency protocol, notify the nurse or clinician immediately, document what happened, and ask the clinician to review the loss of consciousness.",
            ["nice_tloc", "nice_falls"],
        )
    if _number(features.get("fall_cluster_30d")) == 1:
        add(
            "fall_cluster_30d",
            "Two or more falls within 30 days",
            "Notify the nurse or clinician promptly. Record the time, activity, symptoms and injuries for each fall, and request a comprehensive falls assessment plus an updated care plan.",
            ["nice_falls", "cdc_care_plan"],
        )
    if isinstance(past_falls, (int, float)) and past_falls >= 1:
        add(
            "past_falls",
            f"{past_falls} fall{'s' if past_falls != 1 else ''} in the past year",
            "Write down the circumstances of each fall and give the record to the nurse or clinician. Request a comprehensive assessment of gait, balance, blood pressure, vision, cognition, footwear and medicines.",
            ["nice_falls", "cdc_care_plan"],
        )
    if (
        isinstance(days_since_fall, (int, float))
        and past_falls >= 1
        and 0 <= days_since_fall < 30
    ):
        add(
            "days_since_last_fall",
            f"Most recent fall was {days_since_fall} day{'s' if days_since_fall != 1 else ''} ago",
            "Treat this as a recent fall: notify the nurse or clinician, check for injury using the facility's post-fall protocol, document the circumstances, and accompany transfers until the care plan is reviewed.",
            ["nice_falls"],
        )
    if isinstance(tug, (int, float)) and tug >= 12:
        add(
            "tug_seconds",
            f"TUG took {tug} seconds (CDC fall-risk threshold: 12 seconds or more)",
            "Stay beside the resident during the test and transfers, and use only their prescribed walking aid. Ask a physiotherapist or other qualified professional to assess gait and prescribe an individual strength-and-balance plan.",
            ["cdc_tug", "cdc_care_plan"],
        )
    if isinstance(mobility, (int, float)) and mobility <= 4:
        add(
            "mobility_score",
            f"Mobility score is {mobility}/10",
            "Use the resident's prescribed mobility aid and supervise walking according to the care plan. Ask physiotherapy or occupational therapy to assess gait, balance, strength and transfer safety.",
            ["nice_falls", "cdc_care_plan"],
        )
    if _number(features.get("high_risk_medication")) == 1:
        add(
            "high_risk_medication",
            "A medicine linked to falls is recorded",
            "Do not stop or change any medicine yourself. Give the complete medication list promptly to the nurse, pharmacist or prescriber and request a structured review for medicines that can cause drowsiness, dizziness, confusion or low blood pressure.",
            ["cdc_medicines", "ags_beers"],
        )
    if isinstance(medicine_count, (int, float)) and medicine_count >= 4:
        add(
            "polypharmacy_count",
            f"{medicine_count} medicines are recorded",
            "Give a complete, up-to-date medication list to the nurse or pharmacist and request a structured review of every prescription and over-the-counter medicine. Do not omit doses unless the prescriber changes the order.",
            ["cdc_care_plan", "ags_beers"],
        )
    if _number(features.get("orthostatic_hypotension")) == 1:
        add(
            "orthostatic_hypotension",
            "Postural hypotension is recorded",
            "If the resident feels dizzy, have them sit or lie down and do not let them walk. Help them rise slowly, measure lying and standing blood pressure using the facility protocol, and report symptoms to the nurse or clinician.",
            ["cdc_postural", "nice_falls"],
        )
    if isinstance(cognitive, (int, float)) and cognitive >= 1:
        severity = "moderate-to-severe" if cognitive >= 2 else "mild"
        add(
            "cognitive_impairment",
            f"{severity.title()} cognitive impairment is recorded",
            "Follow the resident's individual care plan, supervise transfers and bed exits at the specified level, keep the route clear and well lit, and report any new confusion or unusual drowsiness to the nurse.",
            ["nice_falls"],
        )
    if isinstance(bed_exits, (int, float)) and bed_exits >= 2:
        add(
            "night_bed_exits",
            f"{bed_exits} night-time bed exits are recorded",
            "Before bedtime, check that the call bell, lighting, secure footwear and a clear route are available. Follow the care plan for assisted night transfers, record each exit, and ask the nurse to review toileting or continence needs.",
            ["nice_falls", "cdc_care_plan", "cdc_home_safety"],
        )
    if isinstance(night_activity, (int, float)) and night_activity > 30:
        add(
            "night_activity_duration_min",
            f"Night-time activity lasted {night_activity} minutes",
            "Record when the resident wakes and what they need. Check the route, lighting, pain and toileting needs, and tell the nurse if the change is new, repeated or accompanied by confusion or dizziness.",
            ["nice_falls", "cdc_care_plan"],
        )

    if not items:
        return []

    max_score = max(item["_score"] for item in items)
    for item in items:
        if item["lime_available"] and max_score > 0:
            ratio = item["_score"] / max_score
            priority = 1 if ratio >= 0.67 else 2 if ratio >= 0.33 else 3
            item["priority"] = priority
            item["priority_label"] = SUGGESTION_PRIORITIES[priority]
            item["priority_level"] = item["priority_label"]
            item["priority_name"] = item["priority_label"].lower()
        else:
            # A missing/invalid local explanation is a data-quality state, not
            # evidence for a low-contribution bucket.  The UI renders these
            # items in a separate unranked section.
            item["priority"] = None
            item["priority_label"] = None
            item["priority_level"] = None
            item["priority_name"] = None
        item.pop("_score", None)

    items.sort(key=lambda item: (
        item["priority"] if isinstance(item["priority"], int) else 4,
        -abs(item["weight"]),
        item["feature"],
    ))
    # Keep urgent care-process flags visible even when many non-urgent inputs
    # match the screening rules.  This selection is a safety exception, not a
    # change to their LIME priority; the UI labels these items separately.
    if len(items) > 8:
        urgent = [item for item in items if item["clinical_attention"]]
        other = [item for item in items if not item["clinical_attention"]]
        keep = urgent + other[: max(0, 8 - len(urgent))]
        keep_ids = {id(item) for item in keep}
        items = [item for item in items if id(item) in keep_ids]
    return items


def build_suggestions(
    features: dict,
    lime_explanations=None,
    predicted_level: Optional[str] = None,
) -> dict:
    """Return 60-74 actions; explicitly mark 75-100 as not suggested."""
    age = _number(features.get("age"))
    basis = (
        "Priority is based on each actionable feature's absolute LIME contribution "
        "relative to the strongest actionable feature in this assessment: "
        "High >= 67%, Medium >= 33%, Low < 33%. It is not a clinical urgency score. "
        "Syncope, recent-fall and repeated-fall safety flags are retained even when their contribution is lower."
    )
    basis_zh = (
        "优先级按本次评估中各可执行特征的 |LIME 权重| 相对最大值分档："
        "高 ≥ 67%、中 ≥ 33%、低 < 33%；这不是医疗紧急程度。"
        "晕厥、近期跌倒和连续跌倒等临床安全提示即使贡献较低也会保留，不能因分档较低而跳过。"
    )
    is_not_suggested_75_100 = isinstance(age, (int, float)) and 75 <= age <= 100
    if not isinstance(age, (int, float)) or not (60 <= age <= 74):
        reason = (
            "Not suggested for residents aged 75-100; this page only provides "
            "caregiver guidance for ages 60-74."
            if is_not_suggested_75_100
            else "Caregiver suggestions are currently configured for residents aged 60-74."
        )
        reason_zh = (
            "75–100 岁：不建议使用本页个性化建议；本页只提供 60–74 岁的护理行动。"
            if is_not_suggested_75_100
            else "本页护理建议目前只适用于 60–74 岁。"
        )
        return {
            "band": None,
            "not_suggestion": True,
            "suggestion_status": "not_suggested",
            "not_suggestion_age_band": "75-100" if is_not_suggested_75_100 else None,
            "items": [],
            "priority_basis": basis,
            "priority_basis_zh": basis_zh,
            "references": [],
            "reason": reason,
            "reason_zh": reason_zh,
        }

    explanations = _complete_lime_explanations(features, lime_explanations)
    items = _suggest_60_74(features, explanations, predicted_level)
    references = []
    seen = set()
    for item in items:
        for reference in item.get("references", []):
            if reference["id"] not in seen:
                references.append(reference)
                seen.add(reference["id"])
    return {
        "band": "60-74",
        "not_suggestion": False,
        "suggestion_status": "suggested",
        "not_suggestion_age_band": None,
        "items": items,
        "priority_basis": basis,
        "priority_basis_zh": basis_zh,
        "references": references,
    }


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
        # Keep all model terms so the caregiver detail view can identify the
        # strongest risk-increasing features, not just the first three terms.
        lime_explanations = explain_patient(features_dict, max_features=len(MODEL_FEATURES))
        suggestion = build_suggestions(
            features_dict,
            lime_explanations=lime_explanations,
            predicted_level=result,
        )
        risk_drivers = build_risk_drivers(
            features_dict,
            lime_explanations=lime_explanations,
            predicted_level=result,
        )

        # Save feature profile & prediction output to database
        db_record = PatientRecord(
            sex=features_dict.get("sex"),
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
            days_since_last_fall=features_dict.get("days_since_last_fall"),
            syncopal_fall=features_dict.get("syncopal_fall", 0),
            fall_cluster_30d=features_dict.get("fall_cluster_30d", 0),
            fall_risk_level=result,
            resident_id=features_dict.get("resident_id"),
            lime_explanations=json.dumps(lime_explanations),
        )
        db.add(db_record)
        await db.commit()
        
        # Return the exact JSON structure your friend asked for
        return {
            "id": db_record.id,
            "fall_risk_level": result,
            "lime_explanations": lime_explanations,
            "suggestion": suggestion,
            # Alias kept for clients that use the plural spelling.
            "suggestions": suggestion,
            "risk_drivers": risk_drivers,
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")
    
# ---------- Assessment query endpoints (for the front-end dashboard) ----------

def _record_to_dict(record: PatientRecord) -> dict:
    """Convert a PatientRecord row into a JSON-friendly dict."""
    data_quality = []
    no_fall_history = (record.past_falls or 0) == 0
    days_since_last_fall = None if no_fall_history and record.days_since_last_fall == 0 else record.days_since_last_fall
    if no_fall_history and record.days_since_last_fall == 0:
        data_quality.append({
            "field": "days_since_last_fall",
            "message": "没有记录过跌倒；原始资料中的“0 天”按“未记录”显示。",
            "message_en": "No fall history is recorded; the original 0-day value is displayed as Not recorded.",
        })
    features = {
        "sex": record.sex,
        "age": record.age,
        "night_bed_exits": record.night_bed_exits,
        "night_activity_duration_min": record.night_activity_duration_min,
        "past_falls": record.past_falls,
        "mobility_score": record.mobility_score,
        "high_risk_medication": record.high_risk_medication,
        "cognitive_impairment": record.cognitive_impairment,
        "polypharmacy_count": record.polypharmacy_count,
        "orthostatic_hypotension": record.orthostatic_hypotension,
        "tug_seconds": record.tug_seconds,
        "days_since_last_fall": days_since_last_fall,
        "syncopal_fall": record.syncopal_fall or 0,
        "fall_cluster_30d": record.fall_cluster_30d or 0,
    }
    # Rows created before the all-terms change contain only three LIME terms.
    # Upgrade them on read so the detail card and the priority calculation use
    # the same complete explanation without changing the stored user data.
    lime_explanations = _complete_lime_explanations(features, record.lime_explanations)
    suggestion = build_suggestions(
        features,
        lime_explanations=lime_explanations,
        predicted_level=record.fall_risk_level,
    )
    risk_drivers = build_risk_drivers(
        features,
        lime_explanations=lime_explanations,
        predicted_level=record.fall_risk_level,
    )
    return {
        "id": record.id,
        "sex": record.sex,
        "age": record.age,
        "night_bed_exits": record.night_bed_exits,
        "night_activity_duration_min": record.night_activity_duration_min,
        "past_falls": record.past_falls,
        "mobility_score": record.mobility_score,
        "high_risk_medication": record.high_risk_medication,
        "cognitive_impairment": record.cognitive_impairment,
        "polypharmacy_count": record.polypharmacy_count,
        "orthostatic_hypotension": record.orthostatic_hypotension,
        "tug_seconds": record.tug_seconds,
        "days_since_last_fall": days_since_last_fall,
        "syncopal_fall": record.syncopal_fall,
        "fall_cluster_30d": record.fall_cluster_30d,
        "fall_risk_level": record.fall_risk_level,
        "resident_id": record.resident_id,
        "lime_explanations": lime_explanations,
        "suggestion": suggestion,
        "suggestions": suggestion,
        "risk_drivers": risk_drivers,
        "data_quality": data_quality,
        "created_at": record.created_at.isoformat() if record.created_at else None,
    }


def _format_dt(iso_str):
    if not iso_str:
        return "Not recorded"
    try:
        return datetime.fromisoformat(iso_str).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return iso_str


_PDF_FONT_READY = False
_PDF_FONT_NAME = "Helvetica"
_PDF_FONT_BOLD_NAME = "Helvetica-Bold"


def _ensure_pdf_fonts():
    """Register a CJK-capable font pair once and return the regular face.

    The API normally runs on Windows, but the same code is also used in Linux
    containers during deployment and tests.  Keep the font lookup local to this
    helper so a missing optional host font never prevents an assessment from
    downloading.  ``STSong-Light`` is ReportLab's portable CID fallback.
    """
    global _PDF_FONT_READY, _PDF_FONT_NAME, _PDF_FONT_BOLD_NAME
    if _PDF_FONT_READY:
        return _PDF_FONT_NAME

    windows_fonts = os.path.join(os.environ.get("WINDIR", r"C:\\Windows"), "Fonts")
    # Prefer static Microsoft faces on Windows.  The bold files are separate
    # TTCs; using them gives the title and table headers a real weight instead
    # of asking ReportLab to synthesize one.
    candidates = [
        (
            os.environ.get("SAFE_STRIDE_PDF_FONT"),
            os.environ.get("SAFE_STRIDE_PDF_BOLD_FONT"),
            0,
            0,
        ),
        (
            os.path.join(windows_fonts, "msyh.ttc"),
            os.path.join(windows_fonts, "msyhbd.ttc"),
            0,
            0,
        ),
        (
            os.path.join(windows_fonts, "msjh.ttc"),
            os.path.join(windows_fonts, "msjhbd.ttc"),
            0,
            0,
        ),
        (r"C:\Windows\Fonts\NotoSansTC-VF.ttf", r"C:\Windows\Fonts\NotoSansTC-VF.ttf", 0, 0),
        (r"C:\Windows\Fonts\NotoSansHK-VF.ttf", r"C:\Windows\Fonts\NotoSansHK-VF.ttf", 0, 0),
        ("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc", 0, 0),
        ("/usr/share/fonts/opentype/noto/NotoSansSC-Regular.otf", "/usr/share/fonts/opentype/noto/NotoSansSC-Bold.otf", 0, 0),
        ("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc", "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc", 0, 0),
    ]
    for path, bold_path, regular_index, bold_index in candidates:
        if not path or not os.path.exists(path):
            continue
        try:
            regular_name = "SafeStrideCJK"
            bold_name = "SafeStrideCJK-Bold"
            pdfmetrics.registerFont(TTFont(regular_name, path, subfontIndex=regular_index))
            if bold_path and os.path.exists(bold_path):
                pdfmetrics.registerFont(TTFont(bold_name, bold_path, subfontIndex=bold_index))
            else:
                bold_name = regular_name
            pdfmetrics.registerFontFamily(
                regular_name,
                normal=regular_name,
                bold=bold_name,
                italic=regular_name,
                boldItalic=bold_name,
            )
            _PDF_FONT_READY = True
            _PDF_FONT_NAME = regular_name
            _PDF_FONT_BOLD_NAME = bold_name
            return regular_name
        except Exception:
            # A malformed/unsupported TTC should not block the next candidate.
            continue
    # STSong-Light is a PDF CID font shipped with ReportLab and is a robust
    # cross-platform fallback when no host CJK font is present.
    try:
        pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
        pdfmetrics.registerFontFamily(
            "STSong-Light",
            normal="STSong-Light",
            bold="STSong-Light",
            italic="STSong-Light",
            boldItalic="STSong-Light",
        )
        _PDF_FONT_READY = True
        _PDF_FONT_NAME = "STSong-Light"
        _PDF_FONT_BOLD_NAME = "STSong-Light"
        return "STSong-Light"
    except Exception:
        _PDF_FONT_NAME = "Helvetica"
        _PDF_FONT_BOLD_NAME = "Helvetica-Bold"
        return "Helvetica"


def _pdf_text(value, default="Not recorded"):
    """Safely convert values to ReportLab Paragraph text."""
    if value is None or value == "":
        value = default
    return _xml_escape(str(value)).replace("\n", "<br/>")


def _pdf_number(value, default="Not recorded"):
    """Format numeric values without noisy trailing ``.0`` in the report."""
    if value is None or value == "":
        return default
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if not math.isfinite(number):
        return default
    return str(int(number)) if number.is_integer() else f"{number:.2f}".rstrip("0").rstrip(".")


def _pdf_bool(value) -> str:
    """Render a stored binary field as a stable English Yes/No value."""
    if value is None or value == "":
        return "Not recorded"
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"", "none", "null", "not recorded", "unknown"}:
            return "Not recorded"
        return "Yes" if normalized in {"1", "true", "yes", "y"} else "No"
    try:
        return "Yes" if int(value or 0) == 1 else "No"
    except (TypeError, ValueError):
        return "Yes" if bool(value) else "No"


def _pdf_measure(value, unit: str) -> str:
    """Append a unit without producing strings such as ``Not recorded years``."""
    formatted = _pdf_number(value)
    return formatted if formatted == "Not recorded" else f"{formatted} {unit}"


def _pdf_english(value, fallback: str) -> str:
    """Use caller-provided copy only when it is non-empty and not CJK text."""
    text = str(value or "").strip()
    if not text or re.search(r"[\u3400-\u9fff]", text):
        return fallback
    return text


def generate_assessment_pdf(record: dict) -> bytes:
    """Generate the caregiver-facing English assessment PDF.

    The downloadable copy is deliberately limited to resident information,
    the assessment result, and plain-language care recommendations.  Model
    explanations, weights, thresholds, references, and other implementation
    metadata stay in the API and are never rendered here.
    """
    if not isinstance(record, dict):
        record = {}
    font_name = _ensure_pdf_fonts()
    safe_resident_id = _pdf_english(
        record.get("resident_id") or record.get("id"),
        "Not recorded",
    )
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        title=f"Fall Risk Assessment - {safe_resident_id}",
        leftMargin=1.55 * cm,
        rightMargin=1.55 * cm,
        topMargin=2.1 * cm,
        bottomMargin=1.6 * cm,
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="PdfTitle", parent=styles["Title"], fontName=_PDF_FONT_BOLD_NAME,
        fontSize=21, leading=25, textColor=colors.HexColor("#102A43"),
        spaceAfter=3, alignment=0, wordWrap="LTR", splitLongWords=1,
    ))
    styles.add(ParagraphStyle(
        name="PdfSubtitle", parent=styles["Normal"], fontName=font_name,
        fontSize=9.5, leading=13, textColor=colors.HexColor("#627D98"),
        wordWrap="LTR", splitLongWords=1,
    ))
    styles.add(ParagraphStyle(
        name="PdfSection", parent=styles["Heading2"], fontName=font_name,
        fontSize=12.5, leading=16, textColor=colors.HexColor("#102A43"),
        spaceBefore=10, spaceAfter=6, wordWrap="LTR", splitLongWords=1,
    ))
    styles.add(ParagraphStyle(
        name="PdfBody", parent=styles["BodyText"], fontName=font_name,
        fontSize=9.2, leading=13, textColor=colors.HexColor("#243B53"),
        wordWrap="LTR", splitLongWords=1,
    ))
    styles.add(ParagraphStyle(
        name="PdfSmall", parent=styles["BodyText"], fontName=font_name,
        fontSize=7.6, leading=10, textColor=colors.HexColor("#627D98"),
        wordWrap="LTR", splitLongWords=1,
    ))
    styles.add(ParagraphStyle(
        name="PdfCell", parent=styles["BodyText"], fontName=font_name,
        fontSize=8.6, leading=11.5, textColor=colors.HexColor("#243B53"),
        wordWrap="LTR", splitLongWords=1,
    ))
    styles.add(ParagraphStyle(
        name="PdfCellBold", parent=styles["BodyText"], fontName=_PDF_FONT_BOLD_NAME,
        fontSize=8.6, leading=11.5, textColor=colors.HexColor("#102A43"),
        wordWrap="LTR", splitLongWords=1,
    ))
    styles.add(ParagraphStyle(
        name="PdfRisk", parent=styles["BodyText"], fontName=font_name,
        fontSize=11, leading=22, textColor=colors.white, alignment=1,
        wordWrap="LTR", splitLongWords=1,
    ))
    styles.add(ParagraphStyle(
        name="PdfHeaderCell", parent=styles["BodyText"], fontName=font_name,
        fontSize=8.6, leading=11.5, textColor=colors.white,
        wordWrap="LTR", splitLongWords=1,
    ))
    body = []

    content_width = A4[0] - doc.leftMargin - doc.rightMargin
    resident_id = safe_resident_id
    body.append(Paragraph("Fall Risk Assessment Report", styles["PdfTitle"]))
    body.append(Paragraph("CARE HANDOVER COPY | PRINTABLE SUMMARY", styles["PdfSubtitle"]))
    body.append(Spacer(1, 0.25 * cm))

    risk_level = str(record.get("fall_risk_level") or "").strip().upper()
    risk_label = {
        "HIGH": "HIGH RISK",
        "MEDIUM": "MEDIUM RISK",
        "LOW": "LOW RISK",
    }.get(risk_level, "RISK NOT CLASSIFIED")
    risk_color = {
        "HIGH": colors.HexColor("#D64545"),
        "MEDIUM": colors.HexColor("#D9822B"),
        "LOW": colors.HexColor("#2F9E72"),
    }.get(risk_level, colors.HexColor("#627D98"))
    banner = Table(
        [[Paragraph(
            f"<font size='8.5'>CURRENT FALL RISK</font><br/><font size='18'><b>{_pdf_text(risk_label)}</b></font>",
            styles["PdfRisk"],
        )]],
        colWidths=[content_width],
        hAlign="LEFT",
    )
    banner.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), risk_color),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.white),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
        ("ROUNDEDCORNERS", [8, 8, 8, 8]),
    ]))
    body.append(banner)
    body.append(Spacer(1, 0.2 * cm))

    def cell(value, bold=False, right=False):
        style_name = "PdfCellBold" if bold else "PdfCell"
        if right:
            value = f"<para align='right'>{_pdf_text(value)}</para>"
            return Paragraph(value, styles[style_name])
        return Paragraph(_pdf_text(value), styles[style_name])

    # Identity metadata is kept separate from the 14 assessment inputs.
    metadata = Table([
        [cell("Resident ID", True), cell(resident_id, False, True),
         cell("Assessed at", True), cell(_pdf_english(_format_dt(record.get("created_at")), "Not recorded"), False, True)],
    ], colWidths=[2.5 * cm, 4.0 * cm, 2.8 * cm, content_width - 9.3 * cm], hAlign="LEFT")
    metadata.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F7F9FC")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#D9E2EC")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    body.append(metadata)
    body.append(Spacer(1, 0.22 * cm))

    body.append(Paragraph("Resident profile", styles["PdfSection"]))
    body.append(Paragraph("14 inputs used by this model", styles["PdfSmall"]))
    body.append(Spacer(1, 0.08 * cm))

    sex_raw = str(record.get("sex") or "").strip().upper()
    sex_value = {"M": "Male", "F": "Female", "MALE": "Male", "FEMALE": "Female"}.get(
        sex_raw,
        _pdf_english(record.get("sex"), "Not recorded"),
    )
    cognitive_raw = record.get("cognitive_impairment")
    cognitive_num = _pdf_number(cognitive_raw)
    cognitive_value = {
        "0": "None",
        "1": "Mild",
        "2": "Moderate",
        "3": "Severe",
    }.get(cognitive_num, _pdf_english(cognitive_raw, "Not recorded"))

    days_value = record.get("days_since_last_fall")
    try:
        past_falls_number = float(record.get("past_falls"))
    except (TypeError, ValueError):
        past_falls_number = 0
    if not math.isfinite(past_falls_number):
        past_falls_number = 0
    try:
        days_number = float(days_value) if days_value not in (None, "") else None
    except (TypeError, ValueError):
        days_number = None
    if days_number is not None and not math.isfinite(days_number):
        days_number = None
    if days_number is None or (past_falls_number == 0 and days_number == 0):
        days_since_value = "Not recorded"
    else:
        day_number = days_number
        if day_number == 0:
            days_since_value = "Today"
        elif day_number == 1:
            days_since_value = "1 day"
        elif day_number.is_integer():
            days_since_value = f"{int(day_number)} days"
        else:
            days_since_value = f"{day_number:g} days"

    profile_rows = [
        [Paragraph("INPUT", styles["PdfHeaderCell"]), Paragraph("VALUE", styles["PdfHeaderCell"])],
        [cell("Age"), cell(_pdf_measure(record.get("age"), "years"), right=True)],
        [cell("Sex"), cell(sex_value, right=True)],
        [cell("Night-time bed exits"), cell(_pdf_measure(record.get("night_bed_exits"), "per night"), right=True)],
        [cell("Night-time activity duration"), cell(_pdf_measure(record.get("night_activity_duration_min"), "minutes"), right=True)],
        [cell("Falls in the past year"), cell(_pdf_measure(record.get("past_falls"), "falls"), right=True)],
        [cell("Mobility score"), cell(
            f"{_pdf_number(record.get('mobility_score'))} / 10" if _pdf_number(record.get("mobility_score")) != "Not recorded" else "Not recorded",
            right=True,
        )],
        [cell("Medicine linked to falls"), cell(_pdf_bool(record.get("high_risk_medication")), right=True)],
        [cell("Cognitive impairment"), cell(cognitive_value, right=True)],
        [cell("Number of medicines"), cell(_pdf_measure(record.get("polypharmacy_count"), "medicines"), right=True)],
        [cell("Postural hypotension"), cell(_pdf_bool(record.get("orthostatic_hypotension")), right=True)],
        [cell("Timed Up & Go (TUG)"), cell(_pdf_measure(record.get("tug_seconds"), "seconds"), right=True)],
        [cell("Time since the last fall"), cell(days_since_value, right=True)],
        [cell("Fall with loss of consciousness"), cell(_pdf_bool(record.get("syncopal_fall")), right=True)],
        [cell("Two or more falls within 30 days"), cell(_pdf_bool(record.get("fall_cluster_30d")), right=True)],
    ]
    profile_table = Table(profile_rows, colWidths=[11.5 * cm, content_width - 11.5 * cm], repeatRows=1, hAlign="LEFT")
    profile_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#243B53")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("LINEBELOW", (0, 1), (-1, -1), 0.35, colors.HexColor("#D9E2EC")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7F9FC")]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    body.append(profile_table)
    body.append(Spacer(1, 0.25 * cm))

    # Suggestions are age-gated from the numeric resident age, rather than
    # trusting a payload flag.  This prevents injected actions appearing for
    # residents aged 75-100.
    suggestion = record.get("suggestion") or record.get("suggestions") or {}
    if isinstance(suggestion, str):
        try:
            suggestion = json.loads(suggestion)
        except (TypeError, ValueError, json.JSONDecodeError):
            suggestion = {}
    actions = suggestion.get("items", []) if isinstance(suggestion, dict) else []
    actions = [item for item in actions if isinstance(item, dict)] if isinstance(actions, list) else []
    try:
        age_number = float(record.get("age"))
        if age_number != age_number:
            age_number = None
    except (TypeError, ValueError):
        age_number = None
    suggestions_supported = age_number is not None and 60 <= age_number <= 74
    suggestions_not_available = age_number is not None and 75 <= age_number <= 100
    action_topics = {
        "syncopal_fall": "Loss of consciousness and falls",
        "fall_cluster_30d": "Repeated falls",
        "past_falls": "Fall follow-up",
        "days_since_last_fall": "Recent fall care",
        "tug_seconds": "Transfers and walking",
        "mobility_score": "Transfers and walking",
        "high_risk_medication": "Medication review",
        "polypharmacy_count": "Medication review",
        "orthostatic_hypotension": "Dizziness and standing",
        "cognitive_impairment": "Cognition and environment",
        "night_bed_exits": "Night-time safety",
        "night_activity_duration_min": "Night-time safety",
    }
    fallback_action = "Review this concern with the nurse or clinician and follow the resident's care plan."

    recommendation_heading = Paragraph("Care recommendations", styles["PdfSection"])
    if suggestions_not_available:
        status_box = Table([[Paragraph(
            "<font color='#9C2C2C' size='12'><b>NOT SUGGESTED</b></font><br/>"
            "Personalized care suggestions are not provided for residents aged 75-100. "
            "Follow the facility's standard fall-risk assessment and care plan.",
            styles["PdfBody"],
        )]], colWidths=[content_width], hAlign="LEFT")
        status_box.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FFF4F2")),
            ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#E6A39B")),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, -1), 9),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
        ]))
        body.append(KeepTogether([recommendation_heading, status_box]))
    elif suggestions_supported and actions:
        recommendation_intro = Paragraph("Personalized suggestions for residents aged 60-74.", styles["PdfSmall"])
        recommendation_spacer = Spacer(1, 0.08 * cm)
        action_rows = [[Paragraph("CARE RECOMMENDATIONS", styles["PdfHeaderCell"])]]
        for index, item in enumerate(actions, 1):
            feature = str(item.get("feature") or "")
            topic = action_topics.get(feature, "Care plan follow-up")
            action = _pdf_english(item.get("action"), fallback_action)
            action_rows.append([
                Paragraph(f"<b>{index}. {_pdf_text(topic)}</b><br/>{_pdf_text(action)}", styles["PdfCell"]),
            ])
        action_table = Table(action_rows, colWidths=[content_width], repeatRows=1, hAlign="LEFT")
        action_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#486581")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("LINEBELOW", (0, 1), (-1, -1), 0.35, colors.HexColor("#D9E2EC")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7F9FC")]),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ]))
        body.append(KeepTogether([
            recommendation_heading,
            recommendation_intro,
            recommendation_spacer,
            action_table,
        ]))
    elif suggestions_supported:
        body.append(KeepTogether([
            recommendation_heading,
            Paragraph(
                "No personalized care suggestions are available for this assessment. Follow the facility's standard fall-risk care plan.",
                styles["PdfBody"],
            ),
        ]))
    else:
        body.append(KeepTogether([
            recommendation_heading,
            Paragraph(
                "Personalized care suggestions are configured for residents aged 60-74 only.",
                styles["PdfBody"],
            ),
        ]))

    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")

    def _draw_page(canvas, _doc):
        canvas.saveState()
        width, height = A4
        canvas.setStrokeColor(colors.HexColor("#D9E2EC"))
        canvas.setLineWidth(0.5)
        canvas.line(doc.leftMargin, height - 1.35 * cm, width - doc.rightMargin, height - 1.35 * cm)
        canvas.setFont(font_name, 7.5)
        canvas.setFillColor(colors.HexColor("#627D98"))
        canvas.drawString(doc.leftMargin, height - 1.08 * cm, "CARE STAFF COPY  |  FALL RISK CARE COPY")
        canvas.line(doc.leftMargin, 1.05 * cm, width - doc.rightMargin, 1.05 * cm)
        canvas.drawString(
            doc.leftMargin,
            0.7 * cm,
            f"Care handover copy | Generated {generated_at} | Follow facility protocol",
        )
        canvas.drawRightString(width - doc.rightMargin, 0.7 * cm, f"Page {canvas.getPageNumber()}")
        canvas.restoreState()

    doc.build(body, onFirstPage=_draw_page, onLaterPages=_draw_page)
    pdf = buf.getvalue()
    buf.close()
    return pdf


@app.get("/assessments/summary")
async def get_assessment_summary(db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Summary stats for the dashboard: total + count by risk level."""
    from sqlalchemy import func, select
    result = await db.execute(
        select(PatientRecord.fall_risk_level, func.count()).group_by(PatientRecord.fall_risk_level)
    )
    counts = {level: n for level, n in result.all()}
    total = sum(counts.values())
    return {
        "total": total,
        "high": counts.get("HIGH", 0),
        "medium": counts.get("MEDIUM", 0),
        "low": counts.get("LOW", 0),
    }


@app.get("/assessments")
async def list_assessments(
    page: int = 1,
    itemsPerPage: int = 10,
    risk_level: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Paginated list of assessment records, optionally filtered by risk level."""
    from sqlalchemy import func, select
    stmt = select(PatientRecord)
    count_stmt = select(func.count()).select_from(PatientRecord)
    if risk_level:
        stmt = stmt.where(PatientRecord.fall_risk_level == risk_level)
        count_stmt = count_stmt.where(PatientRecord.fall_risk_level == risk_level)
    stmt = stmt.order_by(PatientRecord.created_at.desc()).offset((page - 1) * itemsPerPage).limit(itemsPerPage)
    total = (await db.execute(count_stmt)).scalar() or 0
    rows = (await db.execute(stmt)).scalars().all()
    items = [_record_to_dict(r) for r in rows]
    return {"items": items, "total": total}


@app.get("/assessments/{record_id}")
async def get_assessment(record_id: int, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Single assessment detail."""
    record = await db.get(PatientRecord, record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Assessment not found")
    return _record_to_dict(record)


@app.get("/assessments/{record_id}/pdf")
async def download_assessment_pdf(record_id: int, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Generate and download a printable PDF for this assessment."""
    record = await db.get(PatientRecord, record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Assessment not found")
    data = _record_to_dict(record)
    pdf_bytes = generate_assessment_pdf(data)
    resident_slug = re.sub(r"[^A-Za-z0-9_-]+", "-", str(data.get("resident_id") or record_id)).strip("-")
    resident_slug = resident_slug or f"id-{record_id}"
    risk_slug = str(data.get("fall_risk_level") or "assessment").lower()
    filename = f"fall-risk-report-{resident_slug}-{risk_slug}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.delete("/assessments/all")
async def delete_all_assessments(db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Delete all assessment records (one-click clear)."""
    from sqlalchemy import delete
    await db.execute(delete(PatientRecord))
    await db.commit()
    return {"deleted": True}


class BatchDeleteRequest(BaseModel):
    ids: list[int]


@app.post("/assessments/batch-delete")
async def batch_delete_assessments(req: BatchDeleteRequest, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Delete multiple assessment records by id."""
    from sqlalchemy import delete
    if not req.ids:
        return {"deleted": 0}
    await db.execute(delete(PatientRecord).where(PatientRecord.id.in_(req.ids)))
    await db.commit()
    return {"deleted": len(req.ids)}


@app.delete("/assessments/{record_id}")
async def delete_assessment(record_id: int, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Delete a single assessment record."""
    record = await db.get(PatientRecord, record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Assessment not found")
    await db.delete(record)
    await db.commit()
    return {"deleted": record_id}


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
        inputTugSeconds,
        inputDaysSinceLastFall,
        inputSyncopalFall,
        inputFallCluster30d
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
        tug_seconds=float(inputTugSeconds),
        days_since_last_fall=(
            int(inputDaysSinceLastFall)
            if inputDaysSinceLastFall not in (None, "")
            else None
        ),
        syncopal_fall=1 if inputSyncopalFall else 0,
        fall_cluster_30d=1 if inputFallCluster30d else 0,
    )

    async with AsyncSessionLocal() as session:
        response = await get_prediction(data=profile, db=session)
        
    risk_level = response["fall_risk_level"]
    explanations = response["lime_explanations"]

    # Format output for the user interface textboxes
    output_text = f"Risk Level: {risk_level}\n"
    output_text += "primary factors:\n"
    # Keep the legacy Gradio textbox concise; the API/dashboard retain all
    # terms for the caregiver risk-driver card.
    for i, exp in enumerate(explanations[:3], start=1):
        output_text += f" {i}. {exp['condition']} | Weight: {exp['weight']} ({exp['direction']})\n"
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
        None if pd.isna(first_row.get("days_since_last_fall")) else first_row.get("days_since_last_fall"),
        bool(first_row.get("syncopal_fall")) if first_row.get("syncopal_fall") is not None else False,
        bool(first_row.get("fall_cluster_30d")) if first_row.get("fall_cluster_30d") is not None else False,
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
    "距上次跌倒天数": "days_since_last_fall",
    "是否晕厥跌倒": "syncopal_fall", "跌倒时是否失去意识": "syncopal_fall",
    "30天内是否连续跌倒": "fall_cluster_30d", "30天内连续跌倒": "fall_cluster_30d",
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
               "orthostatic_hypotension", "tug_seconds",
               "days_since_last_fall", "syncopal_fall", "fall_cluster_30d"]
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
    dv_yesno.add("M2:M2000")
    dv_yesno.add("N2:N2000")

    widths = {"A": 10, "B": 8, "C": 16, "D": 24, "E": 12, "F": 16,
              "G": 20, "H": 18, "I": 18, "J": 22, "K": 14,
              "L": 20, "M": 16, "N": 20}
    for col, w in widths.items():
        ws.column_dimensions[col].width = w

    wb.save(path)


def batch_predict_file(file, return_details: bool = False):
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
    for c in ("syncopal_fall", "fall_cluster_30d"):
        if c in df.columns:
            df[c] = df[c].apply(lambda v: _to_bool(v) if not pd.isna(v) else 0)

    to_save = []
    n_ok = 0
    n_err = 0
    errors = []
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

            # Optional extended fall-detail fields (default if column absent).
            feats["days_since_last_fall"] = None
            feats["syncopal_fall"] = 0
            feats["fall_cluster_30d"] = 0
            if "days_since_last_fall" in df.columns and not pd.isna(r["days_since_last_fall"]):
                try:
                    days_since_last_fall = int(r["days_since_last_fall"])
                except (TypeError, ValueError):
                    raise ValueError(f"days_since_last_fall is not a number: {r['days_since_last_fall']}")
                if not 0 <= days_since_last_fall <= 365:
                    raise ValueError(f"days_since_last_fall={days_since_last_fall} out of range 0~365")
                feats["days_since_last_fall"] = days_since_last_fall
            if "syncopal_fall" in df.columns and not pd.isna(r["syncopal_fall"]):
                syncopal_fall = int(r["syncopal_fall"])
                if syncopal_fall not in (0, 1):
                    raise ValueError(f"syncopal_fall={syncopal_fall} must be 0 or 1")
                feats["syncopal_fall"] = syncopal_fall
            if "fall_cluster_30d" in df.columns and not pd.isna(r["fall_cluster_30d"]):
                fall_cluster_30d = int(r["fall_cluster_30d"])
                if fall_cluster_30d not in (0, 1):
                    raise ValueError(f"fall_cluster_30d={fall_cluster_30d} must be 0 or 1")
                feats["fall_cluster_30d"] = fall_cluster_30d

            # Spreadsheet templates commonly encode an empty date as 0.  Keep
            # the same convention as PatientData: zero is only meaningful when
            # at least one fall is recorded.
            if int(feats.get("past_falls", 0)) == 0:
                feats["days_since_last_fall"] = None

            level = predict_fall_risk(feats)
            # Persist all terms so imported residents receive the same
            # risk-driver explanation as a manually assessed resident.
            expl = explain_patient(feats, max_features=len(MODEL_FEATURES))
            to_save.append(PatientRecord(
                sex=feats.get("sex"),
                age=feats["age"],
                night_bed_exits=feats["night_bed_exits"],
                night_activity_duration_min=feats["night_activity_duration_min"],
                past_falls=feats["past_falls"],
                mobility_score=feats["mobility_score"],
                high_risk_medication=feats["high_risk_medication"],
                cognitive_impairment=feats["cognitive_impairment"],
                polypharmacy_count=feats["polypharmacy_count"],
                orthostatic_hypotension=feats["orthostatic_hypotension"],
                tug_seconds=feats["tug_seconds"],
                days_since_last_fall=feats.get("days_since_last_fall"),
                syncopal_fall=feats.get("syncopal_fall", 0),
                fall_cluster_30d=feats.get("fall_cluster_30d", 0),
                fall_risk_level=level,
                resident_id=pid,
                lime_explanations=json.dumps(expl),
            ))
            n_ok += 1
        except Exception as exc:
            n_err += 1
            errors.append(f"row {idx + 2}: {exc}")

    if to_save:
        async def _save():
            async with AsyncSessionLocal() as session:
                session.add_all(to_save)
                await session.commit()
        asyncio.run(_save())

    msg = (f"### ✅ Batch processed\n\n"
           f"- Successfully saved: **{n_ok}** residents\n"
           f"- Data errors skipped: **{n_err}** rows\n\n"
           f"Please go to the **Risk Dashboard** to view the results:\n\n"
           f"👉 [Open Risk Dashboard](http://localhost:5173/dashboards/fall-risk-dashboard)")
    if n_err:
        msg += ("\n\n> Some rows were skipped due to invalid data. "
                "Please check the values are within range and not empty.")
    if return_details:
        return {
            "success": n_ok,
            "skipped": n_err,
            "total": n_ok + n_err,
            "errors": errors,
            "message": msg,
        }
    return msg


@app.get("/batch-template")
async def download_batch_template():
    """Download the Excel template used by the caregiver batch import flow."""
    template_path = os.path.join(DATA_DIR, "import_template.xlsx")
    if not os.path.exists(template_path):
        _build_excel_template(template_path)
    return FileResponse(
        template_path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename="import_template.xlsx",
    )


@app.post("/batch-predict")
async def batch_predict_api(file: UploadFile = File(...)):
    """Upload an Excel/CSV file and run the existing batch prediction flow.

    The legacy Gradio callback is synchronous and persists all valid rows in one
    database transaction.  Run it in a worker thread so its internal
    ``asyncio.run`` does not conflict with FastAPI's event loop.
    """
    original_name = file.filename or ""
    suffix = os.path.splitext(original_name)[1].lower()
    if suffix not in (".xlsx", ".xlsm", ".csv"):
        raise HTTPException(status_code=400, detail="Please upload a .xlsx, .xlsm, or .csv file")

    # Keep an accidental upload from consuming the whole server's disk/memory.
    max_file_bytes = 25 * 1024 * 1024
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(prefix="fall-risk-", suffix=suffix, delete=False) as tmp:
            temp_path = tmp.name
            total_bytes = 0
            while chunk := await file.read(1024 * 1024):
                total_bytes += len(chunk)
                if total_bytes > max_file_bytes:
                    raise HTTPException(status_code=413, detail="文件不能超过 25 MB")
                tmp.write(chunk)

        try:
            details = await asyncio.to_thread(
                batch_predict_file,
                SimpleNamespace(name=temp_path),
                True,
            )
        except gr.Error as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except (OSError, ValueError, UnicodeDecodeError, zipfile.BadZipFile) as exc:
            raise HTTPException(status_code=400, detail=f"无法读取文件，请检查文件格式：{exc}") from exc

        return details
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Batch prediction failed: {exc}") from exc
    finally:
        await file.close()
        if temp_path:
            try:
                os.unlink(temp_path)
            except OSError:
                pass


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
                inputDaysSinceLastFall = gr.Number(
                    minimum=0,
                    label="距上次跌倒天数（0=没跌过）",
                    value=0
                )
                inputSyncopalFall = gr.Checkbox(
                    label="跌倒时是否失去意识（晕厥）"
                )
                inputFallCluster30d = gr.Checkbox(
                    label="30天内是否连续跌倒≥2次"
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
                inputPolypharmacyCount, inputOrthostaticHypotension, inputTugSeconds,
                inputDaysSinceLastFall, inputSyncopalFall, inputFallCluster30d
            ]
        )

        submit_btn.click(
            fn=predict_gradio, 
            inputs=[
                inputSex, inputAge, inputPastFalls, inputMobilityScore, inputNightBedExits, 
                inputNightActivityDurationMin, inputHighRiskMed, inputCognitiveImpairment,
                inputPolypharmacyCount, inputOrthostaticHypotension, inputTugSeconds,
                inputDaysSinceLastFall, inputSyncopalFall, inputFallCluster30d
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
| days_since_last_fall | Number, 0–365 (empty if past_falls=0) |
| syncopal_fall | Select "Yes" or "No" (fall with loss of consciousness) |
| fall_cluster_30d | Select "Yes" or "No" (≥2 falls within 30 days) |

> Values out of range are marked as "Data Error". Please fill within range.
""")
        gr.DownloadButton(label="Download Excel Template", value=TEMPLATE_PATH)
        batch_file = gr.File(label="Upload filled Excel file (.xlsx)")
        batch_btn = gr.Button("Run Batch Prediction", variant="primary")
        batch_summary = gr.Markdown()
        batch_btn.click(fn=batch_predict_file, inputs=batch_file,
                        outputs=[batch_summary])

# Mount Gradio inside FastAPI application context properly
app = gr.mount_gradio_app(app, interface, path="/")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
