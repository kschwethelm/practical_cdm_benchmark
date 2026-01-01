# Load environment variables from .env file BEFORE importing loguru
# This ensures LOGURU_LEVEL is available when logger is initialized
from dotenv import load_dotenv

load_dotenv()

# ruff: noqa: E402 - imports after load_dotenv() are intentional
import asyncio
from pathlib import Path

import hydra
from langchain_openai import ChatOpenAI
from loguru import logger
from omegaconf import DictConfig
from openai import BadRequestError, LengthFinishReasonError
from tqdm.asyncio import tqdm

from cdm.benchmark.data_models import BenchmarkOutputFullInfo, EvalOutputFullInfo, HadmCase
from cdm.benchmark.utils import gather_all_info, load_cases, write_result_to_jsonl
from cdm.evaluators.pathology_evaluator import PathologyEvaluator
from cdm.llms.agent import build_llm, run_llm_async
from cdm.prompts.gen_prompt_full_info import create_system_prompt, create_user_prompt


async def process_case(
    llm: ChatOpenAI,
    system_prompt: str,
    case: HadmCase,
    semaphore: asyncio.Semaphore,
) -> tuple[HadmCase, BenchmarkOutputFullInfo]:
    """Process a single case with semaphore-based rate limiting."""
    async with semaphore:
        patient_info_dict = gather_all_info(case)
        user_prompt = create_user_prompt(patient_info_dict)
        if not case.pathology:
            logger.warning(f"No pathology for case: {case.hadm_id}")
            return None
        try:
            output = await run_llm_async(llm, system_prompt, user_prompt)
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
    """Run full info benchmark with concurrent async processing."""
    dataset = load_cases(cfg.benchmark_data_path, cfg.num_cases)
    llm = build_llm(cfg.base_url, cfg.temperature)

    system_prompt = create_system_prompt()

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
    tasks = [process_case(llm, system_prompt, case, semaphore) for case in dataset]

    # Process with async progress bar and write results incrementally
    results = []
    for coro in tqdm.as_completed(tasks, total=len(tasks), desc="Processing cases"):
        result = await coro
        if result is None:
            continue

        case, output = result
        results.append((case, output))

        evaluator = PathologyEvaluator(case.ground_truth, case.pathology)
        scores = evaluator.evaluate_case(output)

        if output_path:
            eval_output = EvalOutputFullInfo(
                hadm_id=case.hadm_id,
                ground_truth=case.ground_truth,
                pathology=case.pathology.value,
                prediction=output,
                scores=scores,
            )
            await write_result_to_jsonl(output_path, eval_output.model_dump(), write_lock)

    logger.success(f"Benchmark complete - processed {len(results)} cases")
    if output_path:
        logger.success(f"Results saved to: {output_path}")


@hydra.main(version_base=None, config_path="../configs/benchmark", config_name="full_info")
def main(cfg: DictConfig):
    """Run full info benchmark with async concurrent processing.

    The LLM is provided all information upfront (LLM as second reader).
    Cases are processed concurrently to maximize throughput.
    """
    model_name = cfg.model_name
    if model_name is None:
        raise ValueError("model_name must be specified in config or via command line override")
    if model_name not in cfg.results_output_paths:
        raise ValueError(
            f"Unknown model_name: {model_name}. Available: {list(cfg.results_output_paths.keys())}"
        )
    cfg.results_output_path = cfg.results_output_paths.get(model_name)

    asyncio.run(run_benchmark(cfg))


# Run example: "python scripts/run_benchmark_full_info.py model_name=qwen3"
if __name__ == "__main__":
    main()
