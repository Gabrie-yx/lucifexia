# NeMo Relay Observability

Optional Lucifex observability plugin that maps Lucifex observer hooks to
NeMo Relay scopes, LLM spans, tool spans, marks, ATOF, and ATIF.

NeMo Relay is NVIDIA's runtime layer for agent execution boundaries. It does
not replace Lucifex Agent's planner, tools, memory, model provider routing, or
CLI UX. Instead, this plugin lets Lucifex emit NeMo Relay lifecycle events for
the work Lucifex already owns: sessions, turns, provider/API calls, tool calls,
approval prompts, and delegated subagents.

With this plugin enabled, Lucifex Agent can:

- Preserve Lucifex execution as NeMo Relay scopes, LLM spans, tool spans, and
  mark events.
- Export raw lifecycle events as Agent Trajectory Observability Format (ATOF)
  JSONL for debugging and offline inspection.
- Export Agent Trajectory Interchange Format (ATIF) trajectories for replay,
  evaluation, and harness analysis workflows.
- Correlate parent sessions, delegated subagents, tool calls, and provider
  calls through shared session, turn, and trajectory metadata.

See the NeMo Relay overview for the broader runtime model:
https://docs.nvidia.com/nemo/relay/about-nemo-relay/overview

ATOF is NVIDIA's canonical JSONL event stream representation for NeMo Relay
lifecycle events. The format is documented in the NeMo Agent Toolkit:
https://github.com/NVIDIA/NeMo-Agent-Toolkit/blob/develop/packages/nvidia_nat_atif/atof-event-format.md

ATIF is the trajectory representation produced from those events. NVIDIA and
Harbor upstreamed ATIF v1.7 support for complex harness workflows, including
subagent trajectory embedding, trajectory IDs, multi-LLM-call step metadata, and
deterministic no-LLM orchestration steps:
https://github.com/harbor-framework/harbor/blob/main/rfcs/0001-trajectory-format.md

## Enablement

Enable the plugin before setting export options:

```bash
lucifex plugins enable observability/nemo_relay
```

The `LUCIFEX_NEMO_RELAY_*` environment variables below only configure an
already-enabled plugin. They do not enable plugin discovery by themselves.

For isolated test homes, enable the plugin in the same `LUCIFEX_HOME` that the
agent run will use:

```bash
env LUCIFEX_HOME=/tmp/lucifex-nemo-relay-test \
  lucifex plugins enable observability/nemo_relay
```

Runs started with `--ignore_user_config` skip the enabled-plugin state from
`LUCIFEX_HOME`, so local E2E tests should omit that flag unless the test harness
loads `observability/nemo_relay` explicitly another way.

`LUCIFEX_HOME` is the Lucifex profile/config home used by both
`lucifex plugins enable ...` and the later `lucifex chat ...` run. If unset,
Lucifex uses the user's default home, usually `~/.lucifex`. For isolated smoke
tests, choose any writable temporary directory and use the same value for every
command in that test:

```bash
export LUCIFEX_HOME=/tmp/lucifex-nemo-relay-test
lucifex plugins enable observability/nemo_relay
lucifex chat --query 'Reply exactly ok' --provider custom --model qwen3.6:35b
```

For source checkouts, make sure the `lucifex` command you run is built from the
checkout that contains this plugin. A globally installed older CLI will not see
new bundled plugins from your working tree.

```bash
uv sync --extra nemo-relay
uv run lucifex plugins enable observability/nemo_relay
uv run lucifex chat --query 'Reply exactly ok' --provider custom --model qwen3.6:35b
```

To ship the updated CLI into another environment, build and install a fresh
wheel from this checkout, then install the official NeMo Relay runtime extra:

```bash
uv build --wheel
python -m pip install --force-reinstall dist/lucifex_agent-*.whl
python -m pip install "nemo-relay==0.3"
lucifex plugins enable observability/nemo_relay
```

The plugin fails open when `nemo-relay` is not installed. Install and test it against the official NeMo Relay 0.3 PyPI distribution:

```bash
pip install "nemo-relay==0.3"
```

## Export Configuration

The plugin can configure exporters directly from `LUCIFEX_NEMO_RELAY_*`
environment variables, or delegate exporter setup to a NeMo Relay
`plugins.toml` component config.

Use environment variables for local smoke tests, CI jobs, and one-off CLI
runs. Use `plugins.toml` when you want one NeMo Relay configuration document to
own observability components such as ATOF, ATIF, OpenTelemetry, and
OpenInference.

### Environment Variables

Useful local export settings after the plugin is enabled:

