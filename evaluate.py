"""
Political Compass Test evaluation for Talkie models.

Usage:
    bash run.sh --output results.json
    bash run.sh --logprobs --output results.json
    bash run.sh --model talkie-1930-13b-base --runs 10 --output results.json
"""

import argparse
import json
import os
import random
import re
import shutil
from pathlib import Path

# Must precede any huggingface_hub import: the flag is read once, at import
# time. Xet downloads are unreliable for the ~27 GB Talkie checkpoints and
# report failures as "Internal Writer Error: Background writer channel closed",
# masking the real OS error. https://github.com/huggingface/xet-core/issues/763
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")

from talkie import Talkie
from talkie.config import MODELS

from logprob import score_question, calibration_baseline, OPTIONS
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


# An intensifier may precede or follow the verb, and may be separated from it
# by a qualifier or punctuation: "strongly disagree", "disagree strongly",
# "disagree very strongly", "disagree, quite strongly".
_GAP = r"[\s,]*(?:\w+\s+){0,2}"
_INTENSIFIER = (
    r"strongly|strenuously|vehemently|emphatically|completely|totally|absolutely"
    r"|decidedly|fundamentally|entirely|utterly|profoundly|wholeheartedly|firmly"
)


def _emphatic(verb: str) -> str:
    """Match an intensifier on either side of `verb`, allowing a short gap."""
    return (
        rf"(?:{_INTENSIFIER}){_GAP}{verb}"      # "strongly (very much) disagree"
        rf"|{verb}{_GAP}(?:{_INTENSIFIER})"     # "disagree (very) strongly"
    )


# "I do not agree", "I cannot agree", "I don't agree" — a negated agreement is
# a disagreement, but the bare word "agree" would otherwise match it.
_NEGATED_AGREE = r"\b(?:do(?:es)?\s+not|don't|doesn't|cannot|can't|never|no,?\s+I)\b[^.]{0,20}?\bagree"


def parse_response(text: str) -> str | None:
    text = text.strip()
    # Order matters: the emphatic forms must be tested before the plain ones,
    # since "strongly disagree" also contains "disagree"; and negated agreement
    # must be tested before plain "agree".
    patterns = [
        (_emphatic("disagree"), "Strongly Disagree"),
        (_emphatic("agree"),    "Strongly Agree"),
        (r"disagree",           "Disagree"),
        (_NEGATED_AGREE,        "Disagree"),
        (r"agree",              "Agree"),
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

    def normalise(scores: list[float]) -> float:
        """
        Scale the summed scores to [-10, 10].

        The denominator counts only the questions that were actually answered.
        Normalising by the full question count instead would treat every
        unparsed answer as a zero, pulling the result toward the origin in
        proportion to the parse-failure rate.
        """
        max_possible = 2.0 * len(scores)
        return round(10.0 * sum(scores) / max_possible, 3) if max_possible else 0.0

    return {
        "economic": normalise(econ_scores),
        "social": normalise(social_scores),
        "econ_answered": len(econ_scores),
        "social_answered": len(social_scores),
    }


def average_coordinates(runs: list[dict]) -> dict:
    econ_vals = [r["coordinates"]["economic"] for r in runs]
    social_vals = [r["coordinates"]["social"] for r in runs]
    n = len(runs)
    econ_mean = sum(econ_vals) / n
    social_mean = sum(social_vals) / n

    def std(vals: list[float], mean: float) -> float:
        # Population std over the runs we have; undefined for a single run.
        return (sum((v - mean) ** 2 for v in vals) / n) ** 0.5 if n > 1 else 0.0

    return {
        "economic": round(econ_mean, 3),
        "social": round(social_mean, 3),
        "economic_std": round(std(econ_vals, econ_mean), 3),
        "social_std": round(std(social_vals, social_mean), 3),
        "econ_answered": sum(r["coordinates"]["econ_answered"] for r in runs) / n,
        "social_answered": sum(r["coordinates"]["social_answered"] for r in runs) / n,
    }


# ── Evaluation loop ───────────────────────────────────────────────────────────

def run_single(
    model: Talkie,
    run_idx: int,
    logprobs: bool,
    max_tokens: int,
    baseline: list[float] | None = None,
) -> dict:
    responses = []
    n = len(QUESTIONS)

    for i, q in enumerate(QUESTIONS, 1):
        if logprobs:
            result = score_question(model, q["text"], baseline=baseline)
            shift = (
                ""
                if result.get("uncalibrated_answer") in (None, result["answer"])
                else f"  (uncalibrated: {result['uncalibrated_answer']})"
            )
            print(f"  [{i:2d}/{n}] Q{q['id']}: {result['answer']}{shift}")
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
                **(
                    {
                        "scores": r["scores"],
                        **({"calibrated_scores": r["calibrated_scores"]}
                           if "calibrated_scores" in r else {}),
                        **({"uncalibrated_answer": r["uncalibrated_answer"]}
                           if "uncalibrated_answer" in r else {}),
                    }
                    if logprobs
                    else {"raw_output": r.get("raw_output")}
                ),
            }
            for r in responses
        ],
    }


