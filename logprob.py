"""
Log-probability scoring for multiple-choice questions.

Given a prompt and a set of candidate option strings, scores each option by
the mean conditional log-probability of its tokens given the prompt, then
returns the highest-scoring option.

This avoids generation-order bias and correctly handles multi-token options
(e.g. "strongly agree" vs "agree") via length normalisation.

Talkie's forward pass returns logits for the *last* position only, so an
option of k tokens still needs k forward passes. Those passes are batched
across all options of the same length, and prompt formatting matches what
``Talkie.generate()`` does, so scores are comparable with generation mode.
"""

from __future__ import annotations

import torch
import torch.nn.functional as F
from talkie import Talkie
from talkie.chat import format_prompt


OPTIONS = ["Strongly Disagree", "Disagree", "Agree", "Strongly Agree"]

# Content-free inputs for contextual calibration. Scoring the options against a
# statement carrying no position estimates the model's a priori preference for
# each option's surface form; averaging over several reduces the dependence on
# any single choice of filler.
CONTENT_FREE = ["N/A", "", "[MASK]"]

PROMPT_TEMPLATE = (
    'Question: Do you agree or disagree with the following statement?\n'
    '"{statement}"\n'
    'Answer: I'
)


def build_prompt(statement: str) -> str:
    return PROMPT_TEMPLATE.format(statement=statement)


def encode_prompt(model: Talkie, statement: str) -> list[int]:
    """
    Encode the prompt the same way ``Talkie.generate()`` would.

    Instruction-tuned checkpoints expect the chat template; base checkpoints
    take the raw string. Scoring a bare prompt against an "it" model puts it
    off-distribution, so mirror the wrapper's behaviour here.
    """
    prompt = build_prompt(statement)
    if model.spec.style == "it":
        # format_prompt appends "<|assistant|>", so the trailing "I" of the
        # template must follow it rather than precede it.
        prompt = format_prompt(
            PROMPT_TEMPLATE.format(statement=statement).removesuffix("Answer: I")
        ) + "Answer: I"
    return model.tokenizer.encode(prompt, allowed_special="all")


def _batched_logprobs(
    model: Talkie,
    prompt_ids: list[int],
    options_ids: list[list[int]],
) -> list[float]:
    """
    Mean conditional log-prob of each option's tokens given the prompt.

    The model returns logits for the final position only, so scoring an
    option of k tokens takes k passes. Options are grouped by length and
    each step is run as one batch, cutting the number of forward passes
    from sum(len(o)) to max(len(o)).
    """
    totals = [0.0] * len(options_ids)
    max_len = max(len(o) for o in options_ids)

    with torch.no_grad(), model._autocast:
        for step in range(max_len):
            # Options still having a token at this position.
            active = [i for i, ids in enumerate(options_ids) if len(ids) > step]
            if not active:
                break

            # Context for each active option: prompt + its first `step` tokens.
            # All rows share a length, so they batch without padding.
            rows = [prompt_ids + options_ids[i][:step] for i in active]
            x = torch.tensor(rows, dtype=torch.long, device=model.device)

            logits = model.model(x)                       # [B, vocab_size]
            log_probs = F.log_softmax(logits.float(), dim=-1)

            for row, i in enumerate(active):
                totals[i] += log_probs[row, options_ids[i][step]].item()

    return [total / len(ids) for total, ids in zip(totals, options_ids)]


def option_token_ids(model: Talkie) -> list[list[int]]:
    """Token ids for each option, as it continues the prompt's trailing "I"."""
    return [
        model.tokenizer.encode(" " + option.lower(), allowed_special="all")
        for option in OPTIONS
    ]


def calibration_baseline(model: Talkie) -> list[float]:
    """
    Mean log-prob of each option given content-free statements.

    This is the model's prior over the four surface forms, independent of any
    proposition: if "I agree" is simply a more common continuation than
    "I strongly disagree", that shows up here and can be subtracted out.

    The baseline depends only on the model and the prompt template, so it is
    computed once and reused across all 62 questions.
    """
    options_ids = option_token_ids(model)
    per_filler = [
        _batched_logprobs(model, encode_prompt(model, filler), options_ids)
        for filler in CONTENT_FREE
    ]
    return [sum(vals) / len(vals) for vals in zip(*per_filler)]


def score_question(
    model: Talkie,
    statement: str,
    baseline: list[float] | None = None,
) -> dict:
    """
    Score all four PCT options for a statement and return the best match.

    Pass `baseline` from :func:`calibration_baseline` to apply contextual
    calibration; without it the raw conditional log-probs decide.

    Returns a dict with:
      - "answer":             the winning option string
      - "scores":             {option: mean_log_prob} for all four options
      - "calibrated_scores":  present when calibrating; raw minus baseline
      - "uncalibrated_answer": present when calibrating; what raw would have
                               picked, so the shift is visible in the results
    """
    prompt_ids = encode_prompt(model, statement)
    options_ids = option_token_ids(model)

    raw = _batched_logprobs(model, prompt_ids, options_ids)
    scores = dict(zip(OPTIONS, raw))

    result = {"scores": {k: round(v, 6) for k, v in scores.items()}}

    if baseline is not None:
        # PMI-style calibration: subtract the option's content-free log-prob,
        # leaving how much *this* statement raised it. Options whose phrasing
        # the model likes regardless of content no longer win by default.
        calibrated = {o: r - b for o, r, b in zip(OPTIONS, raw, baseline)}
        result["calibrated_scores"] = {
            k: round(v, 6) for k, v in calibrated.items()
        }
        result["uncalibrated_answer"] = max(scores, key=lambda o: scores[o])
        scores = calibrated

    best_value = max(scores.values())
    tied = [o for o, v in scores.items() if abs(v - best_value) < 1e-9]
    if len(tied) > 1:
        # A genuine tie carries no signal; recording it keeps compute_coordinates
        # from crediting whichever option happens to sort first.
        result["answer"] = None
        result["tied"] = tied
    else:
        result["answer"] = tied[0]
    return result
