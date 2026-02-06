"""Analyze keyword matching for diagnosis criteria tool.

This script extracts clinical findings from benchmark cases and shows:
1. What keywords are present in each case
2. What keywords are being matched by the tool
3. What keywords are missing (present in text but not in our criteria)

Use this to iteratively improve keyword weights and coverage.

Usage:
    uv run python scripts/analyze_diagnosis_keywords.py --num-cases 100
    uv run python scripts/analyze_diagnosis_keywords.py --num-cases 100 --output analysis_output.json
    uv run python scripts/analyze_diagnosis_keywords.py --pathology appendicitis --num-cases 50
"""

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from loguru import logger

from cdm.benchmark.data_models import HadmCase, Pathology
from cdm.tools.diagnosis_criteria import DIAGNOSIS_CRITERIA, _normalize_text, _score_match


def load_benchmark_cases(benchmark_path: Path) -> list[HadmCase]:
    """Load cases directly from benchmark JSON file."""
    with open(benchmark_path) as f:
        data = json.load(f)
    
    cases = [HadmCase(**case) for case in data["cases"]]
    return cases


def extract_clinical_sections(case: HadmCase) -> dict[str, str]:
    """Extract different clinical sections from a case."""
    sections = {}
    
    # Patient history
    if case.patient_history:
        sections["history"] = case.patient_history
    
    # Physical exam
    if case.physical_exam_text:
        sections["physical_exam"] = case.physical_exam_text
    
    # Labs - format as text for keyword matching
    if case.lab_results:
        lab_texts = []
        for lab in case.lab_results:
            # Handle different possible attribute names
            test_name = getattr(lab, 'test_name', None) or getattr(lab, 'name', None) or getattr(lab, 'label', 'Unknown')
            value = getattr(lab, 'value', None) or getattr(lab, 'result', '')
            unit = getattr(lab, 'unit', None) or getattr(lab, 'units', None) or ''
            flag = getattr(lab, 'flag', None) or getattr(lab, 'abnormal_flag', None) or ''
            
            lab_text = f"{test_name}: {value}"
            if unit:
                lab_text += f" {unit}"
            if flag:
                lab_text += f" ({flag})"
            lab_texts.append(lab_text)
        sections["labs"] = "\n".join(lab_texts)
    
    # Radiology
    if case.radiology_reports:
        rad_texts = []
        for report in case.radiology_reports:
            text = getattr(report, 'text', None) or getattr(report, 'report_text', '')
            exam_name = getattr(report, 'exam_name', None) or getattr(report, 'name', 'Unknown')
            if text:
                rad_texts.append(f"[{exam_name}]: {text}")
        sections["imaging"] = "\n".join(rad_texts)
    
    # Combined for scoring
    sections["combined"] = "\n".join(sections.values())
    
    return sections


def find_matched_keywords(text: str, condition: str) -> dict[str, list[tuple[str, float]]]:
    """Find which keywords matched for a condition."""
    text_normalized = _normalize_text(text)
    data = DIAGNOSIS_CRITERIA.get(condition, {})
    matched = defaultdict(list)
    
    for category in ["symptoms", "exam_findings", "labs", "imaging"]:
        keywords = data.get(category, [])
        for item in keywords:
            if isinstance(item, tuple):
                keyword, weight = item
            else:
                keyword, weight = item, 1.0
            
            pattern = re.escape(keyword.lower())
            if re.search(pattern, text_normalized):
                matched[category].append((keyword, weight))
    
    return dict(matched)


def find_potential_keywords(text: str) -> list[str]:
    """Extract potential clinical keywords from text that might be useful."""
    text_lower = text.lower()
    
    # Common clinical patterns to look for
    patterns = [
        # Pain locations
        r'\b(rlq|llq|ruq|luq|epigastric|periumbilical|flank|suprapubic)\s*(pain|tenderness)?',
        r'\b(right|left)\s*(lower|upper)\s*quadrant',
        # Signs
        r"\b(murphy|mcburney|rovsing|psoas|obturator|cullen|grey.?turner)\s*(sign|positive)?",
        r'\b(rebound|guarding|rigidity|distension)',
        # Lab patterns
        r'\bwbc[:\s]*(\d+\.?\d*)',
        r'\b(lipase|amylase|bilirubin|alt|ast|crp)[:\s]*(\d+\.?\d*)',
        r'\b(leukocytosis|elevated\s+\w+)',
        # Imaging findings
        r'\b(appendix|gallbladder|pancrea\w+|diverticul\w+)',
        r'\b(wall\s+thickening|fat\s+stranding|fluid\s+collection|abscess)',
        r'\b(dilated|enlarged|inflam\w+|edema)',
    ]
    
    found = []
    for pattern in patterns:
        matches = re.findall(pattern, text_lower)
        for match in matches:
            if isinstance(match, tuple):
                found.append(" ".join(m for m in match if m))
            else:
                found.append(match)
    
    return list(set(found))


