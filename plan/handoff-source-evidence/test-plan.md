# Handoff 正文证据调用契约 — 测试计划与检查步骤

- Revision: PA-HANDOFF-TP1，配对 PA-HANDOFF-EP1；baseline `7b086ef361db54e2d3f6e333145a750ff56a48dc`。
- Proposed review status: pending；Gate1/Gate2 待独立审核，Gate3 未执行。本轮仅提交双计划。
- 范围依据为执行计划引用的用户需求、Test Engineer Rule 和 Project Consensus。

## 必测清单（验收上限）

| 目标 | 输入/场景 | 预期 | 足够的检查方式 |
|---|---|---|---|
| P1 caller 契约可直接使用 | 修改后的 SKILL/README 与当前 helper CLI | 引用完整 prepare，列明 item 字段及物理页、无 candidate ID 门槛；本地原 PDF 同源验证和失败语义明确 | 人工逐项核对改动及 CLI `main/load_evidence/validate_items/finalize` 源码 |
| P2 不破坏已有边界 | 新说明与 full/gap-only/纯文本边界、旧 CLI、同源 OCR 规则 | 不把任意 TXT 当 PDF，不增模型 pass；旧 candidates-only 仍受原限制，未获得页文字不能伪造成功 | 人工阅读相关段落及差异；引用现有源码和既有 source-spans 结果，不运行新算法回归 |

## 可执行步骤

1. 在本仓库目标分支读取执行计划、SKILL/README 最终 diff；记录实际提交及阅读时间。无需安装、模型、浏览器、用户 PDF 或外部服务。
2. 对 P1 按当前 CLI 参数及 item allowed/required fields 逐项核对示例；确认命令中的 `--candidates prepare.json` 并保留 `--pdf-sha256`。对照 helper SourceLocator 的实际物理页/连续范围及错误行为，不执行示例。
3. 对 P2 读新段落及 Saved PDF full-mode、Boundaries/Runtime 相邻相关说明，确认没有冲突和第二套语义要求。当前 `tests/test_future_work_cli.py::test_prepared_non_candidate_cli_entries_and_upgrade_to_facts` 已覆盖实际正文接口，`tests/test_future_work.py` 有同页/跨页/旧ID/错误页/质量和hash覆盖；它们是已有适用检查，文档改动不重跑、不宣称本轮通过。
4. 保存简短检查记录到本目录，列目标、位置、结果、未完成项；不需要新测试代码或判定器。若实现者发现产品行为要变，停止对应文档假设并修订受影响计划，不用测试扩大本 PR。

缺文件/无法访问时记无法判断并说明路径；修正文档仅重看受影响段落。保留初次问题及修正记录。没有网络重试或运行副作用；不要求安装矩阵、全仓回归、模型样本或批次重跑。独立 reviewer 确认 Gate1/2，实施后按此检查形成 Gate3，作者不自授批准。
