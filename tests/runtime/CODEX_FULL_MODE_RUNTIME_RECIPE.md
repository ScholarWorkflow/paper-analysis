# Codex Full-Mode Runtime Recipe — `PA-CODEX-FULL-LEAF-01`

Producer-owned acceptance recipe for the Codex full-mode nested delegation
topology. It proves, on a clean consumer and the real `mode: full` entry path,
that the unique formal outer child delegates three native subagent children at
Step 3 instead of inlining the three-way analysis.

本文件是 producer 仓库内的正式 Test Recipe：执行者按本文逐步操作，不依赖
issue 文本；issue 只描述目标，本文描述可执行步骤与判定。

Contract authority：issue #16 的 `Frozen Acceptance Contract`
（`PA-SURFACE-01..04`）是本 case 当前的验收来源。issue #13 / PR #14 只保留
问题与实现的历史 provenance；#15 的重复 runtime smoke 与 blanket SHA
invalidation 设计不再生效。旧 `PA-CODEX-NESTED-CAP-00` V1 capability
characterization 不再是本 case 的前置，其历史证据留在 #13 / #14。

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
  - OpenCode runtime compatibility；
  - child 语义结果是否已被 coordinator 消费（wait→consume 由
    `PA-DIRECT-DET-01` 的 producer contract assertions 负责）；
  - delegation blocker 归因（`PA-SURFACE-03` 的 zero-attempt 禁止与
    machine-level failure 前置由 `PA-DIRECT-DET-01` 负责；本 case 不注入
    synthetic failure，也不新增第二个 runtime case）。

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
output.thread_start_effective（仅 §8 resolved-config 记录）
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
tool catalog / Code Mode / assistant prose（不得进入任何 verdict）
```

说明：pinned @9 contract 仍是 formal topology field/rule 的共享事实来源
（`app_server_event_envelope`、`raw_identity_path.formal_spawn_relation`、
`delegation.fail_closed`）；本 producer verifier 直接消费 raw
`/eval` 结构化事件，不让 shared adapter 的 identity-conflict 实现进入
merge verdict 链。@9 的 delegation 维度只有 `confirmed` / `unobservable`，
**没有** native-spawn-failure machine state；因此本 Recipe 不发明 external
delegation-failure gate，也不为它构造 synthetic case（issue #16 §4）。

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
- runtime prerequisite config 固定为 §8 的 `agents.enabled=true`、
  `agents.max_concurrent_threads_per_session=4` 与 `agents.max_depth=2`，
  执行前已确定，不在观察到
  不理想结果后修改。

revision 变化不自动触发整案重跑：是否复用旧 PASS 由 §17 的 declared
dependency + intervening diff impact analysis 决定。

本 Codex case **不启动 `skills-test-fixtures` runtime fixture**，因此不得
伪造 `fixture_run_id`。记录真实 `recipe_run_id`、fixture repo SHA/dirty、
eval runtime provenance。

## 4. Exclusive run root / provenance

正式 acceptance 的 canonical fixture、topology verifier 与 deterministic
suite 都直接从本地 `$PRODUCER_REPO` checkout 读取/执行，所以 producer
worktree 自身的 tracked + untracked 干净状态是 `FINAL_HEAD_SHA` provenance
的必要条件。exact revision 校验、clean producer、clean consumer、APM
install、purity preflight、generated projection、eval/config prerequisite 都是
`CASE_STARTED` 之前的 bootstrap；任何一步失败都必须经过同一个
`case_not_started` 路径，写入 `output/case-status.txt` 后停止，不作产品
verdict。bootstrap 阶段不依赖裸 `set -e` 做分类；只有成功写出
`CASE_STARTED` 后才重新启用 `set -euo pipefail`。

```bash
set -u -o pipefail

RUN_ROOT="$(mktemp -d /tmp/paper-analysis-full-leaf.XXXXXX)" || {
  printf '%s\n' 'CASE_NOT_STARTED: unable to create exclusive run root' >&2
  exit 1
}
mkdir -p "$RUN_ROOT/config" "$RUN_ROOT/output" "$RUN_ROOT/consumer" || {
  printf '%s\n' 'CASE_NOT_STARTED: unable to initialize exclusive run root' >&2
  exit 1
}
export RUN_ROOT
export CONSUMER="$RUN_ROOT/consumer"

case_not_started() {
  local reason="$1"
  printf 'CASE_NOT_STARTED: %s\n' "$reason" >"$RUN_ROOT/output/case-status.txt"
  cat "$RUN_ROOT/output/case-status.txt"
  exit 1
}

write_evidence() {
  local value="$1"
  local path="$2"
  local reason="$3"
  if ! printf '%s\n' "$value" >"$path"; then
    case_not_started "$reason"
  fi
}

if [ -z "${PRODUCER_REPO:-}" ]; then
  case_not_started "required prerequisite PRODUCER_REPO is unset"
fi
if [ -z "${FIXTURES_DIR:-}" ]; then
  case_not_started "required prerequisite FIXTURES_DIR is unset"
fi
if [ -z "${EVAL_SERVER_DIR:-}" ]; then
  case_not_started "required prerequisite EVAL_SERVER_DIR is unset"
fi

FIXTURES_SHA=9cb4547845be323a2a7b59139ee419476f2c7113

if ! FINAL_HEAD_SHA="$(git -C "$PRODUCER_REPO" rev-parse HEAD)"; then
  case_not_started "producer revision is unreadable"
fi
export FINAL_HEAD_SHA

if ! FIXTURES_ACTUAL_SHA="$(git -C "$FIXTURES_DIR" rev-parse HEAD)"; then
  case_not_started "fixture revision is unreadable"
