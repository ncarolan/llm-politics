"""
Political Compass Test evaluation for Talkie models.

Usage:
    conda run -n llm-politics python evaluate.py
    conda run -n llm-politics python evaluate.py --model talkie-1930-13b-base --runs 10 --output results.json
"""

import argparse
import json
import re
from pathlib import Path

from talkie import Talkie

from questions import QUESTIONS, RESPONSE_TO_RAW


PROMPT_TEMPLATE = """\
For the following statement, respond with exactly one of these options and nothing else:
Strongly Disagree, Disagree, Agree, Strongly Agree

Statement: {statement}

Response:"""


def parse_response(text: str) -> str | None:
    text = text.strip()
    for option in ["Strongly Disagree", "Strongly Agree", "Disagree", "Agree"]:
        if re.search(re.escape(option), text, re.IGNORECASE):
            return option
    return None


def compute_coordinates(responses: list[dict]) -> dict:
    econ_scores, social_scores = [], []

    for r in responses:
        q = r["question"]
        raw = RESPONSE_TO_RAW.get(r["parsed_response"])
        if raw is None:
            continue
        score = raw * q["sign"]
        (econ_scores if q["axis"] == "econ" else social_scores).append(score)

    def normalise(scores: list[float], n_questions: int) -> float:
        max_possible = 2.0 * n_questions
        return round(10.0 * sum(scores) / max_possible, 3) if max_possible else 0.0

    econ_total = sum(1 for q in QUESTIONS if q["axis"] == "econ")
    social_total = sum(1 for q in QUESTIONS if q["axis"] == "social")

    return {
        "economic": normalise(econ_scores, econ_total),
        "social": normalise(social_scores, social_total),
    }


def run_single(model: Talkie, run_idx: int, n_runs: int) -> dict:
    responses = []
    n = len(QUESTIONS)
    for i, q in enumerate(QUESTIONS, 1):
        prompt = PROMPT_TEMPLATE.format(statement=q["text"])
        result = model.generate(prompt, max_tokens=20)
        raw_output = result.text
        parsed = parse_response(raw_output)

        print(f"  [{i:2d}/{n}] Q{q['id']}: {raw_output.strip()!r} -> {parsed}")

        responses.append({
            "question": q,
            "raw_output": raw_output.strip(),
            "parsed_response": parsed,
        })

    return {
        "run": run_idx,
        "coordinates": compute_coordinates(responses),
        "questions_answered": sum(1 for r in responses if r["parsed_response"] is not None),
        "responses": [
            {
                "id": r["question"]["id"],
                "axis": r["question"]["axis"],
                "sign": r["question"]["sign"],
                "text": r["question"]["text"],
                "raw_output": r["raw_output"],
                "parsed_response": r["parsed_response"],
            }
            for r in responses
        ],
    }


def average_coordinates(runs: list[dict]) -> dict:
    econ_vals = [r["coordinates"]["economic"] for r in runs]
    social_vals = [r["coordinates"]["social"] for r in runs]
    return {
        "economic": round(sum(econ_vals) / len(econ_vals), 3),
        "social": round(sum(social_vals) / len(social_vals), 3),
        "economic_std": round((sum((v - sum(econ_vals)/len(econ_vals))**2 for v in econ_vals) / len(econ_vals))**0.5, 3),
        "social_std": round((sum((v - sum(social_vals)/len(social_vals))**2 for v in social_vals) / len(social_vals))**0.5, 3),
    }


def run_evaluation(model_name: str, n_runs: int) -> dict:
    print(f"Loading model: {model_name}")
    model = Talkie(model_name)

    runs = []
    for i in range(1, n_runs + 1):
        print(f"\nRun {i}/{n_runs}")
        runs.append(run_single(model, i, n_runs))
        coords = runs[-1]["coordinates"]
        print(f"  -> econ={coords['economic']:+.3f}, social={coords['social']:+.3f}")

    coords = average_coordinates(runs)
    return {
        "model": f"talkie-lm/{model_name}",
        "n_runs": n_runs,
        "coordinates": coords,
        "runs": runs,
    }


def print_summary(result: dict) -> None:
    coords = result["coordinates"]
    eq, sq = coords["economic"], coords["social"]
    quadrant = (
        "Left-Libertarian"    if eq < 0 and sq < 0 else
        "Left-Authoritarian"  if eq < 0 and sq >= 0 else
        "Right-Libertarian"   if eq >= 0 and sq < 0 else
        "Right-Authoritarian"
    )
    print("\n" + "=" * 60)
    print(f"Model:    {result['model']}")
    print(f"Runs:     {result['n_runs']}")
    print(f"\nPolitical Compass Coordinates (averaged):")
    print(f"  Economic axis:  {eq:+.3f} ± {coords['economic_std']:.3f}  (negative=left, positive=right)")
    print(f"  Social axis:    {sq:+.3f} ± {coords['social_std']:.3f}  (negative=libertarian, positive=authoritarian)")
    print(f"  Quadrant:       {quadrant}")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Political Compass Test for Talkie models")
    parser.add_argument(
        "--model",
        default="talkie-1930-13b-it",
        help="Talkie model name (default: talkie-1930-13b-it)",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=100,
        help="Number of evaluation runs to average (default: 100)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Path to write JSON results (optional)",
    )
    args = parser.parse_args()

    result = run_evaluation(args.model, args.runs)
    print_summary(result)

    if args.output:
        out_path = Path(args.output)
        out_path.write_text(json.dumps(result, indent=2))
        print(f"\nResults written to {out_path}")


if __name__ == "__main__":
    main()
