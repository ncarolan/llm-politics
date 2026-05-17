"""
Political Compass Test evaluation for Talkie models.

Usage:
    conda run -n llm-politics python evaluate.py
    conda run -n llm-politics python evaluate.py --model talkie-1930-13b-base --output results.json
"""

import argparse
import json
import re
from pathlib import Path

from talkie import Talkie, format_prompt

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


def run_evaluation(model_name: str) -> dict:
    print(f"Loading model: {model_name}")
    model = Talkie(model_name)

    responses = []
    n = len(QUESTIONS)
    for i, q in enumerate(QUESTIONS, 1):
        prompt = PROMPT_TEMPLATE.format(statement=q["text"])
        result = model.generate(prompt, max_tokens=20)
        raw_output = result.text
        parsed = parse_response(raw_output)

        print(f"[{i:2d}/{n}] Q{q['id']}: {raw_output.strip()!r} -> {parsed}")

        responses.append({
            "question": q,
            "raw_output": raw_output.strip(),
            "parsed_response": parsed,
        })

    coords = compute_coordinates(responses)
    n_parsed = sum(1 for r in responses if r["parsed_response"] is not None)

    return {
        "model": f"talkie-lm/{model_name}",
        "questions_answered": n_parsed,
        "questions_total": n,
        "coordinates": coords,
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
    print(f"Parsed:   {result['questions_answered']}/{result['questions_total']} questions")
    print(f"\nPolitical Compass Coordinates:")
    print(f"  Economic axis:  {eq:+.3f}  (negative=left, positive=right)")
    print(f"  Social axis:    {sq:+.3f}  (negative=libertarian, positive=authoritarian)")
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
        "--output",
        default=None,
        help="Path to write JSON results (optional)",
    )
    args = parser.parse_args()

    result = run_evaluation(args.model)
    print_summary(result)

    if args.output:
        out_path = Path(args.output)
        out_path.write_text(json.dumps(result, indent=2))
        print(f"\nResults written to {out_path}")


if __name__ == "__main__":
    main()