fi
write_evidence "$FIXTURES_ACTUAL_SHA" \
  "$RUN_ROOT/output/fixture-repo-sha.txt" \
  "fixture revision evidence write failed"
if [ "$FIXTURES_ACTUAL_SHA" != "$FIXTURES_SHA" ]; then
  case_not_started "fixture revision does not match pinned SHA"
fi

if ! FIXTURES_DIRTY="$(git -C "$FIXTURES_DIR" status --porcelain)"; then
  case_not_started "fixture dirty-state check failed"
fi
if [ -n "$FIXTURES_DIRTY" ]; then
  write_evidence "$FIXTURES_DIRTY" \
    "$RUN_ROOT/output/fixture-repo-status.txt" \
    "fixture dirty-state evidence write failed"
  case_not_started "fixture repository is dirty"
fi
write_evidence 'fixture_repo_dirty=no' \
  "$RUN_ROOT/output/fixture-repo-dirty.txt" \
  "fixture clean-state evidence write failed"

if ! PRODUCER_DIRTY="$(git -C "$PRODUCER_REPO" status --porcelain)"; then
  case_not_started "producer dirty-state check failed"
fi
if [ -n "$PRODUCER_DIRTY" ]; then
  write_evidence 'producer_repo_dirty=yes' \
    "$RUN_ROOT/output/producer-repo-dirty.txt" \
    "producer dirty-state flag write failed"
  write_evidence "$PRODUCER_DIRTY" \
    "$RUN_ROOT/output/producer-repo-status.txt" \
    "producer dirty-state evidence write failed"
  case_not_started "producer checkout dirty; producer-owned fixture/verifier provenance to FINAL_HEAD_SHA not established"
fi
write_evidence 'producer_repo_dirty=no' \
  "$RUN_ROOT/output/producer-repo-dirty.txt" \
  "producer clean-state evidence write failed"

RECIPE_RUN_ID="${RUN_ROOT##*/}"

if ! git -C "$CONSUMER" init -q; then
  case_not_started "clean consumer initialization failed"
fi

write_evidence "$FINAL_HEAD_SHA" "$RUN_ROOT/output/producer-sha.txt" \
  "producer revision evidence write failed"
write_evidence "$RECIPE_RUN_ID" "$RUN_ROOT/output/recipe-run-id.txt" \
  "recipe run ID evidence write failed"
write_evidence "$CONSUMER" "$RUN_ROOT/output/consumer-path.txt" \
  "consumer path evidence write failed"
write_evidence 'consumer_newly_created=yes' \
  "$RUN_ROOT/output/consumer-newly-created.txt" \
  "consumer creation evidence write failed"
write_evidence 'manual_patch=no' "$RUN_ROOT/output/manual-patch.txt" \
  "manual-patch evidence write failed"

if ! EVAL_SERVER_SHA="$(git -C "$EVAL_SERVER_DIR" rev-parse HEAD)"; then
  case_not_started "eval-server checkout provenance is unreadable"
fi
write_evidence "$EVAL_SERVER_SHA" \
  "$RUN_ROOT/output/eval-server-checkout-sha.txt" \
  "eval-server revision evidence write failed"

if ! apm --version >"$RUN_ROOT/output/apm-version.txt"; then
  case_not_started "APM CLI bootstrap failed"
fi

# Python entry for every §5–§12 python step: the producer project's locked
# environment. A host `python3` may predate tomllib (e.g. macOS 3.9), which is
# a bootstrap failure, not a product result.
if ! ( cd "$PRODUCER_REPO" && uv sync --locked ) \
  >"$RUN_ROOT/output/uv-sync.stdout.txt" \
  2>"$RUN_ROOT/output/uv-sync.stderr.txt"; then
  case_not_started "locked producer environment bootstrap failed"
fi
```

所有 python 步骤统一用锁定的 producer 环境执行，不使用宿主裸 `python3`：

```bash
cd "$PRODUCER_REPO" && uv run --locked python <见各章命令>
```

## 5. Explicit Git-pinned install

不要用可能受 default registry 影响的 `owner/repo#SHA` shorthand。

```bash
if ! cat >"$CONSUMER/apm.yml" <<EOF
name: paper-analysis-codex-full-leaf-consumer
version: 0.0.0
targets: [codex]
dependencies:
  apm:
    - git: https://github.com/ScholarWorkflow/paper-analysis.git
      ref: $FINAL_HEAD_SHA
EOF
then
  case_not_started "consumer APM manifest generation failed"
fi

if ! cp "$CONSUMER/apm.yml" "$RUN_ROOT/output/consumer-apm.yml"; then
  case_not_started "consumer APM manifest evidence copy failed"
fi

if ! yq -e '.dependencies.apm[0].git == "https://github.com/ScholarWorkflow/paper-analysis.git"' \
  "$CONSUMER/apm.yml" >/dev/null; then
  case_not_started "consumer APM manifest source check failed"
fi
if ! yq -e '.dependencies.apm[0].ref == strenv(FINAL_HEAD_SHA)' \
  "$CONSUMER/apm.yml" >/dev/null; then
  case_not_started "consumer APM manifest revision check failed"
fi

if ! (
  cd "$CONSUMER"
  apm install --target codex \
    >"$RUN_ROOT/output/apm-install.stdout.txt" \
    2>"$RUN_ROOT/output/apm-install.stderr.txt"
); then
  case_not_started "APM install failed"
fi
write_evidence 'apm install --target codex' \
  "$RUN_ROOT/output/install-command.txt" \
  "install-command evidence write failed"

if [ ! -f "$CONSUMER/apm.lock.yaml" ]; then
  case_not_started "APM install did not produce apm.lock.yaml"
fi
if [ ! -f "$CONSUMER/.codex/agents/paper-analysis.toml" ]; then
  case_not_started "APM install did not produce the Codex agent projection"
fi
if [ ! -f "$CONSUMER/.agents/skills/paper-analysis/SKILL.md" ]; then
  case_not_started "APM install did not produce the paper-analysis skill"
fi
```

