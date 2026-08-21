# protege CLI reference

Full command reference for `protege`. See [README.md](README.md) for
install, login, and quickstarts.

Every command talks to the URL from `protege login --base-url` (default
IronLabs Studio) using the stored API key from `~/.config/protege/config.json`.

## task

Manage reusable Task definitions — a zip of `agent.py`, `eval.py`,
`dataset.json`, plus optional `dataset.md`/`task.md`.

| Command | Description |
|---|---|
| `task create ZIP [--name] [--description] [--env-id]` | Create a Task from a local zip. Prints the new task id. |
| `task list` | List your Tasks. |
| `task show TASK_ID` | Show a Task's details. |
| `task update TASK_ID [--name] [--description] [--env-id]` | Update name, description, and/or attached environment. |
| `task update-zip TASK_ID ZIP` | Replace `agent.py`/`eval.py`/`dataset.json`. |
| `task update-dataset-md TASK_ID FILE` | Replace `dataset.md`. |
| `task update-task-md TASK_ID FILE` | Replace `task.md`. |
| `task delete TASK_ID` | Delete a Task. |

```
protege task create ./agent.zip --name "support-agent" --env-id <env-id>
```

## environment

Manage Environments — named, encrypted key-sets. Shared across Tasks today;
Custom Router training may attach one in the future.

| Command | Description |
|---|---|
| `environment create NAME --key KEY=VALUE [--key ...]` | Create an Environment with one or more keys. |
| `environment list` | List your Environments. |
| `environment show ENV_ID` | Show an Environment's details (values are always masked). |
| `environment update ENV_ID [--rename] [--set KEY=VALUE] [--unset KEY]` | Rename and/or add/overwrite/remove keys. |
| `environment delete ENV_ID` | Delete an Environment. |

```
protege environment create prod --key OPENAI_API_KEY=sk-... --key OTHER=value
```

## optimize

Launch and monitor agent-finetuning jobs, then run or inspect the resulting
agents. Every job optimizes a Task (or an ad hoc zip) against one or more
target models — one **agent** per target model.

| Command | Description |
|---|---|
| `optimize run (--task-id ID \| --input-url URL \| --input-zip PATH) --target-models MODELS [flags...]` | Launch a job. Prints the new job id. |
| `optimize list` | List all your optimization jobs. |
| `optimize status JOB_ID` | Show a job's status and per-model iteration progress, including each agent's id. |
| `optimize result JOB_ID [--model] [--output-dir]` | Show a job's final results — score, cost, prompt diff, and each agent's id — optionally downloading each model's `agent.py`. |
| `optimize cancel JOB_ID` | Cancel a queued or running job. |
| `optimize download AGENT_ID [--iteration] [--force]` | Download an agent's code so it can be run locally. |
| `optimize run-local AGENT_ID --input "..." [--llm-api-key] [--iteration] [--force-download]` | Download (if needed) and run an agent's code locally, in your own Python environment. |
| `optimize infer AGENT_ID --input "..." [--input ...]` | Run hosted inference against a completed agent (up to 10 inputs). Prints a log id per input. |
| `optimize infer-status AGENT_ID` | Show the hosted inference sandbox status for an agent. |
| `optimize judgement AGENT_ID LOG_ID` | Show the judge's verdict (score/verdict/reasoning) for one inference call. |

`optimize run` flags:

| Flag | Default | Description |
|---|---|---|
| `--task-id` | — | Launch from an existing Task. Mutually exclusive with `--input-url`/`--input-zip`. |
| `--input-url` | — | Launch from an already-hosted zip URL, no Task. |
| `--input-zip` | — | Launch from a local zip file, no Task — uploaded automatically. |
| `--target-models` | required | Comma-separated model list (1-5). |
| `--n-iterations` | `15` | Optimization iterations per model. |
| `--overall-timeout` | `3600` | Overall job timeout, seconds. |
| `--llm-call-timeout` | `600` | Per-LLM-call timeout, seconds. |
| `--sandbox-timeout` | `3600` | Sandbox execution timeout, seconds. |
| `--enable-mcp` | `false` | Enable MCP tool access during optimization. |
| `--force-baseline` | `false` | Force a fresh baseline run instead of reusing a cached one. |
| `--run-benchmark` | `false` | Run the benchmark suite after optimization. |
| `--force-benchmark` | `false` | Force a fresh benchmark run instead of reusing a cached one. |
| `--env-id` | — | Environment to attach — only used with `--input-url`/`--input-zip`; Task-based runs use the Task's own environment. |
| `--team-id` | — | Launch under a team workspace. |
| `--name` / `--description` | — | Label the job. |
| `--watch` | `false` | Poll every 15s and print progress until the job reaches a terminal status. |

Where ids come from: `optimize run`/`optimize list` print the **job id**.
`optimize status`/`optimize result` print each result's **agent id**
(`agent <id>  model=...`). `optimize infer` prints a **log id** per input,
used by `optimize judgement`.

```
protege optimize run --input-zip ./agent.zip --target-models claude-sonnet-4-6,gpt-5 --watch
protege optimize result <job-id> --output-dir ./out
protege optimize infer <agent-id> --input "hello there"
protege optimize judgement <agent-id> <log-id>
```

## router

Train and query a Custom Router — a model that picks the best target model
for a prompt.

| Command | Description |
|---|---|
| `router train (--data-file PATH [--data-file ...] \| --data-url URL [--data-url ...]) [--team-id]` | Train a router on prompt-to-model examples (1-10 data files/URLs combined). Prints the new job id. |
| `router status JOB_ID` | Show a training job's status. Prints the router id once training completes. |
| `router infer ROUTER_ID --prompt "..."` | Get the recommended model and confidence for a prompt from a trained, active router. |

Training data is JSON:

```json
{
  "problems": [
    {
      "problem_key": "p1",
      "problem": "Write a simple hello world function",
      "correct_models": ["openai/gpt-4o-mini", "anthropic/claude-3-5-haiku-20241022"]
    }
  ]
}
```

```
protege router train --data-file ./training.json
protege router status <job-id>
protege router infer <router-id> --prompt "Explain quantum computing in detail"
```
