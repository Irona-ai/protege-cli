# protege

The IronLabs platform CLI.

## Install

```
pip install -e .
```

## Usage

```
protege login --api-key <your IronLabs API key>
# --base-url is optional, only needed to point at a non-default IronLabs deployment

# agent-finetuning: Agent-Finetuning job management
protege agent-finetuning task create ./agent.zip --name "my-task" --env-id <env-id>
protege agent-finetuning task list
protege agent-finetuning task show <task-id>
protege agent-finetuning task update <task-id> --name "renamed"
protege agent-finetuning task update-zip <task-id> ./agent.zip
protege agent-finetuning task delete <task-id>

protege agent-finetuning env create my-env --key OPENAI_API_KEY=sk-... --key OTHER=value
protege agent-finetuning env list
protege agent-finetuning env show <env-id>
protege agent-finetuning env update <env-id> --set NEW_KEY=value --unset OLD_KEY
protege agent-finetuning env delete <env-id>

protege agent-finetuning run --task-id <task-id> --target-models claude-sonnet-4-6,gpt-5 \
    --n-iterations 15 --run-benchmark --watch

# or from a zip URL, without creating a Task
protege agent-finetuning run --input-url https://.../agent.zip --target-models claude-sonnet-4-6

protege agent-finetuning status <job-id>
protege agent-finetuning results <job-id> --output-dir ./out
protege agent-finetuning cancel <job-id>

# Download an optimized agent's code and run it locally against one input
protege agent-finetuning download <optimized-prompt-id>
protege agent-finetuning run-local <optimized-prompt-id> --input "hello" --llm-api-key <your OpenRouter API key>
# or: export OPENROUTER_API_KEY=...
```

`<optimized-prompt-id>` is the per-model result ID shown by `results`. Downloaded
agent code is cached under `~/.cache/protege/agent-finetuning/agents/<optimized-prompt-id>/agent.py`.

This package intentionally installs only `typer`/`httpx` — every downloaded
`agent.py` can depend on a different set of packages, so `run-local` runs it
in your current Python environment as-is. Install whatever that specific
agent's `run_batch` needs yourself before running it locally.

Credentials are stored in `~/.config/protege/config.json` (owner-only
permissions) and are shared across every feature namespace.