production install tree 只保留真实运行资产（`SKILL.md`、`scripts/` 等）；
producer test tree 全部位于 repo 级 `tests/`，不随 skill 分发。安装树内的
test-only artifacts 机械排除见 §6 purity preflight。

用 `yq` 证明 lock 确实 pin 到 final Git commit。APM 0.29 lockfile 把
`repo_url` 归一化为小写 `owner/repo`（不是 `https://...` URL 形式），原始
大小写保留在 `materialization_repo_url`，主机在 `host` 字段，所以机械
判定用 `host` + `materialization_repo_url` 组合：

```bash
if ! yq -e '.dependencies[] | select(.resolved_commit == strenv(FINAL_HEAD_SHA)) | select(.host == "github.com" and .materialization_repo_url == "ScholarWorkflow/paper-analysis")' \
  "$CONSUMER/apm.lock.yaml" >/dev/null; then
  case_not_started "APM lockfile does not prove the exact Git source revision"
fi
if ! cp "$CONSUMER/apm.lock.yaml" "$RUN_ROOT/output/apm.lock.yaml"; then
  case_not_started "APM lockfile evidence copy failed"
fi
```

## 6. Clean-consumer purity preflight

test-only artifacts 一旦进入 production skill 安装树，被测 agent 就能读到
测试执行知识并改变正式入口行为；这种 run 属于 test setup contamination，
不能产生 producer 行为结论。安装后在任何 `/eval` 调用之前机械检查，任一
命中立即按 bootstrap 失败处理：`CASE_NOT_STARTED`，不得继续 runtime
topology，更不得据此判 `FAIL_PRODUCER`。

```bash
PURITY_OUT="$RUN_ROOT/output/purity-preflight.txt"

if ! LEAKS="$(find "$CONSUMER/.agents/skills/paper-analysis" \
  \( -name 'CODEX_FULL_MODE_RUNTIME_RECIPE.md' \
     -o -name 'verify_codex_full_mode_topology.py' \))"; then
  case_not_started "clean-consumer purity scan failed"
fi

if [ -e "$CONSUMER/.agents/skills/paper-analysis/tests" ] || [ -n "$LEAKS" ]; then
  {
    printf 'installed_tests_dir=%s\n' "$([ -e "$CONSUMER/.agents/skills/paper-analysis/tests" ] && echo present || echo absent)"
    [ -n "$LEAKS" ] && printf '%s\n' "$LEAKS"
  } >"$PURITY_OUT"
  case_not_started "clean-consumer purity preflight failed; installed tree contains test-only artifacts"
fi

if ! printf '%s\n' 'purity_preflight=pass' >"$PURITY_OUT"; then
  case_not_started "clean-consumer purity evidence write failed"
fi
```

## 7. Generated projection check

安装后只检查本 issue 的行为 contract，不用 TOML `name` 做 runtime
identity gate。generated projection 必须同时证明 direct 与 deferred Code Mode
两种工具暴露方式都能绑定真实 spawn capability，且错误固定属性检查已被禁止；任一条件不成立都是 bootstrap
失败（`CASE_NOT_STARTED`），因为正式 producer 未按要求部署：

```bash
if ! (
  cd "$PRODUCER_REPO"
  uv run --locked python - <<'PY'
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

# Codex delegation contract: bind the callable actually offered by the surface.
required = {
    "full_delegation_required": "Codex full Step 3 必须使用运行时原生 subagent delegation",
    "bind_offered_spawn": "先绑定当前调用面实际提供的 subagent spawn capability，再用该 exact callable 分派三个有界只读分析工作单元",
    "direct_surface": "直接工具面提供 `spawn_agent` 时直接调用它",
    "deferred_code_mode_surface": "Code Mode 只提供延迟工具目录时，从 `ALL_TOOLS` 按工具说明定位 spawn capability",
    "no_fabricated_missing_tool": "不得用 `typeof tools.spawn_agent` 或固定属性名自检来伪造 `spawn_agent not exposed`",
    "binding_is_not_attempt": "工具绑定本身不算委派尝试；只有 spawn 调用返回 agent id 才计为已发起",
    "zero_attempt_blocker_forbidden": "**零次真实 native 委派尝试时禁止返回 `delegation unavailable` 或等价 blocker**",
    "blocker_needs_machine_failure": "只有本次 full run 已调用实际绑定的 spawn capability，且该调用返回 runtime machine-level delegation failure 时，才允许报告 delegation blocker",
    "no_inline_replacement": "coordinator 不得 inline 执行三路分析来替代 delegation",
    "exactly_three_delegated_units": "Step 3 必须恰好分派 exactly 3 个有界只读分析工作单元",
    "wait_consume_before_step4": "三路调用都发起后，等待并消费三路 child 返回的 Markdown，才进入 Step 4",
    "no_shell_curl_eval_fallback": "`exec_command` shell、`codex exec`、`opencode run`、curl、另起 `/eval` 都不是 delegation fallback",
    "child_failure_no_guess": "任一 required child 失败都必须明确报告，coordinator 不得猜测、补写或伪造 child 结果",
    "opencode_contract_unchanged": "OpenCode 运行时继续保留其原生 `task` / `permission` / `question` contract",
    "final_check_before_return": "零次真实调用时禁止返回 `delegation unavailable` 或等价 blocker",
}
checks = {key: marker in instructions for key, marker in required.items()}
assert all(checks.values())

# Reject the false-negative path observed in the failed run. Tool-directory
# binding is supported; treating a guessed JS property as the tool is not.
retired = {
    "legacy_preflight": "在执行任何三路分析内容前，必须先通过当前 Codex 运行时的 Code Mode / programmatic tool-calling surface 发现实际可调用的原生 multi-agent delegation 工具",
    "legacy_capability_failure": "明确返回 delegation-capability failure",
    "discover_then_dispatch": "先发现后分派",
    "discovery_failure_blocker": "discovery failure 即可变成 delegation blocker",
    "executable_false_probe": "if (typeof tools.spawn_agent",
    "fabricated_not_exposed": "throw new Error(\"spawn_agent not exposed\")",
}
retired_found = {key: marker in instructions for key, marker in retired.items()}
assert not any(retired_found.values()), retired_found

out = {
    "schema": 2,
    "checks": checks,
    "retired_mechanism_found": retired_found,
    "sha256": hashlib.sha256(agent.read_bytes()).hexdigest(),
}
(run_root / "output/generated-projection.json").write_text(
    json.dumps(out, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)
PY
); then
  case_not_started "generated Codex projection contract check failed"
fi
```

