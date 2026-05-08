"""Evaluation engine: compare responses against an answer key."""

import json
import csv
import io
from typing import Any


def load_answer_key(path_or_dict: str | dict) -> dict:
    if isinstance(path_or_dict, dict):
        return path_or_dict
    with open(path_or_dict) as f:
        return json.load(f)


def grade_response(
    response_data: dict,
    answer_key: dict,
) -> dict:
    """Grade a single response against the answer key.

    `response_data` maps question_id → answer_value.
    `answer_key` maps question_id → {"correct": ..., "points": ..., "explanation": ...}.
    """
    result = {
        "total": 0,
        "correct": 0,
        "incorrect": 0,
        "pending_review": 0,
        "score": 0,
        "max_score": 0,
        "questions": {},
    }

    for qid, key in answer_key.items():
        entry = {
            "expected": key.get("correct"),
            "points": key.get("points", 1),
            "explanation": key.get("explanation", ""),
            "type": key.get("type", "auto"),
            "given": response_data.get(qid),
        }
        result["max_score"] += entry["points"]
        result["total"] += 1

        if entry["type"] == "review":
            entry["status"] = "review"
            entry["reason"] = "Requiere revisión manual"
            result["pending_review"] += 1
        elif entry["type"] == "auto":
            given = entry["given"]
            expected = entry["expected"]
            if _is_correct(given, expected):
                entry["status"] = "correct"
                entry["reason"] = ""
                result["correct"] += 1
                result["score"] += entry["points"]
            else:
                entry["status"] = "incorrect"
                entry["reason"] = _explain_incorrect(given, expected, entry["explanation"])
                result["incorrect"] += 1

        result["questions"][qid] = entry

    if result["max_score"] > 0:
        result["percentage"] = round(result["score"] / result["max_score"] * 100, 1)
    else:
        result["percentage"] = 0

    return result


def _is_correct(given: Any, expected: Any) -> bool:
    if expected is None:
        return True
    if isinstance(expected, list):
        if not isinstance(given, list):
            given = [given] if given is not None else []
        return sorted(given) == sorted(expected)
    return str(given) == str(expected)


def _explain_incorrect(given: Any, expected: Any, explanation: str) -> str:
    parts = []
    if given is None or given == "":
        parts.append("No respondió")
    else:
        parts.append(f"Respondió: {given}")
    if expected:
        parts.append(f"Esperado: {expected}")
    if explanation:
        parts.append(f"— {explanation}")
    return " | ".join(parts)


def grade_all(
    responses: list[dict],
    answer_key: dict,
    questions_map: dict[str, dict] | None = None,
) -> list[dict]:
    """Grade multiple responses.

    Each response in `responses` should have `id` and `data` keys
    (Formbricks API format).
    """
    results = []
    for resp in responses:
        rid = resp.get("id", "?")
        person_id = resp.get("personId") or resp.get("person", {}).get("id", "")
        data = resp.get("data", {})
        # data might be nested under "data" again
        if isinstance(data, dict) and "data" in data:
            data = data["data"]
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except (json.JSONDecodeError, TypeError):
                data = {}

        grade = grade_response(data, answer_key)
        grade["response_id"] = rid
        grade["person_id"] = person_id
        results.append(grade)

    return results


def export_csv(results: list[dict], survey_name: str = "evaluation") -> str:
    """Export graded results as CSV string."""
    if not results:
        return ""

    qids = list(results[0].get("questions", {}).keys())

    fieldnames = [
        "response_id", "person_id",
        "score", "max_score", "percentage",
        "correct", "incorrect", "pending_review",
    ] + [f"q_{qid}" for qid in qids] + [f"q_{qid}_status" for qid in qids]

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames)
    writer.writeheader()

    for r in results:
        row = {
            "response_id": r["response_id"],
            "person_id": r["person_id"],
            "score": r["score"],
            "max_score": r["max_score"],
            "percentage": r["percentage"],
            "correct": r["correct"],
            "incorrect": r["incorrect"],
            "pending_review": r["pending_review"],
        }
        for qid in qids:
            q = r["questions"].get(qid, {})
            row[f"q_{qid}"] = q.get("given", "")
            row[f"q_{qid}_status"] = q.get("status", "")
        writer.writerow(row)

    return buf.getvalue()


def export_json(results: list[dict]) -> str:
    return json.dumps(results, indent=2, ensure_ascii=False, default=str)
