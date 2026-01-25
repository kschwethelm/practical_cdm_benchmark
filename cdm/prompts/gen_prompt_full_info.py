from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from cdm.benchmark.data_models import BenchmarkOutputFullInfo
from cdm.prompts.utils import pydantic_to_prompt

TEMPLATE_DIR = Path(__file__).parent
jinja_env = Environment(loader=FileSystemLoader(searchpath=TEMPLATE_DIR))


def create_system_prompt(template_name: str = "full_info/system.j2") -> str:
    """Create full info system prompt with Pydantic schema.

    Args:
        template_name: Path to Jinja2 template file (default: "full_info/system.j2")

    Returns:
        System prompt string with JSON schema for BenchmarkOutputFullInfo
    """
    template = jinja_env.get_template(template_name)
    pydantic_schema = pydantic_to_prompt(BenchmarkOutputFullInfo)
    return template.render(pydantic_schema=pydantic_schema)


def create_user_prompt(case: dict, template_name: str = "full_info/user.j2") -> str:
    """Create full info user prompt with case data.

    Args:
        case: Dictionary containing case data with keys:
            - patient_history: str
            - physical_examination: str (optional)
            - laboratory_results: str (optional)
            - imaging_reports: str (optional)
            - microbiology_results: str (optional)
            - diagnosis_criteria: str (optional)
        template_name: Path to Jinja2 template file (default: "full_info/user.j2")

    Returns:
        User prompt string formatted with case information
    """
    template = jinja_env.get_template(template_name)
    return template.render(
        patient_history=case.get("patient_history"),
        physical_examination=case.get("physical_examination"),
        laboratory_results=case.get("laboratory_results"),
        imaging_reports=case.get("imaging_reports"),
        microbiology_results=case.get("microbiology_results"),
        diagnosis_criteria=case.get("diagnosis_criteria"),
    )
