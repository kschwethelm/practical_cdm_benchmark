from langchain_core.prompts import PromptTemplate

system_prompt = """You are a medical expert.

You are given ALL available diagnostic information at once:
- Chief complaint
- History of present illness
- Microbiology results
- Physical examination
- Laboratory results
- Imaging reports

Your task:
1. Carefully read all information.
2. Provide the SINGLE most likely final diagnosis responsible for the patient's presentation.
3. Briefly justify your reasoning.

Return your answer in the following format:
{format_instructions}"""

format_instructions = """
Return your answer as a JSON object with exactly these fields:
{
  diagnosis
}
Do not include any extra text outside the JSON.
"""

full_info = """Diagnose the patient based on the following information.

PATIENT DEMOGRAPHICS:
- Age: {age}
- Gender: {gender}


HISTORY OF PRESENT ILLNESS:
{history_of_present_illness}


PHYSICAL EXAMINATION:
{physical_examination}


LABORATORY RESULTS:
{laboratory_results}

IMAGING REPORTS:
{imaging_reports}
MICROBIOLOGY RESULTS:
{microbiology_results}

Use ALL information above and return in JSON format.
"""


full_info_prompt_template = PromptTemplate(
    template=full_info,
    input_variables=[
        "age",
        "gender",
        "history_of_present_illness",
        "physical_examination",
        "laboratory_results",
        "imaging_reports",
        "microbiology_results",
    ],
)
system_prompt_template = system_prompt.format(format_instructions=format_instructions)
