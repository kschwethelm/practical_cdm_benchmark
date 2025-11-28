from langchain_core.prompts import PromptTemplate


system_prompt = """You are a medical artificial intelligence assistant. 
You directly diagnose patients based on the provided information to assist a doctor in his clinical duties.
Your goal is to correctly diagnose the patient.
Based on the provided information you will provide a final diagnosis of the most severe pathology.
Don't write any further information. Give only a single diagnosis. 
Provide the most likely final diagnosis of the following patient.

You are given ALL available diagnostic information at once.

Return your answer in the following format:
{format_instructions}"""

format_instructions = """
Return your answer as a JSON object with exactly these fields:
{
  "diagnosis": "your diagnosis here"
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

Use ALL information above and return in JSON format.
"""


full_info_prompt_template = PromptTemplate(
    template=full_info,
    input_variables=[
        "age",
        "gender",
        "history_of_present_illness",
        "physical_examination",
    ],
)
system_prompt_template = system_prompt.format(format_instructions=format_instructions)
