# protege

The IronLabs platform CLI:

1. Optimize an agent's code against one or more target models — launch a job from a reusable Task or a local zip, then watch, inspect, and download the results.
2. Run a finished agent — hosted, or locally in your own Python environment.
3. Train a Custom Router that picks the best model for each prompt.

<p align="center">
  🌐 <a href="https://stg-studio.irona.ai/">Studio</a> |
  📚 <a href="CLI.md">CLI reference</a>
</p>

**Requirements:** Python 3.10+, an IronLabs Studio account.

## Concepts

| Term | What it is |
|---|---|
| **Task** | A reusable bundle — `agent.py`, `eval.py`, `dataset.json` — that a job optimizes. |
| **Job** | One optimization run against one or more target models, launched from a Task or a zip. |
| **Agent** | One job's result for a single target model — has its own id, code, and score. |
| **Environment** | A named, encrypted key-set (e.g. `OPENAI_API_KEY`) a Task can attach to. |
| **Router** | A trained model that picks the best target model for a given prompt. |

## Getting Started

```
pip install protege
```

Create an API key from [IronLabs Studio](https://stg-studio.irona.ai/) 
→ API Keys → Create New API Key, then log in:

```
protege login --api-key <your IronLabs API key>
# --base-url is optional, only needed to point at a non-default IronLabs deployment
```

Optimize your first agent straight from a local zip (`agent.py`, `eval.py`,
`dataset.json`) — no Task needed for a quick run:

```
$ protege optimize run --input-zip ./agent.zip --target-models qwen/qwen3.5-9b --watch
Job queued: 3f1e2a90-4b1c-4b8e-9f2a-6d1c0a9e7b21
Job 3f1e2a90-4b1c-4b8e-9f2a-6d1c0a9e7b21: running
  agent 9c2b1f4d-8a3e-4c2b-9d1f-2e7a5c8b6f34  model=qwen/qwen3.5-9b  iteration=3 score=0.82
Job 3f1e2a90-4b1c-4b8e-9f2a-6d1c0a9e7b21: completed
  agent 9c2b1f4d-8a3e-4c2b-9d1f-2e7a5c8b6f34  model=qwen/qwen3.5-9b  iteration=9 score=0.94
```

```
$ protege optimize result 3f1e2a90-4b1c-4b8e-9f2a-6d1c0a9e7b21
agent 9c2b1f4d-8a3e-4c2b-9d1f-2e7a5c8b6f34  qwen/qwen3.5-9b: {'trainScore': 0.94, 'testScore': 0.89, 'iterationsRun': 9}
  Cost: $0.1834
  --- Prompt diff ---
  --- original
  +++ optimized
  @@ -1,3 +1,4 @@
   You are a helpful assistant.
  +Think step by step before answering, and cite sources when possible.
```

Credentials are stored in `~/.config/protege/config.json` (owner-only
permissions) and are shared across every feature namespace — you only need
to log in once.

## Agent Fine-Tuning

Reusable Tasks bundle the inputs; jobs launch and track an optimization run
against one or more target models.

```
# Reusable Task from a local zip
protege task create ./agent.zip --name "my-task" --env-id <env-id>

# Launch from that Task, and watch until it finishes
protege optimize run --task-id <task-id> --target-models qwen/qwen3.5-9b --watch

protege optimize status <job-id>
protege optimize result <job-id> --output-dir ./out

# Hosted inference against a finished agent (id printed by `optimize result`)
protege optimize infer <agent-id> --input "hello"

# Or download and run its code locally, in your own Python environment
protege optimize run-local <agent-id> --input "hello" --llm-api-key <your OpenRouter API key>
# or: export OPENROUTER_API_KEY=...
```

`optimize infer` prints a log id per input, which `optimize judgement` turns
into a score, verdict, and reasoning:

```
$ protege optimize infer 9c2b1f4d-8a3e-4c2b-9d1f-2e7a5c8b6f34 --input "What's the capital of France?"
cold_start=False  elapsed_ms=812
log 7a4e1d2c-...
  input:  What's the capital of France?
  output: Paris.

$ protege optimize judgement 9c2b1f4d-8a3e-4c2b-9d1f-2e7a5c8b6f34 7a4e1d2c-...
verdict: pass
score: 0.97
reasoning: Correct, concise, directly answers the question.
```

This package intentionally installs only `typer`/`httpx` — every downloaded
`agent.py` can depend on a different set of packages, so `optimize run-local`
runs it in your current Python environment as-is. Install whatever that
specific agent's `run_batch` needs yourself before running it locally.

## Environments

An `environment` is a named, encrypted key-set that a Task can attach to.
It's shared infrastructure:

```
protege environment create my-env --key OPENAI_API_KEY=sk-... --key OTHER=value
protege task create ./agent.zip --env-id <env-id>
```

## Custom Router

Train a router that picks the best model for each prompt, from labeled
prompt-to-model examples:

```json
{
  "problems": [
    {
      "problem_key": "p1",
      "problem": "Write a simple hello world function",
      "correct_models": ["openai/gpt-4o-mini", "qwen3.5-9b"]
    }
  ]
}
```

```
protege router train --data-file ./training.json
protege router status <job-id>
```

Once `router status` shows a router id, query it:

```
$ protege router infer <router-id> --prompt "Explain quantum computing in detail"
top_model: qwen3.5-9b
top_prob: 0.83
```

## Full reference

See [CLI.md](CLI.md) for every command, flag, and where each id comes from.