def analyze_case(case: HadmCase) -> dict:
    """Analyze a single case for keyword matching."""
    sections = extract_clinical_sections(case)
    combined_text = sections.get("combined", "")
    ground_truth = case.pathology.value if case.pathology else None
    
    # Score all conditions
    scores = {}
    matched_keywords = {}
    for condition in DIAGNOSIS_CRITERIA:
        scores[condition] = _score_match(combined_text, condition)
        matched_keywords[condition] = find_matched_keywords(combined_text, condition)
    
    # Sort by score
    sorted_conditions = sorted(scores.items(), key=lambda x: -x[1])
    top_3 = [c for c, s in sorted_conditions[:3] if s > 0]
    
    # Find potential keywords in text
    potential_keywords = find_potential_keywords(combined_text)
    
    # Check if ground truth is in top 3
    correct = ground_truth in top_3 if ground_truth else None
    
    # Get rank of ground truth
    gt_rank = None
    if ground_truth:
        for i, (cond, _) in enumerate(sorted_conditions):
            if cond == ground_truth:
                gt_rank = i + 1
                break
    
    return {
        "hadm_id": case.hadm_id,
        "ground_truth": ground_truth,
        "scores": dict(sorted_conditions),
        "top_3": top_3,
        "correct_in_top3": correct,
        "gt_rank": gt_rank,
        "gt_score": scores.get(ground_truth, 0) if ground_truth else None,
        "matched_keywords": matched_keywords,
        "potential_keywords": potential_keywords,
        "sections": {k: v[:500] + "..." if len(v) > 500 else v 
                    for k, v in sections.items() if k != "combined"},
    }


