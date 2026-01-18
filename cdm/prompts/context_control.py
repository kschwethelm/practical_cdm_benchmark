"""Context length control with hierarchical summarization (cascading approach).

This module implements a cascading context control strategy:
1. Start with ALL imaging regions in the prompt
2. If over limit -> filter to abdomen-only imaging (no summarization)
3. If still over -> summarize individual abdomen reports
4. If still over -> summarize the combined summaries
5. If still over -> hard truncate

Note: Only imaging is affected. Labs, history, physical exam, microbiology are never touched.
"""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from langchain_openai import ChatOpenAI
from loguru import logger
from transformers import PreTrainedTokenizerBase

from cdm.benchmark.data_models import HadmCase
from cdm.prompts.gen_prompt_full_info import create_user_prompt
from cdm.prompts.text_utils import calculate_num_tokens, truncate_text

# Load Jinja2 environment for templates
TEMPLATE_DIR = Path(__file__).parent
jinja_env = Environment(loader=FileSystemLoader(searchpath=TEMPLATE_DIR))


def create_summarization_prompt() -> str:
    """Load summarization system prompt from Jinja2 template.

    Returns:
        System prompt string for summarization (exact MIMIC-CDM prompt).
    """
    template = jinja_env.get_template("full_info/summarize.j2")
    return template.render()


def format_abdomen_only_imaging(case: HadmCase) -> str:
    """Format imaging reports filtered to abdomen region only.

    Args:
        case: HadmCase containing radiology reports

    Returns:
        Formatted string with abdomen-only imaging reports
    """
    imaging_results = ""
    for imaging in case.radiology_reports:
        if imaging.region == "Abdomen":
            modality = imaging.modality or ""
            reports = imaging.text or ""
            imaging_results += f"{modality} {imaging.region}\n"
            imaging_results += f"{reports}\n\n"
    return imaging_results.strip()


async def summarize_single_report(
    llm: ChatOpenAI,
    report_text: str,
    summarization_prompt: str,
) -> str:
    """Summarize a single radiology report using the LLM.

    Args:
        llm: ChatOpenAI client (raw, not with structured output)
        report_text: The radiology report text to summarize
        summarization_prompt: System prompt for summarization

    Returns:
        Summarized report text
    """
    response = await llm.ainvoke(
        [
            {"role": "system", "content": summarization_prompt},
            {"role": "user", "content": f"Please summarize the following result:\n{report_text}"},
        ]
    )
    return response.content


async def summarize_imaging_reports(
    llm: ChatOpenAI,
    case: HadmCase,
    tokenizer: PreTrainedTokenizerBase,
    max_imaging_tokens: int,
    summarization_prompt: str,
) -> str:
    """Summarize abdomen imaging reports using hierarchical approach.

    Stage 1: Summarize individual abdomen reports (one per modality)
    Stage 2: If still too long, summarize the summaries
    Stage 3: If still too long, hard truncate

    Args:
        llm: ChatOpenAI client (raw, not with structured output)
        case: HadmCase containing radiology reports
        tokenizer: Tokenizer for counting tokens
        max_imaging_tokens: Maximum tokens allowed for imaging section
        summarization_prompt: System prompt for summarization

    Returns:
        Summarized/truncated imaging reports string
    """
    # Filter to abdomen only and deduplicate by modality
    seen_modalities: set[str] = set()
    abdomen_reports: list[tuple[str, str]] = []  # (modality, text)

    for imaging in case.radiology_reports:
        if imaging.region == "Abdomen" and imaging.modality not in seen_modalities:
            abdomen_reports.append((imaging.modality or "Unknown", imaging.text or ""))
            seen_modalities.add(imaging.modality or "Unknown")

    if not abdomen_reports:
        logger.debug("No abdomen imaging reports found")
        return ""

    logger.info(f"Summarizing {len(abdomen_reports)} abdomen imaging reports")

    # Stage 1: Summarize each report individually
    summaries: list[str] = []
    for modality, report_text in abdomen_reports:
        if report_text:
            logger.debug(f"Summarizing {modality} report ({len(report_text)} chars)")
            summary = await summarize_single_report(llm, report_text, summarization_prompt)
            summaries.append(summary)
            logger.debug(f"Summary: {len(summary)} chars")

    combined_summaries = "\n".join(summaries)
    combined_tokens = calculate_num_tokens(tokenizer, combined_summaries)
    logger.info(f"After individual summarization: {combined_tokens} tokens")

    # Stage 2: If still too long, summarize the summaries
    if combined_tokens > max_imaging_tokens:
        logger.info("Combined summaries still too long, summarizing summaries...")
        combined_summaries = await summarize_single_report(
            llm, combined_summaries, summarization_prompt
        )
        combined_tokens = calculate_num_tokens(tokenizer, combined_summaries)
        logger.info(f"After summary of summaries: {combined_tokens} tokens")

    # Stage 3: Hard truncate if still too long
    if combined_tokens > max_imaging_tokens:
        logger.warning(f"Truncating imaging from {combined_tokens} to {max_imaging_tokens} tokens")
        combined_summaries = truncate_text(tokenizer, combined_summaries, max_imaging_tokens)

    return combined_summaries


