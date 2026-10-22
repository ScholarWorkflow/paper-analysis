# Future-work 原文连续片段校验执行计划

## 修订与状态

- Requirement revision: FW-SPAN-R1，用户于 2026-10-22 授权两份计划、开发及推送 PR。
- Plan revision: FW-SPAN-EP2。
- Repository baseline: `eceade6b6d22a6114ecdd99b5a0c358869dfc798` (master)。
- 独立执行计划审核：P1–P4 APPROVED，2026-10-22 17:25 UTC，经主协调器转达独立 reviewer 对 EP2 的结论。非作者自批。
- 唯一测试计划：同目录 `test-plan.md` (FW-SPAN-TP2)。实现前完成执行计划和测试范围独立审核；正式执行前完成 recipe 审核。

## 1. 有效需求和边界

规范性目标：关键词、目录、末尾页仅作为优先阅读提示，不能让已经在论文原文发现的真实 future-work 引文因未入候选集而无法保存。允许同页连续一至两句话和跨相邻两页的连续引文，同时保留逐字可回溯、PDF 同源、页码、质量门禁、稳定 ID 和现有 full/facts 消费契约。

用户提供的案例是 22 页 PDF 的第 18 页未被候选规则覆盖，同页两句被分别切成候选，跨页句受页眉/页码干扰。原 PDF 未提供；这是需求输入，不是本实现已经复现的结论。本次用最小合成 PDF 验证相同机制，不声称复现该论文。

非目标：不扩大关键词词典或末尾页数来假装解决机制问题；不增加模型判定、embedding、模糊相似度、通用解析框架、来源认证系统；不改 Zotero/Contact、Nix 安装器、全文分析业务；不批量重写旧 sidecar、不重跑旧正常分析；不为可读原文匹配失败重新 OCR。

## 2. 当前事实及决策依据

以下路径均相对本仓库，事实固定于 baseline，可用 `https://github.com/ScholarWorkflow/paper-analysis/blob/eceade6b6d22a6114ecdd99b5a0c358869dfc798/` 加路径查阅：

- `.apm/skills/paper-analysis/scripts/future_work.py`：`prepare` 已提取所有页文字并计算 PDF SHA256 / 全页质量，但仅保留筛选页面的逐句 candidates；`validate_items` 只接受候选 quote/page 完全相同；`upgrade_full_sidecar` 再依赖候选单句及同目录 candidates.json。修复 owner 因而是本 helper，而非 Contact。
- 同文件：ID = SHA256(NFKC + 空白归一化后的 quote)，正式 sidecar schema=1、extractor_version=future-work-v1、item 字段 id/quote/translation_zh/source/page。`match_quote` 旧路径无条件删除 `- `；新原文路径不沿用这个宽松规则。
- `.apm/agents/paper-analysis.agent.md`：原文引文最多两句，全文阅读与候选准备分离；full 保存调用 upgrade 后 facts；现有 PDF/OCR cache 已校验 fingerprint。
- `.apm/skills/paper-analysis/scripts/facts.py` 和 `tests/test_facts.py`：facts 使用 sidecar 的 ID，并校验 analysis / evidence_level / PDF fingerprint。本次不修改该消费契约。
- `tests/test_future_work.py`、`tests/test_future_work_cli.py`：已有 prepare / candidate 校验 / upgrade / OCR / CLI 测试，新增用例放这些现有入口，不另造测试框架。

因果链：候选白名单造成真引文不可保存 → 保留已提取全文页文本 → 以同一 prepared 的连续原文位置校验而不是候选成员关系 → 未命中启发式但真实存在的引文可保存，伪造或跳句仍失败。

## 3. 方案与接口

### 3.1 prepared 页级证据

`prepare.json` 保留现有字段并新增 `source_pages`：每页保存 1-based page、原始 text、可用于审计的页边缘文字排除区间；复用现有 page_quality 和 pdf_sha256，不建立第二套身份系统。新数据是临时准备产物，不是正式 sidecar schema 迁移。

页级文字来自现有 PyMuPDF 提取。必要的行位置来自同页文本布局信息，并映射回原始字符串位置；无法可靠映射的行不排除。顶部/底部各 8% 和跨页重复仅是噪声候选提示，不能直接授权删除。允许排除的必须是提取顺序最外侧连续页眉/页脚区间：独立文本块，几何上与正文块至少隔开一个该边缘块行高，且为独立纯数字页码或至少两页相同边缘区重复的完整相同行文本。出现正文交织、无法证明独立块/间隔、可能是正文或非最外侧区间时不排除，跨页定位失败也不放宽条件。排除区间保留原文和位置，不根据匹配能否成功反推页眉。此有限版面处理只用于跨页连接，不能删除同页句间文字。

候选文件/Markdown 和 selection 保留，语义明确降为提示。全页原文不会全部打印到 stdout；现有 prepare 短摘要保持。

### 3.2 精确连续定位

用同一个 helper 内的小型定位函数支撑 validate / finalize / upgrade。比较允许 NFKC 与空白折叠；仅原始行末或页末的连字符接下一行/页字母时提供去断词连字符的比较视图，不能删除普通 `- `。保留比较视图到原始字符区间的映射。

校验单位是同页连续片段，或 p 的末尾到 p+1 开头的连续片段。跨页片段必须两页都有正文贡献；只允许上述有版面依据的边缘噪声退出视图，不能跨非相邻页、跳过正文句子或删标点。沿用现有句子边界规则限制为最多两句，不引入语言模型或新的分句依赖。超出支持范围明确失败，不能自动放宽。

