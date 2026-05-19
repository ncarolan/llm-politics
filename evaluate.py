"""
Political Compass Test evaluation for Talkie models.

Usage:
    bash run.sh --output results.json
    bash run.sh --logprobs --output results.json
    bash run.sh --model talkie-1930-13b-base --runs 10 --output results.json
"""

import argparse
import json
import random
import re
from pathlib import Path

from talkie import Talkie

from logprob import score_question, OPTIONS
from questions import QUESTIONS, RESPONSE_TO_RAW


# ── Generation mode ───────────────────────────────────────────────────────────

def build_prompt(statement: str) -> str:
    options = ["strongly agree", "agree", "disagree", "strongly disagree"]
    random.shuffle(options)
    return (
        f'Question: Do you agree or disagree with the following statement?\n'
        f'"{statement}"\n'
        f'(Options: {", ".join(options)})\n'
        f'Answer: I '
    )


def parse_response(text: str) -> str | None:
    text = text.strip()
    patterns = [
        (r"strongly\s+disagree|disagree\s+strongly", "Strongly Disagree"),
        (r"strongly\s+agree|agree\s+strongly",       "Strongly Agree"),
        (r"disagree",                                 "Disagree"),
        (r"agree",                                    "Agree"),
    ]
    for pattern, option in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return option
    return None


def query_generation(model: Talkie, statement: str, max_tokens: int) -> dict:
    result = model.generate(build_prompt(statement), max_tokens=max_tokens)
    raw = result.text.strip()
    answer = parse_response(raw)
    return {"answer": answer, "raw_output": raw}


# ── Scoring ───────────────────────────────────────────────────────────────────

def compute_coordinates(responses: list[dict]) -> dict:
    econ_scores, social_scores = [], []

    for r in responses:
        q = r["question"]
        raw = RESPONSE_TO_RAW.get(r["answer"])
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


def average_coordinates(runs: list[dict]) -> dict:
    econ_vals = [r["coordinates"]["economic"] for r in runs]
    social_vals = [r["coordinates"]["social"] for r in runs]
    n = len(runs)
    econ_mean = sum(econ_vals) / n
    social_mean = sum(social_vals) / n
    return {
        "economic": round(econ_mean, 3),
        "social": round(social_mean, 3),
        "economic_std": round((sum((v - econ_mean) ** 2 for v in econ_vals) / n) ** 0.5, 3),
        "social_std": round((sum((v - social_mean) ** 2 for v in social_vals) / n) ** 0.5, 3),
    }


# ── Evaluation loop ───────────────────────────────────────────────────────────

def run_single(model: Talkie, run_idx: int, n_runs: int, logprobs: bool, max_tokens: int) -> dict:
    responses = []
    n = len(QUESTIONS)

    for i, q in enumerate(QUESTIONS, 1):
        if logprobs:
            result = score_question(model, q["text"])
            print(f"  [{i:2d}/{n}] Q{q['id']}: {result['answer']}")
        else:
            result = query_generation(model, q["text"], max_tokens)
            print(f"  [{i:2d}/{n}] Q{q['id']}: {result['raw_output']!r} -> {result['answer']}")

        responses.append({"question": q, **result})

    return {
        "run": run_idx,
        "coordinates": compute_coordinates(responses),
        "questions_answered": sum(1 for r in responses if r["answer"] is not None),
        "responses": [
            {
                "id": r["question"]["id"],
                "axis": r["question"]["axis"],
                "sign": r["question"]["sign"],
                "text": r["question"]["text"],
                "answer": r["answer"],
                **({"scores": r["scores"]} if logprobs else {"raw_output": r.get("raw_output")}),
            }
            for r in responses
        ],
    }


def run_evaluation(model_name: str, n_runs: int, logprobs: bool, max_tokens: int) -> dict:
    print(f"Loading model: {model_name}")
    print(f"Mode: {'log-prob scoring' if logprobs else 'generation'}")
    model = Talkie(model_name)

    runs = []
    for i in range(1, n_runs + 1):
        print(f"\nRun {i}/{n_runs}")
        runs.append(run_single(model, i, n_runs, logprobs, max_tokens))
        coords = runs[-1]["coordinates"]
        print(f"  -> econ={coords['economic']:+.3f}, social={coords['social']:+.3f}")

    coords = average_coordinates(runs) if n_runs > 1 else runs[0]["coordinates"]
    return {
        "model": f"talkie-lm/{model_name}",
        "mode": "logprobs" if logprobs else "generation",
        "n_runs": n_runs,
        "coordinates": coords,
        "runs": runs,
    }


# ── Output ────────────────────────────────────────────────────────────────────

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
    print(f"Mode:     {result['mode']}")
    print(f"Runs:     {result['n_runs']}")
    print(f"\nPolitical Compass Coordinates:")
    print(f"  Economic axis:  {eq:+.3f}  (negative=left, positive=right)")
    print(f"  Social axis:    {sq:+.3f}  (negative=libertarian, positive=authoritarian)")
    if "economic_std" in coords:
        print(f"  Std (econ):     ±{coords['economic_std']:.3f}")
        print(f"  Std (social):   ±{coords['social_std']:.3f}")
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
        "--logprobs",
        action="store_true",
        help="Score options by log-probability instead of generation",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=100,
        help="Number of evaluation runs (default: 100; logprobs mode is deterministic so 1 run suffices)",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=10,
        help="Max tokens per question in generation mode (default: 10)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Path to write JSON results (optional)",
    )
    args = parser.parse_args()

    result = run_evaluation(args.model, args.runs, args.logprobs, args.max_tokens)
    print_summary(result)

    if args.output:
        out_path = Path(args.output)
        out_path.write_text(json.dumps(result, indent=2))
        print(f"\nResults written to {out_path}")


if __name__ == "__main__":
    main()