def aggregate_results(results: list[dict]) -> dict:
    """Aggregate analysis results across all cases."""
    # Overall accuracy
    total_with_gt = sum(1 for r in results if r["ground_truth"])
    correct_top3 = sum(1 for r in results if r["correct_in_top3"])
    correct_top1 = sum(1 for r in results if r["top_3"] and r["top_3"][0] == r["ground_truth"])
    
    # By pathology
    by_pathology = defaultdict(lambda: {"total": 0, "correct_top3": 0, "correct_top1": 0, 
                                         "avg_gt_score": 0, "avg_gt_rank": 0})
    for r in results:
        gt = r["ground_truth"]
        if gt:
            by_pathology[gt]["total"] += 1
            if r["correct_in_top3"]:
                by_pathology[gt]["correct_top3"] += 1
            if r["top_3"] and r["top_3"][0] == gt:
                by_pathology[gt]["correct_top1"] += 1
            by_pathology[gt]["avg_gt_score"] += r["gt_score"] or 0
            by_pathology[gt]["avg_gt_rank"] += r["gt_rank"] or 0
    
    # Calculate averages
    for gt, stats in by_pathology.items():
        if stats["total"] > 0:
            stats["avg_gt_score"] /= stats["total"]
            stats["avg_gt_rank"] /= stats["total"]
            stats["accuracy_top3"] = stats["correct_top3"] / stats["total"]
            stats["accuracy_top1"] = stats["correct_top1"] / stats["total"]
    
    # Most common matched keywords per pathology
    keyword_counts = defaultdict(lambda: defaultdict(Counter))
    for r in results:
        gt = r["ground_truth"]
        if gt and gt in r["matched_keywords"]:
            for category, keywords in r["matched_keywords"].get(gt, {}).items():
                for kw, weight in keywords:
                    keyword_counts[gt][category][kw] += 1
    
    # Potential keywords found in text but NOT matched for the GT condition
    # This helps identify keywords we should add to each pathology
    potential_missing_by_pathology = defaultdict(Counter)
    
    # Get all keywords that ARE in our criteria for each condition
    existing_keywords_by_condition = {}
    for condition, data in DIAGNOSIS_CRITERIA.items():
        existing = set()
        for category in ["symptoms", "exam_findings", "labs", "imaging", "negative"]:
            for item in data.get(category, []):
                if isinstance(item, tuple):
                    existing.add(item[0].lower())
                else:
                    existing.add(item.lower())
        existing_keywords_by_condition[condition] = existing
    
    for r in results:
        gt = r["ground_truth"]
        if gt:
            existing_for_gt = existing_keywords_by_condition.get(gt, set())
            # Check each potential keyword
            for kw in r["potential_keywords"]:
                kw_lower = kw.lower().strip()
                # Only count if NOT already in our criteria for this pathology
                if kw_lower and kw_lower not in existing_for_gt:
                    # Also check if it's not a substring of an existing keyword
                    is_covered = any(kw_lower in existing or existing in kw_lower 
                                    for existing in existing_for_gt)
                    if not is_covered:
                        potential_missing_by_pathology[gt][kw_lower] += 1
    
    # Also track keywords that appear in OTHER conditions' cases but might be
    # incorrectly boosting scores (potential negatives to add)
    keywords_causing_confusion = defaultdict(lambda: defaultdict(Counter))
    for r in results:
        gt = r["ground_truth"]
        if gt and r["top_3"] and r["top_3"][0] != gt:
            # This case was misclassified
            wrong_prediction = r["top_3"][0]
            # What keywords matched for the wrong prediction?
            for category, keywords in r["matched_keywords"].get(wrong_prediction, {}).items():
                for kw, weight in keywords:
                    if weight > 0:  # Only positive weights
                        keywords_causing_confusion[gt][wrong_prediction][kw] += 1
    
    # Find missed cases (GT not in top 1)
    missed_cases = [
        {
            "hadm_id": r["hadm_id"],
            "ground_truth": r["ground_truth"],
            "top_3": r["top_3"],
            "gt_score": r["gt_score"],
            "gt_rank": r["gt_rank"],
            "matched_for_gt": r["matched_keywords"].get(r["ground_truth"], {}),
            "matched_for_top1": r["matched_keywords"].get(r["top_3"][0], {}) if r["top_3"] else {},
        }
        for r in results
        if r["ground_truth"] and (not r["top_3"] or r["top_3"][0] != r["ground_truth"])
    ]
    
    return {
        "summary": {
            "total_cases": len(results),
            "cases_with_ground_truth": total_with_gt,
            "correct_top3": correct_top3,
            "correct_top1": correct_top1,
            "accuracy_top3": correct_top3 / total_with_gt if total_with_gt > 0 else 0,
            "accuracy_top1": correct_top1 / total_with_gt if total_with_gt > 0 else 0,
        },
        "by_pathology": dict(by_pathology),
        "keyword_counts": {gt: {cat: dict(counts) for cat, counts in cats.items()} 
                          for gt, cats in keyword_counts.items()},
        "potential_missing_by_pathology": {
            gt: dict(counts.most_common(20)) 
            for gt, counts in potential_missing_by_pathology.items()
        },
        "keywords_causing_confusion": {
            gt: {pred: dict(counts.most_common(10)) for pred, counts in preds.items()}
            for gt, preds in keywords_causing_confusion.items()
        },
        "missed_cases": missed_cases,
    }