## 8. Runtime configuration prerequisites and resolved-config record

正式 eval request 固定携带三条 runtime prerequisite config：

```text
--config agents.enabled=true
--config agents.max_concurrent_threads_per_session=4
--config agents.max_depth=2
```

- `4 = 1 outer child + 3 nested leaves`。主线程不计入该 spawned-agent
  thread ceiling；这是本 case 从其冻结拓扑（§1 的 `root -> 1 -> 3`）推导出的
  **test resource ceiling**，不是 `paper-analysis` 的产品业务上限，也不得
  写成跨 case 默认值；
- `2 = outer child depth 1 + nested leaves depth 2`。该 per-request 值只把本 case
  所需的最小嵌套上限写入请求，避免结果依赖宿主配置或共享 app-server 的启动时快照。
  它是冻结拓扑的 hermetic runtime prerequisite，不是对历史失败原因的归因，
  也不改变产品委派数量；
- 该值在 §10 执行之前就已确定。任何失败之后都不得临场提高 ceiling、换
  model、提高 reasoning 或放宽 sandbox（§16）；
- `agents.enabled` / `agents.max_concurrent_threads_per_session` /
  `agents.max_depth` 都是无歧义
  dotted key + bool/int TOML value，按 eval-server 的 `--config` 语义映射到
  本 eval 的 `thread/start.config`，不影响共享 app-server 进程或其他 eval；
- 如果 runtime 在该 config 下拒绝 `thread/start`（HTTP 400 或 runtime
  error），且本 run 尚未取得非空 `output.thread_id`，唯一状态是
  `CASE_NOT_STARTED`：保存已有 response/transport 证据后停止；不得换 key
  名、删 config 或降 ceiling 后重新求绿。只有越过 `CASE_STARTED` 后，
  受支持机器证据才可进入 `BLOCKED` / `NOT TESTED` / `FAIL_PRODUCER` /
  `PASS` 等 case verdict。

pinned `/eval` surface 只把 Codex 实际解析出的
`approvalPolicy` / `approvalsReviewer` / `sandbox` 作为
`output.thread_start_effective` 回报，**不提供任何 `agents.*` readback**。
因此 resolved configuration 的记录方式是：request 侧的 before/after 差值 +
response 侧 effective 快照原样摘录，并明确标注 `agents.*` 为
`not_reported_by_pinned_surface`。本 Recipe 不为此新增第二次 runtime
characterization run（issue #16 Non-goals：不新增 runtime case）。

```bash
if ! (
  cd "$PRODUCER_REPO"
  uv run --locked python - <<'PY'
import json
import os
import pathlib

run_root = pathlib.Path(os.environ["RUN_ROOT"])
record = {
    "schema": 1,
    "case_id": "PA-CODEX-FULL-LEAF-01",
    "before_override": {
        "agents.enabled": None,
        "agents.max_concurrent_threads_per_session": None,
        "agents.max_depth": None,
    },
    "after_override": {
        "agents.enabled": True,
        "agents.max_concurrent_threads_per_session": 4,
        "agents.max_depth": 2,
    },
    "ceiling_derivation": "4 = 1 formal outer child + 3 formal nested leaves; root/main thread not counted",
    "depth_derivation": "2 = outer child depth 1 + nested leaves depth 2",
    "ceiling_kind": "test resource ceiling derived from the frozen topology; not a product business limit",
    "effective_readback_field": "output.thread_start_effective",
    "agents_keys_readback": "not_reported_by_pinned_surface",
    "mutable_after_failure": False,
}
(run_root / "output/runtime-config-requested.json").write_text(
    json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
PY
); then
  case_not_started "runtime prerequisite config record generation failed"
fi
```

`output/runtime-config-effective.json` 在 §10 收到 `/eval` response 后、写出
`CASE_STARTED` 之前从 `output.thread_start_effective` 原样提取。它只是证据：
键集合、缺失值或后续变化都不参与本 case 的 verdict，也不得用来推断
`agents.*` 是否被应用。

## 9. Fixed input / prompt

