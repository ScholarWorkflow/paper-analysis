# Future-work 原文连续片段测试计划

## 版本与关口

- Requirement: FW-SPAN-R1 及当前 EP4 记录的行为约定；Execution plan: FW-SPAN-EP4 (`execution-plan.md`)；Test plan: FW-SPAN-TP4（候选待审）。
- Baseline: `eceade6b6d22a6114ecdd99b5a0c358869dfc798`。
- Gate 1 测试范围：独立 reviewer 对 TP2 APPROVED（2026-10-22 17:25 UTC，由主协调器转达）。
- Gate 2 完整 recipe：独立 reviewer APPROVED（2026-10-22 17:30 UTC，由主协调器转达）；22页例使用 last_pages=3 与用户条件一致。
- TP3 修订：用户于 2026-10-23 授权补齐章节来源/上下文复用静态检查、重复引文首次定位、新 prepared 入口与连续 OCR 合并状态，以及实际解释器恢复路径。只复核这些受影响目标和 recipe；未受影响的 TP2 目标及步骤沿用上述历史审核，不据此推定 TP3 已获批准。
- TP4 本轮修订：依据 [TP3 审核意见](https://github.com/ScholarWorkflow/paper-analysis/pull/23#pullrequestreview-5625681001)，仅澄清第3项失败后的文件状态及现有子进程检查的非候选输入、无兄弟候选文件和指纹继承条件；不新增测试类别。复核限这些受影响预期及步骤，其他目标、检查方法和 recipe 保持不变，不由作者推定当前关口通过。
- 执行计划正式审核：[EP4 审核记录](https://github.com/ScholarWorkflow/paper-analysis/pull/23#issuecomment-6360066817)（对应 `9ef70ebeb13fb84f142d2823b4050d0e7a3c7d28`）；仅为方案审核，不代表测试通过。
- Gate 3 结果：NOT RUN。作者不自授 APPROVED/PASS；pytest 原始结果与独立审核结论分开。

## 1. 范围上界

只验证连续原文定位直接改变的行为、拒绝路径、OCR 页复用及既有 sidecar/facts 兼容。复用现有测试 runner 和 fixtures，不运行模型、外部 OCR、Zotero、Contact 全流程、Nix 构建或安装回归。用户原 PDF 不在测试输入中；合成例不称为用户论文复现。

## 2. 必测清单

1. 候选之外的真原文：合成 22 页可读 PDF，第 18 页含 `in the future` / `we are planning to`、无目录且不命中现有短语，末尾三页无该句。证明 p18 未入 candidates，但 source_pages 完整，upgrade 成功且 quote/page/fingerprint 正确。不得通过改 last-pages 或词表制造通过。
2. 连续片段：同页两句作为一条引用成功；相邻页跨页句在中间有按计划可识别的页码/重复边缘行时成功，page=start，source 保留范围，两个片段的原文位置可核查。例子同时含真实行末断词，确保仅有据规范化。复用同一合成材料放置重复引文：无明确页码时选择物理页码、页内偏移最早的有效准确匹配；通过现有定位结果核对位置，不为测试新增公开字段或判定器。显式错误起始页仍由第3项覆盖。
3. 错误仍拒绝：以同一小 PDF 为输入，拒绝原文不存在/词义改写、跳过正文中间句（将被跳句放在页边区域，证明仅在8%区域或重复并不能把正文当噪声删掉）、错误起始页或非相邻页拼接、普通行内连字符被删除，以及外传 PDF digest 与 prepared 不一致。失败状态按实际受检入口判断：validate 只校验，不改写分析或 sidecar；finalize/upgrade-full-sidecar 的校验失败不能写出对应的有效 sidecar，既有分析文件不因失败而被修补。保存的本地 PDF full 已先写入的初始 Markdown 可以保留，不能要求失败后不存在分析文件；流程仍须报告未完成，不继续生成 facts sidecar，也不报告三文件完成。沿用本项既有拒绝场景观察对应状态，不在每个入口重复全部反例。这些是新增定位直接相关的反例，不扩展无关边界矩阵。
4. 坏页复用：在现有 OCR merge 测试中核对 source_pages 随该坏页 OCR 同步更新，质量未解决不能从坏文字保存；额外非候选坏页可用已获得的页文本 merge，其他好页不变。在同一 prepared 上连续合并两个实际引用的额外坏页；第二次合并后，第一次已解决页的文字与已解决状态仍保留，其他页不变。测试用明确模拟 OCR 文本，不调用识别服务，不声称 OCR 准确率测试。
5. 兼容：保留原 candidates-only CLI 成功入口；既有正常单句以及真实行末断词的单candidate引用保留原candidate规范quote/ID，而不是随传入quote写法变化；新 source-backed sidecar schema=1 / extractor=future-work-v1 / 旧 item 字段正常，被现有 facts.finalize 接受并只注入该 ID。旧已存在 sidecar 不由本功能批量重写。用现有 facts 测试确认错 PDF 链拒绝，不另造 Contact 判定器。

对应入口：在 `tests/test_future_work.py` 添加 1–4 的必要用例并保留原单句/OCR基线；`tests/test_future_work_cli.py` 保留旧 CLI 入口并添加一次 source-backed upgrade→facts 的真实子进程链；`tests/test_facts.py` 复用既有 ID/指纹覆盖，不扩展 facts 产品功能。复用第1项合成 PDF 第18页的非候选引文及含 source_pages 的 prepare.json，在现有 CLI fixture 中分别检查 validate 与 finalize 的正常入口；finalize 不传 `--pdf-sha256`，核对成功结果、引文页码和从 prepared 采用的指纹。上述一次 upgrade→facts 子进程链在 prepared 同目录不提供 `candidates.json`，用同一非候选引文验证 upgrade-full-sidecar 并核对结果、页码和指纹，不另加第二条链。连续匹配规则及反例由已有定位用例覆盖，不在各 CLI 重复整套矩阵。

## 3. 执行 recipe

本轮仅准备测试资产；下列正式命令留给本地执行工程师，未在本轮运行。正式规则为 [Project Consensus](https://app.notion.com/p/3d60101a85f3815a8c43f271f2b4d91d) 与 [Test Engineer Rule](https://app.notion.com/p/3d80101a85f380d8a8f5ce528141e253)。本节补齐 TP4 的操作步骤，不变更第2节目标、预期和范围，不自授第一、第二关口通过。

前提：Gate 1/2 独立通过；记录实际执行 commit SHA、Python/uv 版本、Linux 平台。仅使用云端临时目录，不访问用户论文目录或 Mac。fixture PDF 由测试内 PyMuPDF 生成，既有 binary fixture 从仓库读取；代码不会下载用户论文或访问模型服务。

TP2 记录的既有云端环境包元数据与当时 uv.lock 一致：pytest 8.4.2、pymupdf 1.28.2、scholar-workflow-pdfx 0.1.0。若该环境仍适用，只读复用其依赖，不同步或改写该环境；该历史记录不保证路径在本次运行时仍存在。

一次必要预检：确认工作树/HEAD 为审核目标、目标测试文件存在、锁定开发环境可用，并将 `TEST_PYTHON` 设置为实际确认可用的解释器绝对路径。优先复用仍可用且依赖适配的 `/workspace/shared/paper-sentence-fix/.venv/bin/python`；若该环境不可用，只在当前目标仓库根目录按既有 `uv sync --locked` 准备锁定依赖，然后将 `TEST_PYTHON` 改为该次同步实际创建的解释器（默认 `$PWD/.venv/bin/python`；如已有 `UV_PROJECT_ENVIRONMENT` 配置，则使用其实际环境路径下的 `bin/python`）。两个准备分支择一，不重复安装，不改写他人的已有环境。记录实际解释器路径与发生的准备动作；准备失败即标记环境阻塞，不启动正式测试，不伪称产品失败。不得改 uv.lock、降级断言或替换依赖来取得通过。

以下命令均在目标 Linux 工作树根目录执行。先确认第一、第二关口适用于 TP4，并核对本轮测试资产与随后完成的 EP4 产品实现已经在同一待测提交中；当前 `d56b11656897794665ae309900f3e6240c43fb46` 只有计划，不能作为已实现版本。创建独立输出目录，设定仅供本次用例写入的临时目录：

```sh
RUN_DIR=$(mktemp -d /tmp/fw-span-test.XXXXXX)
export RUN_DIR
mkdir "$RUN_DIR/tmp"
export TMPDIR="$RUN_DIR/tmp"
git rev-parse HEAD > "$RUN_DIR/commit.txt"
git status --short > "$RUN_DIR/worktree.txt"
uv --version > "$RUN_DIR/uv-version.txt"
uname -s > "$RUN_DIR/platform.txt"
```

平台必须为 Linux；若不是，记录环境阻塞并停止。先直接检查已有解释器能否运行，不先搜索路径。仅检查解释器与依赖元数据，不导入产品或调用用例：

```sh
TEST_PYTHON=/workspace/shared/paper-sentence-fix/.venv/bin/python
export TEST_PYTHON
uv run --no-project --no-python-downloads --python "$TEST_PYTHON" python -c '
import importlib.metadata, json, platform, sys
print(json.dumps({"python": sys.version, "executable": sys.executable,
    "platform": platform.system(), "packages": {name: importlib.metadata.version(name)
    for name in ("pytest", "pymupdf", "scholar-workflow-pdfx")}}))
' > "$RUN_DIR/precheck-existing.json" 2> "$RUN_DIR/precheck-existing.err"
```

将上述成功输出交给 `jq` 读取字段，与锁文件中相应包比较；不将进程可启动等同依赖适配。若命令失败，或版本与锁定依赖不符，则该环境不可复用，保留错误输出，在当前仓库根目录执行一次既定准备分支：

```sh
uv sync --locked > "$RUN_DIR/sync.log" 2>&1
```

同步失败立即停止。成功后以同步输出及实际 `UV_PROJECT_ENVIRONMENT` 配置为依据设置 `TEST_PYTHON`；默认是 `$PWD/.venv/bin/python`，不假定是历史路径。重新执行上面的纯元数据检查，输出另存为 `$RUN_DIR/precheck-prepared.json` 和 `$RUN_DIR/precheck-prepared.err`，不覆盖第一次记录。成功的那份文件为后续 `ENV_RECORD`；以其 `executable` 字段确认解释器的实际绝对路径：

```sh
# 按实际采用的准备分支，二选一，不同时执行。
ENV_RECORD="$RUN_DIR/precheck-existing.json"
# ENV_RECORD="$RUN_DIR/precheck-prepared.json"
TEST_PYTHON=$(jq -er '.executable' "$ENV_RECORD")
export TEST_PYTHON
jq '{python, executable, platform, packages}' "$ENV_RECORD"
yq -p toml -o json '.package' uv.lock | jq '[.[] | select(.name == "pytest" or .name == "pymupdf" or .name == "scholar-workflow-pdfx") | {name, version}]' > "$RUN_DIR/locked-packages.json"
```

仅当元数据为 Linux、解释器满足 Python >=3.11，且三个包与当前锁文件一致时继续。确认 `tests/test_future_work.py`、`tests/test_future_work_cli.py`、`tests/test_facts.py` 和原有 `tests/fixtures/` 输入就位。测试在 pytest 临时目录生成合成 PDF 与准备文件；使用当前解释器启动子进程，不访问模型或识别服务，不加载用户配置，不另需密钥。无额外用户授权操作；若后来引入外部服务，该操作不在本 recipe 授权内。

正式唯一主命令（仓库根目录，经 `uv run` 使用已确认的解释器，不同步依赖）：

```sh
date -u +%Y-%m-%dT%H:%M:%SZ > "$RUN_DIR/start.txt"
uv run --no-project --no-python-downloads --python "$TEST_PYTHON" python -m pytest -q tests/test_future_work.py tests/test_future_work_cli.py tests/test_facts.py > "$RUN_DIR/pytest.log" 2>&1
TEST_EXIT=$?
printf '%s\n' "$TEST_EXIT" > "$RUN_DIR/exit-code.txt"
date -u +%Y-%m-%dT%H:%M:%SZ > "$RUN_DIR/end.txt"
```

退出码须紧接正式命令记录；若当前 shell 启用了遇错退出，执行前对该命令关闭该选项，防止失败日志缺少退出码。主命令预计少于60秒；若超过60秒，沿用执行工具的会话编号等待，保留同次日志，不再次启动。5分钟仍无结束或进度时由执行负责人检查并终止该次进程，记录未完成，不当作业务断言失败。独立静态检查依第4节人工完成，不新增判定脚本。外部故障不自动重试（最多一次初次尝试）；依赖、测试准备或产品问题修复后由对应负责人决定受影响入口的复验，每次使用新的 `/tmp/fw-span-test.XXXXXX` 目录并记录原因，不改变输入、断言或运行范围求通过。

以 shell 将 stdout/stderr、退出码、实际 HEAD、平台及时间保存在 `/tmp` 下本次唯一 run 目录，保留每次尝试，不覆盖失败日志。现有 pytest 的断言和退出码为结果来源，不新增收集框架。测试代码只在 pytest 临时目录生成 PDF、prepare、分析和 sidecars。

验收：命令 exit 0 且上述目标断言全部执行通过；记录实际数量，不预编 PASS。failure 按产品缺陷/测试问题/环境阻塞分类；只在修复相关原因后重跑受影响入口，不因为计划文档 SHA 或普通重读重复测试。若运行受阻，结果标 BLOCKED 并给缺少条件，不改为通过。

## 4. 独立静态检查与结果记录

独立 reviewer 对完整 diff 核对：没有模糊匹配、正文跳删、质量绕过；只相邻页；source/ID/schema 与现有 facts 消费兼容；agent 不指示重新 OCR 可读文字；没有旧 sidecar 批处理。另核对 agent/skill：保存的本地 PDF full 不再限制未来工作的章节来源，仅摘要输入仍限摘要尾部；作者明确性及语义完整性继续由现有模型判断。full 复用已有三路分析，gap-only 仅补必要局部原文，不新增模型流水线或第二次全文阅读；保存顺序保持分析 Markdown→future-work sidecar→facts sidecar。本项只检查受影响指令与接线，不运行模型或收集调用轨迹。静态检查不要求另建自动判定器。

结果填写：实际提交、环境、执行命令、原始日志位置、真实退出码和断言结果、偏差/限制。目前均 NOT RUN。完成后在本文件最小更新结果及审核链接；敏感输入和大体积日志不提交仓库。若 reviewer 要求新增测试，必须对应上述需求或新发现的直接风险，不恢复全流程回归。

## 5. 本轮测试准备交接（2026-10-23）

- 目标：EP4 / TP4；起始提交 `d56b11656897794665ae309900f3e6240c43fb46`，产品基线 `eceade6b6d22a6114ecdd99b5a0c358869dfc798`。本轮只修改测试代码与本文件，不实现产品，不宣布 TP4 关口通过。
- 第1项：`tests/test_future_work.py::test_non_candidate_page_has_complete_sources_and_upgrades`；第2项：同文件的同页连续、相邻跨页、重复引文首次位置用例；第3项：同文件拒绝参数组、升级失败及指纹失败，并在 CLI 中检查 validate 失败不写文件；第4项：同文件连续两次额外坏页合并；第5项：保留原单句/OCR/旧 CLI 与 `tests/test_facts.py`，补单候选规范引文及 ID 兼容和一次非候选 upgrade→facts 子进程链。没有额外测试文件、采集器或新的通过条件。
- 公共合成输入函数留在现有 `tests/test_future_work.py`，由 CLI 用例复用；22页例无目录，末尾三页不含第18页原话，固定 `last_pages=3`。跨页例使用独立页眉/纯数字页码和真实断词；拒绝例保留页边重复正文。OCR 用明确模拟文字与质量状态，不调用识别服务。正式产物仍由产品入口产生，不在测试中补造成功 sidecar。
- 本次有限预检：`uv --version` 为 `0.12.22`；指定云端解释器实际调用退出码为 `2`，宿主为 Darwin，不能在此满足 Linux 执行条件。两份测试源码只做语法解析成功，格式检查无错误；未导入测试模块或运行用例。记录位于本次独立 `/tmp/pr23-test-precheck.PAt1zf`，不入库。没有在 Mac 安装测试依赖、生成业务样本或运行产品入口。下一执行者须按第3节在目标 Linux 环境复用有效解释器或执行 `uv sync --locked`；此为明确环境缺项，不记产品失败。
- 第一、第二关口：TP4 受影响部分仍待测试计划工程师复核；第三关口及正式用例均 `NOT RUN`。产品实现尚未交付，由本地执行工程师按 EP4 完成；不得把本轮准备审核写成产品或测试通过。
- 测试准备符合性审核：专用 `implementation_reviewer` 已只读核对起始提交及本轮三份改动、两份完整计划、三份完整测试文件、全部既有夹具、`pyproject.toml`、`uv.lock`、实际入口与预检记录。结论为**部分完成**：测试代码、执行步骤及交接已落实，未发现需要修改的明确测试资产偏差；Linux 环境仍受阻。未运行正式测试，不代替关口批准。
- 未完成项 `ENV-01`：本地执行工程师在目标 Linux 环境按第3节准备解释器及锁定依赖；`GATE-01`：测试计划工程师复核 TP4 受影响的第一、第二关口。两项分别处理，不增加测试或修改断言。后续由本地执行工程师完成 EP4 产品实现，在满足上述条件后执行唯一主命令，并交正式结果审核；本轮不宣称整个任务或业务测试已完成。
