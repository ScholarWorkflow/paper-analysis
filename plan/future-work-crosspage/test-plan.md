# 相邻跨页 future-work 引文：测试计划

- Test revision: CP-T1（候选）；对应 [CP-R1 执行计划](implementation-plan.md)。
- 必测范围来自用户 U3：两个相邻物理页的完整引文、可信页眉处理、OCR 更新、精确定位验证以及直接 contact 读取/显示；保持现有单页兼容。
- G1 必测清单：待正式确认；G2 步骤：待正式审核；G3 结果：未执行。以下命令是待实现后的执行步骤，当前 PR 只有文档，不宣称新测试已存在。

## 1. 唯一必测清单

| ID | 业务目标与输入 | 预期结果 | 足够的检查入口 |
| --- | --- | --- | --- |
| C1 | 相邻双页真实文本候选与保存。用已有 PyMuPDF 测试构造能力建立小 PDF：页 1 尾句以 `specialized` 结束无句末，页 2 正文以 `KGs.` 接续；在两个页顶放同一个运行页眉，单独放页码；正文另外放一处同样页眉文字。TOC 为空并以 --last-pages 0 准备，只让页 1 命中关键词选择，确保页 2 通过交界纳入 | 完整指定引文成为一条候选，排除边缘页眉而保留正文同文；两段原文/offset 能在保存页文本中直接定位，物理页为 1–2；validate/finalize 以及 full upgrade 均保留相同定位，schema2/v2，Markdown 显示 pp.1–2，其他正文不变 | 在现有 tests/test_future_work_cli.py 增加一个有上述固定期望的定向用例，走 prepare→validate→finalize 及用同一候选做 upgrade；检查实际 JSON/Markdown，不启动模型、不重复全文分析 |
| C2 | OCR 刷新保持出处。用 prepare 的同形 payload，将页 2 标为需 OCR，并提供同一 PDF 已识别的精确页文本；再替换页 1 文本，模拟两侧各自更新 | OCR 未齐不产生有效跨页项；merge 后只存在当前两端形成的候选，旧 quote/offset 均不残留；无法确认的边缘噪声不被臆删；不调用 OCR 服务或对旧缓存重新认证 | 在现有 tests/test_future_work.py 增加一个定向用例，直接断言 refresh/merge 返回的候选及现有 required 状态；使用已有单元夹具，不造 OCR 服务 |
| C3 | 正式来源验证及旧单页兼容。提交 C1 原样 quote/定位；其负例分别为改写 quote、把相邻第二页改成非相邻页、删除跨页定位只留 page；同 quote 的两个不同定位在 full 升级中未指明页码。另用既有单页 fixture 走保存 | 正确条目通过；列明的无来源/降级输入及歧义明确失败，不覆盖旧正式 sidecar；单页字段、schema1/v1、quote_id 和 p.N 展示不变 | 在现有 tests/test_future_work.py 添加定位验证的定向用例；复用 tests/test_future_work_cli.py::test_prepare_validate_finalize_checked_in_fixtures 检查旧单页。负例只覆盖本次新接口失败行为，不扩全边界组合 |
| C4 | contact 直接消费。把 C1 实际生成的一个 schema2 sidecar 和其匹配 analysis 作为输入，再以同一内容的单页 schema1 fixture 作兼容对照 | 新版 load_sidecar 接受正确版本/定位，gap 经过 build_gap_pool、当前有效选择/方向投影及生成展示后仍含双页并显示 pp.1–2；不降级为第一页，不改变 gap id。旧 schema1 继续原行为；错误 page_end/segments 对应关系拒绝。若搭配旧 contact，明确记为未接入而非通过 | contact 的现有 Python unittest 模式中增加一个定向消费契约用例，调用真实 loader/投影/render，直接断言目标字段与文本；不运行全教授流程、style model 或业务重评 |

C1 的两种 writer 需要各一次，因为 finalize 与 full upgrade 是分别改变的正式入口；共用同一 prepared/输入，不重复安装、OCR 或模型调用。C4 只证明新增跨页接口的直接接入，不恢复旧基础迁移欠测，也不包含 contact U1/U5/PR91 的测试。

## 2. 实现前测试交接

本地测试工程师按以下目标在上述现有模块中实现测试，不新增自建判定器/采集器。为了可执行且不误跑全仓，拟采用以下 node 名；若实现者采用等价名称，在同一计划更新命令映射即可，不重开未变目标：

- paper `tests/test_future_work_cli.py::test_crosspage_prepare_validate_finalize_upgrade`：C1，使用 pytest tmp_path，保留指定输出目录中的 analysis.md 与 sibling sidecar 供 C4 一次复用。
- paper `tests/test_future_work.py::FutureWorkTests::test_crosspage_ocr_refresh`：C2。
- paper `tests/test_future_work.py::FutureWorkTests::test_crosspage_location_validation`：C3 新定位部分；旧单页沿用既有 CLI test。
- contact `.apm/skills/professor-contact/tests/test_future_work_crosspage_contract.py` 中 `CrosspageConsumerTests.test_crosspage_and_legacy_consumption`：C4；用仓库既有模块加载/fixture 方法导入 contact_state，不增加应用入口或测试框架。