async def control_context_length(
    llm: ChatOpenAI,
    patient_info: dict,
    case: HadmCase,
    system_prompt: str,
    tokenizer: PreTrainedTokenizerBase,
    max_context_length: int,
    final_diagnosis_tokens: int = 25,
) -> dict:
    """Control context length using cascading approach.

    Cascading steps (only imaging is affected):
    1. Start with all imaging regions
    2. If over limit -> filter to abdomen-only (no summarization)
    3. If still over -> summarize abdomen reports
    4. If still over -> summarize the summaries
    5. If still over -> hard truncate

    Args:
        llm: ChatOpenAI client (raw, not with structured output)
        patient_info: Dictionary with patient information (will be modified)
        case: HadmCase for accessing raw radiology reports
        system_prompt: System prompt string
        tokenizer: Tokenizer for counting tokens
        max_context_length: Maximum context length for the model
        final_diagnosis_tokens: Tokens to reserve for model output (default 25)

    Returns:
        Modified patient_info dict with adjusted imaging_reports if needed
    """
    available_tokens = max_context_length - final_diagnosis_tokens

    # Step 1: Check current token count (all imaging regions)
    user_prompt = create_user_prompt(patient_info)
    full_prompt = system_prompt + user_prompt
    initial_tokens = calculate_num_tokens(tokenizer, full_prompt)

    logger.info(f"Step 1 - All imaging: {initial_tokens} / {available_tokens} tokens")

    if initial_tokens <= available_tokens:
        logger.info("Prompt within context limit, no changes needed")
        return patient_info

    # Step 2: Filter to abdomen-only imaging (no summarization yet)
    logger.info("Step 2 - Filtering to abdomen-only imaging...")
    abdomen_only_imaging = format_abdomen_only_imaging(case)
    patient_info["imaging_reports"] = abdomen_only_imaging

    user_prompt = create_user_prompt(patient_info)
    full_prompt = system_prompt + user_prompt
    current_tokens = calculate_num_tokens(tokenizer, full_prompt)

    logger.info(f"Step 2 - Abdomen only: {current_tokens} / {available_tokens} tokens")

    if current_tokens <= available_tokens:
        compression = (initial_tokens - current_tokens) / initial_tokens * 100
        logger.success(f"Abdomen filtering sufficient: {compression:.1f}% reduction")
        return patient_info

    # Calculate max tokens available for imaging
    patient_info_no_imaging = patient_info.copy()
    patient_info_no_imaging["imaging_reports"] = ""
    user_prompt_no_imaging = create_user_prompt(patient_info_no_imaging)
    tokens_without_imaging = calculate_num_tokens(tokenizer, system_prompt + user_prompt_no_imaging)
    max_imaging_tokens = available_tokens - tokens_without_imaging

    logger.info(f"Max tokens for imaging: {max_imaging_tokens}")

    if max_imaging_tokens < final_diagnosis_tokens:
        # Even without imaging, we're over the limit
        logger.warning("No room for imaging, removing entirely")
        patient_info["imaging_reports"] = ""
        return patient_info

    # Step 3 & 4: Summarize imaging reports (handles summarization cascade internally)
    logger.info("Step 3 - Summarizing abdomen imaging...")
    summarization_prompt = create_summarization_prompt()

    summarized_imaging = await summarize_imaging_reports(
        llm=llm,
        case=case,
        tokenizer=tokenizer,
        max_imaging_tokens=max_imaging_tokens,
        summarization_prompt=summarization_prompt,
    )

    patient_info["imaging_reports"] = summarized_imaging

    # Log final stats
    final_user_prompt = create_user_prompt(patient_info)
    final_tokens = calculate_num_tokens(tokenizer, system_prompt + final_user_prompt)
    compression_ratio = (initial_tokens - final_tokens) / initial_tokens * 100

    logger.success(
        f"Context control complete: {initial_tokens} -> {final_tokens} tokens "
        f"({compression_ratio:.1f}% reduction)"
    )

    return patient_info