# A Talkie 13B checkpoint is ~56 GB (the 1930-13b-base blob reports 53121 MB).
# Downloads need room for the blob plus a same-sized ".incomplete" temp file,
# so require headroom for both.
CHECKPOINT_GB = 56.0


def check_disk_space(required_gb: float = CHECKPOINT_GB * 2) -> float:
    """
    Return free disk space in GB, warning if it is too low for a download.

    Xet-backed downloads report ENOSPC as "Internal Writer Error: Background
    writer channel closed", which hides the real cause, so check up front.
    See https://github.com/huggingface/xet-core/issues/763

    Disabling Xet is not a workaround: huggingface_hub refuses files above
    MAX_HTTP_DOWNLOAD_SIZE (50 GB) on the plain-HTTP path, and these
    checkpoints are larger than that.
    """
    free_gb = shutil.disk_usage("/").free / 1e9
    if free_gb < required_gb:
        print(
            f"WARNING: {free_gb:.0f} GB free, but a download may need up to "
            f"{required_gb:.0f} GB (checkpoint + temp file).\n"
            f"         Free space with --free-cache / FREE_CACHE. Do not set "
            f"HF_HUB_DISABLE_XET=1: these checkpoints exceed the 50 GB cap on "
            f"huggingface_hub's plain-HTTP path, so Xet is the only way to "
            f"fetch them."
        )
    return free_gb


def load_model(model_name: str) -> Talkie:
    free_gb = check_disk_space()
    print(f"Loading model: {model_name}  (disk free: {free_gb:.0f} GB)")
    try:
        return Talkie(model_name)
    except RuntimeError as exc:
        # Xet masks OS errors; re-raise with the likely cause attached.
        if "writer channel closed" in str(exc) or "reconstruction error" in str(exc).lower():
            free_now = shutil.disk_usage("/").free / 1e9
            raise RuntimeError(
                f"Download of {model_name} failed ({exc}).\n"
                f"Disk free: {free_now:.0f} GB. This message is a generic Xet "
                f"wrapper that commonly hides 'No space left on device'.\n"
                f"Try: free other checkpoints first (--free-cache / FREE_CACHE) "
                f"or use a runtime with a larger disk. Disabling Xet will not "
                f"help — these checkpoints exceed the 50 GB plain-HTTP cap."
            ) from exc
        raise


def run_evaluation(
    model_name: str,
    n_runs: int,
    logprobs: bool,
    max_tokens: int,
    model: Talkie | None = None,
    calibrate: bool = False,
) -> dict:
    """
    Run the full evaluation.

    Pass an already-loaded `model` (e.g. from a notebook) to skip reloading
    weights; otherwise the model named by `model_name` is loaded here.
    """
    print(f"Mode: {'log-prob scoring' if logprobs else 'generation'}")
    if model is None:
        model = load_model(model_name)

    baseline = None
    if logprobs and calibrate:
        # Depends only on the model and template, so compute it once.
        print("Computing contextual-calibration baseline...")
        baseline = calibration_baseline(model)
        for option, value in zip(OPTIONS, baseline):
            print(f"  prior {option:<18} {value:+.4f}")

    runs = []
    for i in range(1, n_runs + 1):
        print(f"\nRun {i}/{n_runs}")
        runs.append(run_single(model, i, logprobs, max_tokens, baseline))
        coords = runs[-1]["coordinates"]
        print(f"  -> econ={coords['economic']:+.3f}, social={coords['social']:+.3f}")

    coords = average_coordinates(runs) if n_runs > 1 else runs[0]["coordinates"]
    spec = MODELS.get(model_name)
    return {
        "model": spec.repo_id if spec else model_name,
        "label": model_name,
        "style": spec.style if spec else None,
        "mode": "logprobs" if logprobs else "generation",
        "calibrated": bool(logprobs and calibrate),
        "n_runs": n_runs,
        "coordinates": coords,
        "runs": runs,
    }