```bash
export LUCIFEX_NEMO_RELAY_ATOF_ENABLED=1
export LUCIFEX_NEMO_RELAY_ATOF_OUTPUT_DIRECTORY=.nemo-relay/atof
export LUCIFEX_NEMO_RELAY_ATIF_ENABLED=1
export LUCIFEX_NEMO_RELAY_ATIF_OUTPUT_DIRECTORY=.nemo-relay/atif
```

Optional overrides:

- `LUCIFEX_NEMO_RELAY_ATOF_FILENAME`
- `LUCIFEX_NEMO_RELAY_ATOF_MODE` (`append` or `overwrite`)
- `LUCIFEX_NEMO_RELAY_ATIF_FILENAME_TEMPLATE`
- `LUCIFEX_NEMO_RELAY_ATIF_AGENT_NAME`
- `LUCIFEX_NEMO_RELAY_ATIF_AGENT_VERSION`
- `LUCIFEX_NEMO_RELAY_ATIF_MODEL_NAME`
- `LUCIFEX_NEMO_RELAY_ATIF_SUBAGENT_EXPORT_MODE` (`embedded` by default; set `all` to also write standalone child files)

### NeMo Relay Component Config

To initialize NeMo Relay from a component config, create a `plugins.toml` file
and point Lucifex at it:

```bash
export LUCIFEX_NEMO_RELAY_PLUGINS_TOML=.nemo-relay/plugins.toml
```

Minimal ATOF and ATIF config:

```toml
version = 1

[[components]]
kind = "observability"
enabled = true

[components.config]
version = 1

[components.config.atof]
enabled = true
output_directory = ".nemo-relay/atof"
filename = "events.jsonl"
mode = "overwrite"

[components.config.atif]
enabled = true
output_directory = ".nemo-relay/atif"
filename_template = "trajectory-{session_id}.json"
agent_name = "Lucifex Agent"
agent_version = "local"
```

When `LUCIFEX_NEMO_RELAY_PLUGINS_TOML` is set and initializes successfully, NeMo
Relay owns exporter lifecycle through that config. The direct
`LUCIFEX_NEMO_RELAY_ATOF_*` fallback setup is skipped. If the same
`plugins.toml` observability config enables `atif`, the direct
`LUCIFEX_NEMO_RELAY_ATIF_*` fallback setup is also skipped so Lucifex does not
double-export trajectories on teardown. If `plugins.toml` initialization fails,
Lucifex keeps the direct env-var fallbacks active for that run.

To enable NeMo Relay managed execution intercepts for provider and tool calls,
include an adaptive component in the same `plugins.toml`:

```toml
[[components]]
kind = "adaptive"
enabled = true

[components.config.tool_parallelism]
mode = "observe_only"
```

When the adaptive component is enabled and the installed NeMo Relay runtime
exposes `llm.execute(...)` / `tools.execute(...)`, Lucifex routes LLM and tool
execution through those middleware boundaries. The observer hooks still emit
session, turn, approval, and subagent marks; the plugin skips its manual
`llm.call` and `tools.call` spans for executions that are already managed by
NeMo Relay. `tool_parallelism.mode = "observe_only"` keeps tool scheduling
observational while still wrapping the real execution boundary.

For the full generic Lucifex middleware contract, see
[`docs/middleware/README.md`](../../../docs/middleware/README.md).

## Canonical Local Examples

The observe-only examples in this section use the official `nemo-relay==0.3`
distribution and a local Ollama model served through the OpenAI-compatible API.

```bash
pip install "nemo-relay==0.3"

export LUCIFEX_HOME=/tmp/lucifex-nemo-relay-docs/lucifex-home
mkdir -p "$LUCIFEX_HOME"

cat > "$LUCIFEX_HOME/config.yaml" <<'YAML'
model:
  provider: custom
  default: qwen3.6:35b
  base_url: http://127.0.0.1:11434/v1
  api_key: ollama
plugins:
  enabled:
    - observability/nemo_relay
delegation:
  max_spawn_depth: 2
  max_concurrent_children: 2
  child_timeout_seconds: 180
  model: qwen3.6:35b
  provider: custom
  base_url: http://127.0.0.1:11434/v1
  api_key: ollama
YAML
```

### Delegated Subagent Tool Call

This run starts a parent Lucifex session, delegates to a child subagent, has the
child call `terminal`, and writes both ATOF and ATIF.

