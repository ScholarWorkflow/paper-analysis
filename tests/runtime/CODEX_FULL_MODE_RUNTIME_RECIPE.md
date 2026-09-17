# Codex Full-Mode Runtime Recipe — `PA-CODEX-FULL-LEAF-01`

Producer-owned acceptance recipe for issue #13. It proves, on a clean
consumer and the real `mode: full` entry path, that the unique formal outer
child spawns exactly three native nested subagent delegation children at Step 3
instead of inlining the three-way analysis.

本文件是 producer 仓库内的正式 Test Recipe：执行者按本文逐步操作，不依赖
issue 文本；issue 只描述目标，本文描述可执行步骤与判定。

Identity 边界（本 recipe 的 hard boundary）：runtime agent identity /
`agent_type` 永远不是本 case 的 PASS / FAIL / BLOCKED 条件。本 case 只验
formal nested delegation topology：

```text
root thread
  -> exactly 1 formal direct outer child
       -> exactly 3 distinct formal direct nested children
```

`outer child` 只按 formal thread ownership 定位，不声明、不判断它的
runtime agent identity。

## 1. Identity（Test Case 元数据，不是 agent identity）

- **Case ID**: `PA-CODEX-FULL-LEAF-01`
- **Acceptance criterion**: 固定 root prompt 成功产生唯一 formal outer
  child 后，该 outer child 必须产生恰好 3 个 distinct formal direct nested child。
- **Invariant**: root 只负责一次 outer dispatch；nested delegation 必须来自
  安装后的 coordinator instructions（`developer_instructions`），不得由
  root prompt 强迫、描述或暗示。
- **Does NOT prove**:
  - runtime child 的 `agent_type`；
  - requested/loaded/effective role；
  - exact agent identity；
  - 三个 leaf 的内容质量或必须同时存在 3 个 live child；
  - OCR/future-work/facts 质量；
  - `professor-contact` 集成质量；
  - OpenCode runtime compatibility。

业务结构不变：full Step 3 三路 semantic roles
（① 内容沉淀；② 贡献与批判；③ 帮助评估）由 deterministic producer test
锁定；runtime smoke 要求恰好 `3` 个 distinct formal direct nested child。

## 2. Basis

固定 shared fixture revision（执行前必须复核）：

```text
skills-test-fixtures:
9cb4547845be323a2a7b59139ee419476f2c7113
contract:
skills-test-fixtures/codex-eval-adapter@9
```

本 case 只使用：

```text
/eval top-level passed/version
output.thread_id
output.app_server_events
pinned contract 中 formal spawnAgent relation 规则
```

本 case **不使用**：

```text
parse_codex_eval_evidence.py 的 adapter verdict
output.child_thread_reads
dispatch.agent_identity
requested_role / loaded_identity / effective_role
agent_type / agentRole / agentPath
模型文本中的 agent 名称
```

说明：pinned @9 contract 仍是 formal topology field/rule 的共享事实来源
（`app_server_event_envelope`、`raw_identity_path.formal_spawn_relation`、
`delegation.fail_closed`）；本 producer verifier 直接消费 raw
`/eval` 结构化事件，不让 shared adapter 的 identity-conflict 实现进入
merge verdict 链。

版本语义：

- `/eval.version` 记录 provenance；`version == null` → `BLOCKED`；
- 非 null 版本字符串变化本身不 BLOCK / FAIL；
- 当前 runtime 若不再提供 contract 所需 formal topology 字段 →
  `BLOCKED` / `INVALID_EVIDENCE`，并保存原始 response 做 characterization。

## 3. Prerequisites

执行者准备：

```bash
export PRODUCER_REPO=/absolute/path/to/paper-analysis
export FIXTURES_DIR=/absolute/path/to/skills-test-fixtures
export EVAL_SERVER_DIR=/absolute/path/to/eval-server
```

必须满足：

- `PRODUCER_REPO` 是 final implementation branch/worktree；final commit 已
  push，GitHub 可按 exact SHA 获取；
- `FIXTURES_DIR` 精确位于上面 pinned fixture SHA，且 dirty=no；
- 使用既有 eval service；不得启动/停止/重启；
- 不直接 shell 执行 `codex`；
- consumer 在 producer repo / worktrees 外；
- 无 local path / symlink / editable / copied artifact / manual patch；
- producer SHA 或 fixture SHA 变化后旧 acceptance evidence 失效，重建
  consumer 重跑。

本 Codex case **不启动 `skills-test-fixtures` runtime fixture**，因此不得
伪造 `fixture_run_id`。记录真实 `recipe_run_id`、fixture repo SHA/dirty、
eval runtime provenance。

## 4. Exclusive run root / provenance

正式 acceptance 的 canonical fixture、capability/topology verifier 与
deterministic suite 都直接从本地 `$PRODUCER_REPO` checkout 读取/执行，所以
producer worktree 自身的 tracked + untracked 干净状态是 `FINAL_HEAD_SHA`
provenance 的必要条件。创建 run root 之后、消费任何 producer-owned
fixture/verifier 之前机械记录该状态；producer checkout dirty 时只能
`BLOCKED / NOT TESTED`，不得继续 capability probe / formal runtime
acceptance。