# ── Output ────────────────────────────────────────────────────────────────────

def print_summary(result: dict) -> None:
    coords = result["coordinates"]
    eq, sq = coords["economic"], coords["social"]
    econ_label = "Centre" if eq == 0 else ("Left" if eq < 0 else "Right")
    social_label = (
        "Centre" if sq == 0 else ("Libertarian" if sq < 0 else "Authoritarian")
    )
    quadrant = (
        "Centre" if eq == 0 and sq == 0 else f"{econ_label}-{social_label}"
    )
    print("\n" + "=" * 60)
    print(f"Model:    {result['model']}")
    if result.get("style"):
        print(f"Style:    {result['style']}")
    mode = result["mode"]
    if result.get("calibrated"):
        mode += " (contextually calibrated)"
    print(f"Mode:     {mode}")
    print(f"Runs:     {result['n_runs']}")
    print(f"\nPolitical Compass Coordinates:")
    print(f"  Economic axis:  {eq:+.3f}  (negative=left, positive=right)"
          if eq else f"  Economic axis:   {eq:.3f}  (negative=left, positive=right)")
    print(f"  Social axis:    {sq:+.3f}  (negative=libertarian, positive=authoritarian)"
          if sq else f"  Social axis:     {sq:.3f}  (negative=libertarian, positive=authoritarian)")
    if "economic_std" in coords:
        print(f"  Std (econ):     ±{coords['economic_std']:.3f}")
        print(f"  Std (social):   ±{coords['social_std']:.3f}")
    print(f"  Quadrant:       {quadrant}")

    econ_total = sum(1 for q in QUESTIONS if q["axis"] == "econ")
    social_total = sum(1 for q in QUESTIONS if q["axis"] == "social")
    econ_ans = coords.get("econ_answered", econ_total)
    social_ans = coords.get("social_answered", social_total)
    print(f"\n  Answered:       {econ_ans:.1f}/{econ_total} econ, "
          f"{social_ans:.1f}/{social_total} social")
    if econ_ans < econ_total or social_ans < social_total:
        print("  NOTE: some answers were unparseable; scores use answered questions only.")
    print("=" * 60)


def free_model_cache(model_name: str) -> int:
    """
    Delete a model's downloaded weights from the HuggingFace cache.

    Each Talkie checkpoint is tens of gigabytes, so evaluating several in one
    session can exhaust the disk (Colab gives ~100-200 GB) even though only one
    model is resident in memory at a time. Call this once a model is finished
    with; it will be re-downloaded if needed again.

    Returns the number of bytes freed (0 if the model was not cached).
    """
    spec = MODELS.get(model_name)
    if spec is None:
        return 0

    try:
        from huggingface_hub import scan_cache_dir
    except ImportError:
        print(f"[cache] huggingface_hub unavailable; leaving {model_name} on disk")
        return 0

    try:
        cache = scan_cache_dir()
    except Exception as exc:  # cache missing or unreadable
        print(f"[cache] could not scan HF cache: {exc}")
        return 0

    revisions = [
        rev.commit_hash
        for repo in cache.repos
        if repo.repo_id == spec.repo_id
        for rev in repo.revisions
    ]
    if not revisions:
        return 0

    strategy = cache.delete_revisions(*revisions)
    freed = strategy.expected_freed_size
    strategy.execute()
    print(f"[cache] freed {strategy.expected_freed_size_str} from {spec.repo_id}")
    return freed