```bash
export LUCIFEX_NEMO_RELAY_ATOF_ENABLED=1
export LUCIFEX_NEMO_RELAY_ATOF_OUTPUT_DIRECTORY=/tmp/lucifex-nemo-relay-docs/subagent/atof
export LUCIFEX_NEMO_RELAY_ATOF_FILENAME=nested-subagent-atof.jsonl
export LUCIFEX_NEMO_RELAY_ATOF_MODE=overwrite
export LUCIFEX_NEMO_RELAY_ATIF_ENABLED=1
export LUCIFEX_NEMO_RELAY_ATIF_OUTPUT_DIRECTORY=/tmp/lucifex-nemo-relay-docs/subagent/atif
export LUCIFEX_NEMO_RELAY_ATIF_FILENAME_TEMPLATE='nested-subagent-atif-{session_id}.json'
export LUCIFEX_NEMO_RELAY_ATIF_AGENT_NAME='Lucifex Agent E2E'
export LUCIFEX_NEMO_RELAY_ATIF_AGENT_VERSION=docs-example
export LUCIFEX_NEMO_RELAY_ATIF_SUBAGENT_EXPORT_MODE=all

lucifex chat \
  --query 'Use delegate_task exactly once. Ask the child subagent to use the terminal tool exactly once to run printf docs_nested_leaf_function. After the child returns, reply with exactly: parent received nested subagent result.' \
  --provider custom \
  --model qwen3.6:35b \
  --toolsets delegation,terminal \
  --max-turns 10 \
  --quiet \
  --accept-hooks
```

CLI output:

```text
session_id: docs-parent-session
parent received nested subagent result.
```

Sanitized ATOF excerpt:

```jsonl
{"kind":"scope","category":"tool","name":"delegate_task","scope_category":"start","metadata":{"session_id":"docs-parent-session","tool_call_id":"call_delegate"},"data":{"goal":"Run the command `printf docs_nested_leaf_function` using the terminal tool.","toolsets":["terminal"]}}
{"kind":"mark","name":"lucifex.subagent.start","metadata":{"parent_session_id":"docs-parent-session","session_id":"docs-child-session","subagent_id":"sa-0-docs","child_role":"leaf"}}
{"kind":"scope","category":"tool","name":"terminal","scope_category":"end","metadata":{"session_id":"docs-child-session","tool_call_id":"call_terminal","status":"ok"},"data":"{\"output\":\"docs_nested_leaf_function\",\"exit_code\":0,\"error\":null}"}
{"kind":"scope","category":"tool","name":"delegate_task","scope_category":"end","metadata":{"session_id":"docs-parent-session","tool_call_id":"call_delegate","status":"ok"}}
```

Sanitized ATIF excerpt:

```json
{
  "schema_version": "ATIF-v1.7",
  "session_id": "docs-parent-session",
  "agent": {"name": "Lucifex Agent E2E", "version": "docs-example", "model_name": "qwen3.6:35b"},
  "steps": [
    {
      "source": "agent",
      "tool_calls": [{"function_name": "delegate_task"}],
      "observation": {
        "results": [
          {
            "subagent_trajectory_ref": [{"session_id": "docs-child-session"}],
            "content": "{\"results\":[{\"status\":\"completed\",\"tool_trace\":[{\"tool\":\"terminal\",\"status\":\"ok\"}]}]}"
          }
        ]
      }
    },
    {"source": "agent", "message": "parent received nested subagent result."}
  ],
  "subagent_trajectories": [
    {
      "session_id": "docs-child-session",
      "steps": [
        {
          "source": "agent",
          "tool_calls": [{"function_name": "terminal", "arguments": {"command": "printf docs_nested_leaf_function"}}],
          "observation": {"results": [{"content": "{\"output\":\"docs_nested_leaf_function\",\"exit_code\":0,\"error\":null}"}]}
        }
      ]
    }
  ]
}
```

### Parallel Tool Calls

This run asks the model to emit two `read_file` tool calls in the same assistant
message. Lucifex dispatches the read-only tools as one batch, and NeMo Relay
records both tool invocations.

