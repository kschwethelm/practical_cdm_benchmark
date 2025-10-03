from datetime import datetime

from pydantic import BaseModel, Field


class Demographics(BaseModel):
    age: int
    gender: str


class LabResult(BaseModel):
    itemid: int
    charttime: datetime
    value: str | None = None
    valuenum: float | None = None
    valueuom: str | None = None


class MicrobiologyResult(BaseModel):
    charttime: datetime
    spec_type_desc: str | None = None
    test_name: str | None = None
    org_name: str | None = None
    interpretation: str | None = None


class ChiefComplaint(BaseModel):
    complaint: str


class Diagnosis(BaseModel):
    title: str


class PastMedicalHistory(BaseModel):
    note: str
    category: str


class PhysicalExam(BaseModel):
    temporal_context: str | None = None
    vital_signs: str | None = None
    general: str | None = None
    heent_neck: str | None = None
    cardiovascular: str | None = None
    pulmonary: str | None = None
    abdominal: str | None = None
    extremities: str | None = None
    neurological: str | None = None
    skin: str | None = None


class HadmCase(BaseModel):
    """Complete case data for a single hospital admission"""

    hadm_id: int
    demographics: Demographics | None = None
    first_lab_result: LabResult | None = None
    first_microbiology_result: MicrobiologyResult | None = None
    chief_complaints: list[str] = Field(default_factory=list)
    diagnosis: str | None = None
    past_medical_history: list[PastMedicalHistory] = Field(default_factory=list)
    physical_exam: PhysicalExam | None = None


class BenchmarkDataset(BaseModel):
    """Root model for the complete benchmark dataset"""

    cases: list[HadmCase] = Field(default_factory=list)


class DiagnosisOutput(BaseModel):
    """Structured output from LLM clinical decision-making"""

    diagnosis: str
    treatment: list[str]
