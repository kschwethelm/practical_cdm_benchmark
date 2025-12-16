# Load environment variables from .env file BEFORE importing loguru
# This ensures LOGURU_LEVEL is available when logger is initialized
from dotenv import load_dotenv

load_dotenv()

# ruff: noqa: E402 - imports after load_dotenv() are intentional
import asyncio
from pathlib import Path

import hydra
from langchain_core.runnables import Runnable
from loguru import logger
from omegaconf import DictConfig
from openai import BadRequestError, LengthFinishReasonError
from tqdm.asyncio import tqdm

from cdm.benchmark.data_models import AgentRunResult, EvalOutput, HadmCase
from cdm.benchmark.utils import load_cases, write_result_to_jsonl
from cdm.evaluators import get_evaluator
from cdm.llms.agent import build_agent, build_llm, run_agent_async
from cdm.tools import set_current_case


async def process_case(
    agent: Runnable,
    case: HadmCase,
    semaphore: asyncio.Semaphore,
) -> tuple[HadmCase, AgentRunResult]:
    """Process a single case with semaphore-based rate limiting."""
    async with semaphore:
        patient_info = case.patient_history
        set_current_case(case)

        if not case.pathology:
            logger.warning(f"No pathology for case: {case.hadm_id}")
            return None
        try:
            output = await run_agent_async(agent, patient_info)
        except BadRequestError as e:
            if "maximum context length" in str(e).lower():
                logger.error(f"Skipping case {case.hadm_id} due to context length overflow.")
            else:
                logger.error(f"{case.hadm_id} resulted in error {e}")
            return None
        except LengthFinishReasonError:
            logger.error(f"Skipping case {case.hadm_id} due to model output token overflow")
            return None

        return case, output


async def run_benchmark(cfg: DictConfig):
    """Run CDM benchmark with concurrent async processing."""
    dataset = load_cases(cfg.benchmark_data_path, cfg.num_cases)
    llm = build_llm(cfg.base_url, cfg.temperature)
    agent = build_agent(llm, cfg.enabled_tools)

    # Create semaphore for rate limiting concurrent requests
    max_concurrent = cfg.max_concurrent_requests
    semaphore = asyncio.Semaphore(max_concurrent)

    # Setup output file if configured
    output_path = cfg.results_output_path
    write_lock = asyncio.Lock()
    if output_path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        # Clear existing file
        output_path.write_text("")
        logger.info(f"Writing results to: {output_path}")
    logger.info(f"Processing {len(dataset)} cases with max concurrency: {max_concurrent}")

    # Create tasks for all cases
    tasks = [process_case(agent, case, semaphore) for case in dataset]

    # Process with async progress bar and write results incrementally
    results = []
    for coro in tqdm.as_completed(tasks, total=len(tasks), desc="Processing cases"):
        result = await coro
        if result is None:
            continue

        case, output = result
        results.append((case, output))

        try:
            evaluator = get_evaluator(case.pathology, case.ground_truth)
            answers, scores = evaluator.evaluate_case(output)
        except ValueError as e:
            logger.error(e)
            answers, scores = None, None

        if output_path:
            eval_output = EvalOutput(
                hadm_id=case.hadm_id,
                ground_truth=case.ground_truth,
                pathology=case.pathology.value,
                prediction=output.parsed_output,
                num_tool_calls=output.num_tool_calls,
                answers=answers,
                scores=scores,
            )
            await write_result_to_jsonl(output_path, eval_output.model_dump(), write_lock)

    logger.success(f"Benchmark complete - processed {len(results)} cases")
    if output_path:
        logger.success(f"Results saved to: {output_path}")


@hydra.main(version_base=None, config_path="../configs/benchmark", config_name="cdm")
def main(cfg: DictConfig):
    """Run CDM benchmark with async concurrent processing.

    The agent can dynamically query clinical tools to gather information and
    make a diagnosis based on the patient's history. Cases are processed
    concurrently to maximize throughput.
    """
    model_name = cfg.model_name
    cfg.results_output_path = cfg.results_output_paths.get(model_name)


if __name__ == "__main__":
    main()