```bash
set -euo pipefail

export FINAL_HEAD_SHA="$(git -C "$PRODUCER_REPO" rev-parse HEAD)"
FIXTURES_SHA=9cb4547845be323a2a7b59139ee419476f2c7113

test "$(git -C "$FIXTURES_DIR" rev-parse HEAD)" = "$FIXTURES_SHA"
test -z "$(git -C "$FIXTURES_DIR" status --porcelain)"

RUN_ROOT="$(mktemp -d /tmp/paper-analysis-full-leaf.XXXXXX)"
mkdir -p "$RUN_ROOT/config" "$RUN_ROOT/output" "$RUN_ROOT/consumer"
export RUN_ROOT
export CONSUMER="$RUN_ROOT/consumer"

PRODUCER_DIRTY="$(git -C "$PRODUCER_REPO" status --porcelain)"
if [ -n "$PRODUCER_DIRTY" ]; then
  printf '%s\n' 'producer_repo_dirty=yes' \
    >"$RUN_ROOT/output/producer-repo-dirty.txt"
  printf '%s\n' "$PRODUCER_DIRTY" \
    >"$RUN_ROOT/output/producer-repo-status.txt"
  echo 'producer checkout dirty -> BLOCKED / NOT TESTED'
  exit 1
fi
printf '%s\n' 'producer_repo_dirty=no' \
  >"$RUN_ROOT/output/producer-repo-dirty.txt"

RECIPE_RUN_ID="$(basename "$RUN_ROOT")"

git -C "$CONSUMER" init -q

printf '%s\n' "$FINAL_HEAD_SHA" >"$RUN_ROOT/output/producer-sha.txt"
printf '%s\n' "$FIXTURES_SHA" >"$RUN_ROOT/output/fixture-repo-sha.txt"
printf '%s\n' 'fixture_repo_dirty=no' >"$RUN_ROOT/output/fixture-repo-dirty.txt"
printf '%s\n' "$RECIPE_RUN_ID" >"$RUN_ROOT/output/recipe-run-id.txt"
printf '%s\n' "$CONSUMER" >"$RUN_ROOT/output/consumer-path.txt"
printf '%s\n' 'consumer_newly_created=yes' >"$RUN_ROOT/output/consumer-newly-created.txt"
printf '%s\n' 'manual_patch=no' >"$RUN_ROOT/output/manual-patch.txt"
printf '%s\n' "$(git -C "$EVAL_SERVER_DIR" rev-parse HEAD)" >"$RUN_ROOT/output/eval-server-checkout-sha.txt"
apm --version >"$RUN_ROOT/output/apm-version.txt"
```

## 5. Explicit Git-pinned install

不要用可能受 default registry 影响的 `owner/repo#SHA` shorthand。

```bash
cat >"$CONSUMER/apm.yml" <<EOF
name: paper-analysis-issue13-consumer
version: 0.0.0
targets: [codex]
dependencies:
  apm:
    - git: https://github.com/ScholarWorkflow/paper-analysis.git
      ref: $FINAL_HEAD_SHA
EOF

cp "$CONSUMER/apm.yml" "$RUN_ROOT/output/consumer-apm.yml"

yq -e '.dependencies.apm[0].git == "https://github.com/ScholarWorkflow/paper-analysis.git"' \
  "$CONSUMER/apm.yml" >/dev/null
yq -e '.dependencies.apm[0].ref == strenv(FINAL_HEAD_SHA)' \
  "$CONSUMER/apm.yml" >/dev/null

(
  cd "$CONSUMER"
  apm install --target codex \
    >"$RUN_ROOT/output/apm-install.stdout.txt" \
    2>"$RUN_ROOT/output/apm-install.stderr.txt"
)
printf '%s\n' 'apm install --target codex' >"$RUN_ROOT/output/install-command.txt"
```

必须存在：

```bash
test -f "$CONSUMER/apm.lock.yaml"
test -f "$CONSUMER/.codex/agents/paper-analysis.toml"
test -f "$CONSUMER/.agents/skills/paper-analysis/SKILL.md"
```

production install tree 只保留真实运行资产（`SKILL.md`、`scripts/` 等）；
producer test tree 全部位于 repo 级 `tests/`，不随 skill 分发。安装树内的
test-only artifacts 机械排除见 §6 purity preflight。

用 `yq` 证明 lock 确实 pin 到 final Git commit。APM 0.29 lockfile 把
`repo_url` 归一化为小写 `owner/repo`（不是 `https://...` URL 形式），原始
大小写保留在 `materialization_repo_url`，主机在 `host` 字段，所以机械
判定用 `host` + `materialization_repo_url` 组合：

```bash
yq -e '.dependencies[] | select(.resolved_commit == strenv(FINAL_HEAD_SHA)) | select(.host == "github.com" and .materialization_repo_url == "ScholarWorkflow/paper-analysis")' \
  "$CONSUMER/apm.lock.yaml" >/dev/null
cp "$CONSUMER/apm.lock.yaml" "$RUN_ROOT/output/apm.lock.yaml"
```

## 6. Clean-consumer purity preflight

test-only artifacts 一旦进入 production skill 安装树，被测 agent 就能读到
测试执行知识并改变正式入口行为；这种 run 属于 test setup contamination，
不能产生 producer 行为结论。安装后在任何 `/eval` 调用之前机械检查，任一
命中立即 `BLOCKED / NOT TESTED`：不得继续 runtime topology，更不得据此判
`FAIL_PRODUCER`。

```bash
PURITY_OUT="$RUN_ROOT/output/purity-preflight.txt"

LEAKS="$(find "$CONSUMER/.agents/skills/paper-analysis" \
  \( -name 'CODEX_FULL_MODE_RUNTIME_RECIPE.md' \
     -o -name 'verify_codex_full_mode_topology.py' \
     -o -name 'verify_codex_nested_capability_probe.py' \))"

if [ -e "$CONSUMER/.agents/skills/paper-analysis/tests" ] || [ -n "$LEAKS" ]; then
  {
    printf 'installed_tests_dir=%s\n' "$(
      [ -e "$CONSUMER/.agents/skills/paper-analysis/tests" ] && echo present || echo absent
    )"
    [ -n "$LEAKS" ] && printf '%s\n' "$LEAKS"
  } >"$PURITY_OUT"
  cat "$PURITY_OUT"
  echo 'purity_preflight=FAIL -> BLOCKED / NOT TESTED'
  exit 1
fi

printf '%s\n' 'purity_preflight=pass' >"$PURITY_OUT"
```

## 7. Generated projection check

安装后只检查本 issue 的行为 contract，不用 TOML `name` 做 runtime
identity gate：

