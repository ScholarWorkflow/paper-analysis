# Codex Full-Mode Runtime Recipe — `PA-CODEX-FULL-LEAF-01`

Producer-owned acceptance recipe for issue #13. It proves, on a clean
consumer and the real `mode: full` entry path, that the installed exact
`paper-analysis` coordinator produces native nested subagent delegation at
Step 3 instead of inlining the three-way analysis.

本文件是 producer 仓库内的正式 Test Recipe：执行者按本文逐步操作，不依赖
issue 文本；issue 只描述目标，本文描述可执行步骤与判定。

## 1. Identity

- **Case ID**: `PA-CODEX-FULL-LEAF-01`
- **Acceptance criterion**: producer 正式 `mode: full` 入口自然到达 Step 3 时，
  exact `paper-analysis` coordinator 至少产生 1 个 formal **direct** nested
  analysis child。
- **Invariant**: root 只负责 outer dispatch；内部 nested delegation 必须来自
  安装后的 coordinator instructions（`developer_instructions`），不得由 root
  prompt 强迫、描述或暗示。
- **Does NOT prove**: 三个 leaf 的业务内容质量、必须同时存在 3 个 live child、
  OCR/future-work/facts 质量、长论文质量、`professor-contact` 集成质量、
  OpenCode runtime compatibility。

业务结构不变：full Step 3 三路 semantic roles
（① 内容沉淀；② 贡献与批判；③ 帮助评估）由 deterministic producer test
锁定；runtime smoke 只要求 `>= 1` 个 direct nested child。

## 2. Basis

固定 shared fixture revision（本 recipe 编写时当前 master；执行前必须复核）：

```text
skills-test-fixtures:
9cb4547845be323a2a7b59139ee419476f2c7113
contract:
skills-test-fixtures/codex-eval-adapter@9
```

adapter@9 可使用的 machine evidence：

- `output.app_server_events` 中 formal `spawnAgent` relation；
- `dispatch.thread_relations[]`；
- `output.child_thread_reads[]` 的 direct parent attribution / persisted
  role（可用时）；
- `dispatch.agent_identity[...]` identity dimensions（可用时）；
- top-level independent `delegation` dimension。

版本语义：

- `/eval.version` 必须记录；`null` 属于 capability blocker；
- 非 null 版本字符串是 provenance-only；版本号与历史 characterization 不同，
  本身不 BLOCK / FAIL；
- parser/contract 无法解释实际结构时，按 adapter / producer verifier 的
  machine evidence 判 `BLOCKED` / `INVALID_EVIDENCE`。

历史 eval-server merge `3efc910ccf8315502be0e0c6c81a91f1ee2b3a6c` 只作为
adapter@8/9 来源 provenance，不是 checkout equality gate。

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
eval `thread_id` / `runtime_generation`。`fixture_run_id` 只用于实际启动
runtime fixture 的 recipe。

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

用 `yq` 证明 lock 确实 pin 到 final Git commit：

```bash
yq -e '.dependencies[] | select(.resolved_commit == strenv(FINAL_HEAD_SHA)) | select(.repo_url == "https://github.com/ScholarWorkflow/paper-analysis" or .repo_url == "https://github.com/ScholarWorkflow/paper-analysis.git")' \
  "$CONSUMER/apm.lock.yaml" >/dev/null
cp "$CONSUMER/apm.lock.yaml" "$RUN_ROOT/output/apm.lock.yaml"
```

## 6. Generated projection check

canonical test 不能替代 generated projection evidence。直接解析安装后
Codex agent：

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

assert data["name"] == "paper-analysis"
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
    "name": data["name"],
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
从当前 clean consumer 中调用已安装的 exact custom agent paper-analysis 一次，传入：
paper: $PAPER_TXT
research_direction_file: $RUN_ROOT/config/research-direction.txt
mode: full
save: $CONSUMER/runtime-output
等待该 coordinator 返回后结束。
你作为 root 只负责这次 outer dispatch：不要自己分析论文，不要为 paper-analysis 创建任何内部分析 leaf，不要指示它为了测试 spawn/创建 leaf，也不要描述它内部 Step 3 的编排。paper-analysis 内部是否 delegation 必须完全来自安装后的 developer_instructions。
EOF
```

禁止临场修改 prompt / fixture。

## 8. Eval request

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
    "--config", f'projects={{"{consumer}"={{"trust_level":"trusted"}}}}',
    "--", prompt,
]
request = {"command": " ".join(shlex.quote(x) for x in args), "timeout": 300}
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

## 9. Shared adapter

```bash
python3 "$FIXTURES_DIR/scripts/parse_codex_eval_evidence.py" \
  --contract "$FIXTURES_DIR/configs/codex-eval-adapter-contract.json" \
  --eval-response "$RUN_ROOT/output/eval-response.json" \
  --expected-agent paper-analysis \
  --consumer-root "$CONSUMER" \
  --output "$RUN_ROOT/output/adapter.json"
```

shared adapter 只提供 wiring / dispatch / identity / delegation evidence，
不输出本 producer 的 PASS/FAIL。

## 10. Producer topology verifier

```bash
python3 "$PRODUCER_REPO/.apm/skills/paper-analysis/tests/verify_codex_full_mode_topology.py" \
  --eval-response "$RUN_ROOT/output/eval-response.json" \
  --adapter "$RUN_ROOT/output/adapter.json" \
  --output "$RUN_ROOT/output/runtime-topology.json"
