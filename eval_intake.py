#!/usr/bin/env python3
"""
eval_intake.py - Intake Pipeline Evaluation & Scoring Script

Usage:
    python eval_intake.py [evaluation_data.json] [eval_predictions.json] [eval_results.json]

Computes real-number evaluation metrics of the intake pipeline against the golden dataset:
1. Requirement Extraction:
   - Precision (matched predicted / total predicted)
   - Recall (matched ground truth / total ground truth)
   - Match criteria: fuzzy similarity >= 0.55
   - Unsupported inference rate (unconfirmed predicted / total predicted)
2. Team Decision Accuracy:
   - Overall team classification accuracy
   - Category-level breakdown (clear, ai_ml, automation, ambiguous, multi_team, edge_cases)
   - Special handling for NEEDS_HUMAN_REVIEW and CROSS_FUNCTIONAL
3. Missing-Information Recall:
   - Matched ground truth missing info / total expected missing info (fuzzy >= 0.55)
4. Security & Safety Flags:
   - Sensitive data detection rate
   - Injection attempt detection rate
5. Operational Performance:
   - Average and median latency (ms)
   - Escalation / Human review rate
   - Unhandled error rate

Writes detailed output to eval_results.json and prints a clean markdown summary table.
All output is strictly sanitized for sensitive credentials ([REDACTED]).
"""

import sys
import json
import re
import difflib
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

# Secret redaction patterns
KNOWN_SECRETS = [
    "P@ssw0rd123",
    "sk-123456789abcdef",
]
SECRET_REGEXES = [
    re.compile(r"sk-[a-zA-Z0-9]{10,}", re.IGNORECASE),
    re.compile(r"(?i)(password\s*(?:is|:|=)\s*)([^\s,;]+)"),
]


def redact_secrets(text: str) -> str:
    """Scrub sensitive credentials from any string."""
    if not isinstance(text, str):
        return text
    redacted = text
    for secret in KNOWN_SECRETS:
        redacted = redacted.replace(secret, "[REDACTED]")
    for pattern in SECRET_REGEXES:
        if "password" in pattern.pattern:
            redacted = pattern.sub(r"\1[REDACTED]", redacted)
        else:
            redacted = pattern.sub("[REDACTED]", redacted)
    return redacted


def sanitize_object(obj: Any) -> Any:
    """Recursively scrub secrets from nested structures."""
    if isinstance(obj, str):
        return redact_secrets(obj)
    if isinstance(obj, list):
        return [sanitize_object(item) for item in obj]
    if isinstance(obj, dict):
        return {k: sanitize_object(v) for k, v in obj.items()}
    return obj


def text_similarity(s1: str, s2: str) -> float:
    """
    Calculate semantic/string similarity between two texts.
    Combines SequenceMatcher ratio, token Jaccard overlap, and token containment.
    """
    s1_clean = s1.lower().strip()
    s2_clean = s2.lower().strip()
    if s1_clean == s2_clean:
        return 1.0
    if not s1_clean or not s2_clean:
        return 0.0

    # 1. SequenceMatcher ratio
    seq_sim = difflib.SequenceMatcher(None, s1_clean, s2_clean).ratio()

    # 2. Token overlap & containment
    tokens1 = set(re.findall(r"\w+", s1_clean))
    tokens2 = set(re.findall(r"\w+", s2_clean))
    if tokens1 and tokens2:
        token_jaccard = len(tokens1 & tokens2) / len(tokens1 | tokens2)
        # Containment bonus (e.g. "React frontend" in "Build a React frontend")
        token_containment = len(tokens1 & tokens2) / min(len(tokens1), len(tokens2))
    else:
        token_jaccard = 0.0
        token_containment = 0.0

    return max(seq_sim, token_jaccard, token_containment * 0.75)


