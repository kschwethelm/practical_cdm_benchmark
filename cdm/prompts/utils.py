import enum
from pathlib import Path
from typing import Any, Literal, get_args, get_origin

from pydantic import BaseModel

CRITERIA_DIR = Path(__file__).parent / "diagnosis_criterias"


def types_to_str(type_annotation: Any) -> str:
    """Convert Python type annotation to human-readable string format.

    Handles Union types, Enums, Optional types, and generic types.

    Args:
        type_annotation: Python type annotation to convert

    Returns:
        Human-readable string representation of the type

    Examples:
        >>> types_to_str(str | None)
        "str or null"
        >>> types_to_str(list[str])
        "list[str]"
    """
    origin = get_origin(type_annotation)
    if origin is None or origin is list or origin is Literal:
        type_args = (type_annotation,)
    else:
        type_args = get_args(type_annotation)

    type_strings = []
    for type_arg in type_args:
        if isinstance(type_arg, enum.EnumMeta):
            # e.g. 'Cat' or 'Dog' or 'Bird'
            type_str = " or ".join([f"'{member.name}'" for member in type_arg])
        elif type_arg is type(None):
            type_str = "null"
        elif get_origin(type_arg) is Literal:
            type_str = f"'{type_arg.__args__[0]}'"  # e.g. 'Medication'
        elif get_origin(type_arg) is list:
            list_type = type_arg.__args__[0]
            if isinstance(list_type, enum.EnumMeta):
                list_type_str = " or ".join([f"'{member.name}'" for member in list_type])
            else:
                list_type_str = list_type.__name__
            type_str = f"list[{list_type_str}]"  # e.g. list[str]
        elif get_origin(type_arg) in (dict, set, tuple):
            raise NotImplementedError(
                f"Type {get_origin(type_arg).__name__} is not supported. "
                "Only list generic types are supported."
            )
        elif get_origin(type_arg) is not None:
            type_str = str(type_arg)
        else:
            type_str = type_arg.__name__
        type_strings.append(type_str)

    return " or ".join(type_strings)


def search_submodels(type_annotation: Any) -> list[type[BaseModel]]:
    """Search for Pydantic subtypes in type annotations.

    Args:
        type_annotation: Type annotation to search for subtypes

    Returns:
        List of Pydantic models found
    """
    origin = get_origin(type_annotation)
    if origin is list:
        type_args = (type_annotation,)
    elif isinstance(type_annotation, type) and issubclass(type_annotation, BaseModel):
        type_args = (type_annotation,)
    else:
        type_args = get_args(type_annotation)

    submodels = []
    for type_arg in type_args:
        if get_origin(type_arg) is list:
            type_arg = type_arg.__args__[0]
        if isinstance(type_arg, type):
            if issubclass(type_arg, BaseModel):
                submodels.append(type_arg)

    return submodels


def get_pydantic_model_str(
    pydantic_model: type[BaseModel],
    exclude_id: bool = True,
    add_curls: bool = True,
    add_comma: bool = True,
) -> tuple[str, list[BaseModel]]:
    """Get string representation of Pydantic model.

    Args:
        pydantic_model: Pydantic model class to convert
        exclude_id: Whether to exclude the 'id' field (default: True)
        add_curls: Whether to wrap in curly braces (default: True)
        add_comma: Whether to use commas as separators (default: True)

    Returns:
        Tuple containing:
            - String representation of the Pydantic model
            - List of nested Pydantic submodels found in the model

    Example:
        >>> class Person(BaseModel):
        ...     name: str
        ...     age: List[str]
        >>> get_pydantic_model_str(Person)
        ("{\\n  name: str,\\n  age: list[str]\\n}", [])
    """
    prompt_lines = []
    sub_pydantic_models = []
    for field_name, field_info in pydantic_model.model_fields.items():
        if exclude_id and field_name == "id":
            continue
        descr = field_info.description or None
        types = types_to_str(field_info.annotation)
        if descr:
            prompt_lines.append(f"  // {descr}\n  {field_name}: {types}")
        else:
            prompt_lines.append(f"  {field_name}: {types}")

        sub_pydantic = search_submodels(field_info.annotation)
        if sub_pydantic:
            sub_pydantic_models.extend(sub_pydantic)

    if add_comma:
        separator = ",\n"
    else:
        separator = "\n"
    model_body = f"{separator.join(prompt_lines)}"
    if add_curls:
        model_body = f"{{\n{model_body}\n}}"

    return model_body, sub_pydantic_models