```

### A. Common evidence gate

producer verifier 先确认：

- `/eval` 顶层 `passed == true`；
- `version` 非 null，并原样记录；
- adapter/eval JSON 满足 pinned adapter contract；
- 无 fixture/harness contamination、dispatch mismatch、malformed evidence。

**禁止用 `version == 某个字符串` 作为 PASS/BLOCK/FAIL 条件。**

availability/provider/model/harness/capability 不足 → `BLOCKED`；
结构矛盾/损坏 → `INVALID_EVIDENCE`。

### B. Exact coordinator identity

本 case 必须证明 nested edge 的 sender 是 exact `paper-analysis`
coordinator，而不是 generic child。

从 adapter@9 的结构化 identity evidence 唯一定位：

```text
identity_eligible == true
effective_role == "paper-analysis"
```

并确认其 `parent_thread_id == eval root thread_id`。

如果 exact coordinator identity 不能机器确认：`BLOCKED` /
`INVALID_EVIDENCE`；不得用 root prompt 文本或模型自述补证据。

### C. Changed runtime contract: direct nested delegation

从 `adapter.dispatch.thread_relations[]` 只取：

```text
tool == "spawnAgent"
sender_thread_id == coordinator_thread_id
```

将非空 concrete `receiver_thread_ids` 去重为 `nested_child_thread_ids`。

若当前 `child_thread_reads` 有对应 child，cross-check：

```text
parent_thread_id == coordinator_thread_id
```

冲突 → `INVALID_EVIDENCE`。

本 case 唯一 runtime PASS threshold：

```text
len(nested_child_thread_ids) >= 1
```

不要求 3 个 live child，不要求 child 业务输出质量，不要求 child completion
artifact。leaf no-child / no-recursion / gap-only 等由 deterministic suite
验证；live smoke 中额外观察到异常可保存为 diagnostics，但不把未修改
invariant 重复变成第二套 LLM runtime threshold。

verifier 退出码：`0` PASS、`1` FAIL_PRODUCER、`2` BLOCKED、
`3` INVALID_EVIDENCE。

## 11. Producer deterministic suite

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

## 12. Interaction

无。`paper`、`research_direction_file`、`mode`、`save` 全部固定提供；tiny
`.txt` fixture 不触发 PDF/OCR/Zotero/MCP/browser/user approval。

如果 coordinator 返回 `needs_input`：

- 保存原始 machine response；
- 不临场补 prompt；
- 若 exact coordinator 已确认、input delivery 正常且缺失项本应由固定 input
  满足，按 producer behavior 判 FAIL；
- 若是 dispatch/input delivery/provider/runtime/harness 问题，判 `BLOCKED`。

## 13. Evidence

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
output/adapter.json
output/runtime-topology.json
output/uv-sync.stdout.txt
output/uv-sync.stderr.txt
output/pytest.stdout.txt
output/pytest.stderr.txt
output/git-diff-check.txt
```

完整 raw response 保留在 `/tmp` run root；PR 只贴足以证明结论的最小脱敏
machine evidence。

## 14. Verdict

### PASS

全部满足：

- clean consumer 是本次新建，来源为显式 Git dependency；
- lock `resolved_commit == FINAL_HEAD_SHA`；
- fixture repo exact SHA 且 dirty=no；
- `manual_patch=no`；
- generated `paper-analysis.toml` name 正确，且 `developer_instructions`
  包含两个 exact marker；
- eval common evidence healthy；
- exact `paper-analysis` coordinator identity 可机器确认，且为 root direct
  child；
- coordinator 有 `>=1` formal direct `spawnAgent` nested child；
- parent attribution 无冲突；
- producer deterministic suite 全 PASS；
- OpenCode native deterministic/static contract 无回归。

### FAIL_PRODUCER

只有在 common evidence healthy、exact coordinator 已确认、固定 input 已正确
送达时，出现本 issue 直接负责的行为失败：

- 正式 `mode: full` coordinator 到达目标路径后没有 formal direct nested
  child；
- canonical agent 缺任一 exact marker；
- generated Codex projection 丢失任一 exact marker；
- 固定完整输入下，producer-owned behavior 错误导致未进入正式 full path /
  错误 `needs_input`。

### BLOCKED

包括：

- provider/model unavailable；
- eval service / harness failure；
- `/eval.version == null`；
- exact coordinator dispatch / identity 无法被当前结构化 evidence 确认；
- clean consumer/provenance 不成立；
- runtime 明确报告 permission/depth/concurrency/subagent capability
  blocker；
- adapter 表明 producer verdict 所需 machine surface 不可观察。

**版本字符串变化本身不是 BLOCKED。**

### INVALID_EVIDENCE

包括：

- adapter/eval JSON malformed 或与 pinned contract 矛盾；
- coordinator identity 多义；
- formal relation 与 child parent attribution 冲突；
- 同一 child 有冲突 ownership；
- source isolation / manual patch / provenance 证据自相矛盾。

## 15. Retry / invalidation

- retry 保持同一 input、prompt、model、reasoning、sandbox、config；
- 不换模型、不提高 reasoning、不改 prompt、不手动告诉 coordinator spawn；
- 不修改 shared fixtures/eval-server 追绿；
- producer SHA 或 fixture SHA 变化 → 旧 acceptance 失效，重建 clean
  consumer；
- Codex version 变化只更新 provenance；只有 machine evidence
  surface/contract 真正不兼容时才按 adapter/verifier 结果 BLOCK/INVALID，
  并基于真实输出做 characterization；
- PASS evidence 闭合后停止，不追加长论文或下游 Stage 2 E2E。
