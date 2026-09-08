# Codex runtime smoke contract

This document defines the **runtime-only** acceptance probes for Codex compatibility in this repo. It deliberately does not replay the full `paper-analysis` business workflow.

The business workflow remains unchanged: `mode: full` still has three analysis directions in the canonical agent. That three-way fan-out is a **deterministic business contract** and is covered by repository tests. Runtime smoke tests only prove runtime primitives that deterministic tests cannot prove.

Before changing these probes, check the current Codex documentation first. For Codex CLI 0.153.4-specific judgments, also check the matching release/source behavior.

Relevant official documentation:

- https://developers.openai.com/codex/subagents
- https://developers.openai.com/codex/noninteractive
- https://github.com/openai/codex/releases/tag/rust-v0.153.4

## General harness rules

- Use a clean consumer installed from the exact PR head being graded.
- Use the project harness convention: invoke Codex through `direnv exec . codex ...`.
- `openrouter` is the default low-cost smoke profile, but it is not itself a merge criterion. A valid runtime result from another profile is not invalid merely because the profile differs, unless the test explicitly targets that provider/model.
- Do not pre-check whether the command exists before the `direnv exec` invocation.
- Do not substitute Workspace Agents, `search_agents`, a central launcher, a consumer overlay, or a generic child for an exact custom-agent probe.
- Keep each runtime probe minimal. Do not analyze a real paper, do not start all three business analysis leaves, and do not use runtime smoke to re-test deterministic helper behavior.

## C1 — exact custom coordinator spawn

Purpose: prove that the project-scoped custom agent installed at `.codex/agents/paper-analysis.toml` can actually be selected and spawned.

The prompt should directly request the local custom agent by its documented name, `paper-analysis`, while making clear that it is a project-scoped Codex custom agent rather than a ChatGPT Workspace Agent.

For Codex CLI 0.153.4, grade the actual persisted root rollout, not only the `codex exec --json` stdout stream. The decisive evidence is the real native `spawn_agent` request selecting the custom role, e.g. `agent_type = paper-analysis`, followed by a successful child spawn. `task_name` is only a child task/path label and is not a substitute for the custom-agent selector.

PASS requires:

1. the clean consumer contains the APM-projected `.codex/agents/paper-analysis.toml` with `name = "paper-analysis"`;
2. the persisted rollout shows a successful native spawn selecting `paper-analysis` as the custom agent/role for the tested Codex version;
3. the spawned coordinator completes a harmless acknowledgement task.

The absence of `agent_type`, role, or custom-agent identity fields from `codex exec --json` stdout or child preview metadata is **not** by itself a failure. Those surfaces are not the identity source of truth for this smoke.

If the model-visible spawn schema for the tested runtime does not expose any supported custom-agent selector, report a runtime/model tool-surface blocker. If the selector is exposed but the model omits it, report a harness/model routing failure. Only treat it as a repo regression when Codex attempts to select `paper-analysis` and the installed role/config cannot be loaded correctly.

## C2 — deterministic installed-helper acceptance

No model session is required. Keep the existing deterministic clean-consumer helper checks. This probe is intentionally separate from runtime orchestration.

## C3 — single nested-leaf orchestration smoke

Purpose: prove the one runtime primitive the real `full` workflow needs beyond C1: a `paper-analysis` coordinator can spawn a child analysis worker and receive its result.

This is **not** a three-way business replay.

Topology to prove:

```text
root
  -> paper-analysis coordinator
       -> exactly one read-only leaf
```

Use a harmless synthetic task. The coordinator should spawn **exactly one** leaf, ask it to return a fixed marker such as `NESTED_LEAF_OK`, wait for that one leaf, and return the marker to the root. The leaf must not load the coordinator skill and must not spawn another child.

PASS requires:

1. C1 has already established the exact `paper-analysis` coordinator;
2. the persisted/runtime evidence shows one nested child spawned by that coordinator;
3. the nested child returns the fixed marker and the coordinator receives it;
4. no second or third live analysis leaf is required for this smoke.

Do **not** require all three business analysis leaves to start. The three business directions remain locked by deterministic tests in this repository; starting all three would add model cost and failure surface without proving a new Codex primitive.

If a single nested spawn is impossible because of the tested Codex runtime/config topology, record that capability result directly. Do not compensate with a central launcher or by moving the leaf spawn back to the root.

## C4 — same-coordinator continuation smoke

Purpose: prove the Codex fallback for required user input can continue the existing coordinator rather than silently defaulting or replacing it with a fresh coordinator.

Keep this probe minimal and independent of C3 fan-out:

1. root spawns the exact `paper-analysis` coordinator;
2. coordinator receives a synthetic request missing one required input and yields explicit `needs_input`;
3. the root run completes/returns control;
4. continue the **root Codex session** using the documented non-interactive continuation surface, `codex exec resume <ROOT_SESSION_ID> ...`;
5. after the answer is supplied, the existing coordinator is continued/reused through the runtime's native mechanism.

PASS requires semantic continuity: the resumed root must not create a second fresh `paper-analysis` coordinator to replace the first one. Do not require any analysis leaf during C4.

The test contract does not mandate an internal continuation tool name. `send_input`, `resume_agent`, `followup_task`, or another runtime-native primitive may vary by Codex version; the observable requirement is reuse of the existing coordinator rather than fresh-spawn substitution.

## Merge interpretation

Codex runtime acceptance is intentionally small:

- C1: one exact custom coordinator spawn;
- C2: deterministic installed helpers;
- C3: one nested leaf;
- C4: one same-coordinator continuation.

The runtime suite must not be expanded into full-paper analysis or mandatory three-leaf fan-out unless a future PR specifically changes those runtime semantics. The normal test suite remains responsible for the three-way business contract and all deterministic evidence/schema invariants.