```bash
if ! mkdir -p "$CONSUMER/runtime-output"; then
  case_not_started "runtime output directory initialization failed"
fi

# canonical input 仍是 producer-owned fixture：从 producer exact SHA
# checkout 的 repo 级 fixture 复制进本次独占 run root；root prompt 只引用
# $RUN_ROOT 下的路径，不引用 consumer 安装树内路径。
if ! cp "$PRODUCER_REPO/tests/fixtures/paper.txt" "$RUN_ROOT/config/paper.txt"; then
  case_not_started "canonical paper fixture copy failed"
fi
PAPER_TXT="$RUN_ROOT/config/paper.txt"

if ! cat >"$RUN_ROOT/config/research-direction.txt" <<'EOF'
研究方向：测试用最小方向。只用于触发正式 full-mode Step 3，不评价论文质量。
EOF
then
  case_not_started "research-direction fixture generation failed"
fi

if ! cat >"$RUN_ROOT/config/root-prompt.txt" <<EOF
只执行一次 paper-analysis full-mode producer runtime smoke。
从当前 clean consumer 中调用已安装的 paper-analysis custom agent 一次，传入：
paper: $PAPER_TXT
research_direction_file: $RUN_ROOT/config/research-direction.txt
mode: full
save: $CONSUMER/runtime-output
等待该 outer child 返回后结束。
你作为 root 只负责这一次 outer dispatch：不要自己分析论文，不要为该 child 创建任何内部分析 leaf，不要指示它为了测试 spawn/创建 leaf，也不要描述它内部 Step 3 的编排。内部是否 delegation 必须完全来自安装后的 developer_instructions。
EOF
then
  case_not_started "fixed root prompt generation failed"
fi
```

prompt 固定、topology-blind：不提示 nested topology、不提示 tool 名、不提示
任何 discovery/capability mechanism，也不要求 child 报告它是否拥有某个
工具。禁止临场修改 prompt / fixture。

## 10. Execution — existing eval service only

从既有 eval-server checkout 读取端口，不管理服务生命周期。以下所有动作仍在
`CASE_STARTED` 之前，因此 transport/request/response provenance 失败一律经
`case_not_started` 统一分类：

```bash
if ! EVAL_PORT="$(cd "$EVAL_SERVER_DIR" && direnv exec . printenv EVAL_PORT)"; then
  case_not_started "eval service port resolution failed"
fi
if [ -z "$EVAL_PORT" ]; then
  case_not_started "eval service port is empty"
fi
export EVAL_PORT

if ! (
  cd "$PRODUCER_REPO"
  uv run --locked python - <<'PY'
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
    # §8 frozen runtime prerequisites (test resource ceiling, not a product limit)
    "--config", "agents.enabled=true",
    "--config", "agents.max_concurrent_threads_per_session=4",
    "--config", "agents.max_depth=2",
    # Project trust must use the dotted per-run override surface documented
    # by adapter@9 (raw_identity_path.characterization_basis); an inline
    # projects={...} map is rejected by the pinned runtime at thread/start.
    "--config", f'projects."{consumer}".trust_level="trusted"',
    "--", prompt,
]
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
); then
  case_not_started "eval request generation failed"
fi

if ! cp "$RUN_ROOT/config/eval-request.json" "$RUN_ROOT/output/eval-request.json"; then
  case_not_started "eval request evidence copy failed"
fi

if ! curl --fail-with-body -sS \
  -X POST "http://127.0.0.1:$EVAL_PORT/eval" \
  -H 'Content-Type: application/json' \
  --data-binary @"$RUN_ROOT/output/eval-request.json" \
  >"$RUN_ROOT/output/eval-response.json"; then
  case_not_started "eval transport failed before root runtime provenance"
fi
```

`--model gpt-5.6-luna` + `model_reasoning_effort="low"` 是 Project Consensus
冻结的默认 Codex smoke profile；model/profile 本身不是产品 PASS/FAIL 条件。

### CASE_STARTED 边界

`/eval` HTTP 请求失败（`curl` 非零）、response 无法被 `jq` 解析，或响应里
没有可归属本 run 的非空 `output.thread_id`，都表示正式 case 尚未开始：统一
经过 `case_not_started` 停止，只记录 bootstrap/transport failure reason，
不作产品 verdict。只有取得 root provenance、保存 resolved-config evidence
并成功写出 `CASE_STARTED` 后才进入 §11。

```bash
if ! ROOT_THREAD_ID="$(jq -r '.output.thread_id // empty' "$RUN_ROOT/output/eval-response.json")"; then
  case_not_started "eval response is not parseable before root runtime provenance"
fi
if [ -z "$ROOT_THREAD_ID" ]; then
  case_not_started "no root runtime provenance attributable to this run"
fi

if ! EVAL_VERSION="$(jq -r '.version // empty' "$RUN_ROOT/output/eval-response.json")"; then
  case_not_started "eval version provenance could not be parsed"
fi

if ! jq '.output.thread_start_effective' \
  "$RUN_ROOT/output/eval-response.json" \
  >"$RUN_ROOT/output/runtime-config-effective.json"; then
  case_not_started "runtime effective-config evidence could not be parsed"
fi

if ! {
  printf 'CASE_STARTED\n'
  printf 'recipe_run_id=%s\n' "$(cat "$RUN_ROOT/output/recipe-run-id.txt")"
  printf 'root_thread_id=%s\n' "$ROOT_THREAD_ID"
  printf 'eval_version=%s\n' "${EVAL_VERSION:-null}"
} >"$RUN_ROOT/output/case-status.txt"; then
  printf '%s\n' 'CASE_NOT_STARTED: unable to persist CASE_STARTED provenance' >&2
  exit 1
fi

# From this point onward the formal case has started; non-zero product/runtime
# execution results are interpreted by §11/§15 instead of bootstrap logic.
set -euo pipefail
```

`version` 缺失不改变 `CASE_STARTED`：它是 provenance，由 §11 verifier 判
`BLOCKED`。

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