def collect_pydantic_strs(
    pydantic_models: type[BaseModel] | list[type[BaseModel]],
    exclude_id: bool = True,
    add_curls: bool = True,
    add_comma: bool = True,
    add_model_name: bool = False,
) -> list[str]:
    """Collect string representations of Pydantic models and their nested submodels.

    Recursively processes Pydantic models to generate string representations,
    including all nested submodels found within the models.

    Args:
        pydantic_models: Single Pydantic model or list of models to convert
        exclude_id: Whether to exclude the 'id' field (default: True)
        add_curls: Whether to wrap in curly braces (default: True)
        add_comma: Whether to use commas as separators (default: True)
        add_model_name: Whether to prepend model name to string (default: False)

    Returns:
        List of string representations for all models and their submodels
    """
    if not isinstance(pydantic_models, list):
        pydantic_models = [pydantic_models]
    pydantic_strs = []
    for pydantic_model in pydantic_models:
        pydantic_str, submodels = get_pydantic_model_str(
            pydantic_model,
            exclude_id=exclude_id,
            add_curls=add_curls,
            add_comma=add_comma,
        )
        if add_model_name:
            pydantic_str = f"{pydantic_model.__name__}: " + pydantic_str
        pydantic_strs.append(pydantic_str)
        if submodels:
            pydantic_strs.extend(
                collect_pydantic_strs(
                    submodels,
                    exclude_id=exclude_id,
                    add_curls=add_curls,
                    add_comma=add_comma,
                    add_model_name=True,
                )
            )

    return pydantic_strs


def pydantic_to_prompt(
    pydantic_model: type[BaseModel],
    exclude_id: bool = True,
    add_curls: bool = True,
    add_comma: bool = True,
) -> str:
    """Convert Pydantic model to human-readable prompt format.

    Args:
        pydantic_model: Pydantic model class to convert
        exclude_id: Whether to exclude the 'id' field (default: True)
        add_curls: Whether to wrap in curly braces (default: True)
        add_comma: Whether to use commas as separators (default: True)

    Returns:
        String representation of the Pydantic model suitable for prompts
    """
    pydantic_strs = collect_pydantic_strs(
        pydantic_model,
        exclude_id=exclude_id,
        add_curls=add_curls,
        add_comma=add_comma,
    )
    body = pydantic_strs[0]
    if len(pydantic_strs) > 1:
        subtypes = pydantic_strs[1:]
        deduplicated_subtypes = list(dict.fromkeys(subtypes))

        body += "\n**JSON Subtypes:**\n"
        body += "\n".join(deduplicated_subtypes)

    return body


def get_diagnosis_criteria(pathology: str) -> str | None:
    """Load diagnosis criteria from .j2 file.

    Args:
        pathology: Pathology name (e.g., 'pancreatitis', 'appendicitis')

    Returns:
        Diagnosis criteria text, or None if not found
    """
    criteria_file = CRITERIA_DIR / f"{pathology.lower()}.j2"
    if criteria_file.exists():
        return criteria_file.read_text().strip()
    return None


def get_all_diagnosis_criteria() -> dict[str, str]:
    """Load all diagnosis criteria from .j2 files.

    Returns:
        Dictionary mapping pathology name to criteria text
    """
    return {f.stem: f.read_text().strip() for f in CRITERIA_DIR.glob("*.j2")}