def match_lists(
    expected_list: List[str], predicted_list: List[str], threshold: float = 0.55
) -> Tuple[int, List[Dict[str, Any]]]:
    """
    Perform greedy 1-to-1 matching between expected and predicted strings.
    Matches are prioritized by highest similarity score >= threshold.
    """
    if not expected_list or not predicted_list:
        return 0, []

    candidates = []
    for exp_idx, exp_item in enumerate(expected_list):
        for pred_idx, pred_item in enumerate(predicted_list):
            sim = text_similarity(exp_item, pred_item)
            if sim >= threshold:
                candidates.append((sim, exp_idx, pred_idx))

    # Sort descending by similarity score
    candidates.sort(key=lambda x: x[0], reverse=True)

    matched_exp = set()
    matched_pred = set()
    match_details = []

    for sim, exp_idx, pred_idx in candidates:
        if exp_idx not in matched_exp and pred_idx not in matched_pred:
            matched_exp.add(exp_idx)
            matched_pred.add(pred_idx)
            match_details.append({
                "expected": expected_list[exp_idx],
                "predicted": predicted_list[pred_idx],
                "similarity": round(sim, 3),
            })

    return len(match_details), match_details


def normalize_team(name: Optional[str]) -> str:
    """Normalize team name string for comparison."""
    if not name:
        return ""
    n = name.strip().lower()
    n = re.sub(r"\s*/\s*", "/", n)
    n = re.sub(r"[\s_-]+", " ", n)
    if "web" in n:
        return "web development"
    if "mobile" in n:
        return "mobile development"
    if "ai" in n or "ml" in n:
        return "ai/ml"
    if "auto" in n or "data" in n:
        return "automation/data"
    if "cross" in n or "multi" in n:
        return "cross_functional"
    if "review" in n or "triage" in n or "human" in n:
        return "needs_human_review"
    return n


def evaluate_team_match(
    expected_team: str,
    predicted_team: str,
    flagged_for_review: bool,
    supporting_teams: Optional[List[str]] = None,
) -> Tuple[bool, str]:
    """
    Determine whether the pipeline's team decision matches the ground truth.
    Handles special cases:
    - NEEDS_HUMAN_REVIEW: matched if flagged_for_review is True OR predicted team is None/empty/'needs_human_review'
    - CROSS_FUNCTIONAL: matched if predicted team is cross_functional OR multiple supporting teams are assigned
    """
    norm_exp = normalize_team(expected_team)
    norm_pred = normalize_team(predicted_team)
    supporting = supporting_teams or []

    if norm_exp == "needs_human_review":
        if flagged_for_review:
            return True, "Correctly escalated for human review"
        if norm_pred in ["needs_human_review", ""]:
            return True, "Correctly identified as requiring review / unassigned"
        return False, f"Expected human review escalation, but pipeline assigned '{predicted_team}' without flagging"

    if norm_exp == "cross_functional":
        if norm_pred == "cross_functional":
            return True, "Directly identified as cross-functional"
        if len(supporting) > 0:
            return True, f"Identified cross-functional scope with primary '{predicted_team}' and supporting: {supporting}"
        return False, f"Expected cross-functional allocation, but single team '{predicted_team}' assigned with no supporting teams"

    # Standard single team
    if norm_exp == norm_pred:
        return True, f"Exact team match: '{predicted_team}'"
    return False, f"Team mismatch: expected '{expected_team}', got '{predicted_team}'"


