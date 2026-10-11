# Issue #18 执行计划：恢复论文分析链接维护工具

> 状态：Proposed review status: pending。本文是待审核方案；不得据此宣称计划已批准、实现通过或 PR 可合并。
>
> 需求版本：Issue #18（2026-10-11 修订，含 Codex 安装说明）。
> 计划版本：v1.2（2026-10-11；依据 Stage 2 写入代码将索引路径限定为正式绝对路径，明确去重引用检查范围；按用户决定排除符号链接特殊处理。v1.1 的 PR 分支修正保留）。
> 目标仓库：ScholarWorkflow/paper-analysis，基线 master@19eb3e26e8eb7ec60cba1d74efe0f27534c10203。
> 调用方依据：ScholarWorkflow/professor-contact@41aa5f4a3587bdbb7ea31342c7a5a5d39224f4ed，主技能第 676–683 行。
> 外部依据：Codex 技能文档（2026-10-11 查询）；uv tools / entry points 文档；microsoft/apm 安装文档（2026-10-11 查询）。本地执行时记录实际 APM、uv、Python 版本。
> 对应分支：plan/issue-18-paper-analysis-linker。关联草稿 PR 合并时通过 `Closes #18` 关闭议题。

## 一、要解决什么、由谁解决

目标是让现有补链调用真正可用：同一教授的 Markdown 文档出现 `（[zotero](zotero://select/library/items/KEY)）` 时，根据该教授 `论文分析/_index.json` 中 `papers[KEY].file` 的记录，在引用后补 `｜[分析](相对于这份 Markdown 的路径)`。没有对应记录则不补。单独提供预览、对账、可恢复去重命令。

**责任归属**：链接扫描、索引映射、文本修改、去重以及 CLI 是 `paper-analysis` 的新维护工具；`professor-contact` 只保留现有调用与文档约定。不要在 contact 的 Stage 0–5 中重写补链器，也不要修改 Zotero、邮箱生成器或论文分析的语义步骤。

**本次直接改变的行为**：
1. APM 可以安装名为 `paper-analysis-linker` 的技能，Codex 能从实际安装后的 `.agents/skills/paper-analysis-linker/SKILL.md` 发现它；OpenCode 继续使用该技能的正常 APM 安装产物。
2. `uv tool install` 本仓库后确实提供 `paper-analysis-link` 命令；命令完成四种既定用途。
3. 只修改明确属于本次补链目标的本地 Markdown 或安全确认的重复副本。

**保持不变**：现有 `paper-analysis` 主技能、agent、四个 PDF/证据助手、三类证据文件、`professor-contact` 状态、Zotero note、套磁邮件正文、其他 Python 命令的行为。`--map` 和任何 `--dry-run` 必须只读。

**不做**：增加套磁阶段；从论文全文或 Zotero 猜 `KEY`；编辑 `_index.json` 或 `.future_work.json`、`.facts.json`；扫描用户真实资料做测试；额外注册模型代理；建设测试平台；运行整套论文分析、教授收集或套磁模型流程；额外设计或测试符号链接的特殊行为（用户明确排除）。

## 二、依据、现实与关键决定

