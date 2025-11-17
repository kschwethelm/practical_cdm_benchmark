from pydantic import BaseModel, Field
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate


class FullInfoOutput(BaseModel):
    diagnosis: str = Field(..., description="Single most likely diagnosis")
    justification: str = Field(..., description="2–4 sentences of reasoning")
    treatment_plan: str = Field(..., description="Initial treatment plan")


parser = PydanticOutputParser(pydantic_object=FullInfoOutput)

template = """
You are a clinical decision-making assistant for abdominal pain cases.
You are given ALL available diagnostic information at once:
- Chief complaint
- Past medical history
- Microbiology results
- Physical examination
- Laboratory results
- Imaging reports

Your task:
1) Carefully read all information.
2) Provide the SINGLE most likely final diagnosis responsible for the patient's presentation.
3) Briefly justify your reasoning.
4) Propose an appropriate initial treatment plan.

Important:
- Do NOT ask for more tests, you already have all relevant data.
- Be concise but clinically precise.

Return your answer in the following format:
{format_instructions}

PATIENT DEMOGRAPHICS:
- Age: {age}
- Gender: {gender}

CHIEF COMPLAINT(S):
{chief_complaints}

PAST MEDICAL HISTORY:
{pmh_text}

PHYSICAL EXAMINATION:
{physical_exam_text}

LABORATORY RESULTS:
{labs_text}

MICROBIOLOGY RESULTS:
{microbio_text}

Use ALL information above and return in JSON format.
"""

format_instructions = """
Return your answer as a JSON object with exactly these fields:
{
  "diagnosis": "<ONE word>",
  "justification": "<2–4 sentences>",
  "treatment_plan": "<2–4 sentences or short paragraph>"
}
Do not include any extra text outside the JSON.
"""

prompt_template = PromptTemplate(
    template=template,
    input_variables=[
        "age",
        "gender",
        "chief_complaints",
        "pmh_text",
        "physical_exam_text",
        "labs_text",
        "microbio_text",
    ],
    partial_variables={"format_instructions": format_instructions},
)