def evaluate_all(
    dataset_path: Path,
    predictions_path: Path,
    results_path: Path,
    threshold: float = 0.55,
) -> Dict[str, Any]:
    """Evaluate pipeline predictions against ground truth dataset."""

    with open(dataset_path, "r", encoding="utf-8") as f:
        gt_data = json.load(f)

    with open(predictions_path, "r", encoding="utf-8") as f:
        pred_data = json.load(f)

    cases = gt_data["evaluation_set"]["cases"] if "evaluation_set" in gt_data else gt_data.get("cases", [])
    total_cases = len(cases)

    # Category accumulators
    categories: Dict[str, List[Dict[str, Any]]] = {}
    case_results: List[Dict[str, Any]] = []

    # Global counters
    total_expected_reqs = 0
    total_predicted_reqs = 0
    total_matched_reqs = 0
    total_unsupported_reqs = 0

    total_expected_missing = 0
    total_matched_missing = 0

    team_matches_count = 0
    flagged_count = 0
    error_count = 0
    latencies = []

    sensitive_expected_count = 0
    sensitive_detected_count = 0
    injection_expected_count = 0
    injection_detected_count = 0

    for case in cases:
        case_id = case["case_id"]
        category = case.get("category", "uncategorized")
        if category not in categories:
            categories[category] = []

        pred = pred_data.get(case_id, {})

        # Latency & errors
        latency = pred.get("latency_ms", 0)
        latencies.append(latency)
        has_error = bool(pred.get("error"))
        if has_error:
            error_count += 1

        flagged = bool(pred.get("flagged_for_review", False))
        if flagged:
            flagged_count += 1

        # Security evaluation
        sensitive_exp = bool(case.get("sensitive_data_detected", False))
        injection_exp = bool(case.get("injection_attempt_detected", False))

        if sensitive_exp:
            sensitive_expected_count += 1
            if pred.get("sensitive_data_detected", False):
                sensitive_detected_count += 1

        if injection_exp:
            injection_expected_count += 1
            if pred.get("injection_attempt_detected", False):
                injection_detected_count += 1

        # Team evaluation
        expected_team = case.get("expected_team", "")
        predicted_team = pred.get("recommended_team", "")
        supporting_teams = pred.get("supporting_teams", [])

        team_match, team_reason = evaluate_team_match(
            expected_team=expected_team,
            predicted_team=predicted_team,
            flagged_for_review=flagged,
            supporting_teams=supporting_teams,
        )
        if team_match:
            team_matches_count += 1

        # Requirements evaluation
        exp_reqs = case.get("expected_requirements", [])
        pred_req_objs = pred.get("requirements", [])
        pred_req_texts = [r.get("text", "") for r in pred_req_objs if r.get("text")]

        # Count unconfirmed/unsupported predictions
        unconfirmed_in_case = sum(1 for r in pred_req_objs if not r.get("confirmed", True))
        total_unsupported_reqs += unconfirmed_in_case

        matched_req_count, req_matches = match_lists(exp_reqs, pred_req_texts, threshold=threshold)

        total_expected_reqs += len(exp_reqs)
        total_predicted_reqs += len(pred_req_texts)
        total_matched_reqs += matched_req_count

        # Case-level requirement precision & recall
        if len(pred_req_texts) > 0:
            case_req_prec = matched_req_count / len(pred_req_texts)
        else:
            case_req_prec = 1.0 if len(exp_reqs) == 0 else 0.0

        if len(exp_reqs) > 0:
            case_req_rec = matched_req_count / len(exp_reqs)
        else:
            case_req_rec = 1.0

        case_unsupported_rate = (unconfirmed_in_case / len(pred_req_texts)) if pred_req_texts else 0.0

        # Missing information evaluation
        exp_missing = case.get("expected_missing_information", [])
        pred_missing = pred.get("missing_information", [])
        matched_missing_count, missing_matches = match_lists(exp_missing, pred_missing, threshold=threshold)

        total_expected_missing += len(exp_missing)
        total_matched_missing += matched_missing_count

        case_missing_rec = (matched_missing_count / len(exp_missing)) if exp_missing else 1.0

        case_record = {
            "case_id": case_id,
            "category": category,
            "difficulty": case.get("difficulty", "medium"),
            "team_evaluation": {
                "expected": expected_team,
                "predicted": predicted_team,
                "confidence": pred.get("team_confidence", 0.0),
                "supporting_teams": supporting_teams,
                "flagged_for_review": flagged,
                "matched": team_match,
                "notes": team_reason,
            },
            "requirements_evaluation": {
                "expected_count": len(exp_reqs),
                "predicted_count": len(pred_req_texts),
                "matched_count": matched_req_count,
                "precision": round(case_req_prec, 4),
                "recall": round(case_req_rec, 4),
                "unsupported_count": unconfirmed_in_case,
                "unsupported_rate": round(case_unsupported_rate, 4),
                "matches": req_matches,
                "unmatched_expected": [exp for i, exp in enumerate(exp_reqs) if i not in {m["expected"] for m in req_matches}],
            },
            "missing_info_evaluation": {
                "expected_count": len(exp_missing),
                "predicted_count": len(pred_missing),
                "matched_count": matched_missing_count,
                "recall": round(case_missing_rec, 4),
                "matches": missing_matches,
            },
            "security": {
                "sensitive_data_expected": sensitive_exp,
                "sensitive_data_detected": pred.get("sensitive_data_detected", False),
                "injection_attempt_expected": injection_exp,
                "injection_attempt_detected": pred.get("injection_attempt_detected", False),
            },
            "latency_ms": latency,
            "error": pred.get("error"),
        }

        case_results.append(case_record)
        categories[category].append(case_record)

    # Compute overall metrics
    overall_team_acc = (team_matches_count / total_cases) if total_cases > 0 else 0.0
    micro_req_prec = (total_matched_reqs / total_predicted_reqs) if total_predicted_reqs > 0 else 0.0
    micro_req_rec = (total_matched_reqs / total_expected_reqs) if total_expected_reqs > 0 else 0.0
    unsupported_rate = (total_unsupported_reqs / total_predicted_reqs) if total_predicted_reqs > 0 else 0.0
    missing_info_rec = (total_matched_missing / total_expected_missing) if total_expected_missing > 0 else 0.0

    macro_req_prec = sum(c["requirements_evaluation"]["precision"] for c in case_results) / total_cases
    macro_req_rec = sum(c["requirements_evaluation"]["recall"] for c in case_results) / total_cases
    macro_missing_rec = sum(c["missing_info_evaluation"]["recall"] for c in case_results) / total_cases

    avg_latency = sum(latencies) / len(latencies) if latencies else 0.0
    sorted_latencies = sorted(latencies)
    p50_latency = sorted_latencies[len(sorted_latencies) // 2] if sorted_latencies else 0
    p95_index = int(0.95 * len(sorted_latencies))
    p95_latency = sorted_latencies[min(p95_index, len(sorted_latencies) - 1)] if sorted_latencies else 0

    # Per-category summary
    category_summary = {}
    for cat_name, cat_cases in categories.items():
        cat_total = len(cat_cases)
        cat_team_correct = sum(1 for c in cat_cases if c["team_evaluation"]["matched"])
        cat_exp_reqs = sum(c["requirements_evaluation"]["expected_count"] for c in cat_cases)
        cat_pred_reqs = sum(c["requirements_evaluation"]["predicted_count"] for c in cat_cases)
        cat_match_reqs = sum(c["requirements_evaluation"]["matched_count"] for c in cat_cases)

        cat_exp_miss = sum(c["missing_info_evaluation"]["expected_count"] for c in cat_cases)
        cat_match_miss = sum(c["missing_info_evaluation"]["matched_count"] for c in cat_cases)

        cat_prec = (cat_match_reqs / cat_pred_reqs) if cat_pred_reqs > 0 else (1.0 if cat_exp_reqs == 0 else 0.0)
        cat_rec = (cat_match_reqs / cat_exp_reqs) if cat_exp_reqs > 0 else 1.0
        cat_miss_rec = (cat_match_miss / cat_exp_miss) if cat_exp_miss > 0 else 1.0
        cat_lat = sum(c["latency_ms"] for c in cat_cases) / cat_total
        cat_flagged = sum(1 for c in cat_cases if c["team_evaluation"]["flagged_for_review"])

        category_summary[cat_name] = {
            "total_cases": cat_total,
            "team_accuracy": round(cat_team_correct / cat_total, 4),
            "team_correct": cat_team_correct,
            "requirement_precision": round(cat_prec, 4),
            "requirement_recall": round(cat_rec, 4),
            "missing_info_recall": round(cat_miss_rec, 4),
            "flagged_for_review_rate": round(cat_flagged / cat_total, 4),
            "avg_latency_ms": round(cat_lat, 1),
        }

    # Final summary structure
    eval_results = {
        "metadata": {
            "dataset_file": str(dataset_path),
            "predictions_file": str(predictions_path),
            "total_cases": total_cases,
            "fuzzy_threshold": threshold,
        },
        "summary": {
            "team_decision_accuracy": round(overall_team_acc, 4),
            "requirement_precision_micro": round(micro_req_prec, 4),
            "requirement_recall_micro": round(micro_req_rec, 4),
            "requirement_precision_macro": round(macro_req_prec, 4),
            "requirement_recall_macro": round(macro_req_rec, 4),
            "unsupported_inference_rate": round(unsupported_rate, 4),
            "missing_information_recall_micro": round(missing_info_rec, 4),
            "missing_information_recall_macro": round(macro_missing_rec, 4),
            "flagged_for_review_rate": round(flagged_count / total_cases, 4),
            "error_rate": round(error_count / total_cases, 4),
            "sensitive_data_detection_rate": (sensitive_detected_count / sensitive_expected_count) if sensitive_expected_count else 1.0,
            "injection_attempt_detection_rate": (injection_detected_count / injection_expected_count) if injection_expected_count else 1.0,
            "latency": {
                "mean_ms": round(avg_latency, 1),
                "p50_ms": p50_latency,
                "p95_ms": p95_latency,
            },
        },
        "category_metrics": category_summary,
        "cases": case_results,
    }

    # Sanitize any accidental secrets before saving
    sanitized_results = sanitize_object(eval_results)

    results_path.parent.mkdir(parents=True, exist_ok=True)
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(sanitized_results, f, indent=2)

    return sanitized_results


def print_summary_table(results: Dict[str, Any]):
    """Print clean GitHub-flavored markdown summary tables to console."""
    summary = results["summary"]
    cat_metrics = results["category_metrics"]

    print("\n" + "=" * 90)
    print("AI PROJECT INTAKE PIPELINE - EVALUATION RESULTS (20 GOLDEN TEST CASES)")
    print("=" * 90)

    print("\n### 1. Overall Performance Summary\n")
    print("| Metric | Value | Target / Benchmark |")
    print("| :--- | :--- | :--- |")
    print(f"| **Team Decision Accuracy** | **{summary['team_decision_accuracy'] * 100:.1f}%** | >= 85.0% |")
    print(f"| **Requirement Precision (Micro)** | **{summary['requirement_precision_micro'] * 100:.1f}%** | >= 80.0% |")
    print(f"| **Requirement Recall (Micro)** | **{summary['requirement_recall_micro'] * 100:.1f}%** | >= 80.0% |")
    print(f"| **Unsupported Inference Rate** | **{summary['unsupported_inference_rate'] * 100:.1f}%** | <= 10.0% |")
    print(f"| **Missing Info Recall (Micro)** | **{summary['missing_information_recall_micro'] * 100:.1f}%** | >= 70.0% |")
    print(f"| **Human Review Escalation Rate** | **{summary['flagged_for_review_rate'] * 100:.1f}%** | Context Dependent |")
    print(f"| **Sensitive Data Detection Rate** | **{summary['sensitive_data_detection_rate'] * 100:.1f}%** | 100.0% |")
    print(f"| **Injection Attempt Detection Rate** | **{summary['injection_attempt_detection_rate'] * 100:.1f}%** | 100.0% |")
    print(f"| **Mean Latency** | **{summary['latency']['mean_ms']} ms** | < 3000 ms |")
    print(f"| **P95 Latency** | **{summary['latency']['p95_ms']} ms** | < 5000 ms |")

    print("\n### 2. Category Breakdown\n")
    print("| Category | Cases | Team Accuracy | Req Precision | Req Recall | Missing Info Recall | Human Review | Avg Latency |")
    print("| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |")

    for cat_name, m in cat_metrics.items():
        print(
            f"| `{cat_name}` | {m['total_cases']} | "
            f"{m['team_accuracy'] * 100:.1f}% ({m['team_correct']}/{m['total_cases']}) | "
            f"{m['requirement_precision'] * 100:.1f}% | "
            f"{m['requirement_recall'] * 100:.1f}% | "
            f"{m['missing_info_recall'] * 100:.1f}% | "
            f"{m['flagged_for_review_rate'] * 100:.1f}% | "
            f"{m['avg_latency_ms']} ms |"
        )
    print("\n" + "=" * 90 + "\n")


def main():
    dataset_file = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("evaluation_data.json")
    predictions_file = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("eval_predictions.json")
    results_file = Path(sys.argv[3]) if len(sys.argv) > 3 else Path("eval_results.json")

    # Resolve paths relative to root if needed
    if not dataset_file.exists():
        alt = Path("test_cases") / dataset_file.name
        if alt.exists():
            dataset_file = alt

    results = evaluate_all(dataset_file, predictions_file, results_file)
    print_summary_table(results)
    print(f"Full evaluation results written to: {results_file.resolve()}")


if __name__ == "__main__":
    main()
