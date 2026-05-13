# llm-politics

Evaluates LLM political ideology by administering the [Political Compass Test](https://www.politicalcompass.org/test) (62 questions, two axes: economic left/right and authoritarian/libertarian).

## Google Colab (recommended)

Open a Colab notebook with a GPU runtime (Runtime → Change runtime type → T4 GPU), then run:

```python
!git clone https://github.com/ncarolan/llm-politics && cd llm-politics && bash run.sh --output results.json
```

That single command clones the repo, installs dependencies, and runs the full evaluation. Results are written to `results.json`.

## Local setup (conda)

```bash
conda env create -f environment.yml
bash run.sh --output results.json
```

## Arguments

```
bash run.sh [--model MODEL_ID] [--output FILE] [--device DEVICE]
```

- `--model` — any HuggingFace causal LM model ID (default: `talkie-lm/talkie-1930-13b-it`)
- `--device` — `auto`, `cuda`, `mps`, or `cpu` (default: `auto`)
- `--output` — path to write full JSON results (optional)

## Output

Prints per-question responses and a final summary:

```
Political Compass Coordinates:
  Economic axis:  -3.12  (negative=left, positive=right)
  Social axis:    +2.45  (negative=libertarian, positive=authoritarian)
  Quadrant:       Left-Authoritarian
```

Full JSON results include each question's raw model output, parsed response, and computed score.