## 11. Producer topology verifier

```bash
(
  cd "$PRODUCER_REPO"
  uv run --locked python tests/runtime/verify_codex_full_mode_topology.py \
    --eval-response "$RUN_ROOT/output/eval-response.json" \
    --contract "$FIXTURES_DIR/configs/codex-eval-adapter-contract.json" \
    --output "$RUN_ROOT/output/runtime-topology.json"
)
```

verifier 必须执行：

1. 顶层 `/eval.passed` 是 boolean；不是 boolean → `INVALID_EVIDENCE`；
   该字段的 true/false 值只作为 harness summary metadata，不得在 formal
   topology 解析前充当全局 veto，也不得反转已证明的 topology；
2. `version` 非 null 且非空字符串，原样记录 provenance；null → `BLOCKED`；
   非 string 非 null → `INVALID_EVIDENCE`；
3. 从 `output.thread_id` 取得 root thread id；缺失/非字符串 →
   `INVALID_EVIDENCE`；
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
7. 查 sender 为 `outer_thread_id` 的 distinct formal nested children，按
   §15 唯一机器判定表分派：`==3` → `PASS`；`>3` → `FAIL_PRODUCER`；
   `1/2` → `FAIL_PRODUCER`；`==0` → `NOT_TESTED`；
8. formal ownership/malformed evidence 冲突（`app_server_events` entry 或
   `message` wrapper 缺失/非 object、completed spawn 无 concrete receiver、
   relation shape 损坏、同一 child 被不同 sender claim、contract 未声明
   formal spawn 规则）→ `INVALID_EVIDENCE`。

第 7 步的 `==0` 与 `1/2`、`>3` 必须区分：pinned evidence surface 上“formal
edge 不存在”只是 delegation unobservable，不是外部 native-delegation
failure 的机器证据，因此既不能猜 producer 违反 exactly-3，也不能猜 runtime
blocker。`1/2` 是已存在的 concrete formal spawn relation 与 completed run
一起直接违反 exactly-3；`>3` 的 extra dispatch 已经发生，下游任何失败都
不能消除它。

**verifier 不得读取 `child_thread_reads` 或任何 identity 字段**；prompt
文本、assistant/model 自述、`subAgentActivity.agentPath`、tool catalog 均
不得创建、修改或否定 formal ownership。

verdict 输出字段（无任何暗示 identity 已验收的名称）：

