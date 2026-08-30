from __future__ import annotations
from datetime import UTC, datetime
from sqlalchemy import Column, DateTime, Float, Integer, String, Text
from backend.database import Base

# Database Model tailored for deep learning extraction
class PatientRecord(Base):
    __tablename__ = "patient_predictions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    # The 10 required deep learning features
    sex = Column(String(1), nullable=True)             # 'M' / 'F'
    age = Column(Integer, nullable=False)
    night_bed_exits = Column(Integer, nullable=False)
    night_activity_duration_min = Column(Float, nullable=False)
    past_falls = Column(Integer, nullable=False)
    mobility_score = Column(Integer, nullable=False)
    high_risk_medication = Column(Integer, nullable=False)
    cognitive_impairment = Column(Integer, nullable=False)
    polypharmacy_count = Column(Integer, nullable=False)
    orthostatic_hypotension = Column(Integer, nullable=False)
    tug_seconds = Column(Float, nullable=False)
    # Extended fall-detail fields (NOT model inputs; kept for clinical context & dashboard display)
    days_since_last_fall = Column(Integer, nullable=True)   # days since most recent fall (empty if no fall)
    syncopal_fall = Column(Integer, nullable=True, default=0)       # 1 = fall with loss of consciousness
    fall_cluster_30d = Column(Integer, nullable=True, default=0)    # 1 = >=2 falls within 30 days
    # Outcome tracking
    fall_risk_level = Column(String, nullable=False)
    resident_id = Column(String, nullable=True, index=True)  # resident identifier (for trend tracking)
    lime_explanations = Column(Text, nullable=True)          # LIME explanation (JSON string)
    created_at = Column(DateTime, default=datetime.utcnow)