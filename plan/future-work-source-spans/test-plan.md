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

前提：Gate 1/2 独立通过；记录实际执行 commit SHA、Python/uv 版本、Linux 平台。仅使用云端临时目录，不访问用户论文目录或 Mac。fixture PDF 由测试内 PyMuPDF 生成，既有 binary fixture 从仓库读取；代码不会下载用户论文或访问模型服务。

TP2 记录的既有云端环境包元数据与当时 uv.lock 一致：pytest 8.4.2、pymupdf 1.28.2、scholar-workflow-pdfx 0.1.0。若该环境仍适用，只读复用其依赖，不同步或改写该环境；该历史记录不保证路径在本次运行时仍存在。

一次必要预检：确认工作树/HEAD 为审核目标、目标测试文件存在、锁定开发环境可用，并将 `TEST_PYTHON` 设置为实际确认可用的解释器绝对路径。优先复用仍可用且依赖适配的 `/workspace/shared/paper-sentence-fix/.venv/bin/python`；若该环境不可用，只在当前目标仓库根目录按既有 `uv sync --locked` 准备锁定依赖，然后将 `TEST_PYTHON` 改为该次同步实际创建的解释器（默认 `$PWD/.venv/bin/python`；如已有 `UV_PROJECT_ENVIRONMENT` 配置，则使用其实际环境路径下的 `bin/python`）。两个准备分支择一，不重复安装，不改写他人的已有环境。记录实际解释器路径与发生的准备动作；准备失败即标记环境阻塞，不启动正式测试，不伪称产品失败。不得改 uv.lock、降级断言或替换依赖来取得通过。

正式唯一主命令（仓库根目录）：

```sh
"$TEST_PYTHON" -m pytest -q tests/test_future_work.py tests/test_future_work_cli.py tests/test_facts.py
```

以 shell 将 stdout/stderr、退出码、实际 HEAD、平台及时间保存在 `/tmp` 下本次唯一 run 目录，保留每次尝试，不覆盖失败日志。现有 pytest 的断言和退出码为结果来源，不新增收集框架。测试代码只在 pytest 临时目录生成 PDF、prepare、分析和 sidecars。

验收：命令 exit 0 且上述目标断言全部执行通过；记录实际数量，不预编 PASS。failure 按产品缺陷/测试问题/环境阻塞分类；只在修复相关原因后重跑受影响入口，不因为计划文档 SHA 或普通重读重复测试。若运行受阻，结果标 BLOCKED 并给缺少条件，不改为通过。

## 4. 独立静态检查与结果记录

独立 reviewer 对完整 diff 核对：没有模糊匹配、正文跳删、质量绕过；只相邻页；source/ID/schema 与现有 facts 消费兼容；agent 不指示重新 OCR 可读文字；没有旧 sidecar 批处理。另核对 agent/skill：保存的本地 PDF full 不再限制未来工作的章节来源，仅摘要输入仍限摘要尾部；作者明确性及语义完整性继续由现有模型判断。full 复用已有三路分析，gap-only 仅补必要局部原文，不新增模型流水线或第二次全文阅读；保存顺序保持分析 Markdown→future-work sidecar→facts sidecar。本项只检查受影响指令与接线，不运行模型或收集调用轨迹。静态检查不要求另建自动判定器。

结果填写：实际提交、环境、执行命令、原始日志位置、真实退出码和断言结果、偏差/限制。目前均 NOT RUN。完成后在本文件最小更新结果及审核链接；敏感输入和大体积日志不提交仓库。若 reviewer 要求新增测试，必须对应上述需求或新发现的直接风险，不恢复全流程回归。