明确指定 page 的 item 只从该起始页定位；upgrade 从准备原文定位，若同一引文出现多处且原 Markdown 未给足页码，要求提供明确页码，不能随便认定。错误指出引文序号及失败类别，不把失败解释成“论文无 future work”。

source-backed canonical quote 规则：先在指定起始页证明输入 quote 是有效原文连续片段；若该片段与某个单 candidate 的有效原文片段完全相同（包括仅由真实行末断词造成的输入差异），保留那个 candidate 的规范 quote 和 ID，不改成输入者的断词写法。candidate 自身也必须通过同一原文定位，不能凭旧宽松字符串替换决定复用。多个不同 candidate 规范文本对应同一片段而无法唯一确定时明确拒绝而非猜测。没有对应单 candidate 的新 span 使用输入 quote 的既有 NFKC/空白规范化作为 canonical quote，ID 沿用现算法；translation/source 语义不改。正式 item 仍仅包含旧字段，page 为起始页。跨页范围写入既有自由文本 source，例如 `Conclusion (pp.18–19)`，不加新必需字段或 extractor_version。位置细节留在 prepare/校验输出，不要求 Contact 读取新字段。

### 3.3 调用和兼容

- `--candidates` 参数保持可用，但新 prepare.json 可作为完整证据输入。agent 的新流程传 prepare.json，而不是 candidates.json。
- 保留旧列表或仅 candidates 的输入为旧式“单条候选完全匹配”兼容路径，不使旧无原文产物获得新能力；不静默重建旧证据。
- 新 prepared 输入时，finalize 若提供 `--pdf-sha256`，必须与 prepared digest 一致；不提供时由 prepared 设置正式 fingerprint。禁止不同 PDF 的 fingerprint 与 source_pages 混用。旧 candidate-only 参数行为保持。
- upgrade 直接使用同一个 prepared 完成定位和 finalize，取消对兄弟 candidates.json 的隐式依赖。仍先要求 Markdown 存在，先完整验证再 patch/write。
- 旧单候选正常引用不改变 quote 和 ID。旧 sidecar 文件不扫描、不迁移、不批改；现有 facts 指纹/ID 连接不变。

### 3.4 质量和 OCR

全页 source_pages 中 untrusted/empty 文字不可直接变成已验证证据。prepare 的既有 selected required OCR 列表保持，不自动要求所有坏页 OCR。实际引用额外坏页时给出具体页码，先复用同次 full OCR 或已经由现有 pdf_runtime 验证同 PDF 的缓存；只在确实缺页且已有授权时走原 OCR 路径。

merge-ocr 除既有 required 页外，允许合并 page_quality 为 untrusted/empty 的额外实际引用页。保持现有 required 页完整性要求；已解决后可再次合并额外坏页。同步替换这些 source_pages 的文字并标记 OCR 已解决，同时按原 selection 刷新候选，不修改其他页。不得把好页当作匹配失败的 OCR 修复目标。使用现有 fingerprint 校验入口，不新建 cache 格式或认证系统。

## 4. 实施步骤

1. 对 baseline 和远端 head 做并发核对，建独立功能分支，提交本执行/测试计划两个文件，状态 pending；独立复核通过后才实现。
2. 在 future_work.py 添加页原文保留与受限连续定位，接入 validate/finalize/upgrade，保留旧 candidates 路径、ID、正式 sidecar 结构。
3. 同步 merge OCR 的页级原文更新和坏页范围，不改变 pdf_runtime cache owner。
4. 最小修改 agent / SKILL 的优先候选、原文回查、prepared 参数、两句及跨页出处说明。gap-only 在同一 agent 中优先看候选，必要时查阅 source_pages；仅候选无命中不能宣称整篇无 future work，未覆盖原文须明确未完成。不能新增第二次 full 分析或模型流水线。额外非候选 OCR 页仍须现有授权，不扩大 auto_candidate_pages 的预授权范围。失败保持失败，不能手写 sidecar。
5. 按独立通过的 test-plan 添加到现有测试文件，审查最终 recipe，再在云端隔离临时目录执行受影响入口；记录真实结果，不自授审核结论。
6. 完整 diff 独立复核，正常提交推送 Draft PR，读回分支 SHA/PR 内容；不合并，不 force，不覆盖并发改动。

## 5. 保持项与风险边界

- 保持：三产物 full 保存顺序、facts owner、原分析语义、旧 ID/hash、NFKC/空白规则、APM/uv/Nix 入口、既有有效 sidecar。
- 允许变化：真实非候选引文可通过；两句/相邻跨页连续引文可通过；存在歧义需明确页码；新 prepared 的指纹矛盾显式失败。
- 禁止副作用：生成无依据引文、跨正文删句、候选命中即跳过原文质量、全仓回归/模型业务重跑、重建用户 PDF 或更改用户全局配置。
- 版面提取不一定表达多栏自然阅读顺序；不添加阅读顺序重建引擎，不确定则定位失败并说明限制。8% 规则不能覆盖全部复杂版式，不承诺通用 PDF 解析。
- prepared 是本次任务的输入产物而非敌对文档认证边界；沿用既有当前 PDF/cache 指纹链，不宣称能认证人为篡改 prepared。
- 所有条目通过后才开始写分析与 sidecar；保持现有单文件原子写，仍不声称两个文件是跨文件事务。并行论文使用独立临时目录。

## 6. 独立审核记录

P1 事实、P2 owner/方案、P3 质量及兼容边界、P4 可执行性：独立 reviewer 对 EP2 全部通过（2026-10-22 17:25 UTC，由主协调器转达）；初版三项修订已收敛为受限外侧噪声、旧 canonical ID 保留、gap-only 回查与 OCR 授权边界。后续修订直接更新本文，历史差异由 Git 保留；不追加冲突方案。