| 决定 | 当前事实及来源 | 由此确定的修改 |
|---|---|---|
| D1：必须交付新实现 | 基线仓库树只有 `.apm/skills/paper-analysis`；没有 linker 技能目录或 CLI 模块。按候选路径 `.apm/skills/paper-analysis-linker` 和 `paper_analysis_linker` 查询的仓库提交历史未返回原件。不能据此断言其他仓库永远没有原件。 | 先以已有源码、已知历史和调用方约定寻找；未得到可信原件时按本文限定接口重建，不复制未经验证的旧脚本。 |
| D2：身份与路径来自 index | contact@41aa5f4 第 676–683 行规定用 `papers[key].file` 产生以引用文档为起点的链接。相同版本的 `packages/professor-contact-codex/.apm/agents/professor-contact-analyzer.agent.md` 第 364–385 行将 index `file` 定义为绝对路径；实际写入者 `_stage2_chatgpt_handoff_impl.py` 第 551–611、629–643 行从教授目录解析目标，并以 `str(analysis_path)` 写入 index。旧相对路径的起点没有已确认的正式约定。 | 精确 `KEY` 匹配后直接使用已登记的绝对路径计算引用文档相对链接；遇到旧相对路径则报告无法判定，不能擅自指定相对基准或按文件名猜测。 |
| D3：技能和命令是两种安装物 | 基线 `apm.yml` 为 `targets: [opencode, codex]`，但 `pyproject.toml` 只有依赖，没有构建后端或 `[project.scripts]`。Codex 文档规定本地技能扫描 `.agents/skills` 并支持 `$技能名`；uv 文档规定工具安装只暴露 Python 分发物的命令入口。 | 在 `.apm/skills` 增加技能源，并经 APM 正式安装投影；在独立 Python 包中提供 `project.scripts` 加构建配置。不能用 `uv tool install` 冒充技能安装。 |
| D4：不修改 contact | contact 目前引用 OpenCode `skill(name: "...")` 写法；它对 Codex 的调用写法不能直接复用。 | linker 技能说明分开写 OpenCode 与 Codex：OpenCode 保留现有方式，Codex 明确 `$paper-analysis-linker`；本 PR 不跨仓改 contact。 |
| D5：清理须可恢复 | Issue 要求去重不影响被引用文件与证据附属文件；现有补链扫描明确排除 `论文分析/`，所以不能拿补链扫描结果判断副本有没有被引用。 | 去重只处理明确的冗余 `.md` 副本；独立检查本教授目录内所有 Markdown（含 `论文分析/`）是否引用候选，被引用或引用关系无法确认即跳过；确认安全才移动到可恢复隔离目录。 |

参考地址：

