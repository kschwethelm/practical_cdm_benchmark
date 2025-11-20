from langchain_core.prompts import PromptTemplate

template = """
The output result does not adhere to the specified output format. Please fix the following: 
{old_result}  

Return your answer as a JSON object with exactly these fields:  
{
  "diagnosis": "<1-2 word>",
  "justification": "<2–4 sentences>",
  "treatment_plan": "<2–4 sentences or short paragraph>"
  "confidence": "<1 word>"
}
Do not include any extra text outside the JSON.
"""

retry_prompt_template = PromptTemplate.from_template(template)