def print_analysis(aggregated: dict):
    """Print analysis results in a readable format."""
    print("\n" + "=" * 80)
    print("DIAGNOSIS CRITERIA KEYWORD ANALYSIS")
    print("=" * 80)
    
    summary = aggregated["summary"]
    print(f"\n📊 OVERALL ACCURACY")
    print(f"   Total cases: {summary['total_cases']}")
    print(f"   With ground truth: {summary['cases_with_ground_truth']}")
    print(f"   Correct in Top 3: {summary['correct_top3']} ({summary['accuracy_top3']:.1%})")
    print(f"   Correct in Top 1: {summary['correct_top1']} ({summary['accuracy_top1']:.1%})")
    
    print(f"\n📋 BY PATHOLOGY")
    for pathology, stats in sorted(aggregated["by_pathology"].items()):
        print(f"\n   {pathology.upper()}")
        print(f"      Cases: {stats['total']}")
        print(f"      Top 3 Accuracy: {stats.get('accuracy_top3', 0):.1%}")
        print(f"      Top 1 Accuracy: {stats.get('accuracy_top1', 0):.1%}")
        print(f"      Avg GT Score: {stats['avg_gt_score']:.1f}")
        print(f"      Avg GT Rank: {stats['avg_gt_rank']:.1f}")
    
    print(f"\n🔑 MATCHED KEYWORDS (per pathology)")
    for pathology, categories in aggregated["keyword_counts"].items():
        print(f"\n   {pathology.upper()}")
        for category, keywords in categories.items():
            if keywords:
                top_kw = sorted(keywords.items(), key=lambda x: -x[1])[:5]
                kw_str = ", ".join(f"{kw}({cnt})" for kw, cnt in top_kw)
                print(f"      {category}: {kw_str}")
    
    print(f"\n💡 POTENTIAL MISSING KEYWORDS (by pathology - not in current criteria)")
    for pathology, keywords in sorted(aggregated["potential_missing_by_pathology"].items()):
        if keywords:
            print(f"\n   {pathology.upper()}")
            for kw, count in list(keywords.items())[:10]:
                print(f"      '{kw}': found in {count} cases")
    
    print(f"\n⚠️  KEYWORDS CAUSING MISCLASSIFICATION (by GT pathology)")
    for gt_pathology, confused_with in sorted(aggregated["keywords_causing_confusion"].items()):
        if confused_with:
            print(f"\n   {gt_pathology.upper()} cases misclassified due to:")
            for wrong_pred, keywords in sorted(confused_with.items(), 
                                                key=lambda x: -sum(x[1].values()))[:3]:
                total_cases = sum(keywords.values())
                print(f"      → {wrong_pred} ({total_cases} cases confused):")
                for kw, count in list(keywords.items())[:5]:
                    print(f"         '{kw}': {count} times")
    
    print(f"\n❌ MISSED CASES (GT not Top 1): {len(aggregated['missed_cases'])}")
    for case in aggregated["missed_cases"][:10]:
        print(f"\n   hadm_id: {case['hadm_id']}")
        print(f"   Ground Truth: {case['ground_truth']} (rank: {case['gt_rank']}, score: {case['gt_score']:.1f})")
        print(f"   Top 3: {case['top_3']}")
        print(f"   Matched for GT: {case['matched_for_gt']}")
        if case['top_3']:
            print(f"   Matched for {case['top_3'][0]}: {case['matched_for_top1']}")
    
    if len(aggregated["missed_cases"]) > 10:
        print(f"\n   ... and {len(aggregated['missed_cases']) - 10} more missed cases")


def main():
    parser = argparse.ArgumentParser(description="Analyze diagnosis criteria keywords")
    parser.add_argument("--benchmark-path", default="database/output/benchmark_data.json",
                        help="Path to benchmark JSON file")
    parser.add_argument("--num-cases", type=int, default=100,
                        help="Number of cases to analyze")
    parser.add_argument("--pathology", type=str, default=None,
                        help="Filter by pathology (appendicitis, cholecystitis, etc.)")
    parser.add_argument("--output", type=str, default=None,
                        help="Output JSON file for detailed results")
    parser.add_argument("--show-cases", action="store_true",
                        help="Show detailed per-case analysis")
    
    args = parser.parse_args()
    
    # Load cases directly
    benchmark_path = Path(args.benchmark_path)
    logger.info(f"Loading cases from {benchmark_path}")
    
    if not benchmark_path.exists():
        logger.error(f"Benchmark file not found: {benchmark_path}")
        return
    
    cases = load_benchmark_cases(benchmark_path)
    logger.info(f"Loaded {len(cases)} cases")
    
    # Filter by pathology if specified
    if args.pathology:
        try:
            target_pathology = Pathology(args.pathology.lower())
            cases = [c for c in cases if c.pathology == target_pathology]
            logger.info(f"Filtered to {len(cases)} cases with pathology={args.pathology}")
        except ValueError:
            logger.error(f"Invalid pathology: {args.pathology}")
            logger.info(f"Valid options: {[p.value for p in Pathology]}")
            return
    
    # Limit number of cases
    cases = cases[:args.num_cases]
    logger.info(f"Analyzing {len(cases)} cases")
    
    # Analyze each case
    results = []
    for case in cases:
        result = analyze_case(case)
        results.append(result)
        
        if args.show_cases:
            print(f"\n--- Case {case.hadm_id} (GT: {result['ground_truth']}) ---")
            print(f"Top 3: {result['top_3']} | Correct: {result['correct_in_top3']}")
            print(f"GT Score: {result['gt_score']:.1f} | GT Rank: {result['gt_rank']}")
            if result['ground_truth']:
                print(f"Matched for GT: {result['matched_keywords'].get(result['ground_truth'], {})}")
    
    # Aggregate results
    aggregated = aggregate_results(results)
    
    # Print analysis
    print_analysis(aggregated)
    
    # Save detailed output
    if args.output:
        output_path = Path(args.output)
        output_data = {
            "aggregated": aggregated,
            "cases": results,
        }
        with open(output_path, "w") as f:
            json.dump(output_data, f, indent=2, default=str)
        logger.success(f"Detailed results saved to {output_path}")


if __name__ == "__main__":
    main()