from pydantic import BaseModel, Field
from langchain_core.output_parsers import PydanticOutputParser
from cdm.Prompts.retry import retry_prompt_template


class FullInfoOutput(BaseModel):
    diagnosis: str = Field(..., description="Single most likely diagnosis")
    justification: str = Field(..., description="2–4 sentences of reasoning")
    treatment_plan: str = Field(..., description="Initial treatment plan")
    
parser = PydanticOutputParser(pydantic_object=FullInfoOutput)

def retry_parse(llm, result, max_retries=0):
    # Attempt to parse result
    content = result.content if hasattr(result, "content") else str(result)

    try:
        return parser.parse(content)
    except Exception:
        pass
    
    # If it doesn't work, retry max_retries times 
    current_text = content
    for _ in range(max_retries):
        new_result = current_text
        try:
            retry_prompt = retry_prompt_template.format(old_result=current_text)
            attempt = llm.invoke([{"role": "user", "content": retry_prompt}])
            new_result = (
                attempt.content if hasattr(attempt, "content") else str(attempt)
            )
            return parser.parse(new_result)

        except Exception:
            # Update input text for next iteration
            current_text = new_result

    # All attempts have failed 
    return None
