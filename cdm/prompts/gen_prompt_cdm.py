from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from cdm.benchmark.data_models import BenchmarkOutputCDM
from cdm.prompts.utils import pydantic_to_prompt

TEMPLATE_DIR = Path(__file__).parent
jinja_env = Environment(loader=FileSystemLoader(searchpath=TEMPLATE_DIR))


def create_system_prompt(template_name: str = "cdm/system.j2") -> str:
    """Create CDM system prompt with Pydantic schema.

    Args:
        template_name: Path to Jinja2 template file (default: "cdm/system.j2")

    Returns:
        System prompt string with JSON schema for BenchmarkOutputCDM
    """
    template = jinja_env.get_template(template_name)
    pydantic_schema = pydantic_to_prompt(BenchmarkOutputCDM)
    return template.render(pydantic_schema=pydantic_schema)


def create_user_prompt(patient_info: str, template_name: str = "cdm/user.j2") -> str:
    """Create CDM user prompt with patient information.

    Args:
        patient_info: Patient history and information string
        template_name: Path to Jinja2 template file (default: "cdm/user.j2")

    Returns:
        User prompt string formatted with patient information
    """
    template = jinja_env.get_template(template_name)
    return template.render(patient_info=patient_info)
