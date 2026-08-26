# llm-politics

Evaluates LLM political ideology by administering the [Political Compass Test](https://www.politicalcompass.org/test) (62 questions, two axes: economic left/right and authoritarian/libertarian) to the [Talkie](https://github.com/talkie-lm/talkie) model family.

Three checkpoints are evaluated, which isolates two separate effects:

| model | pretraining | instruction tuned |
|---|---|---|
| `talkie-1930-13b-base` | pre-1931 corpus | no |
| `talkie-1930-13b-it` | pre-1931 corpus | yes |
| `talkie-web-13b-base` | modern web | no |

Comparing the two **base** models isolates the pretraining distribution's effect on measured ideology; comparing `1930-base` with `1930-it` isolates instruction tuning's effect.

Downloads use plain HTTP rather than HuggingFace's Xet backend (`HF_HUB_DISABLE_XET=1`, set automatically). Xet is unreliable for files this large and reports failures as `Internal Writer Error: Background writer channel closed`, which [masks the real OS error](https://github.com/huggingface/xet-core/issues/763) — usually `No space left on device`.

Each checkpoint is 13.3B parameters — about 27 GB in bfloat16, so an A100 (40 GB) is the smallest GPU that fits one; a T4 or L4 will OOM on load. Models are evaluated one at a time, and `--free-cache` (CLI) or `FREE_CACHE` (notebook) deletes each checkpoint from disk once it is done, since three of them exceed a typical Colab disk.

## Google Colab (recommended)

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/ncarolan/llm-politics/blob/main/political_compass.ipynb)

Open `political_compass.ipynb` in Colab, set a GPU runtime (Runtime → Change runtime type → T4 GPU), then Runtime → Run all.

The notebook clones this repo, installs dependencies, loads the model once, runs the evaluation, plots the compass, and offers the results for download. Because the model is loaded in its own cell, you can re-run the evaluation with different settings without reloading weights.

## Local setup (conda)

```bash
conda env create -f environment.yml
conda activate llm-politics

# One model
python evaluate.py --output results.json

# All three, written to results.<model>.json
python evaluate.py --all-models --logprobs --free-cache --output results.json
python plot.py results.*.json --output compass.png
```

## Arguments

```
python evaluate.py [--model NAME ...] [--all-models] [--logprobs] [--runs N]
                   [--max-tokens N] [--output FILE]
```

- `--model` — one or more Talkie model names, evaluated in turn (default: `talkie-1930-13b-it`). Valid names are the registry keys — `talkie-1930-13b-base`, `talkie-1930-13b-it`, `talkie-web-13b-base` — not full HuggingFace repo IDs
- `--all-models` — evaluate every model in the Talkie registry
- `--free-cache` — delete each model's weights from the HuggingFace cache after it is evaluated
- `--calibrate` — apply contextual calibration in logprobs mode (see below)
- `--logprobs` — score options by log-probability instead of generation; deterministic, so one run suffices
- `--runs` — number of evaluation runs, averaged with standard deviations (default: 100)
- `--max-tokens` — max tokens per question in generation mode (default: 10)
- `--output` — path to write full JSON results (optional). With several models the name is used as a stem: `results.json` → `results.talkie-1930-13b-it.json`

## Modes

**Generation** (default) samples a completion for each proposition and parses the answer. Options are shuffled per question to avoid anchoring, and repeated runs capture sampling variance as error bars.

**Log-prob** (`--logprobs`) scores each of the four options by its mean conditional log-probability and picks the highest. This removes order bias and handles multi-token options. It reads raw logits with no sampling step, so it is deterministic — temperature does not apply, and `--runs` is forced to 1.

Prompts are formatted to match each checkpoint's style: instruction-tuned models get Talkie's chat template, base models get the raw string, so scores are comparable across both modes and all three models.

### Contextual calibration

Raw log-probs conflate two things: how much the model endorses a proposition, and how likely that phrasing is in the first place. If `"I agree"` is simply a more common string than `"I strongly disagree"`, it wins regardless of content — the surface-form competition problem.

`--calibrate` corrects for this. Each option is scored against content-free statements (`N/A`, `""`, `[MASK]`), which estimates the model's prior over the four phrasings, and that prior is subtracted from every question's score:

```
calibrated(option) = log P(option | statement) − log P(option | content-free)
```

The baseline depends only on the model and the prompt template, so it is computed once per model rather than per question — three extra scoring passes total.

Calibrated results record both scores plus `uncalibrated_answer`, so you can see which questions the correction actually flipped. When calibration leaves all four options exactly tied, the answer is recorded as unanswered rather than letting option order decide.

This matters most for the base models, which have no instruction tuning to even out their response priors.

## Output

```
Political Compass Coordinates:
  Economic axis:  -3.12  (negative=left, positive=right)
  Social axis:    +2.45  (negative=libertarian, positive=authoritarian)
  Quadrant:       Left-Authoritarian
```

Full JSON results include each question's raw model output (or per-option log-probs), parsed response, and computed score. Pass one or more result files to `plot.py` to chart them on the compass.