```bash
mkdir -p /tmp/lucifex-nemo-relay-docs/workdir
printf 'docs_parallel_alpha_function\n' > /tmp/lucifex-nemo-relay-docs/workdir/alpha.txt
printf 'docs_parallel_beta_function\n' > /tmp/lucifex-nemo-relay-docs/workdir/beta.txt
cd /tmp/lucifex-nemo-relay-docs/workdir

export LUCIFEX_NEMO_RELAY_ATOF_ENABLED=1
export LUCIFEX_NEMO_RELAY_ATOF_OUTPUT_DIRECTORY=/tmp/lucifex-nemo-relay-docs/parallel/atof
export LUCIFEX_NEMO_RELAY_ATOF_FILENAME=parallel-tools-atof.jsonl
export LUCIFEX_NEMO_RELAY_ATOF_MODE=overwrite
export LUCIFEX_NEMO_RELAY_ATIF_ENABLED=1
export LUCIFEX_NEMO_RELAY_ATIF_OUTPUT_DIRECTORY=/tmp/lucifex-nemo-relay-docs/parallel/atif
export LUCIFEX_NEMO_RELAY_ATIF_FILENAME_TEMPLATE='parallel-tools-atif-{session_id}.json'
export LUCIFEX_NEMO_RELAY_ATIF_AGENT_NAME='Lucifex Agent E2E'
export LUCIFEX_NEMO_RELAY_ATIF_AGENT_VERSION=docs-example

lucifex chat \
  --query 'Use exactly two read_file tool calls in the same assistant message. Read alpha.txt and beta.txt. Do not call terminal. After both tool results are available, reply with exactly: parallel tools complete.' \
  --provider custom \
  --model qwen3.6:35b \
  --toolsets file \
  --max-turns 8 \
  --quiet \
  --accept-hooks
```

CLI output:

```text
session_id: docs-parallel-session
parallel tools complete.
```

Sanitized ATOF excerpt:

```jsonl
{"kind":"scope","category":"llm","name":"custom","scope_category":"end","data":{"assistant_message":{"tool_calls":[{"id":"call_alpha","name":"read_file","arguments":"{\"path\":\"alpha.txt\"}"},{"id":"call_beta","name":"read_file","arguments":"{\"path\":\"beta.txt\"}"}]},"finish_reason":"tool_calls"}}
{"kind":"scope","category":"tool","name":"read_file","scope_category":"start","timestamp":"2026-05-31T00:15:08.956732+00:00","metadata":{"session_id":"docs-parallel-session","tool_call_id":"call_alpha"},"data":{"path":"alpha.txt"}}
{"kind":"scope","category":"tool","name":"read_file","scope_category":"start","timestamp":"2026-05-31T00:15:08.956804+00:00","metadata":{"session_id":"docs-parallel-session","tool_call_id":"call_beta"},"data":{"path":"beta.txt"}}
{"kind":"scope","category":"tool","name":"read_file","scope_category":"end","metadata":{"session_id":"docs-parallel-session","tool_call_id":"call_beta","status":"ok"},"data":"{\"content\":\"     1|docs_parallel_beta_function\\n\"}"}
{"kind":"scope","category":"tool","name":"read_file","scope_category":"end","metadata":{"session_id":"docs-parallel-session","tool_call_id":"call_alpha","status":"ok"},"data":"{\"content\":\"     1|docs_parallel_alpha_function\\n\"}"}
```

Sanitized ATIF excerpt:

```json
{
  "schema_version": "ATIF-v1.7",
  "session_id": "docs-parallel-session",
  "agent": {"name": "Lucifex Agent E2E", "version": "docs-example", "model_name": "qwen3.6:35b"},
  "steps": [
    {
      "source": "agent",
      "tool_calls": [
        {"tool_call_id": "call_alpha", "function_name": "read_file", "arguments": {"path": "alpha.txt"}},
        {"tool_call_id": "call_beta", "function_name": "read_file", "arguments": {"path": "beta.txt"}}
      ],
      "observation": {
        "results": [
          {"source_call_id": "call_beta", "content": "{\"content\":\"     1|docs_parallel_beta_function\\n\"}"},
          {"source_call_id": "call_alpha", "content": "{\"content\":\"     1|docs_parallel_alpha_function\\n\"}"}
        ]
      }
    },
    {"source": "agent", "message": "parallel tools complete."}
  ]
}
```

## ATOF Mapping

The plugin keeps NeMo Relay's native event model:

- Lucifex sessions map to `agent` scopes.
- Lucifex API request hooks map to `llm` scope start/end events.
- Lucifex tool hooks map to `tool` scope start/end events.
- Turn, approval, subagent, and diagnostic fallback events map to `mark`
  events.

For subagent correlation, mark metadata includes parent and child session IDs,
subagent IDs, role/status fields when present, and derived
`parent_trajectory_id` / `child_trajectory_id` values. This keeps the ATOF
stream lossless for later ATIF conversion that can compact subagents into
separate trajectories.

## Adaptive Middleware Example

The `observability/nemo_relay` plugin uses Lucifex execution middleware to hand
LLM and tool calls to NeMo Relay managed execution when an adaptive component is
enabled.

Minimal `plugins.toml`:

