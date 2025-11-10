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


class MicrobiologyResult(BaseModel):
    charttime: datetime
    spec_type_desc: str | None = None
    test_name: str | None = None
    org_name: str | None = None
    interpretation: str | None = None


class RadiologyReport(BaseModel):
    charttime: datetime
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

    primary_diagnosis: str
    treatments: list[str]


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


class HadmCaseCDMv1(BaseModel):
    """Complete case data for a single hospital admission based on CDMv1 schema"""

    hadm_id: int
    demographics: Demographics | None = None
    history_of_present_illness: str | None = None
    lab_results: list[DetailedLabResult] = Field(default_factory=list)
    radiology_reports: list[RadiologyReport] = Field(default_factory=list)
    physical_exams: list[PhysicalExam] = Field(default_factory=list)
    ground_truth: GroundTruth | None = None


class BenchmarkDataset(BaseModel):
    """Root model for the complete benchmark dataset"""

    cases: list[HadmCase] = Field(default_factory=list)


class BenchmarkDatasetCDMv1(BaseModel):
    """Root model for the complete benchmark dataset based on CDMv1 schema"""

    cases: list[HadmCaseCDMv1] = Field(default_factory=list)


class DiagnosisOutput(BaseModel):
    """Structured output from LLM clinical decision-making"""

    diagnosis: str
    treatment: list[str]
