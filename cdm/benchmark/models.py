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


class DetailedLabResult(BaseModel):
    test_name: str
    value: str | None = None
    unit: str | None = None
    ref_range_lower: float | None = None
    ref_range_upper: float | None = None
    flag: str | None = None


class MicrobiologyEvent(BaseModel):
    test_name: str | None = None
    spec_type_desc: str | None = None
    organism_name: str | None = None
    interpretation: str | None = None
    charttime: datetime | None = None


class MicrobiologyResult(BaseModel):
    charttime: datetime
    spec_type_desc: str | None = None
    test_name: str | None = None
    org_name: str | None = None
    interpretation: str | None = None


class RadiologyReport(BaseModel):
    charttime: datetime
    exam_name: str | None = None
    region: str | None = None
    modality: str | None = None
    findings: str | None = None


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


class GroundTruth(BaseModel):
    """The ground truth for evaluation."""

    primary_diagnosis: str | None = None
    treatments: list[str]


class HadmCase(BaseModel):
    """Complete case data for a single hospital admission based on CDMv1 schema"""

    hadm_id: int
    demographics: Demographics | None = None
    history_of_present_illness: str | None = None
    lab_results: list[DetailedLabResult] = Field(default_factory=list)
    microbiology_events: list[MicrobiologyEvent] = Field(default_factory=list)
    radiology_reports: list[RadiologyReport] = Field(default_factory=list)
    physical_exam_text: str | None = None
    ground_truth: GroundTruth | None = None


class BenchmarkDataset(BaseModel):
    """Root model for the complete benchmark dataset"""

    cases: list[HadmCase] = Field(default_factory=list)


class DiagnosisOutput(BaseModel):
    """Structured output from LLM clinical decision-making"""

    diagnosis: str
    treatment: list[str]
