# Future-work 原文连续片段测试计划

## 版本与关口

- Requirement: FW-SPAN-R1；Execution plan: FW-SPAN-EP2 (`execution-plan.md`)；Test plan: FW-SPAN-TP2。
- Baseline: `eceade6b6d22a6114ecdd99b5a0c358869dfc798`。
- Gate 1 测试范围：独立 reviewer 对 TP2 APPROVED（2026-10-22 17:25 UTC，由主协调器转达）。
- Gate 2 完整 recipe：独立 reviewer APPROVED（2026-10-22 17:30 UTC，由主协调器转达）；22页例使用 last_pages=3 与用户条件一致。
- Gate 3 结果：NOT RUN。作者不自授 APPROVED/PASS；pytest 原始结果与独立审核结论分开。

## 1. 范围上界

只验证连续原文定位直接改变的行为、拒绝路径、OCR 页复用及既有 sidecar/facts 兼容。复用现有测试 runner 和 fixtures，不运行模型、外部 OCR、Zotero、Contact 全流程、Nix 构建或安装回归。用户原 PDF 不在测试输入中；合成例不称为用户论文复现。

## 2. 必测清单

1. 候选之外的真原文：合成 22 页可读 PDF，第 18 页含 `in the future` / `we are planning to`、无目录且不命中现有短语，末尾三页无该句。证明 p18 未入 candidates，但 source_pages 完整，upgrade 成功且 quote/page/fingerprint 正确。不得通过改 last-pages 或词表制造通过。
2. 连续片段：同页两句作为一条引用成功；相邻页跨页句在中间有按计划可识别的页码/重复边缘行时成功，page=start，source 保留范围，两个片段的原文位置可核查。例子同时含真实行末断词，确保仅有据规范化。
3. 错误仍拒绝：以同一小 PDF 为输入，拒绝原文不存在/词义改写、跳过正文中间句（将被跳句放在页边区域，证明仅在8%区域或重复并不能把正文当噪声删掉）、错误起始页或非相邻页拼接、普通行内连字符被删除，以及外传 PDF digest 与 prepared 不一致。失败前后 analysis/sidecar 无成功写入。这些是新增定位直接相关的反例，不扩展无关边界矩阵。
4. 坏页复用：在现有 OCR merge 测试中核对 source_pages 随该坏页 OCR 同步更新，质量未解决不能从坏文字保存；额外非候选坏页可用已获得的页文本 merge，其他好页不变。测试用明确模拟 OCR 文本，不调用识别服务，不声称 OCR 准确率测试。
5. 兼容：保留原 candidates-only CLI 成功入口；既有正常单句以及真实行末断词的单candidate引用保留原candidate规范quote/ID，而不是随传入quote写法变化；新 source-backed sidecar schema=1 / extractor=future-work-v1 / 旧 item 字段正常，被现有 facts.finalize 接受并只注入该 ID。旧已存在 sidecar 不由本功能批量重写。用现有 facts 测试确认错 PDF 链拒绝，不另造 Contact 判定器。

对应入口：在 `tests/test_future_work.py` 添加 1–4 的必要用例并保留原单句/OCR基线；`tests/test_future_work_cli.py` 保留旧 CLI 入口并添加一次 source-backed upgrade→facts 的真实子进程链；`tests/test_facts.py` 复用既有 ID/指纹覆盖，不扩展 facts 产品功能。

## 3. 执行 recipe

前提：Gate 1/2 独立通过；记录实际执行 commit SHA、Python/uv 版本、Linux 平台。仅使用云端临时目录，不访问用户论文目录或 Mac。fixture PDF 由测试内 PyMuPDF 生成，既有 binary fixture 从仓库读取；代码不会下载用户论文或访问模型服务。

本次现存云端环境包元数据与 uv.lock 一致：pytest 8.4.2、pymupdf 1.28.2、scholar-workflow-pdfx 0.1.0；使用其 Python 只读复用依赖，不同步或改写该环境。

一次必要预检：确认工作树/HEAD 为审核目标、目标测试文件存在、既有锁定开发环境可用。优先复用已有环境，不反复创建或同步；若依赖缺失，只按仓库既有 `uv sync --locked` 安装锁定依赖，记录发生的准备动作，不将环境准备失败伪称产品失败。不得改 uv.lock、降级断言或替换依赖来取得通过。

正式唯一主命令（仓库根目录）：

```sh
/workspace/shared/paper-sentence-fix/.venv/bin/python -m pytest -q tests/test_future_work.py tests/test_future_work_cli.py tests/test_facts.py
```

以 shell 将 stdout/stderr、退出码、实际 HEAD、平台及时间保存在 `/tmp` 下本次唯一 run 目录，保留每次尝试，不覆盖失败日志。现有 pytest 的断言和退出码为结果来源，不新增收集框架。测试代码只在 pytest 临时目录生成 PDF、prepare、分析和 sidecars。

验收：命令 exit 0 且上述目标断言全部执行通过；记录实际数量，不预编 PASS。failure 按产品缺陷/测试问题/环境阻塞分类；只在修复相关原因后重跑受影响入口，不因为计划文档 SHA 或普通重读重复测试。若运行受阻，结果标 BLOCKED 并给缺少条件，不改为通过。

## 4. 独立静态检查与结果记录

独立 reviewer 对完整 diff 核对：没有模糊匹配、正文跳删、质量绕过；只相邻页；source/ID/schema 与现有 facts 消费兼容；agent 不指示重新 OCR 可读文字；没有旧 sidecar 批处理。静态检查不要求另建自动判定器。

结果填写：实际提交、环境、执行命令、原始日志位置、真实退出码和断言结果、偏差/限制。目前均 NOT RUN。完成后在本文件最小更新结果及审核链接；敏感输入和大体积日志不提交仓库。若 reviewer 要求新增测试，必须对应上述需求或新发现的直接风险，不恢复全流程回归。
