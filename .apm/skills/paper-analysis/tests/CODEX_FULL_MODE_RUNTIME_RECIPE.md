# Codex Full-Mode Runtime Recipe — `PA-CODEX-FULL-LEAF-01`

Producer-owned acceptance recipe for issue #13. It proves, on a clean
consumer and the real `mode: full` entry path, that the unique formal outer
child spawns native nested subagent delegation at Step 3 instead of inlining
the three-way analysis.

本文件是 producer 仓库内的正式 Test Recipe：执行者按本文逐步操作，不依赖
issue 文本；issue 只描述目标，本文描述可执行步骤与判定。

Identity 边界（本 recipe 的 hard boundary）：runtime agent identity /
`agent_type` 永远不是本 case 的 PASS / FAIL / BLOCKED 条件。本 case 只验
formal nested delegation topology：

```text
root thread
  -> exactly 1 formal direct outer child
       -> >= 1 formal direct nested child
```

`outer child` 只按 formal thread ownership 定位，不声明、不判断它的
runtime agent identity。

## 1. Identity（Test Case 元数据，不是 agent identity）

- **Case ID**: `PA-CODEX-FULL-LEAF-01`
- **Acceptance criterion**: 固定 root prompt 成功产生唯一 formal outer
  child 后，该 outer child 至少产生 1 个 formal direct nested child。
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
锁定；runtime smoke 只要求 `>= 1` 个 formal direct nested child。

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
test -f "$CONSUMER/.agents/skills/paper-analysis/tests/fixtures/paper.txt"
```

用 `yq` 证明 lock 确实 pin 到 final Git commit。APM 0.29 lockfile 把
`repo_url` 归一化为小写 `owner/repo`（不是 `https://...` URL 形式），原始
大小写保留在 `materialization_repo_url`，主机在 `host` 字段，所以机械
判定用 `host` + `materialization_repo_url` 组合：

```bash
yq -e '.dependencies[] | select(.resolved_commit == strenv(FINAL_HEAD_SHA)) | select(.host == "github.com" and .materialization_repo_url == "ScholarWorkflow/paper-analysis")' \
  "$CONSUMER/apm.lock.yaml" >/dev/null
cp "$CONSUMER/apm.lock.yaml" "$RUN_ROOT/output/apm.lock.yaml"
```

## 6. Generated projection check

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

## 7. Fixed input / prompt

```bash
PAPER_TXT="$CONSUMER/.agents/skills/paper-analysis/tests/fixtures/paper.txt"
mkdir -p "$CONSUMER/runtime-output"

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

## 8. Execution — existing eval service only

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

## 9. Producer topology verifier

```bash
python3 "$PRODUCER_REPO/.apm/skills/paper-analysis/tests/verify_codex_full_mode_topology.py" \
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
   `item.tool == spawnAgent`、非空 `senderThreadId`、非空字符串数组
   `receiverThreadIds`）；
5. dedupe started/completed 的同一 formal edge；
6. root direct formal child 数量：`0` → `BLOCKED`；`>1` → `BLOCKED`；
   `==1` → 得到 `outer_thread_id`；
7. 查 sender 为 `outer_thread_id` 的 formal nested children：`>=1` →
   topology threshold 满足；`0` → `FAIL_PRODUCER`；
8. formal ownership/malformed evidence 冲突（completed spawn 无 concrete
   receiver、relation shape 损坏、同一 child 被不同 sender claim、
   contract 未声明 formal spawn 规则）→ `INVALID_EVIDENCE`。

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
  "nested_direct_child_count": 1,
  "nested_child_thread_ids": ["..."],
  "formal_spawn_relation_count": 2,
  "reasons": [],
  "provenance": {"eval_version": "...", "contract_id": "..."}
}
```

verifier 退出码：`0` PASS、`1` FAIL_PRODUCER、`2` BLOCKED、
`3` INVALID_EVIDENCE。

## 10. Producer deterministic suite

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

## 11. Interaction

无。`paper`、`research_direction_file`、`mode`、`save` 全部固定提供；tiny
`.txt` fixture 不触发 PDF/OCR/Zotero/MCP/browser/user approval。

如果运行中需要额外 user input：

- 保存原始 machine response；
- 不临场补 prompt；
- 未进入目标 full path → `BLOCKED`；
- 只有在 evidence 已明确进入唯一 outer child 的 producer-owned full path，
  且固定完整输入理应足够时，才可按 producer behavior 判 FAIL。

## 12. Evidence

至少保留：

```text
output/producer-sha.txt
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
output/generated-projection.json
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
脱敏 machine evidence。不要求 `adapter.json`，因为 shared adapter 不属于
本 case 的 merge verdict 链。

## 13. Verdict

### PASS

全部满足：

- clean consumer 为本次新建，来源为显式 Git dependency；
- lock `resolved_commit == FINAL_HEAD_SHA`；
- fixture repo exact SHA 且 dirty=no；
- `manual_patch=no`；
- generated Codex projection 保留两个 exact orchestration markers；
- `/eval` execution healthy，version 有 provenance；
- root 恰有 1 个 formal direct outer child；
- outer child 有 `>=1` formal direct `spawnAgent` nested child；
- formal ownership 无冲突；
- producer deterministic suite 全 PASS；
- OpenCode native deterministic/static contract 无回归。

**任何 identity 字段的缺失、`default`、mismatch、unobservable 或
contradiction 均不改变上述 topology verdict。**

### FAIL_PRODUCER

只有在：

- `/eval` healthy；
- 固定 input 正常；
- root 恰有唯一 formal outer child；
- formal topology evidence 本身有效；

并出现以下本 issue 直接负责的行为失败时才判 FAIL：

- outer child 没有任何 formal direct nested `spawnAgent` child；
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

## 14. Retry / invalidation

- retry 保持同一 input、prompt、model、reasoning、sandbox、config；
- 不换模型、不提高 reasoning、不改 prompt、不手动告诉 outer child spawn；
- 不修改 shared fixtures/eval-server 追绿；
- 不通过删改 `child_thread_reads` 或 identity events 制造 PASS（本 producer
  verifier 根本不消费它们；原始响应必须完整保存）；
- producer SHA 或 fixture SHA 变化 → 旧 acceptance 失效，重建 clean
  consumer；
- Codex version 变化只更新 provenance；只有 formal topology surface 真正
  不兼容时才 BLOCK/INVALID，并保存真实输出 characterization；
- PASS evidence 闭合后停止，不追加长论文或下游 Stage 2 E2E。
