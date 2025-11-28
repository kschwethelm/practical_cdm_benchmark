from langchain_core.prompts import PromptTemplate

system_prompt = """You are a medical artificial intelligence assistant. 
You give helpful, detailed and factually correct answers to the doctors questions to help him in his clinical duties. 
Your goal is to correctly diagnose the patient and provide treatment advice. 
You will consider information about a patient and provide a final diagnosis.
Use the tools to gather physical exam and lab results.

{{ format_instructions }}
"""

format_instructions = """
Give your final response in JSON using this schema:
{
  "thought": "<string: Reflect on the gathered information and explain the reasoning>",
  "final_diagnosis": "<string: The final diagnosis based on the case information>",
  "treatment": ["<array of strings: Treatment recommendations>"]
}"""

user_prompt = """Consider the following case and come to a final diagnosis and treatment by thinking, planning, and using the aforementioned tools and format.

Patient History:
{{ patient_info }}
"""

system_prompt_template = PromptTemplate(
    template=system_prompt,
    template_format="jinja2",
    partial_variables={"format_instructions": format_instructions},
)

user_prompt_template = PromptTemplate(
    template=user_prompt,
    template_format="jinja2",
    input_variables=["patient_info"],
)
