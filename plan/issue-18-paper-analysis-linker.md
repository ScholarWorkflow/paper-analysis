# Issue #18 范围修订：只移植实际存在的论文链接功能

> 状态：**原实施计划已撤销，禁止按旧版本开发**。本文件是更新后的唯一范围说明，Proposed review status: pending；不声称实现完成、测试通过或可合并。
>
> 当前需求： [Issue #18](https://github.com/ScholarWorkflow/paper-analysis/issues/18)（2026-10-11 用户修订：只移植已有功能；未实现的不做）。
>
> 本文件版本：**v2.1（2026-10-11）**，取代 v1–v1.2 中的技能、命令、回填、对账、去重及对应测试交付要求；补充后续若重新批准安装工作的安装复用原则，不恢复已撤销的任务。
>
> 目标仓库：`ScholarWorkflow/paper-analysis@19eb3e26e8eb7ec60cba1d74efe0f27534c10203`；调用方事实版本：`ScholarWorkflow/professor-contact@41aa5f4a3587bdbb7ea31342c7a5a5d39224f4ed`。
>
> 关联 PR：[#19](https://github.com/ScholarWorkflow/paper-analysis/pull/19)，分支 `plan/issue-18-paper-analysis-linker`。后续本仓库变更不得另建分支；旧版本的实施授权、验收和审批结论不沿用。

## 一、核对后的事实

1. 目标仓库当前只有 `.apm/skills/paper-analysis/SKILL.md` 和实际用于分析论文的脚本，`pyproject.toml` 不含 `paper-analysis-link` 命令入口。没有可作为原始实现移植的 `paper-analysis-linker` 技能、`paper_analysis_linker` 模块或者三个维护命令；历史候选路径亦未找到原件。此结论只针对已经读取的目标版本与候选路径，不宣称其他仓库历史绝对不存在类似实现。
2. [`professor-contact` 的链接调用约定](https://github.com/ScholarWorkflow/professor-contact/blob/41aa5f4a3587bdbb7ea31342c7a5a5d39224f4ed/.apm/skills/professor-contact/SKILL.md#L676-L683) 确实写了 `paper-analysis-linker`、`paper-analysis-link`、`--backfill`、`--map`、`--dedup`，但它是**调用方文档**，不能证明独立命令已存在。
3. 真正的已有代码在 [`contact_state.py` 的 `citation_render`](https://github.com/ScholarWorkflow/professor-contact/blob/41aa5f4a3587bdbb7ea31342c7a5a5d39224f4ed/.apm/skills/professor-contact/scripts/contact_state.py#L4134-L4147)、[论文一览渲染](https://github.com/ScholarWorkflow/professor-contact/blob/41aa5f4a3587bdbb7ea31342c7a5a5d39224f4ed/.apm/skills/professor-contact/scripts/contact_state.py#L4360-L4375) 与[阶段二索引写入](https://github.com/ScholarWorkflow/professor-contact/blob/41aa5f4a3587bdbb7ea31342c7a5a5d39224f4ed/.apm/skills/professor-contact/scripts/_stage2_chatgpt_handoff_impl.py#L551-L611)。这些程序按真实论文编号、分析文件路径生成 Markdown 链接／保存索引，现已由调用方使用。

**决定**：本次不新造批量回填、独立对账或去重工具。也不因历史文档提到了某个技能名称，就重新实现一个从未找到源码的技能。维持现有 `professor-contact` 链接生成行为不变。

## 二、原计划撤销范围

| v1–v1.2 曾要求 | v2 决定及理由 |
|---|---|
| 新增 `.apm/skills/paper-analysis-linker/SKILL.md` | **撤销**：未发现原始技能源文件，不为文档中虚列的能力创建新技能。 |
| 新增 `paper_analysis_linker/` 和 `paper-analysis-link` Python 命令 | **撤销**：无已存在的 CLI 模块可迁移，不能把新实现称为恢复。 |
| `--backfill` 和 `--backfill --dry-run` | **撤销**：现有链接渲染不等于独立批量修改旧 Markdown 的命令。 |
| `--map` | **撤销**：索引读写、普通链接渲染不等于已存在的只读对账工具。 |
| `--dedup`、移动重复分析文件、隔离目录及恢复流程 | **撤销**：没有原始去重程序和本次获确认的清理需求。 |
| 为以上命令增加 `pyproject.toml` 构建入口、锁文件与安装文档 | **撤销**：无需交付新的命令安装物。 |
| 以 T1–T4 验收新技能安装、回填、对账和去重 | **撤销**：需求已取消；不得继续编写或执行原必测清单。 |

用户已明确决定不考虑符号链接特殊情况。本次也不添加任何此类测试。

## 三、保持行为及责任归属

- `professor-contact` 已实现的阶段二／三分析链接与 Zotero 引用继续由**现有代码**生成，不改变原文件名、分析文件路径、索引、论文分析正文、证据附属文件、套磁状态或邮件。
- 无需把 `contact_state.py` 的链接渲染逻辑无条件迁出：它属于当前 `professor-contact` 的可用功能。未来确需迁移这段**已存在**的代码时，必须先有获确认的具体调用方和目标责任归属，再提交独立的实施范围；不在本 Issue 中预授权跨仓库重构。
- `professor-contact` 主技能文档中宣称存在独立命令的内容已在[调用方自己的 PR #79](https://github.com/ScholarWorkflow/professor-contact/pull/79) 提交文档更正（未合并）。该更正不改变业务代码，也不使不存在的命令成为 `paper-analysis` 的必做项。
- 未发现本次需要 `paper-analysis` 新建或修改的产品文件；不得由本地代理为了填满 PR 自行添加新能力。

## 四、执行与交接

1. **停止旧计划的实现工作**：不得执行 v1–v1.2 中创建 `paper-analysis-linker`／`paper-analysis-link` 或 T1–T4 的步骤；不操作任何真实用户资料。
2. **保存当前事实与范围变更**：在现有 PR #19 分支保留本文件，Issue #18 与 PR 描述均指向此 v2。旧审核记录是旧版本的历史结果，不能当作本版本实施授权。
3. **后续若提出真实迁移**：先从实际源代码、使用点和明确要改的行为形成新的需求与完整计划，在获批准后再实施；测试只覆盖那次真正决定改变的行为。不得把未实现的 `--backfill`、`--map`、`--dedup` 重新加回要求。

**安装复用规则（仅供未来经批准且确实涉及安装的工作引用；当前没有安装任务）**：已有干净安装仍能满足本次实际测试时直接复用，并沿用原安装记录；**仅在已安装的技能、代码、依赖、生成配置或安装方式发生相关变化，导致既有安装失效，或明确获批的验收目标要求全新安装时重装**。单纯改文档、测试记录或提交编号，不触发重装。确需安装时，使用目标 PR **现有分支的最新提交**执行正式安装，不在安装命令中硬编码提交编号；安装完成后记录实际解析的提交编号、安装位置与命令，以明确受测版本。代码变更若影响当前被测的已安装行为，旧安装即不再适用，应安装该变更后的分支最新版本；不得拿旧安装冒充新行为。

当前结果：**无产品实现任务、无新安装物、无本次需执行的测试**；PR 保持草稿，不因仅修订文字而宣称代码已经交付。