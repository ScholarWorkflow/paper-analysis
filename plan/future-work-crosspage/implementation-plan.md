# 相邻跨页 future-work 引文：执行计划

- Requirement revision: U3，2026-10-16 用户提供的问题报告 §5，以及随后要求为剩余任务直接建立计划 PR 的授权。
- Plan revision: CP-R1（候选）。Proposed review status: pending。
- 本 PR 只提交本计划与测试计划；不含产品或测试实现，不表示实现/测试通过，不合并。
- 目标基线：paper-analysis `5967a431a6c8c164bdee5e0a8f581a99406c854b`（master）；直接消费者 professor-contact `305bc08f8b186672108cffbba0293d249bc8b4b2`（main）。实施时核对最新差异，只调整受影响处。

## 1. 目标、事实与边界

目标是让跨越两个相邻物理 PDF 页的完整作者原句成为可精确核对的候选，排除有明确依据的页眉/页脚，保留两个来源页与页内位置；准备、OCR 刷新、正式验证/输出及 contact 直接读取不能把跨页误称为单页。

用户报告的例子在第 9 页末为 `In addition, we will investigate domain adaptation strategies to support more diverse and specialized`，第 10 页开头正文为 `KGs.`，中间混入运行页眉。报告原始 PDF 和本地运行文件未在本轮读取；本文据报告定义复现目标，据固定版本源码确认逐页机制。合成样例通过不能冒称原论文已实测修复。

已确认因果链及 owner：

