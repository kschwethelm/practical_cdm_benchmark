from pydantic import BaseModel, Field
from langchain_core.output_parsers import PydanticOutputParser


class FullInfoOutput(BaseModel):
    diagnosis: str = Field(..., description="Single most likely diagnosis")
    justification: str = Field(..., description="2–4 sentences of reasoning")
    treatment_plan: str = Field(..., description="Initial treatment plan")
    
parser = PydanticOutputParser(pydantic_object=FullInfoOutput)