```bash
python3 - <<'PY'
import hashlib
import json
import os
import pathlib
import tomllib

consumer = pathlib.Path(os.environ["CONSUMER"])
run_root = pathlib.Path(os.environ["RUN_ROOT"])
agent = consumer / ".codex/agents/paper-analysis.toml"
data = tomllib.loads(agent.read_text(encoding="utf-8"))
instructions = data["developer_instructions"]
assert isinstance(instructions, str) and instructions

required = {
    "full_delegation_required": "Codex full Step 3 必须使用运行时原生 subagent delegation",
    "no_inline_replacement": "coordinator 不得 inline 执行三路分析来替代 delegation",
    "exactly_three_delegated_units": "Step 3 必须恰好分派 exactly 3 个有界只读分析工作单元",
    "discovery_before_analysis": "在执行任何三路分析内容前，必须先通过当前 Codex 运行时的 Code Mode / programmatic tool-calling surface 发现实际可调用的原生 multi-agent delegation 工具",
    "no_shell_curl_eval_fallback": "`exec_command` shell、curl、另起 `/eval` 都不是 delegation fallback",
    "discovery_failure_explicit": "明确返回 delegation-capability failure",
}
checks = {key: marker in instructions for key, marker in required.items()}
assert all(checks.values())

out = {
    "schema": 1,
    "checks": checks,
    "sha256": hashlib.sha256(agent.read_bytes()).hexdigest(),
}
(run_root / "output/generated-projection.json").write_text(
    json.dumps(out, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)
PY
```

## 8. PA-CODEX-NESTED-CAP-00：nested-capability characterization（正式 acceptance 前置）

正式 `PA-CODEX-FULL-LEAF-01` acceptance 在本 characterization 完成前**尚未
开始**。Codex V1 路径默认 `DEFAULT_AGENT_MAX_DEPTH = 1`
（`core/src/config/mod.rs`），且 `collab_tools_enabled` 在
`next_thread_spawn_depth > agent_max_depth` 时根本不向当前 thread 暴露
collab 工具面（`core/src/tools/spec_plan.rs`；spawn handler 超限路径见
`core/src/tools/handlers/multi_agents/spawn.rs` 的
`Agent depth limit reached. Solve the task yourself.`）。因此"root 成功
spawn outer、outer 零 spawn 尝试"与"depth-1 child 根本没有 nested spawn
工具面"两种解释相容；未完成本 characterization 前，正式 business prompt
观察到的 `outer nested != 3` 不得唯一归因 producer instruction。

**调用面事实（corrected design 的依据）**：本 runtime 调用原生 V1
multi-agent 工具的已观察入口是 Code Mode programmatic tool calling——
`custom_tool_call: exec` 内执行
`await tools.multi_agent_v1__spawn_agent(...)`（root 先以 `ALL_TOOLS`
发现工具名，再经 `exec` 调用；formal `collabAgentToolCall/spawnAgent`
随后出现）。因此 probe prompt 一旦禁止 `exec`，就同时禁掉了被测
capability 的实际调用入口，child 的 `nested=0` 无法区分：

1. child 根本没有 `multi_agent_v1__spawn_agent`；
2. child 有该 tool，但被 test prompt 禁止通过 Code Mode `exec` 调用；
3. model 没有主动发现/调用它。

历史教训：producer SHA `68bb65d` 的首轮 Probe A/B prompt 含
"不得用 shell、curl、exec…"，属 `BLOCKED /
INVALID_CHARACTERIZATION_DESIGN / NOT ATTRIBUTABLE`（§19）；本轮起改用
§9 corrected prompt 重跑。characterization 不能靠一个会抑制被测
capability 的 prompt 得出 capability absence 结论。

- Case ID: `PA-CODEX-NESTED-CAP-00`；
- Acceptance / characterization target：在与正式 smoke 相同的 Codex profile
  下，确认 root 创建的 depth-1 child 能否继续产生 formal depth-2
  grandchild；然后只改变 `agents.max_depth=2` 做一次 A/B；
- 只证明 runtime nested delegation capability；不证明 `paper-analysis`
  behavior、agent identity、child role、内容质量；
- identity / `agent_type` / `agentRole` / `agentPath` 一律不进入 probe
  verdict；
- Basis：沿用当前 pinned `skills-test-fixtures/codex-eval-adapter@9` 的
  formal `spawnAgent` relation：只认 raw `/eval` `output.app_server_events`
  中 `collabAgentToolCall + spawnAgent` 的 formal sender/receiver
  ownership；不靠模型自述"有没有工具"；
- Prerequisites：复用正式 Recipe 已完成的 exact producer SHA、clean
  consumer、purity preflight（§6）、generated projection（§7）、fixture
  SHA、既有 eval service；
- Probe 必须在正式 `paper-analysis` business prompt（§13/§14）之前运行；
  corrected Probe A′、B′ 各只运行一次，是 characterization A/B，不允许
  retry-until-green。

## 9. 固定 capability probe prompt（corrected design）

root 仍只创建 exactly one direct child；child 固定任务为下述原文。**不得
再写入"不得使用 exec"**：Code Mode `custom_tool_call: exec` 是本 runtime
调用 `tools.multi_agent_v1__spawn_agent(...)` 的 programmatic tool-calling
surface，不等同于 shell command；禁止它就是抑制被测 capability（§8）。

```bash
cat >"$RUN_ROOT/config/nested-capability-prompt.txt" <<'EOF'
这是 nested-subagent capability characterization，不读取项目业务文件，不做业务分析。

你作为 root 只创建 exactly one direct child，并把下面"direct child 任务"整段原文交给该 child，等待它完成后结束；root 不得自己创建 grandchild。

--- direct child 任务（原文传达，不要改写）---
这是 nested-subagent capability characterization，不读取项目业务文件，不做业务分析。

你必须尝试使用当前 runtime 提供的原生 subagent delegation 创建 exactly one child。
允许使用 Code Mode / programmatic tool calling 来发现并调用 runtime 已暴露的 native multi-agent tool；这不属于 shell fallback。

禁止：
- shell command / terminal command；
- curl / HTTP；
- 文件写入；
- 另起 /eval；
- 用文本声称 GRANDCHILD_OK 来冒充 delegation。

grandchild 只返回 GRANDCHILD_OK。
创建后等待它完成，然后 direct child 只返回 CHILD_DONE。
若 runtime 确实未向该 child 暴露 nested multi-agent tool，则直接结束，不走替代路径。
--- direct child 任务结束 ---
EOF
```

