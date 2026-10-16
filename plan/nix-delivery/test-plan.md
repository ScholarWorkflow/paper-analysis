# paper-analysis：Nix 最小测试计划与执行步骤

Test plan revision: t1.2；对应 [执行计划 v1.2](implementation-plan.md)。
状态：候选待审，第一关必测清单与第二关步骤待确认；第三关未执行。本 PR 只交文档。

## 1. 必测清单与上限

只检查 `aarch64-darwin` / Codex 新增 Nix 交付。按本轮明确范围，不新增模型 eval、gap-only/full 代理业务运行或真实 OCR 调用义务，也不做分析质量认证、全仓回归、OpenCode/Linux 矩阵或上游通用安装器复验。规则及固定来源见执行计划第 1–2 节。

| 项 | 业务目标 | 输入或场景 | 预期结果与检查方式 |
|---|---|---|---|
| T1 | 固定输出可构建，真实安装完整资源与原生角色 | 一个隔离 consumer；paper-analysis-project | build/apply 成功；完整技能、四 scripts、六 bin 入口、原生 paper-analysis 角色与 vision-tools 直接依赖就位。读实际文件/配置与包声明，不把 store view/eval 当安装。 |
| T2 | 四个固定 helper 与本地 pdfx 入口能完成必要最小动作 | 既有 normalized_abstract.json、future_work.pdf、analysis.md、future_work_items.json、facts valid_draft | canonical JSON、PDF 提取/渲染、quality、future-work prepare/validate/finalize 与 facts validate 成功。用原退出码/JSON/目标文件和既有 fixture 预期判断。 |
| T3 | 新增 OCR wrapper 接到已交真实 vision 依赖 | 安装的 bin/vision-glance 与固定 base-skills app | 固定路径/参数原样转发/closure 正确，不依赖 PATH 或运行时安装；以生成 launcher 和依赖定义只读核对，复用上游现有结果，不重复实际 OCR。 |

T2 只验证 Nix 安装入口，没有修改原 helper 业务。既有 full-mode facts/fingerprint、OCR cache 与分析质量要求不在本轮重新认证。实现若改变这些业务，先报告并按影响修订，不自动扩大本计划。

## 2. 实施与环境前提

产品尚未实现：`PRODUCER_SHA` 必须由产品负责人提供实际实现的完整 40 位提交，且已提供执行计划约定的输出与六入口；文档 PR SHA 不能代填。以下是实施完成后的 recipe，目前不执行、没有通过结论。

本地测试工程师准备 Apple Silicon macOS、已有 Nix flakes/Git/jq/支持 TOML 输入的 yq，记录实际工具版本。`TEST_RUN_ROOT` 是仓库外、位于 `/tmp` 的本次测试位置。构建保留原 HOME，以免丢失读取 private Nix inputs 的既有凭据；apply 只使用本轮独立 CODEX_HOME，不改用户配置或信任。无需 Codex/eval 服务、模型认证、Zotero/Chrome fixture 或视觉 API 配置。

真实 OCR 运行仍依赖 vision-tools 的端点、模型、凭据和授权预算；这些是产品 README 必须声明的外部前提。本轮不要求准备或传输密钥，不以依赖/接线成立宣称真实 OCR 已验证。

## 3. T1：真实 build/apply 与安装核对

在 Bash 中逐条运行并检查退出码。已有有效同 SHA 安装直接复用其 RUN/consumer/记录；本次首次验证新交付时才做一次 fresh build/apply。

