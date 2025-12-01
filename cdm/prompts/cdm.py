from pathlib import Path

from jinja2 import Environment, FileSystemLoader, Template

TEMPLATE_DIR = Path(__file__).parent
jinja_env = Environment(loader=FileSystemLoader(searchpath=TEMPLATE_DIR))

format_instructions_template: Template = jinja_env.get_template("format_instructions/diagnosis_treatment.j2")
format_instructions = format_instructions_template.render()

system_prompt_template: Template = jinja_env.get_template("tool_calling/system.j2")
system_prompt = system_prompt_template.render(format_instructions=format_instructions)

user_prompt_template: Template = jinja_env.get_template("tool_calling/user.j2")