这是 characterization prompt，允许明确要求 nested spawn；它**绝不复用**为
正式 `PA-CODEX-FULL-LEAF-01` prompt。

## 10. Probe A′ — 当前默认配置

与正式 acceptance 完全相同的 runtime profile（`--json --ephemeral
--skip-git-repo-check --sandbox workspace-write --cd $CONSUMER --model
gpt-5.6-luna --config model_reasoning_effort="low" --config
projects."$CONSUMER".trust_level="trusted"`），唯一 prompt 为
`$RUN_ROOT/config/nested-capability-prompt.txt`，**不增加
`agents.max_depth` override**，只运行一次：

```bash
python3 - <<'PY'
import json
import os
import pathlib
import shlex

run_root = pathlib.Path(os.environ["RUN_ROOT"])
consumer = os.environ["CONSUMER"]
prompt = (run_root / "config/nested-capability-prompt.txt").read_text(encoding="utf-8")

args = [
    "--json",
    "--ephemeral",
    "--skip-git-repo-check",
    "--sandbox", "workspace-write",
    "--cd", consumer,
    "--model", "gpt-5.6-luna",
    "--config", 'model_reasoning_effort="low"',
    "--config", f'projects."{consumer}".trust_level="trusted"',
    "--", prompt,
]
request = {"command": " ".join(shlex.quote(x) for x in args), "timeout": 900}
(run_root / "config/capability-default-eval-request.json").write_text(
    json.dumps(request, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)
PY

cp "$RUN_ROOT/config/capability-default-eval-request.json" \
  "$RUN_ROOT/output/capability-default-eval-request.json"

curl --fail-with-body -sS \
  -X POST "http://127.0.0.1:$EVAL_PORT/eval" \
  -H 'Content-Type: application/json' \
  --data-binary @"$RUN_ROOT/output/capability-default-eval-request.json" \
  >"$RUN_ROOT/output/capability-default-eval-response.json"

python3 "$PRODUCER_REPO/tests/runtime/verify_codex_nested_capability_probe.py" \
  --eval-response "$RUN_ROOT/output/capability-default-eval-response.json" \
  --contract "$FIXTURES_DIR/configs/codex-eval-adapter-contract.json" \
  --output "$RUN_ROOT/output/capability-default-topology.json"
```

## 11. Probe B′ — 唯一变化 `agents.max_depth=2`

仅在 Probe A′ 结果为 `NO_NESTED` 时运行（A′=NESTED_OK 时不得运行 B′，
直接按 §12 分支进入正式 acceptance）。完全复用 Probe A′ 的 model /
reasoning / sandbox / cwd / trust / prompt；
**唯一允许变化**是 args 列表在 trust config 之后新增一项
`"--config", "agents.max_depth=2"`；同样只运行一次：

```bash
python3 - <<'PY'
import json
import os
import pathlib
import shlex

run_root = pathlib.Path(os.environ["RUN_ROOT"])
consumer = os.environ["CONSUMER"]
prompt = (run_root / "config/nested-capability-prompt.txt").read_text(encoding="utf-8")

args = [
    "--json",
    "--ephemeral",
    "--skip-git-repo-check",
    "--sandbox", "workspace-write",
    "--cd", consumer,
    "--model", "gpt-5.6-luna",
    "--config", 'model_reasoning_effort="low"',
    "--config", f'projects."{consumer}".trust_level="trusted"',
    "--config", "agents.max_depth=2",
    "--", prompt,
]
request = {"command": " ".join(shlex.quote(x) for x in args), "timeout": 900}
(run_root / "config/capability-depth2-eval-request.json").write_text(
    json.dumps(request, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)
PY

cp "$RUN_ROOT/config/capability-depth2-eval-request.json" \
  "$RUN_ROOT/output/capability-depth2-eval-request.json"

curl --fail-with-body -sS \
  -X POST "http://127.0.0.1:$EVAL_PORT/eval" \
  -H 'Content-Type: application/json' \
  --data-binary @"$RUN_ROOT/output/capability-depth2-eval-request.json" \
  >"$RUN_ROOT/output/capability-depth2-eval-response.json"

python3 "$PRODUCER_REPO/tests/runtime/verify_codex_nested_capability_probe.py" \
  --eval-response "$RUN_ROOT/output/capability-depth2-eval-response.json" \
  --contract "$FIXTURES_DIR/configs/codex-eval-adapter-contract.json" \
  --output "$RUN_ROOT/output/capability-depth2-topology.json"
```

不换模型、不提高 reasoning、不改 prompt、不改 sandbox、不改 fixture、不改
producer、不改 eval-server。

## 12. Probe 判定与分支

`verify_codex_nested_capability_probe.py` 的机械规则（只看 formal machine
evidence；不从模型自述、prompt 文本或 identity 推导 capability）：

- `/eval` 不 healthy（`passed == false`）或 `version` 为 null → `BLOCKED`；
- malformed formal evidence → `INVALID_EVIDENCE`；
- root formal direct child `!= 1` → `BLOCKED`（probe 没进入目标 path）；
- root 恰 1 child 且该 child `>=1` direct formal `spawnAgent` grandchild →
  `NESTED_OK`；
- root 恰 1 child 且该 child `0` grandchild → `NO_NESTED`；
- started/completed 同一 formal edge 去重；child 文本说"没有工具"不作为
  verdict；
- `tool_surface_diagnostics`（child/root 线程的 `custom_tool_call` 计数、
  tool 名与是否查询过 `ALL_TOOLS`）只作 characterization 诊断，**永不改变
  status，也不作为 identity gate**。

