{ pkgs
, mkAgentPackage
, mkProject
, pdfx
, visionTools
, visionGlanceProgram
}:

# Nix delivery for the paper-analysis Codex skill.
#
# The APM skill/agent sources under .apm/ remain the only business source.  This
# file adds a bounded build-time entry-point conversion plus fixed launchers; it
# never keeps a second copy of the business body.

let
  inherit (pkgs) lib;

  fail = message: throw "paper-analysis-nix: ${message}";

  # ---------------------------------------------------------------- frontmatter

  # Both APM documents carry exactly one "---" frontmatter separator.  Anything
  # else is a source-format change this bounded conversion refuses to guess at.
  splitFrontmatter = label: file:
    let parts = lib.splitString "\n---\n" (builtins.readFile file);
    in if builtins.length parts == 2
    then {
      frontmatter = builtins.head parts;
      body = builtins.elemAt parts 1;
    }
    else fail "${label} must contain exactly one '---' frontmatter separator";

  # Read one single-line YAML scalar without pretending to be a YAML parser: the
  # source frontmatter uses one plain or single-quoted line per key.  Anything
  # that needs escaping is rejected instead of silently mis-parsed.
  frontmatterScalar = label: key: frontmatter:
    let
      prefix = "${key}: ";
      matches = builtins.filter (line: lib.hasPrefix prefix line) (lib.splitString "\n" frontmatter);
    in
    if builtins.length matches != 1
    then fail "${label}: expected exactly one '${key}:' frontmatter line"
    else
      let raw = lib.removePrefix prefix (builtins.head matches);
      in if lib.hasPrefix "'" raw && lib.hasSuffix "'" raw
      then
        let value = builtins.substring 1 (builtins.stringLength raw - 2) raw;
        in if lib.hasInfix "''" value
        then fail "${label}: '${key}' uses YAML quote escaping this bounded conversion does not support"
        else value
      else raw;

  joinFrontmatter = parsed: body: "${parsed.frontmatter}\n---\n${body}";

  # ------------------------------------------------------------- text rewriting

  replaceOnce = label: from: to: text:
    let parts = lib.splitString from text;
    in if builtins.length parts == 2
    then "${builtins.head parts}${to}${builtins.elemAt parts 1}"
    else fail "${label}: expected exactly one occurrence of '${from}' (found ${toString (builtins.length parts - 1)})";

  replaceAll = from: to: text: lib.replaceStrings [ from ] [ to ] text;

  applySteps = label: steps: text: builtins.foldl' (acc: step: step label acc) text steps;

  stepOnce = from: to: label: text: replaceOnce label from to text;
  stepAll = from: to: label: text: replaceAll from to text;

  requireInfixes = label: needles: text:
    let missing = builtins.filter (needle: !(lib.hasInfix needle text)) needles;
    in if missing == []
    then text
    else fail "${label} is missing expected converted markers: ${lib.concatStringsSep ", " missing}";

  forbidInfixes = label: needles: text:
    let hits = builtins.filter (needle: lib.hasInfix needle text) needles;
    in if hits == []
    then text
    else fail "${label} still contains unconverted entry points: ${lib.concatStringsSep ", " hits}";

  stepRequire = needles: label: text: requireInfixes label needles text;
  stepForbid = needles: label: text: forbidInfixes label needles text;

  lstrip = text:
    let
      head = builtins.substring 0 1 text;
      rest = builtins.substring 1 (builtins.stringLength text - 1) text;
    in if head == "\n" || head == " " || head == "\t" then lstrip rest else text;

  # -------------------------------------------------------------------- agent

  agentSource = splitFrontmatter "paper-analysis.agent.md" ../.apm/agents/paper-analysis.agent.md;

  agentDescriptionRaw = frontmatterScalar "paper-analysis.agent.md" "description" agentSource.frontmatter;

  codexRouting = ''
    ## Codex 路由约定（Nix 生成的 Codex 投影）

    - 运行环境是 Codex；调用方用运行时正式提供的 native subagent delegation 按 exact name `paper-analysis` 启动本角色，并在委派后等待、消费本角色返回的最终消息。不得用 shell `codex exec`、`opencode run`、curl 或另起 `/eval` 请求代替。
    - 本角色是 specialized coordinator child，负责同一篇论文的完整 workflow；不承担无关任务，不自我委派，也不加载或再次 spawn `paper-analysis`。
    - `mode: full` 的 Step 3 用同一运行面提供的 native spawn 分派 3 个有界只读工作单元，再用同一运行面的 native wait 等待并消费结果；不固定私有 namespace、参数签名或事件 schema。
    - 只有本次运行真实调用 native delegation 并收到 machine-level failure 时，才允许报告 delegation blocker；零次真实调用不得报告该 blocker。
    - Codex 没有原生 `question` 工具；缺必要用户输入时按 needs_input 约定 yield 明确状态，要求 parent 拿到答案后 resume 同一 coordinator 线程。

  '';

  agentSteps = [
    (stepOnce "## 深度约束（先读，违反即出错）" "${codexRouting}## 深度约束（先读，违反即出错）")

    (stepOnce
      "You are spawned by the `paper-analysis` skill via the Task tool —"
      "You are spawned by the `paper-analysis` skill through runtime-native subagent delegation —")

    (stepOnce
      "## 输入（由 task prompt 传入）"
      "## 输入（由 delegation prompt 传入）")

    (stepOnce
      "- **Codex full Step 3 必须使用运行时原生 subagent delegation**：`mode: full` 到达 Step 3 且需要三路分析时，先绑定当前调用面实际提供的 subagent spawn capability，再用该 exact callable 分派三个有界只读分析工作单元，随后绑定 wait capability、等待并消费三路结果。直接工具面提供 `spawn_agent` 时直接调用它；Code Mode 只提供延迟工具目录时，从 `ALL_TOOLS` 按工具说明定位 spawn capability 与 wait capability，再调用目录列出的 exact callable。不要把 OpenCode 专属的 `task` 字段当作 Codex 接口。"
      "- **Codex full Step 3 必须使用运行时原生 subagent delegation**：`mode: full` 到达 Step 3 且需要三路分析时，直接使用本次运行正式提供的 native spawn capability（公开 `spawn_agent`）分派三个有界只读分析工作单元，再用同一运行面提供的 native wait 等待并消费三路结果。不要把 OpenCode 专属的 `task` 字段当作 Codex 接口；不需要先做 tool、catalog 或 programmatic discovery。")

    (stepOnce
      "- **Codex Step 3 工具绑定规则**：Code Mode 下按语义匹配“spawn a sub-agent”的工具说明，并以目录返回的完整 `name` 为准；不得假定它一定是 `tools.spawn_agent`，不得用 `typeof tools.spawn_agent` 或固定属性名自检来伪造 `spawn_agent not exposed`。工具绑定本身不算委派尝试；只有 spawn 调用返回 agent id 才计为已发起。为三个不同语义角色各调用一次，三次都返回 agent id 后再等待；不得把一次错误名称检查包装成三路失败。**零次真实 native 委派尝试时禁止返回 `delegation unavailable` 或等价 blocker**。"
      "- **Codex Step 3 委派规则**：直接调用运行时正式提供的 native spawn，按语义把它用于三个不同角色，不固定私有 namespace、参数签名、request schema 或未文档化事件字段，也不以工具可用性检查代替委派。工具可用性检查不算委派尝试；只有 spawn 调用返回 agent id 才计为已发起。为三个不同语义角色各调用一次，三次都返回 agent id 后再等待；不得把一次错误名称检查包装成三路失败。**零次真实 native 委派尝试时禁止返回 `delegation unavailable` 或等价 blocker**。")

    (stepOnce
      "- **Codex Step 3 blocker 只能来自真实委派调用失败**：只有本次 full run 已调用实际绑定的 spawn capability，且该调用返回 runtime machine-level delegation failure 时，才允许报告 delegation blocker；这时明确返回失败并说明是哪一路，不得 inline 自己完成三路分析，也不得猜测补齐结果。`exec_command` shell、`codex exec`、`opencode run`、curl、另起 `/eval` 都不是 delegation fallback。"
      "- **Codex Step 3 blocker 只能来自真实委派调用失败**：只有本次 full run 已调用 native spawn，且该调用返回 runtime machine-level delegation failure 时，才允许报告 delegation blocker；这时明确返回失败并说明是哪一路，不得 inline 自己完成三路分析，也不得猜测补齐结果。`exec_command` shell、`codex exec`、`opencode run`、curl、另起 `/eval` 都不是 delegation fallback。")

    (stepOnce
      "- **coordinator 不得 inline 执行三路分析来替代 delegation**：三路分析结果必须全部来自 delegated child 返回；等待并消费全部三路结果后 coordinator 才执行 Step 4 组装。任一 required child 失败都必须明确报告，coordinator 不得猜测、补写或伪造 child 结果。OpenCode 运行时继续保留其原生 `task` / `permission` / `question` contract，本条不改变 OpenCode 行为。"
      "- **coordinator 不得 inline 执行三路分析来替代 delegation**：三路分析结果必须全部来自 delegated child 返回；等待并消费全部三路结果后 coordinator 才执行 Step 4 组装。任一 required child 失败都必须明确报告，coordinator 不得猜测、补写或伪造 child 结果。")

    (stepOnce
      "1. 先解析当前 skill 的绝对目录，并得到："
      "1. 先解析当前安装 skill 的绝对目录 `<skill_dir>`（Codex 项目安装为 `<project>/.agents/skills/paper-analysis`），并得到：")

    (stepOnce
      "   - `FUTURE_WORK_SCRIPT=<skill_dir>/scripts/future_work.py`"
      "   - `FUTURE_WORK=<skill_dir>/bin/future-work`")

    (stepOnce
      "   - `PAPER_INPUT_SCRIPT=<skill_dir>/scripts/paper_input.py`"
      "   - `PAPER_INPUT=<skill_dir>/bin/paper-input`")

    (stepOnce
      "   - `PDF_RUNTIME_SCRIPT=<skill_dir>/scripts/pdf_runtime.py`"
      "   - `PDF_RUNTIME=<skill_dir>/bin/pdf-runtime`")

    (stepOnce
      "   - `FACTS_SCRIPT=<skill_dir>/scripts/facts.py`"
      "   - `FACTS=<skill_dir>/bin/facts`\n   - `PDFX=<skill_dir>/bin/pdfx`\n   - `VISION_GLANCE=<skill_dir>/bin/vision-glance`")

    (stepOnce
      "   后续永远使用这些绝对路径，不假设当前工作目录位于仓库根目录。"
      "   每个入口自行解析安装 skill 根；后续永远使用这些绝对路径，不使用 caller 当前工作目录、源码 `.apm` 路径或宿主 Python。")

    (stepOnce
      "2. 四个 helper 都以 `uv run \"<absolute-script>\" ...` 执行。`future_work.py` 与 `pdf_runtime.py` 用 PEP 723 自举正式 release 发行版 `scholar-workflow-pdfx`（exact pin `0.1.0`）；`paper_input.py` 与 `facts.py` 是无第三方依赖的 PEP 723 脚本。"
      "2. 六个固定入口（`bin/paper-input`、`bin/pdf-runtime`、`bin/future-work`、`bin/facts`、`bin/pdfx`、`bin/vision-glance`）由 Nix 安装提供，用固定 Python 与固定 `scholar-workflow-pdfx` 运行；运行时不需要 uv、PEP 723 自举、宿主 Python 或全局 `pdfx`/`glance`，直接以绝对路径调用即可，例如 `\"$FUTURE_WORK\" prepare ...`。")

    (stepOnce
      "6. `pdfx` 不得假设全局安装。质量检查统一通过 uv 运行正式 release 发行版的公共 CLI："
      "6. `pdfx` 不得假设全局安装。质量检查统一通过安装 skill 的固定入口运行正式 release 发行版的公共 CLI：")

    (stepAll
      "uvx --from \"scholar-workflow-pdfx==0.1.0\" pdfx quality"
      "\"$PDFX\" quality")

    (stepAll "uv run \"$FUTURE_WORK_SCRIPT\"" "\"$FUTURE_WORK\"")
    (stepAll "uv run \"$PAPER_INPUT_SCRIPT\"" "\"$PAPER_INPUT\"")
    (stepAll "uv run \"$PDF_RUNTIME_SCRIPT\"" "\"$PDF_RUNTIME\"")
    (stepAll "uv run \"$FACTS_SCRIPT\"" "\"$FACTS\"")

    (stepOnce
      "运行一次确定性的 `future_work.py prepare`"
      "运行一次确定性的 `\"$FUTURE_WORK\" prepare`")

    (stepOnce
      "Step 1.5 完成后运行 `future_work.py prepare`"
      "Step 1.5 完成后运行 `\"$FUTURE_WORK\" prepare`")

    (stepOnce
      "先运行 `PAPER_INPUT_SCRIPT`"
      "先运行 `bin/paper-input`")

    (stepOnce
      "只有 `pdf_runtime.py validate-ocr-cache` 校验当前 PDF"
      "只有 `bin/pdf-runtime validate-ocr-cache` 校验当前 PDF")

    (stepOnce
      "若后续 `future_work.py prepare` 报告"
      "若后续 `bin/future-work prepare` 报告")

    (stepOnce
      "好页保留 `PDF_RUNTIME_SCRIPT extract` 提取结果不动"
      "好页保留 `\"$PDF_RUNTIME\" extract` 提取结果不动")

    (stepOnce
      "**normalized JSON** → 必须先经过 `paper_input.py` 确定性校验"
      "**normalized JSON** → 必须先经过 `bin/paper-input` 确定性校验")

    (stepOnce
      "2. 调用 `vision-tools` 的 `glance <页图> --ocr`（免费模型 429 → 自动切付费兜底，见 vision-tools skill）；"
      "2. 调用安装 skill 的 OCR wrapper `\"$VISION_GLANCE\" <页图> --ocr`（固定转发到本次安装的 vision-tools `vision-glance` app；免费模型 429 → 自动切付费兜底，见 vision-tools skill）；")

    (stepOnce
      "将全文放入临时文件后，Step 3 必须恰好分派 exactly 3 个有界只读分析工作单元，分别对应表中的三路语义角色；三路结果必须全部来自 delegated child，coordinator 不得 inline 完成或降级为 best-effort。分派是硬门槛：先绑定当前调用面实际提供的 subagent spawn capability；直接工具面调用公开 `spawn_agent`，Code Mode 延迟工具面从 `ALL_TOOLS` 按说明取得完整工具名并调用该 exact callable，绝不检查一个臆测的固定属性名。工具绑定本身不算委派尝试；只有 spawn 调用返回 agent id 才计为已发起。用 generic/default leaf 为表中三个角色各发起一次调用。三路调用都发起后，等待并消费三路 child 返回的 Markdown，才进入 Step 4；Code Mode 用同样方式绑定目录中的 wait capability。只有实际绑定的 spawn capability 调用返回 runtime machine-level delegation failure 时，才允许把本次运行报告成 delegation blocker；本次未真实发起 required 委派调用时禁止该结论。`exec_command` shell、`codex exec`、`opencode run`、curl、另起 `/eval` 都不是 delegation fallback，走任一替代路径都算违反本 contract。每个工作单元只接收全文路径、角色和产出要求，直接返回 Markdown，不修改文件；某一路失败就明确报告，不得由 coordinator 猜测、补写或伪造该路结果。"
      "将全文放入临时文件后，Step 3 必须恰好分派 exactly 3 个有界只读分析工作单元，分别对应表中的三路语义角色；三路结果必须全部来自 delegated child，coordinator 不得 inline 完成或降级为 best-effort。分派是硬门槛：直接调用运行时正式提供的 native spawn capability（公开 `spawn_agent`），不固定私有 namespace、参数签名或事件 schema，也不依赖 tool、catalog 或 programmatic discovery。工具可用性检查不算委派尝试；只有 spawn 调用返回 agent id 才计为已发起。用 generic/default leaf 为表中三个角色各发起一次调用。三路调用都发起后，用同一运行面提供的 native wait 等待并消费三路 child 返回的 Markdown，才进入 Step 4。只有本次真实调用的 native spawn 返回 runtime machine-level delegation failure 时，才允许把本次运行报告成 delegation blocker；本次未真实发起 required 委派调用时禁止该结论。`exec_command` shell、`codex exec`、`opencode run`、curl、另起 `/eval` 都不是 delegation fallback，走任一替代路径都算违反本 contract。每个工作单元只接收全文路径、角色和产出要求，直接返回 Markdown，不修改文件；某一路失败就明确报告，不得由 coordinator 猜测、补写或伪造该路结果。")
  ];

  agentDescription = applySteps "paper-analysis agent description" [
    (stepOnce "由 paper-analysis skill 通过 task 启动。" "由 paper-analysis skill 通过运行时原生 subagent delegation 启动。")
    (stepOnce "以 future_work.py prepare/validate/finalize 作为唯一证据写入流程。" "以 `bin/future-work` prepare/validate/finalize 作为唯一证据写入流程。")
  ] agentDescriptionRaw;

  agentInstructions = applySteps "paper-analysis agent body" (agentSteps ++ [
    (stepRequire [
      "## Codex 路由约定（Nix 生成的 Codex 投影）"
      "native spawn"
      "native wait"
      "needs_input"
      "绝不递归"
      "$FUTURE_WORK"
      "$PAPER_INPUT"
      "$PDF_RUNTIME"
      "$FACTS"
      "$PDFX"
      "$VISION_GLANCE"
    ])
    (stepForbid [
      "uv run"
      "uvx"
      "ALL_TOOLS"
      "Code Mode"
      "Task tool"
      "tools.spawn_agent"
      "FUTURE_WORK_SCRIPT"
      "PAPER_INPUT_SCRIPT"
      "PDF_RUNTIME_SCRIPT"
      "FACTS_SCRIPT"
      "scripts/paper_input.py"
      "scripts/pdf_runtime.py"
      "scripts/future_work.py"
      "scripts/facts.py"
      "`future_work.py prepare"
      "`paper_input.py"
      "`pdf_runtime.py"
      "`facts.py validate"
    ])
  ]) (lstrip agentSource.body);

  # -------------------------------------------------------------------- skill

  skillSource = splitFrontmatter "SKILL.md" ../.apm/skills/paper-analysis/SKILL.md;

  skillSteps = [
    (stepOnce
      "This skill starts the registered `paper-analysis` agent. It accepts one of:"
      "This skill starts the native `paper-analysis` agent through runtime-native subagent delegation and waits for and consumes the delegated result. It accepts one of:")

    (stepOnce
      "The agent must run the absolute `scripts/paper_input.py` helper first"
      "The agent must run the installed `bin/paper-input` helper first")

    (stepOnce
      "For saved local-PDF `mode: full`, include these instructions when spawning the registered `paper-analysis` agent:"
      "For saved local-PDF `mode: full`, include these instructions when delegating natively to the exact `paper-analysis` agent, and consume the result it returns:")

    (stepAll "uv run \"$FACTS_SCRIPT\"" "<skill_dir>/bin/facts")

    (stepOnce
      "- Direct clone/development: run `uv sync --locked` at the repository root. The project dependency is `scholar-workflow-pdfx>=0.1.0,<0.2`, which supplies both `import pdfx` and PyMuPDF transitively."
      "- Nix installation: `<skill_dir>` below is the installed skill root (`<project>/.agents/skills/paper-analysis` for Codex). The `<skill_dir>/bin/*` entries are fixed launchers; each resolves its own installed skill root and runs the fixed Nix Python and `scholar-workflow-pdfx` runtime, so `uv`, PEP 723 bootstrap, a synced checkout, a host Python, and a global `pdfx`/`glance` are not required.\n- Direct clone/development: run `uv sync --locked` at the repository root. The project dependency is `scholar-workflow-pdfx>=0.1.0,<0.2`, which supplies both `import pdfx` and PyMuPDF transitively.")

    (stepOnce
      "- Normalized JSON validator: run `uv run <absolute paper_input.py> <absolute-json-path>` and use only its canonical output."
      "- Normalized JSON validator: run `<skill_dir>/bin/paper-input <absolute-json-path>` and use only its canonical output.")

    (stepOnce
      "- Full-mode PDF extraction/rendering: run `uv run <absolute pdf_runtime.py> extract ...` and `uv run <absolute pdf_runtime.py> render ...`. The PEP 723 helper bootstraps `scholar-workflow-pdfx==0.1.0`, so APM installations do not depend on host PyMuPDF."
      "- Full-mode PDF extraction/rendering: run `<skill_dir>/bin/pdf-runtime extract ...` and `<skill_dir>/bin/pdf-runtime render ...`.")

    (stepOnce
      "- Standalone future-work helper: run `uv run <absolute future_work.py> ...`; PEP 723 metadata bootstraps `scholar-workflow-pdfx==0.1.0` without requiring a synced checkout."
      "- Standalone future-work helper: run `<skill_dir>/bin/future-work ...`.")

    (stepOnce
      "- Structured facts helper: run `uv run <absolute facts.py> validate ...` / `finalize ...`. It has no third-party dependencies and never invokes a model or parses the analysis Markdown for facts."
      "- Structured facts helper: run `<skill_dir>/bin/facts validate ...` / `finalize ...`. It has no third-party dependencies and never invokes a model or parses the analysis Markdown for facts.")

    (stepOnce
      "- PDF quality CLI: invoke it through the released distribution, e.g. `uvx --from \"scholar-workflow-pdfx==0.1.0\" pdfx quality \"<PDF>\" --json`. Do not assume a global `pdfx` executable."
      "- PDF quality CLI: run `<skill_dir>/bin/pdfx quality \"<PDF>\" --json`. Do not assume a global `pdfx` executable.\n- OCR wrapper: run `<skill_dir>/bin/vision-glance <image> --ocr`; it forwards to the fixed `vision-tools` `vision-glance` app installed with this package.")

    (stepOnce
      "use the uv-managed PDF runtime helper."
      "use the installed `bin/pdf-runtime` helper.")

    (stepOnce
      "Run `future_work.py prepare` for the source PDF before Step 3."
      "Run `<skill_dir>/bin/future-work prepare` for the source PDF before Step 3.")

    (stepOnce
      "reuse the exact page OCR text through `future_work.py merge-ocr`"
      "reuse the exact page OCR text through `<skill_dir>/bin/future-work merge-ocr`")

    (stepOnce
      "run `future_work.py upgrade-full-sidecar` against"
      "run `<skill_dir>/bin/future-work upgrade-full-sidecar` against")
  ];

  skillText = applySteps "SKILL.md" (skillSteps ++ [
    (stepRequire [
      "runtime-native subagent delegation"
      "consumes the delegated result"
      "<skill_dir>/bin/paper-input"
      "<skill_dir>/bin/pdf-runtime"
      "<skill_dir>/bin/future-work"
      "<skill_dir>/bin/facts"
      "<skill_dir>/bin/pdfx"
      "<skill_dir>/bin/vision-glance"
    ])
    (stepForbid [
      "uv run"
      "uvx"
      "registered `paper-analysis` agent"
      "FACTS_SCRIPT"
      "`future_work.py prepare"
      "`future_work.py merge-ocr"
      "`future_work.py upgrade-full-sidecar"
      "`pdf_runtime.py"
      "`paper_input.py"
      "scripts/paper_input.py"
      "scripts/pdf_runtime.py"
      "scripts/future_work.py"
      "scripts/facts.py"
      "<absolute paper_input.py>"
      "<absolute pdf_runtime.py>"
      "<absolute future_work.py>"
      "<absolute facts.py>"
    ])
  ]) (joinFrontmatter skillSource skillSource.body);

  # ---------------------------------------------------------------- launchers

  coreutils = pkgs.coreutils;

  # Every launcher takes its own installed path, not the caller cwd, and never
  # reaches back into the source checkout.
  mkLauncher = name: text: pkgs.writeTextFile {
    name = "paper-analysis-${name}";
    destination = "/bin/${name}";
    executable = true;
    text = ''
      #!${pkgs.bash}/bin/bash
      ${text}
    '';
  };

  scriptLauncher = name: script: mkLauncher name ''
    set -euo pipefail
    self=$(${coreutils}/bin/readlink -f -- "$0")
    skill_root=$(${coreutils}/bin/dirname -- "$(${coreutils}/bin/dirname -- "$self")")
    exec ${pdfx.python}/bin/python3 "$skill_root/scripts/${script}" "$@"
  '';

  appLauncher = name: program: mkLauncher name ''
    set -euo pipefail
    exec ${program} "$@"
  '';

  launcherNames = [
    "paper-input"
    "pdf-runtime"
    "future-work"
    "facts"
    "pdfx"
    "vision-glance"
  ];

  launcherDerivations = {
    paper-input = scriptLauncher "paper-input" "paper_input.py";
    pdf-runtime = scriptLauncher "pdf-runtime" "pdf_runtime.py";
    future-work = scriptLauncher "future-work" "future_work.py";
    facts = scriptLauncher "facts" "facts.py";
    pdfx = appLauncher "pdfx" "${pdfx.pdfx}/bin/pdfx";
    vision-glance = appLauncher "vision-glance" visionGlanceProgram;
  };

  launchers = pkgs.runCommand "paper-analysis-launchers" { } ''
    mkdir -p "$out/bin"
    ${lib.concatStringsSep "\n" (lib.mapAttrsToList
      (name: derivation: ''cp ${derivation}/bin/${name} "$out/bin/${name}"'')
      launcherDerivations)}
    chmod 0555 "$out"/bin/*
  '';

  # ------------------------------------------------------------- skill payload

  skillDerivation = pkgs.runCommand "paper-analysis-skill" { } ''
    mkdir -p "$out"
    cp -R ${../.apm/skills/paper-analysis}/. "$out/"
    chmod -R u+w "$out"
    cp ${pkgs.writeText "paper-analysis-SKILL.md" skillText} "$out/SKILL.md"
    mkdir -p "$out/bin"
    cp -R ${launchers}/bin/. "$out/bin/"
    chmod 0555 "$out"/bin/*
  '';

  # --------------------------------------------------------------- packaging

  versionLines = builtins.filter (line: lib.hasPrefix "version: " line)
    (lib.splitString "\n" (builtins.readFile ../apm.yml));

  version =
    if builtins.length versionLines == 1
    then lib.removePrefix "version: " (builtins.head versionLines)
    else fail "apm.yml must declare exactly one 'version:' line";

  package = mkAgentPackage {
    inherit pkgs;
    id = "paper-analysis";
    inherit version;
    files."skills/paper-analysis" = skillDerivation;
    exports = {
      skills.paper-analysis = "skills/paper-analysis";
      agents.paper-analysis = {
        description = agentDescription;
        developer_instructions = agentInstructions;
      };
    };
    agentDependencies = [ visionTools ];
    runtimePackages = [ pdfx.python pdfx.pdfx launchers ];
    enableHarnesses = [ "codex" ];
  };

  project = mkProject {
    inherit pkgs;
    name = "paper-analysis-project";
    roots = [ package ];
  };
in
{
  inherit package project launchers skillDerivation launcherNames;
}
