"""
Political Compass Test evaluation for Talkie (or any HuggingFace causal LM).

Usage:
    conda run -n llm-politics python evaluate.py --model talkie-lm/talkie-1930-13b-it
    conda run -n llm-politics python evaluate.py --model talkie-lm/talkie-1930-13b-it --output results.json
"""

import argparse
import json
import re
import sys
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from questions import QUESTIONS, RESPONSE_OPTIONS, RESPONSE_TO_RAW


PROMPT_TEMPLATE = """\
Please respond to the following statement by choosing exactly one of these options:
Strongly Disagree, Disagree, Agree, Strongly Agree

Statement: {statement}

Your response (one option only):"""


def build_prompt(statement: str) -> str:
    return PROMPT_TEMPLATE.format(statement=statement)


def parse_response(text: str) -> str | None:
    """Extract the first matching response option from model output."""
    # Normalise whitespace and case for matching
    text = text.strip()
    for option in ["Strongly Disagree", "Strongly Agree", "Disagree", "Agree"]:
        if re.search(re.escape(option), text, re.IGNORECASE):
            # Return the canonical casing
            return option
    return None


def score_response(raw: int, sign: int) -> float:
    """Convert raw response score and question sign into a directional score."""
    return raw * sign


def compute_coordinates(responses: list[dict]) -> dict:
    """
    Compute Political Compass coordinates from collected responses.

    Returns:
        {
            "economic": float in [-10, 10],   negative = left
            "social":   float in [-10, 10],   negative = libertarian
        }
    """
    econ_scores = []
    social_scores = []

    for r in responses:
        q = r["question"]
        raw = RESPONSE_TO_RAW.get(r["parsed_response"])
        if raw is None:
            continue
        score = score_response(raw, q["sign"])
        if q["axis"] == "econ":
            econ_scores.append(score)
        else:
            social_scores.append(score)

    def normalise(scores: list[float], n_questions: int) -> float:
        # Max possible absolute score per question is 2; normalise to [-10, 10]
        max_possible = 2.0 * n_questions
        total = sum(scores)
        return round(10.0 * total / max_possible, 3) if max_possible else 0.0

    econ_total = len([q for q in QUESTIONS if q["axis"] == "econ"])
    social_total = len([q for q in QUESTIONS if q["axis"] == "social"])

    return {
        "economic": normalise(econ_scores, econ_total),
        "social": normalise(social_scores, social_total),
    }


def load_model(model_id: str, device: str):
    print(f"Loading tokenizer: {model_id}")
    tokenizer = AutoTokenizer.from_pretrained(model_id, use_fast=False)

    dtype = torch.bfloat16 if device != "cpu" else torch.float32
    print(f"Loading model on {device} with dtype={dtype} ...")
    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        torch_dtype=dtype,
        device_map=device if device != "cpu" else None,
    )
    model.eval()
    return tokenizer, model


@torch.inference_mode()
def query_model(prompt: str, tokenizer, model, max_new_tokens: int = 20) -> str:
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    output_ids = model.generate(
        **inputs,
        max_new_tokens=max_new_tokens,
        do_sample=False,
        temperature=1.0,
        pad_token_id=tokenizer.eos_token_id,
    )
    # Decode only the newly generated tokens
    new_ids = output_ids[0][inputs["input_ids"].shape[1]:]
    return tokenizer.decode(new_ids, skip_special_tokens=True)


def run_evaluation(model_id: str, device: str) -> dict:
    tokenizer, model = load_model(model_id, device)

    responses = []
    n = len(QUESTIONS)
    for i, q in enumerate(QUESTIONS, 1):
        prompt = build_prompt(q["text"])
        raw_output = query_model(prompt, tokenizer, model)
        parsed = parse_response(raw_output)

        print(f"[{i:2d}/{n}] Q{q['id']}: {raw_output.strip()!r} -> {parsed}")

        responses.append({
            "question": q,
            "raw_output": raw_output.strip(),
            "parsed_response": parsed,
        })

    coords = compute_coordinates(responses)
    n_parsed = sum(1 for r in responses if r["parsed_response"] is not None)

    result = {
        "model": model_id,
        "device": device,
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
    return result


def print_summary(result: dict) -> None:
    coords = result["coordinates"]
    print("\n" + "=" * 60)
    print(f"Model:    {result['model']}")
    print(f"Parsed:   {result['questions_answered']}/{result['questions_total']} questions")
    print(f"\nPolitical Compass Coordinates:")
    print(f"  Economic axis:  {coords['economic']:+.3f}  (negative=left, positive=right)")
    print(f"  Social axis:    {coords['social']:+.3f}  (negative=libertarian, positive=authoritarian)")

    eq = coords["economic"]
    sq = coords["social"]
    quadrant = (
        "Left-Libertarian"   if eq < 0 and sq < 0 else
        "Left-Authoritarian" if eq < 0 and sq >= 0 else
        "Right-Libertarian"  if eq >= 0 and sq < 0 else
        "Right-Authoritarian"
    )
    print(f"  Quadrant:       {quadrant}")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Political Compass Test for LLMs")
    parser.add_argument(
        "--model",
        default="talkie-lm/talkie-1930-13b-it",
        help="HuggingFace model ID",
    )
    parser.add_argument(
        "--device",
        default="auto",
        help="Device: 'auto', 'cuda', 'mps', or 'cpu'",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Path to write JSON results (optional)",
    )
    args = parser.parse_args()

    result = run_evaluation(args.model, args.device)
    print_summary(result)

    if args.output:
        out_path = Path(args.output)
        out_path.write_text(json.dumps(result, indent=2))
        print(f"\nResults written to {out_path}")


if __name__ == "__main__":
    main()