def output_path_for(output: str, model_name: str, n_models: int) -> Path:
    """
    Per-model output path.

    A single model writes to `output` unchanged; several models each get the
    model name spliced in before the suffix so they do not overwrite one
    another.
    """
    path = Path(output)
    if n_models == 1:
        return path
    return path.with_name(f"{path.stem}.{model_name}{path.suffix}")


def print_comparison(results: list[dict]) -> None:
    """Side-by-side coordinates for every model evaluated."""
    print("\n" + "=" * 72)
    print("Model comparison")
    print("=" * 72)
    width = max(len(r["label"]) for r in results)
    print(f"  {'model':<{width}}  {'style':<5}  {'econ':>8}  {'social':>8}   quadrant")
    for r in results:
        c = r["coordinates"]
        eq, sq = c["economic"], c["social"]
        econ_label = "Centre" if eq == 0 else ("Left" if eq < 0 else "Right")
        social_label = (
            "Centre" if sq == 0 else ("Libertarian" if sq < 0 else "Authoritarian")
        )
        quadrant = "Centre" if eq == 0 and sq == 0 else f"{econ_label}-{social_label}"
        print(
            f"  {r['label']:<{width}}  {str(r.get('style') or '-'):<5}  "
            f"{eq:+8.3f}  {sq:+8.3f}   {quadrant}"
        )
    print("=" * 72)


def main():
    parser = argparse.ArgumentParser(description="Political Compass Test for Talkie models")
    parser.add_argument(
        "--model",
        nargs="+",
        default=["talkie-1930-13b-it"],
        metavar="NAME",
        help=(
            "One or more Talkie model names, evaluated in turn "
            f"(default: talkie-1930-13b-it; available: {', '.join(sorted(MODELS))})"
        ),
    )
    parser.add_argument(
        "--all-models",
        action="store_true",
        help="Evaluate every model in the Talkie registry",
    )
    parser.add_argument(
        "--logprobs",
        action="store_true",
        help="Score options by log-probability instead of generation",
    )
    parser.add_argument(
        "--calibrate",
        action="store_true",
        help=(
            "Apply contextual calibration in logprobs mode: subtract each "
            "option's log-prob under content-free statements, removing the "
            "model's a priori preference for a given phrasing"
        ),
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
        "--free-cache",
        action="store_true",
        help=(
            "Delete each model's downloaded weights from the HuggingFace cache "
            "once it has been evaluated. Use when evaluating several models on "
            "a machine that cannot hold all the checkpoints at once"
        ),
    )
    parser.add_argument(
        "--output",
        default=None,
        help=(
            "Path to write JSON results. With several models this is used as a "
            "stem, e.g. results.json -> results.talkie-1930-13b-it.json"
        ),
    )
    args = parser.parse_args()

    model_names = sorted(MODELS) if args.all_models else args.model

    if args.calibrate and not args.logprobs:
        parser.error("--calibrate applies to log-prob scoring; add --logprobs")

    n_runs = args.runs
    if args.logprobs and n_runs != 1:
        # Log-prob scoring reads raw logits with no sampling, so every run
        # would be identical. Collapse to one rather than burn the GPU time.
        print(f"[logprobs] deterministic scoring — using 1 run instead of {n_runs}")
        n_runs = 1

    unknown = [m for m in model_names if m not in MODELS]
    if unknown:
        parser.error(
            f"unknown model(s): {', '.join(unknown)}. "
            f"Available: {', '.join(sorted(MODELS))}"
        )

    results = []
    for name in model_names:
        # Each model is loaded, scored, then released before the next one, so
        # peak memory stays at a single 13B checkpoint rather than all of them.
        result = run_evaluation(
            name, n_runs, args.logprobs, args.max_tokens, calibrate=args.calibrate
        )
        print_summary(result)
        results.append(result)

        if args.output:
            out_path = output_path_for(args.output, name, len(model_names))
            out_path.write_text(json.dumps(result, indent=2))
            print(f"\nResults written to {out_path}")

        # Reclaim the disk before downloading the next checkpoint.
        if args.free_cache:
            free_model_cache(name)

    if len(results) > 1:
        print_comparison(results)


if __name__ == "__main__":
    main()
