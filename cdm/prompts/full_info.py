from pathlib import Path

from jinja2 import Environment, FileSystemLoader, Template

TEMPLATE_DIR = Path(__file__).parent
jinja_env = Environment(loader=FileSystemLoader(searchpath=TEMPLATE_DIR))

format_instructions_template: Template = jinja_env.get_template("format_instructions/only_diagnosis.j2")
format_instructions = format_instructions_template.render()

system_prompt_template: Template = jinja_env.get_template("full_info/system.j2")
system_prompt = system_prompt_template.render(format_instructions=format_instructions)

full_info_prompt_template: Template = jinja_env.get_template("full_info/user.j2")