| 决策 | 当前事实与精确来源 | 改动职责 |
| --- | --- | --- |
| 候选必须在 producer 合成 | [future_work.py](https://github.com/ScholarWorkflow/paper-analysis/blob/5967a431a6c8c164bdee5e0a8f581a99406c854b/.apm/skills/paper-analysis/scripts/future_work.py) 的 page_candidates / prepare 逐页调用，refresh_candidates 也逐页替换 | paper-analysis 保留页级来源，统一构造页内与跨页候选；不能由 contact 或测试补拼 |
| OCR 更新必须使跨页旧候选失效 | 同文件 refresh_candidates 只按 item.page 保留旧项，prepare 当前未保存供重建用的页文本 | 临时 prepared 保存参与页原文/定位；刷新任一端时重建相关候选 |
| 单 page 不能代表双页 | 同文件 validate_items 白名单仅 page，render_section 为 p.N，upgrade_full_sidecar 只复制 candidate.page | 扩展明确的版本化定位契约、精确验证、双页展示和 full 升级 |
| consumer 需要配套而非忽略新字段 | [contact_state.py](https://github.com/ScholarWorkflow/professor-contact/blob/305bc08f8b186672108cffbba0293d249bc8b4b2/.apm/skills/professor-contact/scripts/contact_state.py) 的 load_sidecar 只接受 schema 1；build_gap_pool、gap_fingerprint、方向/渲染投影复制单 page，展示 p.N | contact 识别新版本、保留定位并正确展示；未更新的版本明确拒绝新 sidecar |
| 不扩 facts schema | [facts.py 的 validated_future_work_ids](https://github.com/ScholarWorkflow/paper-analysis/blob/5967a431a6c8c164bdee5e0a8f581a99406c854b/.apm/skills/paper-analysis/scripts/facts.py#L172-L207) 按 analysis、evidence_level、PDF fingerprint 和 id 连接，不读页范围 | 保留 facts schema、quote_id、来源 fingerprint 语义 |

非目标：三个以上页面、非相邻拼接、任意段落拼接、通用版面/NLP 框架、模型补字或近似匹配、全论文重新分析、改 OCR 引擎、全量历史迁移、Nix 安装变化、U1/U5 contact 缺陷、PR91 的 resolve/validation 修复。U2/U4 句界由 [PR21](https://github.com/ScholarWorkflow/paper-analysis/pull/21) 单独处理；该修复现已进入上述 master；实施时复用其生效的页内切句，不在此 PR 再实现一套。

## 2. 核心方案与定位契约

### 2.1 有限的相邻页候选

1. 保留现有 TOC/关键词/末页选择及页内候选规则。prepare 已遍历全 PDF；利用已读页文本，检查原选中页两侧各一个物理邻页的交界。只为可继续的未终止句引入对应邻页到候选来源集合，不递归向外扩页，不扫描任意页组合。若交界一端质量不足，纳入该交界需要的 OCR 页并暂停生成这条跨页候选，不能用坏页原文拼接。
2. 保留原始页文本及行/字符位置。PDF 文本采用同一次 PyMuPDF 提取的行和 bbox；跨页输入按正文阅读顺序，只使用前页最后一个未终止句片段与后页第一个句子片段。前片段若已有真正句末，不能追加后页；片段合并后须在后页出现句末、总长不超过现有 1200 字符，否则不生成跨页项。已有页内候选不被无条件删除；模型仍只挑作者明确未来行动。
3. 页眉/页脚只在候选交界清理：位于页顶/底边缘带（页面高度首尾 10%）且在同文档另一页同一边缘位置重复的规范化整行，或该边缘的独立页码行，才可从交界候选剔除。重复比较只归一化空白与独立页码，不删除任意数字/作者名，不以大写或“看起来像页眉”判定。重复核对可使用已提取其他页，不能触发额外 OCR。正文中的同样文字保留。保留原文位置映射，不将清理后的下标冒充原文下标。
4. OCR 现有入口提供精确页文本而无 bbox：保留行号/字符偏移；仅剔除文本首尾行中已由同一 PDF 的布局证据确认的同名运行页眉/页脚，或至少两页同一端重复且有 PDF 布局证据支持的行；没有足够证据就不剔除。若交界仍有无法排除的噪声，不伪造“无页眉完整句”，保留既有候选并返回可定位的未形成跨页候选原因。页眉检测不是新的 OCR/模型调用理由。
5. 统一候选构造供 prepare 与 refresh_candidates 使用。prepared 在仓库外暂存参与页的原始文本、提取来源与必要定位；OCR 替换某页原文后重建依赖该页的页内/两侧交界候选，删除旧跨页项。只在两端文本可信且已就绪时生成，继续使用已通过当前 PDF fingerprint 校验的缓存，不增加 OCR 次数。

这是保守支持，不承诺任意版式均能自动识别。原报告样本若无法满足上述可定位条件，记录具体未满足条件再修订受影响方案；不能放宽出处验证求通过。

### 2.2 向后兼容的数据表达

- 旧单页 `items[]` 不变：`id/quote/translation_zh/source/page`；`page` 为 1-based 物理 PDF 页，不是印刷页号。单页 sidecar 仍输出 `schema: 1` / `extractor_version: future-work-v1`。
- 跨页条目增加 `page_end` 和 `segments`。`page_end == page + 1`；segments 恰好两个，页分别为 page、page_end。每段为 `{page, text, start, end}`：text 是对应原始页文本的连续切片，start/end 为该次提取页文本的 0-based、半开字符偏移；无 bbox 的 OCR 也可明确定位。偏移对规范化前的保存页文本定义；slice(start,end) 必须等于 text。
- 跨页 quote 是两个 segment.text 按原顺序以一个空格连接后，经现有 normalized_quote 得到的字符串；不补词、不模糊匹配、不额外变更连字符规则。仍用现有 quote_id(normalized quote)，不会因添加定位改写历史单页 ID。
- 任一跨页条目存在时，整个 sidecar 使用 `schema: 2` / `extractor_version: future-work-v2`；同一 sidecar 可含旧形状单页条目。纯单页保持 v1。当前 consumer 会拒绝 schema 2，避免静默把 page 当完整来源。
- prepared/candidates 的定位表达同步支持以上扩展，并标记新 prepared 版本以携带原始页文本/定位。旧 prepared 仍可做旧单页验证；需要 OCR 重建跨页时缺少页源数据则明确要求重新 prepare（只确定性提取，不重跑分析），不能猜测补段。
- validate_items 只接受与 prepared 候选完全相同的 quote 和完整定位；跨页不能仅提交 page，不允许删 page_end/segments 退化为单页。引用片段由确定性准备器生成，选择者复制而不改写；升级 full 路径从匹配候选取得完整定位。所有正式 writer 从经过验证的定位生成 sidecar，不能靠用户指定 extractor-version 把跨页输出伪装成 v1。
- prepare 与 refresh 的候选聚合按“规范化 quote + 完整来源定位”去重，不能沿用只按 quote_id 覆盖的旧字典；同一 quote 的不同位置全部保留供选择，quote_id 本身保持原算法。
- 如果同一规范化 quote 出现在多个不同定位，full 升级不得用 dict 的最后一个覆盖；有明确页/范围时匹配它，否则报定位歧义并要求选择具体候选。保持同一 sidecar 内 quote ID 唯一的既有规则，不新建通用消歧框架。

## 3. 修改点、失败行为与实施顺序

1. paper-analysis 产品负责人先改 future_work.py 的候选构造/原文定位和 OCR 重建；沿用既有 API、原子文件写入及临时目录约束，不另造服务。跨页未具备可信来源时不能进入有效跨页候选；外部 OCR 失败沿用现有错误行为，不降级成作者未提出 future work。
2. 同一文件改 validate/finalize/upgrade_full_sidecar、render_candidates、render_section：单页 p.N；跨页 pp.N–M（候选注释也明确范围）。upgrade 解析 source 时同时识别自己生成的单页/双页后缀，避免重复追加页码。validate 失败不得覆盖旧正式 sidecar；继续保持只有专用 future-work 节可被 patch，其他正文不变。不扩为多个文件事务框架。
3. 更新唯一 `.apm/agents/paper-analysis.agent.md` 的 gap-only items 白名单/复制定位规则、full 保存规则，以及 `.apm/skills/paper-analysis/SKILL.md` 对版本和双页定位的说明。仅改受影响格式，不改角色路由、分析语义、安装方式或模型职责。
4. contact 产品负责人另行实施消费端配套（本次不另开第三个 PR）：load_sidecar 接受上述 schema/version 对及完整双页形状；旧 v1/legacy 单页处理保持。扩展现有 SIDECAR_EXTRACTOR_VERSIONS 注册（不另设平行接受表），同步其进入包元数据/cache 校验的位置；版本能力元数据变化按既有 resolution_semantics_changed 路径使旧 preflight 失效（包括未变的单页输入），沿用已有重建/复用流程准备受影响包，不强行复用过期包、不修改旧文件冒充新结果，不触发全历史批量重跑。build_gap_pool 和选中/resolve/finalize/材料包中的 gap 投影完整传递定位，gap_fingerprint 在新定位存在时纳入新字段，旧输入维持旧计算；现有 sidecar_sha 仍让修改后的文件正常失效。所有引用页码的生成展示/校验材料改成单页/双页格式，不改变 quote_id、gap 选择权或排名规则。不能只改主 Markdown 而在后续输出丢掉 page_end。配套修改与 U1/U5 的展示修复有共享文件，应按双方最新代码合并，只审真实冲突。
5. 消费端兼容先落地或与 producer 同步交付；paper 的确定性准备/验证可独立开发验证，但面向 contact 的跨页可消费就绪结论必须等实际消费端版本和对应验证。消费者未更新时明确不支持 v2；不可输出伪 v1 规避。当前只记录这个实施依赖，不以未生成的 consumer SHA 阻止计划审阅。
6. 不批量改旧 sidecar、facts 或私人论文库。旧单页直接读；已有失败的跨页论文待新两端就绪后只重新准备/升级受影响证据，沿用有效分析与已识别 OCR。如实际引用文本也需改变，交业务执行者按原流程处理，不能脚本自动改写作者原话。

## 4. 方案选择、影响与反例

选择保守的两页候选加版本化定位，代价是复杂/无定位页眉可能仍需人工提供更好的原始输入。直接拼全文再切句会丢来源与段落边界；仅把 page 解释为第一页会误导旧消费者；放宽子串/模糊匹配会改变证据准入，均不采用。

不变量：每条跨页引文只来自同一 PDF 的 n/n+1 两个可信片段；正式输出包含完整定位；非候选/改写仍失败；未变单页语义和 ID 不变。代表性反例在设计上对应处理：下一页未选中→有限交界纳入；其中一页待 OCR→不提前拼接且刷新后重建；正文重复标题→不能仅凭重复剔除；旧 consumer→版本拒绝；同 quote 多定位→不静默择最后一项。没有业务并发变化，不增加并发锁/全局缓存/清理协议。

本计划的字段与候选构造是拟议实现契约，须经正式计划审核后实施，不因计划作者写入而成为新增产品需求。未决限制为未读取原报告 PDF 的具体版式；现有机制证据足够编写方案，但不能承诺该 PDF 的实际复现结果。

## 5. 测试与交接

唯一测试计划：[test-plan.md](test-plan.md)，CP-T1。执行计划不另追加测试义务。产品/测试实现及正式执行均未开始；P1–P4 与测试 G1/G2 待正式审核，G3 未执行。后续分别由 paper 实现负责人、contact 消费端负责人及测试执行者交付版本、相关结果和仍受阻项；本文没有 APPROVED/PASS 自授。

依据：[项目共识](https://app.notion.com/p/3d60101a85f3815a8c43f271f2b4d91d)、[执行计划规则](https://app.notion.com/p/3e80101a85f3817a94cbc6eca1a76a5c)、[测试规则](https://app.notion.com/p/3d80101a85f380d8a8f5ce528141e253)。本轮读取固定树未发现适用 AGENTS.md/CLAUDE.md；不引入额外仓库约束。
