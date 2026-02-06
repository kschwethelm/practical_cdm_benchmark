"""Test script to evaluate the retrieve_diagnosis_criteria tool with real benchmark cases.

This script loads patient cases from the benchmark and tests what the diagnosis
criteria tool returns when given the patient's clinical information.

Usage:
    # Test with 5 random cases
    uv run python scripts/test_diagnosis_criteria_tool.py

    # Test with specific number of cases
    uv run python scripts/test_diagnosis_criteria_tool.py --num-cases 10

    # Test specific case by hadm_id
    uv run python scripts/test_diagnosis_criteria_tool.py --hadm-id 20000602

    # Interactive mode
    uv run python scripts/test_diagnosis_criteria_tool.py --interactive

    # Show all keywords
    uv run python scripts/test_diagnosis_criteria_tool.py --show-keywords
"""

import argparse
import json
import random
from pathlib import Path

from cdm.benchmark.data_models import HadmCase
from cdm.tools.context import set_current_case
from cdm.tools.diagnosis_criteria import (
    retrieve_diagnosis_criteria,
    DIAGNOSIS_CRITERIA,
    _score_match,
)


def load_benchmark_cases(benchmark_path: str, num_cases: int | None = None) -> list[HadmCase]:
    """Load cases from benchmark JSON file."""
    path = Path(benchmark_path)
    with open(path) as f:
        data = json.load(f)
    
    cases = [HadmCase(**case) for case in data["cases"]]
    
    if num_cases:
        cases = random.sample(cases, min(num_cases, len(cases)))
    
    return cases


def extract_clinical_findings(case: HadmCase) -> str:
    """Extract clinical findings from a case to use as tool input.
    
    This mimics what an LLM agent might pass to the tool based on the patient info.
    """
    findings = []
    
    # Add patient history (main clinical narrative)
    if case.patient_history:
        findings.append(case.patient_history)
    
    # Add lab results summary
    if case.lab_results:
        lab_summary = []
        for lab in case.lab_results[:10]:  # Limit to first 10 labs
            if lab.value:
                lab_summary.append(f"{lab.test_name}: {lab.value}")
        if lab_summary:
            findings.append("Labs: " + ", ".join(lab_summary))
    
    # Add radiology findings
    if case.radiology_reports:
        for report in case.radiology_reports[:2]:  # Limit to first 2 reports
            if report.text:
                # Take first 500 chars of report
                findings.append(f"Imaging ({report.exam_name}): {report.text[:500]}")
    
    # Add physical exam findings
    if case.physical_exam_text:
        findings.append(f"Physical Exam: {case.physical_exam_text[:500]}")
    
    return "\n".join(findings)


def test_case(case: HadmCase, verbose: bool = True) -> dict:
    """Test the diagnosis criteria tool with a single case."""
    # Set the current case context
    set_current_case(case)
    
    # Extract clinical findings
    clinical_findings = extract_clinical_findings(case)
    
    # Get scores for each condition
    scores = {cond: _score_match(clinical_findings, cond) 
              for cond in DIAGNOSIS_CRITERIA}
    sorted_scores = sorted(scores.items(), key=lambda x: -x[1])
    
    # Get tool output
    tool_output = retrieve_diagnosis_criteria.invoke(clinical_findings)
    
    # Check if ground truth pathology is in top matches
    ground_truth = case.pathology.value if case.pathology else None
    top_conditions = [cond for cond, score in sorted_scores[:3] if score > 0]
    correct_in_top3 = ground_truth in top_conditions if ground_truth else None
    
    result = {
        "hadm_id": case.hadm_id,
        "ground_truth": ground_truth,
        "scores": dict(sorted_scores),
        "top_3": top_conditions,
        "correct_in_top3": correct_in_top3,
        "tool_output": tool_output,
    }
    
    if verbose:
        print("\n" + "=" * 80)
        print(f"CASE: {case.hadm_id}")
        print(f"GROUND TRUTH: {ground_truth}")
        print("=" * 80)
 
        
        print("\n--- CONDITION SCORES ---")
        for cond, score in sorted_scores:
            marker = " ✓" if cond == ground_truth else ""
            print(f"  {cond}: {score}{marker}")
        
        
        print("\n--- TOOL OUTPUT ---")
        print(tool_output)
    
    return result


def show_keywords():
    """Display all keywords the tool can match against."""
    print("\n" + "=" * 80)
    print("AVAILABLE KEYWORDS BY CONDITION")
    print("=" * 80)
    
    for condition, data in DIAGNOSIS_CRITERIA.items():
        print(f"\n### {condition.upper()} ###")
        for category in ["symptoms", "exam_findings", "labs", "imaging"]:
            keywords = data.get(category, [])
            print(f"  {category}: {keywords}")
        print(f"  criteria: {data.get('criteria', [])}")