verdict 输出字段：

```json
{
  "schema": 2,
  "case_id": "PA-CODEX-NESTED-CAP-00",
  "status": "NESTED_OK | NO_NESTED | BLOCKED | INVALID_EVIDENCE",
  "root_thread_id": "...",
  "root_direct_child_count": 1,
  "depth1_thread_id": "...",
  "depth2_direct_child_count": 0,
  "depth2_child_thread_ids": [],
  "formal_spawn_relation_count": 1,
  "tool_surface_diagnostics": {},
  "reasons": [],
  "provenance": {"eval_version": "...", "contract_id": "..."}
}
```

verifier 退出码：`0` NESTED_OK、`1` NO_NESTED、`2` BLOCKED、
`3` INVALID_EVIDENCE。

分支（`depth_hypothesis`）：

| Probe A′ | Probe B′ | depth_hypothesis | 动作 |
| --- | --- | --- | --- |
| `NESTED_OK` | 不运行 | `REFUTED_BY_DEFAULT` | **不停**：默认 runtime 已能 nested，depth 假设直接否定；直接进入 §13-§15 正式 acceptance，保持默认 Luna low、**不加** depth override；若正式 outer 仍 `nested != 3`，在 capability 已证明可用的前提下归 `FAIL_PRODUCER` |
| `NO_NESTED` | `NESTED_OK` | `CONFIRMED_BY_A_B` | 写 `output/nested-capability-decision.txt`（见下），**不停下来等人工 review**，直接继续 §13-§15 的正式 acceptance，正式 eval request 固定加 `agents.max_depth=2` |
| `NO_NESTED` | `NO_NESTED` | `NOT_CONFIRMED` | 停止：不跑 business acceptance；把 A′/B′ raw response + topology + child 工具面诊断贴 PR，等 reviewer 决定下一层 runtime/tool-surface 诊断；不提前换模型找 PASS |
| `BLOCKED` / `INVALID_EVIDENCE` | 停止，B′ 不运行 | `UNDETERMINED` | 停止：贴证据；不得拿它推断 producer |

`CONFIRMED_BY_A_B` 分支写入：

```text
output/nested-capability-decision.txt
  baseline=NO_NESTED
  agents.max_depth=2=NESTED_OK
  acceptance_depth_override=agents.max_depth=2
```

额外诊断义务（所有分支）：完整 raw response 本身已包含 child turn 的全部
raw `custom_tool_call` / `custom_tool_call_output` 与 formal collab
events，原样保留；若 child 通过 Code Mode 查询 `ALL_TOOLS`，该 raw output
完整保留在本地 run root。"child 是否存在该 tool"只作 characterization
诊断，不作为 identity gate。

## 13. Fixed input / prompt

```bash
mkdir -p "$CONSUMER/runtime-output"

# canonical input 仍是 producer-owned fixture：从 producer exact SHA
# checkout 的 repo 级 fixture 复制进本次独占 run root；root prompt 只引用
# $RUN_ROOT 下的路径，不引用 consumer 安装树内路径。
cp "$PRODUCER_REPO/tests/fixtures/paper.txt" "$RUN_ROOT/config/paper.txt"
PAPER_TXT="$RUN_ROOT/config/paper.txt"

cat >"$RUN_ROOT/config/research-direction.txt" <<'EOF'
研究方向：测试用最小方向。只用于触发正式 full-mode Step 3，不评价论文质量。
EOF

cat >"$RUN_ROOT/config/root-prompt.txt" <<EOF
只执行一次 paper-analysis full-mode producer runtime smoke。
从当前 clean consumer 中调用已安装的 paper-analysis custom agent 一次，传入：
paper: $PAPER_TXT
research_direction_file: $RUN_ROOT/config/research-direction.txt
mode: full
save: $CONSUMER/runtime-output
等待该 outer child 返回后结束。
你作为 root 只负责这一次 outer dispatch：不要自己分析论文，不要为该 child 创建任何内部分析 leaf，不要指示它为了测试 spawn/创建 leaf，也不要描述它内部 Step 3 的编排。内部是否 delegation 必须完全来自安装后的 developer_instructions。
EOF
```

禁止临场修改 prompt / fixture。

## 14. Execution — existing eval service only

仅当 §12 分支结果为 `depth_hypothesis=CONFIRMED_BY_A_B` 或
`REFUTED_BY_DEFAULT` 时才执行本章（两种分支都是 characterization 已完成、
capability 已证实可用）；`NOT_CONFIRMED` / `UNDETERMINED` 不得进入本章。

正式 eval request 在原 profile 之上，仅当 `CONFIRMED_BY_A_B` 时固定加入
已经由 A′/B′ 证明为必要 runtime prerequisite 的
`--config agents.max_depth=2`；`REFUTED_BY_DEFAULT` 分支不加该 config
（这不是"同 SHA FAIL 后改 config 重跑到绿"：正式 acceptance 在
capability probe 完成之前尚未开始）。

从既有 eval-server checkout 读取端口，不管理服务生命周期：