```json
{
  "schema": 2,
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

字段映射（verifier JSON 保持稳定 schema，issue #16 判定表用另一套名字）：

```text
verifier root_direct_child_count   == issue 表 root_direct_child_count
verifier nested_direct_child_count == issue 表 outer_nested_direct_child_count
```

verifier 退出码：`0` PASS、`1` FAIL_PRODUCER、`2` BLOCKED、
`3` INVALID_EVIDENCE、`4` NOT_TESTED。exit code 与
`producer_status` 必须一致；不一致属 evidence 问题。

## 12. Producer deterministic suite

```bash
(
  cd "$PRODUCER_REPO"
  uv run --locked pytest -q \
    >"$RUN_ROOT/output/pytest.stdout.txt" \
    2>"$RUN_ROOT/output/pytest.stderr.txt"

  git diff --check \
    >"$RUN_ROOT/output/git-diff-check.txt"
)
```

`PA-DIRECT-DET-01`（见 issue #16 Test Plan）是 deterministic Merge Gate 的
owner，包含本 issue 的 contract markers、negative discovery-preflight
assertions、child-failure no-guess assertions 与既有业务 contract。本章只是
在同一个 clean producer checkout 上复跑一次该 suite 并留下本 run 的原始
证据；它不证明真实 Codex runtime topology，也**不改变**
`PA-CODEX-FULL-LEAF-01` 的 runtime verdict。若 deterministic suite 失败，
按 `PA-DIRECT-DET-01` 自己的 Recipe / verdict 单独记录；本 runtime case 仍只按
§11 / §15 的 formal topology machine evidence 判定。JSON/JSONL、YAML/TOML
的正式判断使用结构化 parser（`jq` / `yq` / `tomllib`），不用 grep/sed/awk
代替字段判定。

## 13. Interaction

无。`paper`、`research_direction_file`、`mode`、`save` 全部固定提供；tiny
`.txt` fixture 不触发 PDF/OCR/Zotero/MCP/browser/user approval。

如果运行中需要额外 user input：

- 保存原始 machine response；
- 不临场补 prompt；
- 未进入目标 full path → `BLOCKED`；
- 只有在 evidence 已明确进入唯一 outer child 的 producer-owned full path，
  且固定完整输入理应足够时，才可按 producer behavior 判 FAIL。

## 14. Evidence

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
output/runtime-config-requested.json
output/runtime-config-effective.json
output/eval-request.json
output/eval-response.json
output/case-status.txt
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
本 case 的 merge verdict 链。

## 15. Verdict

终止状态与结果一一对应；先做 malformed/conflicting/contaminated 检查，再按
下表顺序判定。同一状态不得落入多个结果。

| 机器状态 | Verdict |
| --- | --- |
| 未越过 §4–§8、§10 `CASE_STARTED` 边界 | `CASE_NOT_STARTED` |
| malformed / conflicting / contaminated evidence | `INVALID_EVIDENCE`（产品层即 `INVALID_TEST_EXECUTION`） |
| `version` 为 null、provider/model unavailable | `BLOCKED` |
| `root_direct_child_count != 1` | `BLOCKED` |
| `root_direct_child_count == 1` 且 nested `== 3`，ownership valid | `PASS` |
| `root_direct_child_count == 1` 且 nested `in {1,2}` | `FAIL_PRODUCER` |
| `root_direct_child_count == 1` 且 nested `> 3` | `FAIL_PRODUCER` |
| `root_direct_child_count == 1` 且 nested `== 0` | `NOT TESTED` |

当前 pinned `codex-eval-adapter@9` 没有 native-spawn-failure machine state，
所以「外部 failure 阻止 required topology 形成」的 `BLOCKED` 分支不可人为
触发：不得为它发明 reason code、私有 schema 或 synthetic injection。

### PASS

全部满足：

- clean consumer 为本次新建，来源为显式 Git dependency；
- lock `resolved_commit == FINAL_HEAD_SHA`；
- fixture repo exact SHA 且 dirty=no；
- producer checkout tracked + untracked 干净，`output/producer-repo-dirty.txt`
  为 `producer_repo_dirty=no`；
- `manual_patch=no`；
- clean-consumer purity preflight 通过（安装树无 test-only artifacts）；
- generated Codex projection 通过 §7 全部 checks：15 条 direct/deferred-surface
  contract markers 全在，且 6 条 retired false-failure clauses 全不在；
  `ALL_TOOLS` 只用于绑定目录实际列出的 callable，不把臆测的固定属性名当作能力判定；
- §8 的三条 runtime prerequisite config 原样出现在
  `output/eval-request.json`，ceiling 为 `4`；
- `output/case-status.txt` 为 `CASE_STARTED`；
- `/eval.passed` 具有合法 boolean shape，version 有 provenance；`passed`
  的 true/false 值本身不覆盖 formal topology verdict；
- canonical input 为 `$RUN_ROOT/config/paper.txt`（producer repo 级 fixture
  复制，不来自 consumer 安装树）；
- root 恰有 1 个 formal direct outer child；
- outer child 有恰好 `3` 个 distinct formal direct `spawnAgent` nested child；
- formal ownership 无冲突。

`PA-DIRECT-DET-01` 的 pytest / static contract 结果是独立 deterministic Gate，
不作为本 runtime case 的 PASS 条件，也不得反转已经由 formal topology 证明的
runtime verdict。

formal exactly-3 topology 一旦由上述受支持机器证据证明，本 case 的 routing
proof 即成立：之后 scope 外的 child、business 或 provider failure 都不反转
该 topology PASS，只影响它们自己所属的 integration/business verdict。顶层
`/eval.passed == false` 单独也不是受支持的 native-delegation failure machine
state，不得覆盖已经成立的 formal topology。verifier 只读 formal spawn
relations，因此这类下游噪声在结构上就进不了判定；
`output/runtime-topology.json` 的 `PASS` 是唯一依据。

PR evidence 对本 case 的 runtime prerequisite 只写事实：

```text
Codex runtime prerequisites pinned for this acceptance:
agents.enabled=true
agents.max_concurrent_threads_per_session=4 (test resource ceiling)
agents.max_depth=2 (minimum required by root -> outer -> nested topology)
agents.* effective value: not reported by the pinned /eval surface
```

不得声称「runtime 已确认 ceiling 生效」，也不得声称
`output.thread_start_effective` 覆盖了 `agents.*`。

**任何 identity 字段的缺失、`default`、mismatch、unobservable 或
contradiction 均不改变上述 topology verdict。**

### FAIL_PRODUCER

只有在：

- 已越过 `CASE_STARTED`；
- `/eval.passed` 具有合法 boolean shape；其值单独不构成 blocker；
- producer checkout 干净（`producer_repo_dirty=no`）；
- 固定 input 正常；
- clean-consumer purity preflight 已通过（consumer 无 test-only artifact
  污染）；
- root 恰有唯一 formal outer child；
- formal topology evidence 本身有效；

并出现以下本 runtime case 直接负责的行为失败时才判 FAIL：

- outer child 产生了 concrete formal nested `spawnAgent` children，但数量
  为 `1` 或 `2`（completed run 直接违反 exactly-3 obligation）；
- outer child 的 distinct formal direct nested child `> 3`（extra dispatch
  已正面发生，下游 failure 不能消除）。

§7 generated projection failure 发生在 `CASE_STARTED` 前，唯一分类是
`CASE_NOT_STARTED`；canonical/static producer contract 的 FAIL 归
`PA-DIRECT-DET-01`，不得在本 runtime case 中重复归因。

`nested == 0` 不属于本 verdict：absence 不是 producer 违反 exactly-3 的机器
证据（见 `### NOT TESTED`）。

### BLOCKED

包括：

- provider/model unavailable；
- 受支持 machine evidence 正面证明的 external runtime/provider blocker；
- `/eval.version == null`；
- root 没有 formal direct outer child，无法证明进入目标 path；
- root 出现多个不同 formal direct children，固定 outer dispatch 无法唯一
  归属；
- 当前 runtime/eval evidence surface 不再提供本 Recipe 所需 formal
  topology 字段；
- runtime 明确报告 permission/concurrency/subagent capability blocker（必须
  有原始 machine evidence 在案，不得由模型 prose 推断）。

**不得因为 `agent_type=default`、identity 不可观察或 identity mismatch 判
BLOCKED。不得从 `nested == 0` 猜出 runtime blocker。**

### INVALID_EVIDENCE

只限 formal topology / source evidence 本身损坏或自相矛盾（产品层对应
`INVALID_TEST_EXECUTION`）：

- `eval-response.json` malformed；
- `passed` 不是 boolean，或 `version` 是非 null 的非字符串；
- completed formal `spawnAgent` relation 缺 concrete receivers；
- formal sender/receiver shape malformed；
- 同一 child 被不同 sender 的 formal spawn relation claim；
- source isolation / manual patch / provenance 证据自相矛盾；
- evidence 被 test setup 以外的方式污染（例如改写过 raw response）。

