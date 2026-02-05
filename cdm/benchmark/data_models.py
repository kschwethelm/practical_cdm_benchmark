from datetime import datetime
from enum import StrEnum

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
    itemid: int
    test_name: str
    fluid: str | None = None
    category: str | None = None
    value: str | None = None
    ref_range_lower: float | None = None
    ref_range_upper: float | None = None


class MicrobiologyEvent(BaseModel):
    test_itemid: int
    test_name: str | None = None
    spec_type_desc: str | None = None
    organism_name: str | None = None
    comments: str | None = None
    charttime: datetime | None = None


class RadiologyReport(BaseModel):
    note_id: str
    exam_name: str | None = None
    region: str | None = None
    modality: str | None = None
    text: str | None = None


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


class Treatment(BaseModel):
    """Treatment/procedure information."""

    title: str
    icd_code: str | None = None
    is_coded: bool = False  # True if from ICD codes, False if from free text


class GroundTruth(BaseModel):
    """The ground truth for evaluation."""

    primary_diagnosis: list[str] = Field(default_factory=list)
    treatments: list[Treatment]


class Pathology(StrEnum):
    """Pathology/condition type for benchmark cases."""

    APPENDICITIS = "appendicitis"
    CHOLECYSTITIS = "cholecystitis"
    DIVERTICULITIS = "diverticulitis"
    PANCREATITIS = "pancreatitis"


class HadmCase(BaseModel):
    """Complete case data for a single hospital admission based on CDMv1 schema"""

    hadm_id: int
    pathology: Pathology | None = None
    demographics: Demographics | None = None
    patient_history: str | None = None
    lab_results: list[DetailedLabResult] = Field(default_factory=list)
    microbiology_events: list[MicrobiologyEvent] = Field(default_factory=list)
    radiology_reports: list[RadiologyReport] = Field(default_factory=list)
    physical_exam_text: str | None = None
    ground_truth: GroundTruth | None = None


class BenchmarkDataset(BaseModel):
    """Root model for the complete benchmark dataset"""

    cases: list[HadmCase] = Field(default_factory=list)

    def __iter__(self):
        """Allow iteration over cases directly."""
        return iter(self.cases)

    def __len__(self):
        """Return the number of cases."""
        return len(self.cases)

    def __getitem__(self, index):
        """Allow indexing and slicing."""
        return self.cases[index]


class BenchmarkOutputCDM(BaseModel):
    """Structured output from LLM clinical decision-making"""

    thought: str = Field(
        description="Reflect on the gathered information and explain the reasoning for the final diagnosis"
    )
    final_diagnosis: str = Field(description="The final diagnosis to the original case")
    treatment: list[str] = Field(description="The treatment for the given diagnosis")


class BenchmarkOutputFullInfo(BaseModel):
    """Structured output from LLM clinical decision-making with full information"""

    diagnosis: str


class AgentRunResult(BaseModel):
    """Complete agent execution result with tool calls and parsed output."""

    parsed_output: BenchmarkOutputCDM
    messages: list[dict]  # Full conversation history with tool calls

    @property
    def tool_calls(self) -> dict[str, int]:
        """Count occurrences of each tool call type"""
        counts: dict[str, int] = {}
        total = 0
        for msg in self.messages:
            if "tool_calls" in msg and msg["tool_calls"]:
                for tc in msg["tool_calls"]:
                    name = tc.get("name", "unknown")
                    counts[name] = counts.get(name, 0) + 1
                    total += 1
        counts["total"] = total
        return counts


class EvalOutput(BaseModel):
    """Evaluation output for a single case, including ground truth and predictions."""

    hadm_id: int
    ground_truth: GroundTruth
    pathology: str
    prediction: BenchmarkOutputCDM
    tool_calls: dict[str, int]
    answers: dict
    scores: dict


class EvalOutputFullInfo(BaseModel):
    """Evaluation output for full info baseline (no tool calls)."""

    hadm_id: int
    ground_truth: GroundTruth
    pathology: str
    prediction: BenchmarkOutputFullInfo
    scores: dict