```bash
EVAL_PORT="$(cd "$EVAL_SERVER_DIR" && direnv exec . printenv EVAL_PORT)"
export EVAL_PORT

python3 - <<'PY'
import json
import os
import pathlib
import shlex

run_root = pathlib.Path(os.environ["RUN_ROOT"])
consumer = os.environ["CONSUMER"]
prompt = (run_root / "config/root-prompt.txt").read_text(encoding="utf-8")

args = [
    "--json",
    "--ephemeral",
    "--skip-git-repo-check",
    "--sandbox", "workspace-write",
    "--cd", consumer,
    "--model", "gpt-5.6-luna",
    "--config", 'model_reasoning_effort="low"',
    # Project trust must use the dotted per-run override surface documented
    # by adapter@9 (raw_identity_path.characterization_basis); an inline
    # projects={...} map is rejected by the pinned runtime at thread/start.
    "--config", f'projects."{consumer}".trust_level="trusted"',
    "--", prompt,
]
# depth_hypothesis=CONFIRMED_BY_A_B 时在 trust config 之后、"--" 之前插入：
#   "--config", "agents.max_depth=2",
# （V1 default agents.max_depth=1 已被 Probe A'/B' 证明对 depth-1 child
# 不暴露 nested spawn 工具面；该 override 只能以 CONFIRMED_BY_A_B 为凭据
# 加入，REFUTED_BY_DEFAULT 分支不得添加。）
request = {"command": " ".join(shlex.quote(x) for x in args), "timeout": 900}
# timeout: caller-side wall-clock budget for one full nested run
# (root -> outer child -> nested leaves -> assembly). 300s proved too small
# once delegation actually happens (the eval service aborts with HTTP 504);
# this budget caps the run, it never changes model, reasoning, sandbox or
# prompt.
(run_root / "config/eval-request.json").write_text(
    json.dumps(request, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)
PY

cp "$RUN_ROOT/config/eval-request.json" "$RUN_ROOT/output/eval-request.json"

curl --fail-with-body -sS \
  -X POST "http://127.0.0.1:$EVAL_PORT/eval" \
  -H 'Content-Type: application/json' \
  --data-binary @"$RUN_ROOT/config/eval-request.json" \
  >"$RUN_ROOT/output/eval-response.json"
```

### 重要：本 case 不调用 shared adapter 形成 verdict

**不要执行：**

```text
parse_codex_eval_evidence.py --expected-agent ...
parse_codex_eval_evidence.py --consumer-root ...
parse_codex_eval_evidence.py ... 作为 PASS/FAIL/BLOCKED gate
```

也不要删除或改写 `eval-response.json` 中的 `child_thread_reads` 来“让
adapter 通过”。原始响应完整保存；本 producer topology verifier 根本不消费
identity surface。

## 15. Producer topology verifier

```bash
python3 "$PRODUCER_REPO/tests/runtime/verify_codex_full_mode_topology.py" \
  --eval-response "$RUN_ROOT/output/eval-response.json" \
  --contract "$FIXTURES_DIR/configs/codex-eval-adapter-contract.json" \
  --output "$RUN_ROOT/output/runtime-topology.json"
```

verifier 必须执行：

1. 顶层 `/eval.passed == true`；否则在没有 producer-specific violation
   证据时 `BLOCKED`；
2. `version` 非 null，原样记录 provenance；
3. 从 `output.thread_id` 取得 root thread id；
4. 从 `output.app_server_events` 按 pinned contract 提取 formal
   `spawnAgent` ownership（`item/started` | `item/completed`、
   `message.params.item`、`item.type == collabAgentToolCall`、
   `item.tool == spawnAgent`）；先读取并校验 `receiverThreadIds`：
   `item/started` 没有 concrete receiver 时忽略（即使没有
   `senderThreadId`），`item/completed` 没有 concrete receiver 时判
   `INVALID_EVIDENCE`；只有存在 concrete receiver 后才要求非空
   `senderThreadId`；
5. dedupe started/completed 的同一 formal edge；
6. root direct formal child 数量：`0` → `BLOCKED`；`>1` → `BLOCKED`；
   `==1` → 得到 `outer_thread_id`；
7. 查 sender 为 `outer_thread_id` 的 distinct formal nested children：`==3` →
   topology threshold 满足；`0/1/2/>3` → `FAIL_PRODUCER`；
8. formal ownership/malformed evidence 冲突（`app_server_events` entry 或
   `message` wrapper 缺失/非 object、completed spawn 无 concrete receiver、
   relation shape 损坏、同一 child 被不同 sender claim、contract 未声明
   formal spawn 规则）→ `INVALID_EVIDENCE`。

**verifier 不得读取 `child_thread_reads` 或任何 identity 字段**；prompt
文本、assistant/model 自述、`subAgentActivity.agentPath` 均不得创建、修改
或否定 formal ownership。

verdict 输出字段（无任何暗示 identity 已验收的名称）：

```json
{
  "schema": 1,
  "case_id": "PA-CODEX-FULL-LEAF-01",
  "producer_status": "PASS",
  "root_thread_id": "...",
  "root_direct_child_count": 1,
  "outer_thread_id": "...",
  "nested_direct_child_count": 3,
  "nested_child_thread_ids": ["...", "...", "..."],
  "formal_spawn_relation_count": 4,
  "reasons": [],
  "provenance": {"eval_version": "...", "contract_id": "..."}
}
```

verifier 退出码：`0` PASS、`1` FAIL_PRODUCER、`2` BLOCKED、
`3` INVALID_EVIDENCE。

## 16. Producer deterministic suite

```bash
(
  cd "$PRODUCER_REPO"
  uv sync --locked \
    >"$RUN_ROOT/output/uv-sync.stdout.txt" \
    2>"$RUN_ROOT/output/uv-sync.stderr.txt"

  uv run pytest -q \
    >"$RUN_ROOT/output/pytest.stdout.txt" \
    2>"$RUN_ROOT/output/pytest.stderr.txt"

  git diff --check \
    >"$RUN_ROOT/output/git-diff-check.txt"
)
```

JSON/JSONL、YAML/TOML 的正式判断使用结构化 parser（`jq` / `yq` /
`tomllib`），不用 grep/sed/awk 代替字段判定。

## 17. Interaction

无。`paper`、`research_direction_file`、`mode`、`save` 全部固定提供；tiny
`.txt` fixture 不触发 PDF/OCR/Zotero/MCP/browser/user approval。

如果运行中需要额外 user input：

- 保存原始 machine response；
- 不临场补 prompt；
- 未进入目标 full path → `BLOCKED`；
- 只有在 evidence 已明确进入唯一 outer child 的 producer-owned full path，
  且固定完整输入理应足够时，才可按 producer behavior 判 FAIL。

## 18. Evidence

至少保留：