C1 通过环境变量 `CROSSPAGE_OUTPUT_DIR` 把该次真实 producer 输出保存到运行目录，这是测试产物位置而非产品行为覆盖。C4 通过 `CROSSPAGE_INPUT_DIR` 读取同一目录中的 analysis.md / analysis.md.future_work.json；测试 fixture 应让 expected_analysis 与实际 sibling 绑定一致。只有 C1 成功且消费端实现就绪才运行 C4。不要手工改 sidecar 让跨仓用例通过；C3/C4 的明确负例在测试自己的临时副本中构造。

## 3. 执行 recipe（实现完成后使用）

前提：正式审核的本计划、已实现对应 node 的 paper 提交，以及含 §3 消费端配套的 contact 提交。记录两个实际 SHA。Python >=3.11，复用仓库既有 uv 环境和缓存；这是纯确定性产品函数/CLI 检查，无 Zotero/MCP/模型/浏览器/网络业务调用。不要创建干净安装消费者或重新跑 Nix 构建来证明这些目标。

在 bash 运行；只替换两个 checkout 绝对路径为本次实际代码仓库。不能把云端旧路径当成本机路径。

```bash
set -euo pipefail
PAPER=/absolute/path/to/paper-analysis
CONTACT=/absolute/path/to/professor-contact
RUN="$(mktemp -d /tmp/paper-crosspage.XXXXXX)"
export CROSSPAGE_OUTPUT_DIR="$RUN/producer"
mkdir -p "$CROSSPAGE_OUTPUT_DIR"
cd "$PAPER"
git rev-parse HEAD
# 复用已具备 locked 依赖的环境；确实缺依赖时才执行 uv sync --locked。
uv run --locked pytest -q \
  tests/test_future_work_cli.py::test_crosspage_prepare_validate_finalize_upgrade \
  tests/test_future_work.py::FutureWorkTests::test_crosspage_ocr_refresh \
  tests/test_future_work.py::FutureWorkTests::test_crosspage_location_validation \
  tests/test_future_work_cli.py::test_prepare_validate_finalize_checked_in_fixtures \
  2>&1 | tee "$RUN/paper-results.txt"
```

测试 node 尚未实现、依赖不可用等属于无法执行/未执行，不可用空选择或 skipped 冒充通过。C1–C3 可先独立完成；contact 配套未完成时 C4 标为待上游/未执行，保留 producer 产物，不为等待重新跑 C1。

消费端就绪后，在同一 shell 使用上面的 RUN；换 shell 时设置为已记录的那个绝对路径，不新建假输入。

```bash
export CROSSPAGE_INPUT_DIR="$RUN/producer"
cd "$CONTACT"
git rev-parse HEAD
PYTHONPATH="$CONTACT/.apm/skills/professor-contact/tests${PYTHONPATH:+:$PYTHONPATH}" \
  python3 -m unittest \
  test_future_work_crosspage_contract.CrosspageConsumerTests.test_crosspage_and_legacy_consumption \
  2>&1 | tee "$RUN/contact-results.txt"
```

实现者须依仓库既有测试约定准备模块依赖；不得让 PYTHONPATH 指向替换的产品副本。上面的 PYTHONPATH 仅用于定位已提交的测试模块。若后续改成仓库既有等价命令，更新本节并保留同一 C4 目标，不增加整模块/全仓运行。

## 4. 结果、复用与停止

- 每项只记录实际两个产品/测试 SHA、命令、通过/业务失败/无法判断/未执行及相关输出路径，标准 pytest/unittest 输出足够。C4 尚未执行不能宣称跨仓完成。
- 当前表：C1 未执行；C2 未执行；C3 未执行；C4 未执行。尚无本功能正式测试结果；U2/U4 的 23/148 测试通过不证明跨页支持。
- 确定性测试失败先保留结果并定位；不改样例/放宽断言求通过。无外部业务服务，故不设置重复采样。依赖安装/环境错误修复后只继续受影响项；保留第一次失败。文档 SHA 变化不触发重跑。
- 本轮不读写私人论文库、不重跑报告里所有论文。原报告 PDF 若以后由用户提供，可按既有方法替换相应复现材料并确认受影响步骤；不把交付私人原件当新增合并前置，也不在未执行时声称其修复已证实。
- 正式可复用测试与合成夹具随实施入库；临时 PDF、配置、运行原始产物留在 RUN，不推远端。无需另建结果格式、来源认证或完整 trace。执行者保留所需结果后按普通临时目录管理，不把清理成功列为业务通过条件。

依据：[Test Engineer Rule](https://app.notion.com/p/3d80101a85f380d8a8f5ce528141e253)、[Project Consensus](https://app.notion.com/p/3d60101a85f3815a8c43f271f2b4d91d)。实现/测试计划作者只提交候选；正式计划与关口结论由审核记录给出。
