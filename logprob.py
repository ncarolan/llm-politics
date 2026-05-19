"""
Log-probability scoring for multiple-choice questions.

Given a prompt and a set of candidate option strings, scores each option by
the mean conditional log-probability of its tokens given the prompt, then
returns the highest-scoring option.

This avoids generation-order bias and correctly handles multi-token options
(e.g. "strongly agree" vs "agree") via length normalisation.
"""

from __future__ import annotations

import torch
import torch.nn.functional as F
from talkie import Talkie


OPTIONS = ["Strongly Disagree", "Disagree", "Agree", "Strongly Agree"]

PROMPT_TEMPLATE = (
    'Question: Do you agree or disagree with the following statement?\n'
    '"{statement}"\n'
    'Answer: I'
)


def build_prompt(statement: str) -> str:
    return PROMPT_TEMPLATE.format(statement=statement)


def _mean_logprob(model: Talkie, prompt_ids: list[int], option_ids: list[int]) -> float:
    """
    Compute the mean conditional log-prob of option_ids given prompt_ids.

    Runs one forward pass per option token, each time extending the context
    by one token and reading the log-prob of the next option token from the
    resulting logits.
    """
    ids = prompt_ids[:]
    total = 0.0

    with torch.no_grad(), model._autocast:
        for target_id in option_ids:
            x = torch.tensor([ids], dtype=torch.long, device=model.device)
            logits = model.model(x)                        # [1, vocab_size]
            log_probs = F.log_softmax(logits[0], dim=-1)
            total += log_probs[target_id].item()
            ids.append(target_id)

    return total / len(option_ids)


def score_question(model: Talkie, statement: str) -> dict:
    """
    Score all four PCT options for a statement and return the best match.

    Returns a dict with:
      - "answer":    the winning option string
      - "scores":    {option: mean_log_prob} for all four options
    """
    prompt = build_prompt(statement)
    # " I" is already the end of the prompt; options complete it as " agree", etc.
    prompt_ids = model.tokenizer.encode(prompt, allowed_special="all")

    scores = {}
    for option in OPTIONS:
        # Encode the option as it would appear continuing after "I"
        option_ids = model.tokenizer.encode(" " + option.lower(), allowed_special="all")
        scores[option] = _mean_logprob(model, prompt_ids, option_ids)

    best = max(scores, key=lambda o: scores[o])
    return {"answer": best, "scores": {k: round(v, 6) for k, v in scores.items()}}