def interactive_mode(cases: list[HadmCase]):
    """Interactive mode to explore cases."""
    print("\n" + "=" * 80)
    print("INTERACTIVE MODE")
    print("Commands:")
    print("  <number>  - Test case by index")
    print("  hadm <id> - Test case by hadm_id")
    print("  list      - List all loaded cases")
    print("  custom    - Enter custom clinical findings")
    print("  quit      - Exit")
    print("=" * 80)
    
    case_map = {c.hadm_id: c for c in cases}
    
    while True:
        cmd = input("\nCommand: ").strip().lower()
        
        if cmd in ('quit', 'exit', 'q'):
            break
        elif cmd == 'list':
            for i, c in enumerate(cases):
                print(f"  [{i}] {c.hadm_id} - {c.pathology.value if c.pathology else 'unknown'}")
        elif cmd == 'custom':
            findings = input("Enter clinical findings: ").strip()
            if findings:
                print("\n--- CONDITION SCORES ---")
                for cond in DIAGNOSIS_CRITERIA:
                    score = _score_match(findings, cond)
                    print(f"  {cond}: {score}")
                print("\n--- TOOL OUTPUT ---")
                print(retrieve_diagnosis_criteria.invoke(findings))
        elif cmd.startswith('hadm '):
            try:
                hadm_id = int(cmd.split()[1])
                if hadm_id in case_map:
                    test_case(case_map[hadm_id])
                else:
                    print(f"Case {hadm_id} not found in loaded cases")
            except (ValueError, IndexError):
                print("Invalid hadm_id")
        else:
            try:
                idx = int(cmd)
                if 0 <= idx < len(cases):
                    test_case(cases[idx])
                else:
                    print(f"Index out of range (0-{len(cases)-1})")
            except ValueError:
                print("Unknown command")


def run_batch_evaluation(cases: list[HadmCase]) -> dict:
    """Run evaluation on multiple cases and compute accuracy."""
    results = []
    correct = 0
    total = 0
    
    for case in cases:
        result = test_case(case, verbose=False)
        results.append(result)
        
        if result["ground_truth"] and result["correct_in_top3"] is not None:
            total += 1
            if result["correct_in_top3"]:
                correct += 1
    
    accuracy = correct / total if total > 0 else 0
    
    print("\n" + "=" * 80)
    print("BATCH EVALUATION RESULTS")
    print("=" * 80)
    print(f"Total cases: {len(cases)}")
    print(f"Cases with ground truth: {total}")
    print(f"Correct in top 3: {correct}/{total} ({accuracy:.1%})")
    
    # Show breakdown by pathology
    by_pathology = {}
    for r in results:
        gt = r["ground_truth"]
        if gt:
            if gt not in by_pathology:
                by_pathology[gt] = {"correct": 0, "total": 0}
            by_pathology[gt]["total"] += 1
            if r["correct_in_top3"]:
                by_pathology[gt]["correct"] += 1
    
    print("\nBy pathology:")
    for path, stats in sorted(by_pathology.items()):
        acc = stats["correct"] / stats["total"] if stats["total"] > 0 else 0
        print(f"  {path}: {stats['correct']}/{stats['total']} ({acc:.1%})")
    
    # Show cases where ground truth was NOT in top 3
    print("\nMissed cases (ground truth not in top 3):")
    for r in results:
        if r["ground_truth"] and not r["correct_in_top3"]:
            print(f"  {r['hadm_id']}: GT={r['ground_truth']}, Top3={r['top_3']}")
    
    return {"accuracy": accuracy, "results": results}


def main():
    parser = argparse.ArgumentParser(description="Test diagnosis criteria tool")
    parser.add_argument("--benchmark-path", default="database/output/benchmark_data.json",
                        help="Path to benchmark JSON file")
    parser.add_argument("--num-cases", type=int, default=5,
                        help="Number of random cases to test")
    parser.add_argument("--hadm-id", type=int, help="Test specific case by hadm_id")
    parser.add_argument("--interactive", action="store_true", help="Interactive mode")
    parser.add_argument("--show-keywords", action="store_true", help="Show all keywords")
    parser.add_argument("--batch", action="store_true", help="Run batch evaluation")
    parser.add_argument("--all", action="store_true", help="Test all cases (with --batch)")
    
    args = parser.parse_args()
    
    if args.show_keywords:
        show_keywords()
        return
    
    # Load cases
    num_to_load = None if args.all or args.interactive else args.num_cases
    if args.hadm_id:
        # Load all cases to find the specific one
        all_cases = load_benchmark_cases(args.benchmark_path)
        cases = [c for c in all_cases if c.hadm_id == args.hadm_id]
        if not cases:
            print(f"Case {args.hadm_id} not found")
            return
    else:
        cases = load_benchmark_cases(args.benchmark_path, num_to_load)
    
    print(f"Loaded {len(cases)} cases")
    
    if args.interactive:
        show_keywords()
        interactive_mode(cases)
    elif args.batch:
        run_batch_evaluation(cases)
    elif args.hadm_id:
        test_case(cases[0])
    else:
        for case in cases:
            test_case(case)


if __name__ == "__main__":
    main()
