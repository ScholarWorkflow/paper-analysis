# Handoff 正文证据调用契约 — 执行计划

- Requirement revision: 用户 2026-10-26 05:05 UTC 批准两个普通流程 PR，准备双计划：候选只是线索，可从已读按页正文补充作者明确 future work，本地核验后保存；不重做总结、不上传 PDF。
- Plan revision: PA-HANDOFF-EP1；Proposed review status: pending。
- Baseline: `7b086ef361db54e2d3f6e333145a750ff56a48dc`（master）；下游 professor-contact `18fd48d1b6f2e26241c304d6acddb025297f08e4`。
- 唯一测试计划：[test-plan.md](test-plan.md)。本 PR 仅计划，不实施、不测试、不快合。
- 规则：[Plan Reviewer](https://app.notion.com/p/3e80101a85f3817a94cbc6eca1a76a5c)、[Test Engineer](https://app.notion.com/p/3d80101a85f380d8a8f5ce528141e253)、[Consensus](https://app.notion.com/p/3d60101a85f3815a8c43f271f2b4d91d)。

## 事实与真实缺口

本仓库原 `plan/future-work-source-spans/` 已实现正文证据支持，不能重复开发：

| 决策 | 固定版本事实与位置 |
|---|---|
| 复用原文校验器 | baseline `.apm/skills/paper-analysis/scripts/future_work.py` 的 `load_evidence/SourceLocator/validate_items/finalize`：`--candidates` 可读取完整 `prepare.json`；含 `source_pages` 时验证连续正文，只有 candidates 时保留旧精确候选行为。 |
| 不恢复候选或章节白名单 | baseline `.apm/agents/paper-analysis.agent.md` Step 3/4、skill 的 Saved PDF full-mode：允许任意正文中作者明确待做事项；一至两句、保留条件；同一次分析三路角色，不另跑模型。 |
| 兼容现有身份 | helper 只接受 `id/quote/translation_zh/source/page`；id 可省略，程序依据规范引文生成；显式页码必须匹配，`finalize` 核对 prepare PDF SHA。 |
| 下游负责接线 | contact baseline `stage2_chatgpt_handoff.py` 的 `_instructions/_finalize_future_work` 强制 exact-items-v1 候选集并把 candidates.json 传给 helper。已有上游正文能力在此被截断。 |

上游 SKILL 目前围绕本地 PDF full/gap-only 说明能力，缺少供外部文本 handoff caller 直接引用的完整简短调用契约。此次只明确该边界与示例，保留现有算法与测试实现。

实际材料只读核对（2026-10-26，未运行校验或重跑模型）：批次 TB5Z8XNL 的 prepare 已有全页文字，候选仅物理页 4/27/28/29，正文 24–25 有作者待研究事项；U8PH7T7A 的候选仅 16–18，正文 15 明写 “Part of our future work will add robustness against outliers to our proposed method.”，其旧 prepare 缺 `source_pages`。这是调用/旧准备材料的两类限制，不能据此判论文没有 future work。材料位于已交付 20261026 奈良结果及原轻量包；不把私人论文或全批产物提交仓库。

## 方案、owner 与接口

1. 在 `.apm/skills/paper-analysis/SKILL.md` 添加独立、简短的“外部 PDF 文本 handoff caller”契约段，README helper 索引链接该段；agent 只在确有跨入口矛盾处链接，不复制完整规则。此处明确网页只做现有角色的语义分析及草稿，完整文本来源仍是本地 PDF 的准备证据；普通任意 TXT 输入不会自动取得 PDF-backed sidecar 权利。
2. 外部返回仍为 `{"items":[{"quote":"完整连续原话","translation_zh":"中文翻译","source":"章节","page":15}]}`，`id` 可省略，不要求 candidate ID。`page` 是从 1 开始的物理 PDF 页；跨页仅沿用现有相邻两页，起始页填 page，正式范围由 helper 写入 source。语义仍由原分析角色判断，不能从局限性推断作者未明确承诺的计划。
3. 本地 caller 对同一 PDF 的完整 prepare 调用现有命令：`future_work.py validate --items items.json --candidates prepare.json`，随后 `finalize --analysis analysis.md --items items.json --candidates prepare.json --patch --pdf-sha256 <original SHA>`。使用安装提供的固定入口；无固定入口沿用原 uv 方式。只传候选文件不能激活正文定位。
4. 本地 caller 先验证原 PDF 与绑定 hash；可复用同源完整 prepare。旧 prepare 缺页级正文时，用现有 `prepare` 在原 PDF 路径生成独立临时新版材料，复用授权且指纹校验通过的页级 OCR，经现有 `merge-ocr` 合并。不得把任意运输文本直接包装成可信 prepare，不覆盖输入旧 JSON、不复制 PDF。不为匹配失败重新 OCR 可读页。未取得必要可信页文字时明确未完成，不写伪造 sidecar。
5. 原文匹配继续沿用 SourceLocator 的 NFKC/空白及真实行末断词处理、质量门禁、单页/一处相邻接缝限制；不加模糊匹配或跨任意页拼接。旧 candidates-only CLI、有效候选 quote/ID、sidecar schema/facts join 均不变。

选择文档级明确公共 caller 契约，替代方向是新增 `--source` 参数或另写校验器；现有 CLI 已满足需要，新增参数/算法没有业务收益，故不采用。contact 负责传输版本、prepare 与 paper.txt 一致性、导入接线及安装事务；paper-analysis 负责语义指导与原文证据 helper，fixtures 不补偿产品。

## 实施顺序与影响

执行计划及测试设计正式审核后，再提交上述精简说明。contact 可并行准备自己的计划，实际接入以拥有上述现存 source_pages 接口的固定 paper-analysis 输出为据；不以本 PR 文档 SHA 作为重跑上游算法的理由。

intended_change：跨仓库 caller 能准确区分正文证据和候选提示，并调用既有接口。preserved_behavior：算法、结果格式、原 PDF 身份、纯文本/摘要边界、原 OCR 授权、旧 sidecar/CLI；prohibited_side_effect：新模型任务、论文批量重跑、原 PDF 复制、清空或重写历史输出、绕过质量/哈希/引用校验。

关键反例：旧 candidates-only 不能声称已具备正文；错页/改写原话不能靠缺 candidate ID 获准；已有源 hash 不匹配不能靠新文字运输 hash 替代。现有 helper 已承担拒绝行为，本计划只明确 caller 用法。无关键未知假设；没有新增状态、并发、生命周期或清理机制。公共正文能力已获先前需求及本轮用户授权，具体 helper 名称和布局仍为实现细节。

下一负责人：计划 reviewer 完整复核 P1–P4；文档实施者完成说明；测试 reviewer 按同目录设计审查说明一致性；未执行任何正式测试，不声明 APPROVED/PASS。