```bash
set -euo pipefail
: "${PRODUCER_SHA:?提供实际产品 SHA}"
: "${TEST_RUN_ROOT:?提供仓库外 /tmp 测试位置}"
RUN=$(mktemp -d "${TEST_RUN_ROOT%/}/paper-nix.XXXXXX")
CONSUMER="$RUN/consumer"
mkdir -p "$CONSUMER" "$RUN/output" "$RUN/input" "$RUN/codex-home" "$RUN/caller"
REF="github:ScholarWorkflow/paper-analysis/$PRODUCER_SHA"
git clone --no-checkout https://github.com/ScholarWorkflow/paper-analysis.git "$RUN/source"
git -C "$RUN/source" checkout --detach "$PRODUCER_SHA"
SOURCE="$RUN/source"
nix build "$REF#packages.aarch64-darwin.paper-analysis-project" \
  --out-link "$RUN/project-env" > "$RUN/output/build.log" 2>&1
CODEX_HOME="$RUN/codex-home" "$RUN/project-env/bin/agent-env" apply \
  --project "$CONSUMER" > "$RUN/output/apply.log" 2>&1
SKILL="$CONSUMER/.agents/skills/paper-analysis"
for file in SKILL.md scripts/paper_input.py scripts/pdf_runtime.py scripts/future_work.py scripts/facts.py; do
  test -f "$SKILL/$file" || exit 1
done
for entry in paper-input pdf-runtime future-work facts pdfx vision-glance; do
  test -x "$SKILL/bin/$entry" || exit 1
done
test -f "$CONSUMER/.agents/skills/vision-tools/SKILL.md"
test -f "$CONSUMER/.agents/skills/vision-tools/bin/glance"
test -f "$CONSUMER/.agents/skills/vision-tools/vision_client.py"
yq -p toml -o json "$CONSUMER/.codex/agents/paper-analysis.toml" \
  | jq -e '.name == "paper-analysis" and (.description | length > 0) and (.developer_instructions | length > 0)'
```

只读对照本包 `files` 声明与安装树，确认附属资源完整、没有安装 pdfxAgent/其他 base-skills 根包。检查生成的原生角色来自原 body、准确 name/description，入口指向安装 skill 的 bin，保留 full/gap-only/needs_input/禁止自委派业务约束，没有把 OpenCode 字段冒充 Codex ACL，也没有保留强制 ALL_TOOLS discovery 的旧前置。只核本次转换，不启动模型或重验旧业务拓扑。共享安装保护直接复用，不扩安装矩阵或来源认证。

## 4. T2：既有数据与四 helper 最小动作

数据从受测 producer 的既有文件/fixture factory 取得；不让 AI 生成新论文、JSON fixture 或 expected output。下列 Python 只调用已有 facts fixture factory，不是判定器，也不替代被测 helper。源码 checkout 只提供数据，实际产品命令一律走安装 bin。

```bash
cp "$SOURCE/tests/fixtures/normalized_abstract.json" "$RUN/input/normalized_abstract.json"
cp "$SOURCE/tests/fixtures/future_work.pdf" "$RUN/input/future_work.pdf"
cp "$SOURCE/tests/fixtures/future_work_items.json" "$RUN/input/items.json"
cp "$SOURCE/tests/fixtures/analysis.md" "$RUN/output/analysis.md"
PYTHON_OUT=$(nix build --no-link --print-out-paths \
  github:NixOS/nixpkgs/6510408d147d8c5e6d76043e899e9251756f6a75#python3)
PYTHON="$PYTHON_OUT/bin/python3"
"$PYTHON" - "$SOURCE/tests/test_facts.py" "$RUN/input/facts-draft.json" <<'PY'
import json, pathlib, runpy, sys
fixture = runpy.run_path(sys.argv[1])["FactsTests"]().valid_draft()
pathlib.Path(sys.argv[2]).write_text(json.dumps(fixture), encoding="utf-8")
PY
cd "$RUN/caller"
PATH= "$SKILL/bin/paper-input" "$RUN/input/normalized_abstract.json" > "$RUN/output/canonical.json"
jq -e '.ok == true and .schema == 1 and .level == "abstract" and
  (has("source") | not) and (has("item_key") | not)' "$RUN/output/canonical.json"
PATH= "$SKILL/bin/pdf-runtime" extract "$RUN/input/future_work.pdf" \
  --output "$RUN/output/fulltext.txt" > "$RUN/output/extract.json"
jq -e '.ok == true and .pages == 1' "$RUN/output/extract.json"
test -s "$RUN/output/fulltext.txt"
PATH= "$SKILL/bin/pdf-runtime" render "$RUN/input/future_work.pdf" \
  --page 1 --output "$RUN/output/page-1.png" --scale 4 > "$RUN/output/render.json"
jq -e '.ok == true and .page == 1' "$RUN/output/render.json"
test -s "$RUN/output/page-1.png"
PATH= "$SKILL/bin/pdfx" quality "$RUN/input/future_work.pdf" --json > "$RUN/output/quality.json"
jq -e --arg pdf "$RUN/input/future_work.pdf" '.pdf == $pdf and (.pages | length == 1) and (.summary | type == "object")' "$RUN/output/quality.json"
PATH= "$SKILL/bin/future-work" prepare "$RUN/input/future_work.pdf" \
  --debug-dir "$RUN/output/debug" > "$RUN/output/prepare.json"
jq -e '.result == "ok" and .candidate_count >= 1 and .ocr_required_pages == []' "$RUN/output/prepare.json"
PATH= "$SKILL/bin/future-work" validate --items "$RUN/input/items.json" \
  --candidates "$RUN/output/debug/candidates.json" > "$RUN/output/validate.json"
jq -e '.ok == true' "$RUN/output/validate.json"
PDF_SHA=$(jq -er '.pdf_sha256' "$RUN/output/prepare.json")
PATH= "$SKILL/bin/future-work" finalize --analysis "$RUN/output/analysis.md" \
  --items "$RUN/input/items.json" --candidates "$RUN/output/debug/candidates.json" \
  --patch --pdf-sha256 "$PDF_SHA" > "$RUN/output/finalize.json"
jq -e '.ok == true and .items == 1' "$RUN/output/finalize.json"
jq -e '.status == "ok" and .items[0].page == 1 and
  .items[0].quote == "Future work will evaluate the method on longer documents."' \
  "$RUN/output/analysis.md.future_work.json"
PATH= "$SKILL/bin/facts" validate --draft "$RUN/input/facts-draft.json" > "$RUN/output/facts.json"
jq -e '.ok == true and .facts.paper.title == "Paper title"' "$RUN/output/facts.json"
```