```text
output/producer-sha.txt
output/producer-repo-dirty.txt
output/fixture-repo-sha.txt
output/fixture-repo-dirty.txt
output/recipe-run-id.txt
output/consumer-path.txt
output/consumer-newly-created.txt
output/eval-server-checkout-sha.txt
output/apm-version.txt
output/install-command.txt
output/manual-patch.txt
output/consumer-apm.yml
output/apm.lock.yaml
output/apm-install.stdout.txt
output/apm-install.stderr.txt
output/purity-preflight.txt
output/generated-projection.json
output/capability-default-eval-request.json
output/capability-default-eval-response.json
output/capability-default-topology.json
# 仅 Probe A′ = NO_NESTED 后运行 Probe B′ 时保留以下 capability-depth2-*：
output/capability-depth2-eval-request.json
output/capability-depth2-eval-response.json
output/capability-depth2-topology.json
# depth_hypothesis=CONFIRMED_BY_A_B 分支必备：
output/nested-capability-decision.txt
output/eval-request.json
output/eval-response.json
output/runtime-topology.json
output/uv-sync.stdout.txt
output/uv-sync.stderr.txt
output/pytest.stdout.txt
output/pytest.stderr.txt
output/git-diff-check.txt
```

完整 raw response 保留在本次 `/tmp` run root；PR 只贴足以证明结论的最小
脱敏 machine evidence。`output/producer-repo-status.txt` 仅 producer
checkout dirty 分支保存诊断。不要求 `adapter.json`，因为 shared adapter 不属于
本 case 的 merge verdict 链。corrected probe 的 child turn 中全部 raw
`custom_tool_call` / `custom_tool_call_output` 与 formal collab events 随
完整 raw response 原样保留；child 是否通过 Code Mode 查询过 `ALL_TOOLS`
这类 tool 存在性信息仅作 characterization 诊断，不作为 identity gate。

## 19. Verdict

### PASS

全部满足：

- clean consumer 为本次新建，来源为显式 Git dependency；
- lock `resolved_commit == FINAL_HEAD_SHA`；
- fixture repo exact SHA 且 dirty=no；
- producer checkout tracked + untracked 干净，`output/producer-repo-dirty.txt`
  为 `producer_repo_dirty=no`；
- `manual_patch=no`；
- clean-consumer purity preflight 通过（安装树无 test-only artifacts）；
- generated Codex projection 保留全部六条 exact behavior markers（含
  delegation discovery 与 exactly-3 delegated units 指令），丢任一条即
  `FAIL_PRODUCER`；
- PA-CODEX-NESTED-CAP-00 已完成且 `depth_hypothesis` 为
  `CONFIRMED_BY_A_B`（正式 eval request 含 `--config agents.max_depth=2`，
  `output/nested-capability-decision.txt` 在案）或 `REFUTED_BY_DEFAULT`
  （Probe A′=NESTED_OK，正式 eval request 不含 depth override）；
- `/eval` execution healthy，version 有 provenance；
- canonical input 为 `$RUN_ROOT/config/paper.txt`（producer repo 级 fixture
  复制，不来自 consumer 安装树）；
- root 恰有 1 个 formal direct outer child；
- outer child 有恰好 `3` 个 distinct formal direct `spawnAgent` nested child；
- formal ownership 无冲突；
- producer deterministic suite 全 PASS；
- OpenCode native deterministic/static contract 无回归。

PR evidence 必须写明本 acceptance 的 characterization 前提，二选一：

`depth_hypothesis=CONFIRMED_BY_A_B` 时：

```text
Codex V1 runtime prerequisite characterized for this acceptance:
agents.max_depth=2
```

并且不得声称"默认 depth 配置也通过"。

`depth_hypothesis=REFUTED_BY_DEFAULT` 时：

```text
Codex V1 nested capability characterized for this acceptance:
default depth sufficient (Probe A' NESTED_OK); no agents.max_depth override
```

两种情形都只在 `paper-analysis` repo 范围内把它记录进本 runtime
Recipe / repo-local compatibility documentation；不为此修改
professor-contact、fixtures、eval-server，也不修改 production agent
wording。

**任何 identity 字段的缺失、`default`、mismatch、unobservable 或
contradiction 均不改变上述 topology verdict。**

### FAIL_PRODUCER

只有在：

- PA-CODEX-NESTED-CAP-00 已完成且 `depth_hypothesis` 为
  `CONFIRMED_BY_A_B`（Probe A′=NO_NESTED、Probe B′=NESTED_OK，正式 eval
  request 含 `agents.max_depth=2`）或 `REFUTED_BY_DEFAULT`（Probe A′=
  NESTED_OK，正式 eval request 不加 depth override）：两种情形下 nested
  capability 均已被 corrected probe 以未受抑制的调用面证实可用，正式
  acceptance 在 capability probe 完成之前尚未开始，未 probe 的 run 无资格
  产生本 verdict；
- `/eval` healthy；
- producer checkout 干净（`producer_repo_dirty=no`）；
- 固定 input 正常；
- clean-consumer purity preflight 已通过（consumer 无 test-only artifact
  污染）；
- root 恰有唯一 formal outer child；
- formal topology evidence 本身有效；

并出现以下本 issue 直接负责的行为失败时才判 FAIL：

- outer child 的 distinct formal direct nested `spawnAgent` child 数量不是 `3`（`0/1/2/>3`）；
- canonical agent 缺任一 exact marker；
- generated Codex projection 丢失任一 exact marker；
- producer deterministic contract 被本改动破坏。

### BLOCKED

包括：

- provider/model unavailable；
- eval service / harness failure（`passed == false`）；
- `/eval.version == null`；
- root 没有 formal direct outer child，无法证明进入目标 path；
- root 出现多个不同 formal direct children，固定 outer dispatch 无法唯一
  归属；
- clean consumer/provenance 不成立；
- producer checkout dirty（tracked 或 untracked 修改未提交）：
  **`BLOCKED / NOT TESTED`**，停止，不继续 capability probe / formal
  runtime acceptance。记录格式：

  ```text
  BLOCKED / NOT TESTED
  reason: producer checkout dirty; producer-owned fixture/verifier
  provenance to FINAL_HEAD_SHA not established
  ```