```toml
version = 1

[[components]]
kind = "adaptive"
enabled = true

[components.config.tool_parallelism]
mode = "observe_only"
```

Enable it for Lucifex:

```bash
export LUCIFEX_NEMO_RELAY_PLUGINS_TOML=/tmp/lucifex-middleware-test/plugins.toml
```

When the adaptive component is enabled and the installed NeMo Relay runtime
exposes `llm.execute(...)` and `tools.execute(...)`, Lucifex routes execution
through these boundaries:

```text
Lucifex provider call
  -> llm_execution middleware
    -> nemo_relay.llm.execute(...)
      -> Lucifex provider adapter next_call(...)

Lucifex tool call
  -> tool_execution middleware
    -> nemo_relay.tools.execute(...)
      -> Lucifex tool dispatcher next_call(...)
```

The plugin still emits observer marks for sessions, turns, approvals, and
subagents. When adaptive managed execution is active, it skips manual
`llm.call` and `tools.call` observer spans to avoid duplicate LLM/tool events
for the same execution.

### Local Adaptive E2E

This example enables both NeMo Relay observability export and adaptive execution
middleware for a local Lucifex run. This path requires a NeMo Relay runtime that
supports `[components.config.tool_parallelism]`; the `nemo-relay==0.3`
install used by the earlier observability-only examples does not support this
adaptive config.

```bash
export LUCIFEX_HOME=/tmp/lucifex-middleware-test/lucifex-home
mkdir -p "$LUCIFEX_HOME" /tmp/lucifex-middleware-test/nemo-relay

cat > "$LUCIFEX_HOME/config.yaml" <<'YAML'
model:
  provider: custom
  default: qwen3.6:35b
  base_url: http://127.0.0.1:11434/v1
  api_key: ollama
plugins:
  enabled:
    - observability/nemo_relay
YAML

cat > /tmp/lucifex-middleware-test/nemo-relay/plugins.toml <<'TOML'
version = 1

[[components]]
kind = "observability"
enabled = true

[components.config]
version = 1

[components.config.atof]
enabled = true
output_directory = "/tmp/lucifex-middleware-test/atof"
filename = "middleware-events.jsonl"
mode = "overwrite"

[components.config.atif]
enabled = true
output_directory = "/tmp/lucifex-middleware-test/atif"
filename_template = "middleware-trajectory-{session_id}.json"
agent_name = "Lucifex Middleware E2E"
agent_version = "local"

[[components]]
kind = "adaptive"
enabled = true

[components.config.tool_parallelism]
mode = "observe_only"
TOML

export LUCIFEX_NEMO_RELAY_PLUGINS_TOML=/tmp/lucifex-middleware-test/nemo-relay/plugins.toml

lucifex chat \
  --query 'Use the terminal tool exactly once to run printf middleware_execution_ok. Then reply with exactly the command output.' \
  --provider custom \
  --model qwen3.6:35b \
  --toolsets terminal \
  --max-turns 4 \
  --quiet \
  --accept-hooks
```

Expected CLI output:

```text
session_id: middleware-demo-session
middleware_execution_ok
```

Expected ATOF shape:

```jsonl
{"kind":"scope","category":"llm","name":"custom","scope_category":"start","metadata":{"session_id":"middleware-demo-session"},"data":{"mode":"observe_only"}}
{"kind":"scope","category":"tool","name":"terminal","scope_category":"start","metadata":{"session_id":"middleware-demo-session","tool_call_id":"call_terminal"},"data":{"mode":"observe_only"}}
{"kind":"scope","category":"tool","name":"terminal","scope_category":"end","metadata":{"session_id":"middleware-demo-session","tool_call_id":"call_terminal","status":"ok"},"data":"{\"output\":\"middleware_execution_ok\",\"exit_code\":0,\"error\":null}"}
```

Expected ATIF shape:

```json
{
  "schema_version": "ATIF-v1.7",
  "session_id": "middleware-demo-session",
  "agent": {
    "name": "Lucifex Middleware E2E",
    "version": "local",
    "model_name": "qwen3.6:35b"
  },
  "steps": [
    {
      "source": "agent",
      "tool_calls": [
        {
          "function_name": "terminal",
          "arguments": {"command": "printf middleware_execution_ok"}
        }
      ],
      "observation": {
        "results": [
          {
            "source_call_id": "call_terminal",
            "content": "{\"output\":\"middleware_execution_ok\",\"exit_code\":0,\"error\":null}"
          }
        ]
      }
    },
    {
      "source": "agent",
      "message": "middleware_execution_ok"
    }
  ]
}
```