- [需求 Issue #18](https://github.com/ScholarWorkflow/paper-analysis/issues/18)
- [contact 引用契约（固定提交）](https://github.com/ScholarWorkflow/professor-contact/blob/41aa5f4a3587bdbb7ea31342c7a5a5d39224f4ed/.apm/skills/professor-contact/SKILL.md#L676-L683)
- [paper-analysis 基线包配置](https://github.com/ScholarWorkflow/paper-analysis/blob/19eb3e26e8eb7ec60cba1d74efe0f27534c10203/pyproject.toml)
- [Codex 官方技能文档](https://developers.openai.com/codex/skills)
- [uv 工具安装](https://docs.astral.sh/uv/concepts/tools/)
- [uv 项目入口配置](https://docs.astral.sh/uv/concepts/projects/config/)
- [APM 包安装](https://github.com/microsoft/apm/blob/main/docs/src/content/docs/consumer/install-packages.md)
- [此前本仓库的 APM 到 Codex 安装记录（PR #9）](https://github.com/ScholarWorkflow/paper-analysis/pull/9)：记录了安装后 `.agents/skills/paper-analysis/` 的真实投影；作为历史观测，不保证其他版本相同。

**因果链**：调用方承诺补链，但 producer 不包含安装物 → APM 无技能可部署、uv 无命令入口 → 在 producer 恢复技能及可安装 CLI，并用 index 驱动确定性修改 → 现有补链调用获得指定结果，contact 不增加阶段。

**替代方向**：把补链直接写到 contact 阶段 2。放弃此方向，因为会把一个独立维护操作塞进业务阶段，`--map` 和 `--dedup` 仍缺可复用命令，而且在 consumer 修补 producer 缺项。选择独立 producer CLI + 轻量技能说明。

## 三、文件与职责

| 路径 | 修改内容 |
|---|---|
| `.apm/skills/paper-analysis-linker/SKILL.md` | YAML 头须有 `name: paper-analysis-linker` 与明确使用时机的 `description`；说明输入、四个命令、预览及改写的保护条件、Codex/ OpenCode 调用差异；引导执行已安装的 CLI，不另造代理。 |
| `paper_analysis_linker/__init__.py`、`cli.py`、`core.py` | 新增独立 Python 包。`cli.py` 做参数、工作目录、退出码与摘要；`core.py` 做目录发现、index 校验、精确匹配、Markdown 处理、对账和冗余文件判定。可以内部拆函数，不增加第二套 CLI。 |
| `pyproject.toml` | 增 `[project.scripts] paper-analysis-link = "paper_analysis_linker.cli:main"`；增加能安装上述包的构建后端（例如 Hatchling），显式限制 wheel 打包为新包，不把 `.apm/` 或 tests 当作分发模块。保留 `scholar-workflow-pdfx` 依赖。 |
| `uv.lock` | 按实际构建配置重建并提交锁文件，`uv sync --locked` 不得漂移。 |
| `README.md` | 分开说明 APM 技能安装、uv 命令安装、Codex `$paper-analysis-linker` 和 OpenCode 现有调用形式；四种命令的输入、写入范围和退出语义。 |
| `tests/test_paper_analysis_linker.py` | 新增 producer 自有的最小合成文件测试；不读用户目录、不连接 Zotero、不启动模型。 |
| `plan/issue-18-paper-analysis-linker.md` | 本文是唯一规范执行计划；修订在原文件中合并，不让本地 agent 依赖聊天评论拼接。 |

不要修改 `.apm/agents/paper-analysis.agent.md`，也不要创建同名协调代理。此能力只要求确定性文本/文件操作。

## 四、CLI 与输入输出（冻结对外行为）

### 4.1 使用方式

保留全部已承诺选项，增加可选 `--root PATH` 用于明确目标根目录，省略时使用命令当前目录。用户可以在单个教授目录或包含多个教授的业务目录运行：

```bash
paper-analysis-link --root "<业务或教授目录>" --backfill --dry-run
paper-analysis-link --root "<业务或教授目录>" --backfill
paper-analysis-link --root "<业务或教授目录>" --map
paper-analysis-link --root "<业务或教授目录>" --dedup --dry-run
paper-analysis-link --root "<业务或教授目录>" --dedup
```

`--backfill`、`--map`、`--dedup` 三者一次只能选一个；没有模式或同时多选时给出用法错误，不写文件。`--dry-run` 只支持会产生改动的 `--backfill`、`--dedup`。`--map` 始终只读。

目录解析：
- 当根目录直接有 `论文分析/_index.json` 时，视为一位教授的目录。
- 否则在根目录下的 `教授研究`（或根目录本身就是 `教授研究`）内查找带 `论文分析/_index.json` 的教授目录，排序后逐个处理；目录身份用真实相对路径，不能仅用教授显示名合并。
- 没有可识别的教授索引就返回明确错误，不把别的 `.md` 当作候选扫描；多个教授相互隔离、各用自己的 index。
- 只在显式目标下执行。所有真实写入都限于该目标中的 Markdown 或可恢复去重目录；测试始终用 `/tmp` 合成输入。

### 4.2 索引、身份与目标路径

- 索引根对象必须是对象，`papers` 必须是对象；键即精确论文 `KEY`，值必须是对象。`file` 缺失、`null`、空字符串的条目表示没有分析链接。
- 非空 `file` 是唯一来源。正式 Stage 2 将其写为绝对路径（见 D2 的写入者与格式约定），因此直接使用该绝对路径，并要求其位于本教授 `论文分析` 子树内。若旧 index 记载相对路径，本次没有可靠的历史解析基准，**跳过该条并报告路径含义无法确认**；不得擅自将它解释为相对 index、教授目录或当前工作目录。超出该教授分析目录的路径拒绝并报告；绝不写入界外位置。
- 以当前 Markdown 文件的父目录为起点计算 `file` 的相对链接地址，统一用 `/`，并对空格、括号等 Markdown URL 特殊字符编码；**不通过作者、标题或文件名猜测**。索引路径明确但物理文件暂缺时，`--map` 报告缺失；`--backfill` 是否能加链接只由规范索引 `file` 非空决定，遵守 contact 原约定。
- 同一 `KEY` 在不同教授的索引中可以指向不同文件；任何处理都不得跨教授读取另一份索引填空。

### 4.3 补链

- 搜索目标教授目录下的本地 Markdown；排除 `论文分析` 整棵子目录、内部隔离目录、套磁邮件正文（`套磁邮件.md`、`套磁跟进邮件.md` 及对应邮件目录），以及任何非 Markdown 产物。只修改确实出现指定 Zotero 链接且需要补链的文档。
- 只识别现有约定的 `（[zotero](zotero://select/library/items/KEY)）`，按 URI 中的 `KEY` 匹配 `papers`。对正常正文引用在右侧追加 `｜[分析](相对路径)`。 fenced code block / inline code 内的示例不改；普通段落其余字节不变。
- 已存在紧随该引用之后的 `[分析]` 链接时不再追加第二条。对应 index 已取消或缺失时，保留原 Zotero 引用，不为了补链删除其他用户内容；现有链接与 index 不一致由 `--map` 明确报告，避免在回填时静默替换用户编辑。
- `--dry-run` 输出每位教授的待改文件数和引用数，不写盘、不创建备份或索引。实跑对文件逐个检测差异：无变化零写；写入用同目录临时文件及原子替换，写前再次核对源文件没有在运行过程中变化，变化则停止该文件并报告。批量文件逐个提交，失败保留已成功结果并列清未完成项；重复执行不生成新链接或额外修改。

### 4.4 对账

`--map` 只读 index 和被扫描的 Markdown，按教授与 `KEY` 输出：记录的分析路径、是否有 Zotero 引用、实际分析链接是否存在及匹配、索引所指物理文件是否存在。缺失、过期链接或不可解析项用明确文字标记；正常差异只是报告，不修改任何内容，也不把结果写成新的机器状态文件。索引 JSON 错误、路径越界或读盘错误才返回非零并给出原因。

### 4.5 安全去重

- 仅检查同一教授 `论文分析` 目录内的普通分析 `.md` 文件。先以 index 中所有非空 `file` 建立**保护集合**；这些文件及相邻 `.future_work.json`、`.facts.json` 等证据附属文件永不移动。
- 只考虑**未被 index 引用、无相邻证据附属文件、未被该教授目录内其他 Markdown 链接指向、内容与至少一份受 index 保护的分析 `.md` 完全按字节一致**的冗余文件。去重必须独立于补链扫描，检查本教授目录的全部现存 Markdown（**包括 `论文分析/` 内的分析正文**，排除隔离目录）对候选文件的本地链接；任何已引用、引用关系无法确认、同名但内容不同或解析失败的候选一律跳过。文件去重是清理不再使用的重复副本，不用于更新原分析文件；不能只靠标题或文件名推定重复。
- `--dedup --dry-run` 列出原路径、可恢复目标路径和跳过原因，零写入。
- 显式 `--dedup` 只把符合条件的副本移动到该教授 `.paper-analysis-linker-quarantine/` 下按本次运行隔离的路径，保留原文件字节供恢复；不永久删除、不移动 index、证据附属文件或索引引用的分析文件；再次执行不扫描隔离目录。中途异常给出已移动清单和可恢复位置，绝不尝试猜测后续清理。
- 此命令仅在未来用户主动指定自己的目标目录时运行；本 Issue 的实现、测试和审核禁止对用户真实资料执行去重。

## 五、实施顺序（同一 PR 分支继续）

1. **检出现有 PR 分支并确认基线**：在 `ScholarWorkflow/paper-analysis` 仓库中检出 PR #19 的既有分支 `plan/issue-18-paper-analysis-linker`；若本地尚无该分支，则从对应远端跟踪分支检出，禁止重新从 `master` 建实施分支或直接在 `master` 修改。执行前记录 `git branch --show-current` 和 `git rev-parse HEAD`，核对 PR 基线 `master@19eb3e26`、本仓库树、历史候选路径和 contact 固定版本文档；后续实现、测试及计划更新均提交并推送到 **同一 PR 分支**。若找到可信原件，比较它和第 4 节正式约定，仅恢复兼容部分；不把旧的运行时私有调用规则搬入 Codex。
2. **完成纯核心**：创建 `paper_analysis_linker`，先处理目录身份、索引值及路径约束，再做 Markdown 的精确引用更新与只读 `--map`；确保 preview 和 apply 使用同一套决策结果。不要读 Zotero、PDF 或 contact 的状态文件。
3. **完成去重保护**：实现严格的保护集合、字节比对、引用排除和隔离移动。任何信息不足都跳过；不增加“按标题近似去重”。
4. **公开 CLI**：完成参数互斥、退出码、摘要提示、构建后端、`project.scripts` 与锁文件。确认正常安装后命令在任意工作目录可执行，未安装工程源码不应被运行时隐式导入。
5. **交付技能**：在 `.apm/skills/paper-analysis-linker/SKILL.md` 编写最短可执行步骤；Codex 使用 `$paper-analysis-linker`，OpenCode 依旧遵循自身原生技能调用；不要教 Codex 使用 `skill(name: ...)`。保留 manifest 的双宿主目标。
6. **更新文档并实现聚焦测试**：对照第六节的唯一必测清单编写生产仓库测试；在 `/tmp` 准备独立运行目录；检查安装和合成业务结果。保持已有 `paper-analysis` 单篇分析功能未更改。
7. **PR 交接**：所有新实现、测试和计划修订继续提交到本分支，PR 保持草稿直到计划获审、代码实现和测试按规则完成。不要先合并或手动关闭 #18。变化触及本文冻结的索引、写入边界或清理规则时先修订同一份计划并复核受影响决定。

## 六、唯一必测清单与执行安排

测试权威依据为 [Test Engineer Rule](https://app.notion.com/p/rekidunois/Test-Engineer-Rule-3d80101a85f380d8a8f5ce528141e253) 和 [Project Consensus](https://app.notion.com/p/rekidunois/Project-Consensus-3d60101a85f3815a8c43f271f2b4d91d)。清单只覆盖本次改变的业务行为；不得另加全仓回归、Codex 委派拓扑、模型验收、真实资料或通用采集器。

| 必测目标 | 输入或场景 | 预期结果 | 一个足够的检查入口 |
|---|---|---|---|
| T1：正式交付 | 来自本 PR 待测 SHA 的独立消费者；APM Codex 安装与隔离 `uv tool install` | Codex 安装树含正确 `paper-analysis-linker/SKILL.md`；`paper-analysis-link --help` 正常启动并列出三种模式及 `--dry-run` | 检查实际安装文件与已安装命令；安装是本 Issue 的明确目标，故需要这一项。 |
| T2：补链、预览、幂等与禁改 | `/tmp` 合成的两位教授、索引含有与缺失的 `file`、正常 Markdown 引用和一个套磁邮件正文 | 预览零写；应用仅给对应 `KEY` 的本地 Markdown 增加相对分析链接，不跨教授、不修改缺失项或邮件；第二次实跑零变化 | `tests/test_paper_analysis_linker.py` 中比较预期 Markdown 内容和运行前后文件状态。 |
| T3：对账 | 同一合成目录：一条已补链接、一条缺失链接、一条不存在的索引文件 | `--map` 显示对应匹配/缺失/文件状态；所有输入文件保持原样 | 直接检查命令报告中这三项和目录内容。 |
| T4：去重及保护 | 合成目录中一份 index 引用的分析原件、字节相同且无人引用的副本、带附属证据或仍有引用的文件 | 预览零写；实跑只隔离符合全部条件的副本；index、原件、带 sidecar 文件及其引用不变；可从隔离处恢复原始字节 | 检查移动前后实际路径和字节，不在用户资料上操作。 |

**准备及命令**（实施人使用当前 PR 最终 SHA 替换 `${SHA}`，在 `/tmp` 创建独立运行目录，所有安装、命令、缓存可写目录均与个人生产环境隔离）：

```bash
# 在 paper-analysis 源码仓库执行；先记录 git rev-parse HEAD 和实际工具版本。
uv sync --locked
uv run pytest -q tests/test_paper_analysis_linker.py

# 独立消费者，取当前 PR 的精确提交；APM 不使用 editable、本地复制或软连接安装。
export RUN="$(mktemp -d /tmp/paper-analysis-issue18.XXXXXX)"
export SHA="$(git rev-parse HEAD)"
mkdir -p "$RUN/consumer" "$RUN/uv-tools" "$RUN/uv-bin"
cd "$RUN/consumer"
apm init --target codex -y
apm install "ScholarWorkflow/paper-analysis#${SHA}" --target codex
test -f .agents/skills/paper-analysis-linker/SKILL.md

# 单独验证 Python 分发包提供命令；不把这一安装当作技能安装。
export UV_TOOL_DIR="$RUN/uv-tools"
export UV_TOOL_BIN_DIR="$RUN/uv-bin"
uv tool install "git+https://github.com/ScholarWorkflow/paper-analysis.git@${SHA}"
"$UV_TOOL_BIN_DIR/paper-analysis-link" --help
```

APM 是否能接受本机实际版本的 `init` 参数、双宿主投影位置，以正式安装命令的结果为准；若特定版本不一致，记录工具版本与实际报错，按该版本官方安装命令修正步骤，**不手工修补消费者**。合成业务测试由 producer 的新测试生成自己的临时输入；不要依赖共享 fixture 复制产品技能代码。若已存在同一 SHA、同一环境可复用的干净安装，引用记录，不重复安装。

**失败与重试**：产品断言不满足，记录为业务失败，修产品后只重测受影响项；安装或服务暂时不可达且确认与产品无关时，同条件最多再试一次，仍失败则记为无法判断、说明受影响 T1；不得临场更换输入、绕过正式安装或反复换模型求通过。准备失败标未执行。报告保留正式尝试及必要诊断，记录 SHA、版本、命令、`/tmp` 输出目录、T1–T4 的通过/业务失败/无法判断/未执行，不提交敏感原始材料或运行缓存到 Git。

## 七、风险、反例与未决事项

| 代表性反例 | 守住的约束 |
|---|---|
| 两位教授恰好有相同的 `KEY` 或相同显示名 | 以教授真实目录和各自 index 隔离，绝不借另一个教授的文件路径。 |
| 作者子目录含空格，分析标题包含括号 | 只计算 index 已有路径相对引用文档的链接，编码 Markdown 特殊字符，不自行拼标题。 |
| index 没有某个 `KEY`，或用户已经手写了一条分析链接 | 不创建臆造链接；不叠加重复 `[分析]`；对已存在但不匹配的链接只报告。 |
| 两份分析文件同名但内容不同，或重复文件存在 sidecar/索引/反向引用 | `--dedup` 跳过；不能为完成“去重”损坏唯一证据。 |
| 运行期间 Markdown 被其他程序改写 | 发现写前内容变化则跳过该文件并报错；不覆盖最新内容。 |
| 只运行了 `uv tool install`，Codex 仍找不到技能 | 这仅说明命令安装完成；必须检查另外的 APM 技能安装产物。 |

已知限制：去重只处理命令指定的、由技能维护的教授目录；独立检查该教授目录内所有 Markdown（含 `论文分析/`）的本地链接，无法确认引用关系时跳过；不宣称识别其他项目或目录外文档的引用。因此只对在本次维护范围内可证实冗余的文件执行可恢复隔离，不永久删除。正常论文分析更新仍保持原路径并直接修改原文件；符号链接特殊行为按用户决定不纳入本次范围。当前未发现影响核心方案的必须等待外部决定的事实；本地运行时版本、所需网络和安装是否可用由测试执行记录说明，不以未运行的测试声称通过。

## 八、交接与审核状态

- 唯一事实依据：修订后的 Issue #18；本文件是实施及测试步骤的唯一当前计划。
- 方案核心已经给出：producer 独立 CLI + APM 技能，基于教授本地 `_index.json` 与 Zotero `KEY`，两条安装渠道互不冒充，去重可恢复且保留证据。
- 代码、测试及提交由后续本地 agent 在本 PR 分支完成。
- 审核仍需按 [Plan Reviewer Rule](https://app.notion.com/p/rekidunois/Plan-Reviewer-Rule-3e80101a85f3817a94cbc6eca1a76a5c) 对 P1–P4 给出正式结论；本文件的 `pending` 不表示 `APPROVED`。测试 T1–T4 目前均为**未执行**，实现与合并状态也均未通过审核。
