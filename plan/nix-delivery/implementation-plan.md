# paper-analysis：Nix 交付执行计划

Requirement revision: 2026-10-16 Nix 后续批次；直接提交计划 PR，不新建 issue。
Plan revision: v1.2。Proposed review status: pending。
目标基线：`ScholarWorkflow/paper-analysis@19eb3e26e8eb7ec60cba1d74efe0f27534c10203`（`master`）。本 PR 仅新增本计划与同目录测试计划；没有实施、安装或正式测试结果。

## 1. 目标、范围与依据

在 `aarch64-darwin` 新增一个可由共享安装器独立安装的 Codex `paper-analysis` 包：完整技能资源、四个 helper、准确命名的原生 `paper-analysis` 角色、普通 PDF runtime 与真实 OCR 所需的 `vision-tools` 直接依赖。Nix 激活完成后无需 APM、uv 或运行时安装 Python 依赖。

保留 APM、uv、PEP 723、OpenCode 原件与既有业务 contract；Nix 只做生成转换和固定入口适配。本轮不恢复 [PR #19](https://github.com/ScholarWorkflow/paper-analysis/pull/19) 撤销的 linker、CLI backfill、map、dedup，不迁移 Zotero/browser 业务链，不新增 MCP，不认证 full-mode 分析质量、全量业务或其他平台/harness。

规范：[Nix skill 交付规则](https://app.notion.com/p/3fb0101a85f38185b17adb417590e50e)（2026-10-16）、[Project Consensus](https://app.notion.com/p/3d60101a85f3815a8c43f271f2b4d91d)、[Plan Reviewer Rule](https://app.notion.com/p/3e80101a85f3817a94cbc6eca1a76a5c)、[Test Engineer Rule](https://app.notion.com/p/3d80101a85f380d8a8f5ce528141e253)。测试范围与 recipe 只由 [test-plan.md](test-plan.md) 定义；按本轮明确收缩，只验本地固定入口最小动作、资源与原生角色安装，不新增模型 eval 或真实 OCR 调用义务。

## 2. 已核事实与固定依赖

以下是设计依据，不是本包运行通过的声明。

- 本仓 [技能](https://github.com/ScholarWorkflow/paper-analysis/blob/19eb3e26e8eb7ec60cba1d74efe0f27534c10203/.apm/skills/paper-analysis/SKILL.md) 与 [角色](https://github.com/ScholarWorkflow/paper-analysis/blob/19eb3e26e8eb7ec60cba1d74efe0f27534c10203/.apm/agents/paper-analysis.agent.md) 是唯一业务来源。四 helper 是 `paper_input.py`、`pdf_runtime.py`、`future_work.py`、`facts.py`；资源完整复制 `.apm/skills/paper-analysis/`。根目录 `tests/` 是开发/测试资源，不混入技能 payload。基线递归树无适用于本修改路径的 `AGENTS.md`/`CLAUDE.md`，没有 `flake.nix` 或 Nix 计划；open PR #19 只记录 linker 收缩。
- `paper_input.py` 接受绝对路径、schema 1 / kind `paper-analysis-input` / level `abstract`，输出 canonical JSON 去掉 `source`/`item_key`；`pdf_runtime.py` 用 PyMuPDF；`future_work.py` 用 `pdfx`；`facts.py` 无第三方依赖。现有角色使用绝对 skill-script 路径，但运行命令为 `uv run`/`uvx`。因此仅写 `runtimePackages` 不能完成 Nix 入口适配。
- [agent-env-nix@2158e933aab6c845ae1ceb1228458d624f8777d5](https://github.com/RekiDunois/agent-env-nix/tree/2158e933aab6c845ae1ceb1228458d624f8777d5) 的 `lib.mkAgentPackage` 支持 `files`、`exports.skills`、`exports.agents`、`agentDependencies`、`runtimePackages`；原生角色字段是 `description`/`developer_instructions`，名字来自 export key。`lib.mkProject { roots = [ ... ]; }` 递归组合，`bin/agent-env apply --project` 真实复制资源。`runtimePackages` 只保留 closure，不设置 PATH/PYTHONPATH。
- 统一 pin：nixpkgs `6510408d147d8c5e6d76043e899e9251756f6a75`；共享层已 pin agent-skills-nix `2948865044b2af55c8c4e4eb2abda7de79d60f0e`、mcp-servers-nix `31848978eefbca17f1658a55066b1d2aaa43cafc`。复用共享层已交接口与安装保护，不复制安装器或重验共享通用矩阵。
- [pdf-processing-core@3444dca0e0b84f46d1839ab5c707afa78e23d3a7/nix/pdfx.nix](https://github.com/ScholarWorkflow/pdf-processing-core/blob/3444dca0e0b84f46d1839ab5c707afa78e23d3a7/nix/pdfx.nix) 实际返回 `{ pdfx, pdfxAgent, python }`。以相同 `pkgs`/`mkAgentPackage` import 后，`python` 已带 PyMuPDF、Pillow、`scholar-workflow-pdfx`。直接复用 `python` 与 `pdfx`，不要求上游新增公共 `python.withPackages` 输出，不依赖其私有 Python 模块布局，也不安装无调用需求的 `pdfxAgent` 角色。
- [base-skills@3ab2ac188e625b8a8ae37b5fa318c579787c3d1e](https://github.com/ScholarWorkflow/base-skills/tree/3ab2ac188e625b8a8ae37b5fa318c579787c3d1e) 已由 [PR #8](https://github.com/ScholarWorkflow/base-skills/pull/8) 合并。实际接口是 `packages.aarch64-darwin.vision-tools` 与 `apps.aarch64-darwin.vision-glance.program`；后者固定 Python/资源，接受 `<image> --ocr`。包安装技能但不把 CLI 放入 PATH。其现有 closure 含其他视觉工具与浏览器资源；本包不增加浏览器调用、浏览器测试或其他 base-skills 根包。既有视觉测试不等于真实 OCR 模型已可用。

## 3. 冻结方案与职责

因果链：新增 Nix 安装入口 → 原技能依赖 uv 与 ambient vision CLI → 在 producer 构建时生成等价技能/角色并固定运行入口 → 共享安装器复制完整资源和依赖 → 安装后能使用相同四 helper 与原生角色。

### 3.1 flake 与包

新增 `flake.nix`、`flake.lock`、`nix/paper-analysis.nix` 和必要的小型生成转换。只导出 `aarch64-darwin`：

- `packages.aarch64-darwin.paper-analysis`：`mkAgentPackage`，ID/skill/agent 名均为 `paper-analysis`，版本取现有 `0.1.0`。
- `packages.aarch64-darwin.paper-analysis-project`：`mkProject`，唯一 root 为上面的包。
- `agentDependencies = [ base-skills.packages.aarch64-darwin.vision-tools ]`；不将普通 Python/CLI runtime 当作 agent 依赖。
- `files."skills/paper-analysis"` 指向完整生成 skill tree；`exports.skills.paper-analysis` 与 `exports.agents.paper-analysis` 保留准确名字。
- 运行 closure 保留固定 `pdfx.python`、`pdfx.pdfx` 及本包 launcher derivation；launcher 对 `vision-glance.program` 的 Nix 字符串引用保留实际 OCR app/runtime closure。不能仅记录一个无上下文的 store 路径。

flake 固定第 2 节全部 revision；base-skills 的 nixpkgs 与 agent-env-nix inputs follows 本仓统一输入。pdf-processing-core 可作为固定 source input，import 其现有 `nix/pdfx.nix`。提交真实生成的 lock，不写伪造 hash。

### 3.2 固定入口与单源生成

生成 skill tree 先完整复制原 skill，保留 scripts/ 与未来附属资源，再增加 `bin/` 六个可执行文件：

| 安装后入口 | 调用目标 |
|---|---|
| `bin/paper-input` | 原 `scripts/paper_input.py` |
| `bin/pdf-runtime` | 原 `scripts/pdf_runtime.py` |
| `bin/future-work` | 原 `scripts/future_work.py` |
| `bin/facts` | 原 `scripts/facts.py` |
| `bin/pdfx` | 固定 `pdfx.pdfx/bin/pdfx` |
| `bin/vision-glance` | 固定 base-skills `vision-glance.program` |

前四个 launcher 用固定 Nix Bash/coreutils 解析自身所在的安装 skill 根，再用固定 `pdfx.python/bin/python` 执行该根下对应原脚本；不使用 caller cwd、源码 `.apm` 路径或宿主 Python。参数以独立参数与 `"$@"` 传递，保留原 CLI、exit code、stdout/stderr，不改写 JSON/schema。后两个 launcher 直接 exec 固定 app。只写生成副本；PEP 723 原文不变。

对原 `SKILL.md` 与 agent body 做有边界的构建时转换：原 helper 变量改为安装 skill 的 `bin/*`，所有 helper `uv run`、质量命令 `uvx ... pdfx`、OCR `glance` 改用上述对应入口；说明只适用于 Nix。skill 中 caller-facing 启动说明转换为 Codex native delegation 到准确 `paper-analysis` 并等待消费结果；原生角色保留 coordinator、full/gap-only、needs_input 与禁止自委派语义，不再把 OpenCode Task 当作 Codex 接口。Nix 生成角色正文前部加入当前 Codex 路由约定；替换原 body 中“必须先从 ALL_TOOLS 发现并绑定 spawn/wait callable”的旧段，直接使用运行时正式提供的 native spawn 与 wait/consume，不固定私有 namespace、签名或事件 schema，不把 tool/catalog/programmatic discovery 当委派前置。只有真实 native 调用返回的失败才能报 delegation blocker。此处仅修正 Nix 角色转换与当前公开调用约定，不改 full 的三路业务职责或增加模型测试。不要把安装适配文本扩散回 APM/OpenCode 原件。

角色的 name、description 与完整 body 从同一 `.apm/agents/paper-analysis.agent.md` 读取并转换；用 YAML/frontmatter 与 TOML 正规生成处理转义，不维护第二份业务正文。共享接口仅接受 description/developer_instructions：OpenCode 专属 mode/hidden/temperature/permission 不伪造为 Codex ACL。转换找不到预期边界、必需入口残留或源格式不可解析时构建明确失败，不能静默漏转换。

### 3.3 配置、状态、错误与安装

PDF/helper 业务错误仍由原脚本负责。OCR 配置与配额仍由 vision-tools 负责；API、网络、模型与授权是外部运行前提，秘密不进入 Nix/store/仓库。`VISION_ENV_FILE` 指向已有获准运行配置，`VISION_STATE_FILE` 指向本次可写状态。没有配置或 OCR 授权时保留现有询问/错误路径，不降级成伪 OCR。

消费者通过固定输出的 `agent-env apply --project` 安装，不做手工链接或另跑 APM。共享层拥有资源复制、冲突处理、GC roots 与 remove；受管 skill/agent 更新会覆盖该叶子的手改，无关同级资源保留。配置冲突不静默覆盖；失败修正原因后按共享层简单重跑，不新增 journal/回滚系统。运行产物与缓存写到用户选择路径或临时目录，不写 store。

## 4. 影响、反例与实施顺序

- intended_change / approved_behavior_change：仅增加上述 Nix/Codex 交付与固定入口适配。
- preserved_behavior：四种输入、canonical stripping、PDF/OCR cache fingerprint、future-work 验证、facts schema、full 三件套与 gap-only 边界，以及 APM/uv/PEP 723/OpenCode 原件。
- prohibited_side_effect：运行时安装依赖、消费者补造产品资源、Zotero 状态访问、browser 流程、恢复撤销命令、改 full 分析/证据语义、秘密入 store。
- invariant / 代表性反例：从任意 cwd 调用仍定位同一安装 skill；只声明 runtimePackages 的反例由固定 launcher 消除；OCR CLI 不在 PATH 的反例由固定 app 消除；缺依赖或源转换漂移必须失败；原角色不得在 full 内再 spawn 自己；原始 OpenCode ACL 不冒充 Codex 安全边界。共享配置与并发保护直接复用，不为此另造状态机。

现实替代方案是 Nix 仅安装提示词，再依赖 uv/全局 glance；它无法满足新增 Nix 入口独立可运行的目标。把四脚本业务重写成新 Python 包会增加双源与兼容风险，本方案保留脚本与 CLI。

顺序：①固定 inputs/lock 并接入已交 pdfx/vision 接口；②实现同源生成与六 launcher；③导出 agent 包和单 root project；④更新 README 的平台、固定版本、安装、覆盖/移除与 OCR 外部前提；⑤依同目录测试计划执行最小验收，再交结果审核。README 不提前声称其他平台或真实 OCR 就绪。

产品 SHA、实际 launcher store 路径和本包 build/install 结果尚不存在，是实施顺序前提；不能拿本文件提交号当成已实现产品号。实现时将实际 revision 与命令填入简短执行记录，若实际接口事实与上述来源冲突，停止受影响设计并交计划 owner 修订。当前无须等待上游新增接口；本包未实施、未批准、未测试。

## 5. 交接

本计划与测试计划是本次唯一完整候选。下一负责人：独立 reviewer 审核候选；正式计划批准后产品负责人实施；本地测试工程师核对实际输出后执行已确认 recipe。本作者不填写 P1–P4 PASS 或 Plan conclusion: APPROVED，不将历史上游结果冒充本包通过。