**identity contradiction 不属于本 case 的 `INVALID_EVIDENCE` 条件。**

### NOT TESTED

`root_direct_child_count == 1` 且 `nested_direct_child_count == 0`，且
当前受支持 evidence surface 没有外部 delegation-failure machine state。

含义：delegation 在该 evidence surface 上仅为 unobservable。本 run 既没有
证明 producer 的 exactly-3 obligation 被违反，也没有证明 runtime blocker
存在；不产生 PASS/FAIL，也不得归因。记录 verifier 的
`producer_status == "NOT_TESTED"` 与 `reasons`，并按 §16 判断是否属于
Recipe 预定义的可重试 transport 条件。

### CASE_NOT_STARTED

预判定终态，不是 case verdict。触发条件全部在 `CASE_STARTED` 边界之前：

- exact revision 校验失败（producer/fixture SHA 或 dirty 不符）；
- producer checkout dirty（tracked 或 untracked 未提交）：

  ```text
  CASE_NOT_STARTED
  reason: producer checkout dirty; producer-owned fixture/verifier
  provenance to FINAL_HEAD_SHA not established
  ```

- clean consumer / APM install / lock provenance 不成立；
- clean-consumer purity preflight 失败（安装树存在 test-only artifacts）；
- §7 generated projection 断言失败（正式 producer 未按 contract 部署）；
- §8 runtime prerequisite config 不被 runtime 接受；
- `curl` 到 `/eval` 失败，或响应无非空 `output.thread_id`。

只记录具体 bootstrap failure reason 与已取得的证据；reason code 只用本文
已定义的这些，不新增。

## 16. Retry / stop rules

- 每个 final SHA 的正式 acceptance 只产生一个 verdict；
- retry 仅限本节预先声明的 transport/基础设施条件：`/eval` HTTP 层失败
  （连接被拒、DNS、进程重启导致的 502/504）或 eval service 明确报告的
  harness transient。retry 时输入、prompt、model、reasoning、sandbox、
  `agents.*` config、fixture、consumer 布局、断言与判定规则全部不变，且先
  确认前一次尝试未污染产品状态；
- `FAIL_PRODUCER` 一旦成立即终止该 SHA 的 acceptance，不得用同一 SHA
  后续无变更重跑得到的 `PASS` 覆盖；
- `NOT TESTED` 不允许通过换 config、换 model、加提示或提高 ceiling 重采样
  来找成功；没有新增排查价值时停止；
- `BLOCKED`（provider / harness transient）只在上述同一冻结输入下做有界
  retry；不得临场提高 ceiling、放宽 sandbox、改 prompt 或手动告诉 outer
  child spawn；
- `INVALID_EVIDENCE` 不得通过 retry-until-green 覆盖，必须先修复损坏或矛盾
  的 evidence/source；
- test setup contamination（purity preflight 失败或安装树被 test-only
  artifacts 污染）按 `CASE_NOT_STARTED` 处理：此时观察到的任何 topology
  结果（包括 `nested == 0`）都不得作为 `FAIL_PRODUCER` 结论，修复测试布局
  后以新 final SHA 重建 consumer 重跑；
- 不修改 shared fixtures/eval-server 追绿；
- 不通过删改 `child_thread_reads` 或 identity events 制造 PASS（本 producer
  verifier 根本不消费它们；原始响应必须完整保存）；
- 不追加“再多跑一次看看”的额外 runtime smoke；PASS evidence 闭合后停止，
  不追加长论文或下游 Stage 2 E2E。

## 17. Impact-based revalidation

取代旧的 blanket “producer/fixture SHA changed ⇒ rerun everything”。

本 case 的 declared revalidation dependencies：

- `paper-analysis` Codex delegation instructions（`.apm/agents/paper-analysis.agent.md`）；
- generated `.codex/agents/paper-analysis.toml` projection；
- `tests/runtime/verify_codex_full_mode_topology.py` 与其 evidence contract；
- `agents.enabled` / `agents.max_concurrent_threads_per_session` /
  `agents.max_depth` 等正式
  runtime prerequisite；
- `skills-test-fixtures` revision 与 `codex-eval-adapter` contract id；
- 固定 prompt（`config/root-prompt.txt`）、consumer install path、APM 版本、
  eval-server checkout 提供的 `/eval` evidence surface；
- verdict semantics（§15 判定表与 verifier exit-code 映射）。

规则：

- SHA 单独改变不自动使无关 PASS 失效。先比较两个 revision 之间的
  intervening diff 与本 case 的 declared dependency 与证明事项；
- 命中 dependency 时按影响范围处理：`EXECUTE_CURRENT`（重新执行本 case）、
  `REJUDGE_PRIOR_EVIDENCE`（旧 raw evidence 完整且包含当前判定所需事实时，
  用当前规则重新判定）或 `REUSE_PRIOR_PASS`（未受影响，直接复用）；
- 只重跑受影响的 case 与必要的 adjacent contract tests，并记录旧 PASS 的
  revision、impact analysis 与复用理由；
- 未命中 dependency 的 producer/fixture SHA 变化属 `REUSE_PRIOR_PASS`，需
  写明该 diff 未触及上述任何一项；
- Codex runtime version 变化只更新 provenance；只有 formal topology
  surface 真正不兼容时才 `BLOCKED` / `INVALID_EVIDENCE`，并保存真实输出
  characterization；
- 旧执行不得记作当前执行；重新判定若不再 PASS，如实记录新结果。