直接打开 PNG，确认是一页可读的原 fixture；查看提取文本中的 `<!-- PDF_PAGE: 1 -->` 与既有 future-work 句子，canonical 的 abstract/metadata 与输入相符；Markdown 专节位于原两个锚点之间。上述预期沿用 `tests/test_future_work_cli.py` / `tests/test_facts.py`，不构造新数据。quality 只核原 CLI 正常返回对应 PDF 的质量信息，不要求极短 fixture 被判为高质量；字段依据固定 [pdfx CLI cmd_quality](https://github.com/ScholarWorkflow/pdf-processing-core/blob/3444dca0e0b84f46d1839ab5c707afa78e23d3a7/lib/pdfx/cli.py)，只查对应路径、单页和质量摘要。

## 5. T3：OCR 固定接线与结果复用

读取安装的 `bin/vision-glance`，核对它 exec 的绝对程序来自固定 `base-skills@3ab2ac188e625b8a8ae37b5fa318c579787c3d1e` 的 `apps.aarch64-darwin.vision-glance.program`，转发 `"$@"`，没有 ambient `python`/`glance`、uv/pip 或 checkout 路径。读取同次构建定义/共享 metadata，确认直接 agentDependencies 为 vision-tools 且 launcher 的 Nix 引用保留 OCR app closure。角色 OCR 命令应指向安装 skill 的同一 wrapper。

上游 [PR #8](https://github.com/ScholarWorkflow/base-skills/pull/8) 与其 [计划/结果记录](https://github.com/ScholarWorkflow/base-skills/blob/3ab2ac188e625b8a8ae37b5fa318c579787c3d1e/plan/issue-7-nix-packages.md) 已覆盖 vision 包资源和固定 runtime 的相关安装/本地动作；本轮复用未受影响部分，不重复 OCR、视觉功能或 browser 测试。该历史记录不是 live OCR 模型通过的证据，T3 也不作此声明。

## 6. 失败、复用与交接

每条命令检查退出码，非零停止受影响项并保留 stdout/stderr；不得以随后成功的 jq/清理覆盖失败。只有下载的暂态外部故障可在版本/输入/配置不变时重试一次；产品命令失败先判原因，不改输入或预期求通过。持续不可达/缺信息记录无法判断，停止无新信息重试。

记录产品 SHA、共享固定版本、平台、命令、T1–T3 的通过/业务失败/无法判断/未执行、必要输出路径与复用来源即可。未改 APM/uv/PEP 723/OpenCode 原件不触发全套重跑，文档或 SHA 变化本身不触发复验。配置/日志/产物留在仓库外 RUN，只交脱敏简短记录；不停止无关进程或接触生产数据。

下一负责人：独立 reviewer 检查候选全范围；产品实施后本地测试工程师补实际 SHA/路径并确认输出存在，再按已确认步骤执行；结果交第三关 reviewer。未实现入口、缺少前提和未执行项不得填为通过。