- clean-consumer purity preflight 失败：安装树存在 test-only artifacts
  （NOT TESTED）；
- **`BLOCKED / NOT YET ATTRIBUTABLE`**：在 PA-CODEX-NESTED-CAP-00 完成
  之前取得的任何正式 topology 观察（包括 `outer nested=0`）。记录格式：

  ```text
  BLOCKED / NOT YET ATTRIBUTABLE
  reason: nested runtime capability prerequisite not yet characterized
  ```

  它仍是有价值的历史观察，但在未确认 depth-1 child 是否拿到 nested
  delegation surface 的 runtime 下，不能直接证明 producer instruction
  违反 contract，因此不得作为 `FAIL_PRODUCER` 结论；
- **`BLOCKED / INVALID_CHARACTERIZATION_DESIGN / NOT ATTRIBUTABLE`**：
  characterization 自身的 probe prompt 抑制了 runtime 已观察到的 native
  调用面（Code Mode `custom_tool_call: exec` 调用
  `tools.multi_agent_v1__spawn_agent(...)`），其 A/B 结果不能区分"child
  没有 nested 工具面"与"被 prompt 禁止调用入口"，不得得出任何
  `depth_hypothesis` 结论。记录格式：

  ```text
  INVALID_CHARACTERIZATION_DESIGN / NOT ATTRIBUTABLE
  reason: probe prompt prohibited the observed native Code Mode invocation
  surface (`exec`) used to call multi_agent_v1__spawn_agent
  ```

  历史 case：producer SHA `68bb65ddbb58990198bcac874663667e642e45a2` 的
  首轮 Probe A/B（run root 见该 SHA 的 PR evidence）即属此类，
  已从 `depth_hypothesis=NOT_CONFIRMED` 重分类；
- probe A′/B′ 任一为 `BLOCKED` / `INVALID_EVIDENCE`，或
  `depth_hypothesis=NOT_CONFIRMED`（停止并贴证据，不归因 producer）；
- runtime 明确报告 permission/depth/concurrency/subagent capability
  blocker；
- 当前 runtime/eval evidence surface 不再提供本 Recipe 所需 formal
  topology 字段。

**不得因为 `agent_type=default`、identity 不可观察或 identity mismatch 判
BLOCKED。**

### INVALID_EVIDENCE

只限 formal topology / source evidence 本身损坏或自相矛盾：

- `eval-response.json` malformed；
- completed formal `spawnAgent` relation 缺 concrete receivers；
- formal sender/receiver shape malformed；
- 同一 child 被不同 sender 的 formal spawn relation claim；
- source isolation / manual patch / provenance 证据自相矛盾。

**identity contradiction 不属于本 case 的 `INVALID_EVIDENCE` 条件。**

## 20. Retry / invalidation

- 正式 acceptance 的入口顺序固定为：完成 PA-CODEX-NESTED-CAP-00 corrected
  Probe A′/B′ 并得到 `depth_hypothesis` 之后，才允许产生至多一次正式
  business verdict；A′、B′ 各只运行一次，是 characterization A/B，不允许
  retry-until-green；
- **probe 设计约束**：corrected probe prompt 不得禁止 runtime 已观察到的
  native 调用面（Code Mode `custom_tool_call: exec` 调用
  `tools.multi_agent_v1__spawn_agent(...)`）；违反该约束的
  characterization 按 §19 `BLOCKED /
  INVALID_CHARACTERIZATION_DESIGN / NOT ATTRIBUTABLE` 记录，必须先修
  Recipe 再以 corrected prompt 重跑 A′/B′，不得沿用其结论；
- 每个 final SHA 的正式 acceptance 只产生一个 verdict；
- `FAIL_PRODUCER` 一旦成立即终止该 SHA 的 acceptance，不得用同一 SHA
  后续无变更重跑得到的 `PASS` 覆盖；
- 只有 `BLOCKED`（例如 provider / harness transient）允许在同一
  input、prompt、model、reasoning、sandbox、config 下做有界 retry；
- test setup contamination（purity preflight 失败或安装树被 test-only
  artifacts 污染）按 `BLOCKED / NOT TESTED` 处理：此时观察到的任何
  topology 结果（包括 `nested=0`）不得作为 `FAIL_PRODUCER` 结论，修复测试
  布局后以新 final SHA 重建 consumer 重跑；
- capability characterization 未完成时取得的任何正式 topology 观察按
  `BLOCKED / NOT YET ATTRIBUTABLE` 记录，不得作为 `FAIL_PRODUCER` 结论；
  完成 corrected Probe A′/B′ 后按 §12 分支继续或停止；
- `agents.max_depth=2` 只能作为 Probe A′/B′ 以 `CONFIRMED_BY_A_B` 确认的
  runtime prerequisite 进入正式 eval request；`REFUTED_BY_DEFAULT` 分支
  （A′=NESTED_OK）不得添加该 override；除此之外不换模型、不提高
  reasoning、不改 prompt、不放宽 sandbox、不手动告诉 outer child spawn；
- 若要从 `FAIL_PRODUCER` 重新获得正式 `PASS`，必须先修复 producer、生成并
  push 新的 final SHA，再按本文重建 clean consumer 并运行一次正式 acceptance；
- `INVALID_EVIDENCE` 不得通过 retry-until-green 覆盖，必须先修复损坏或矛盾的
  evidence/source；
- 不修改 shared fixtures/eval-server 追绿；
- 不通过删改 `child_thread_reads` 或 identity events 制造 PASS（本 producer
  verifier 根本不消费它们；原始响应必须完整保存）；
- producer SHA 或 fixture SHA 变化 → 旧 acceptance 失效，重建 clean
  consumer；
- Codex version 变化只更新 provenance；只有 formal topology surface 真正
  不兼容时才 BLOCK/INVALID，并保存真实输出 characterization；
- PASS evidence 闭合后停止，不追加长论文或下游 Stage 2 E2E。
