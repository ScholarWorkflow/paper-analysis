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
# file adds a bounded build-time entry-point binding plus fixed launchers: it
# only maps helper variables, helper/quality/OCR invocations and the paths that
# describe them onto the installed bin/* entries.  It never keeps a second copy
# of the business body and never edits the source orchestration rules.

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
    else fail "${label} is missing expected markers: ${lib.concatStringsSep ", " missing}";

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

  # Entry-point leftovers that must never survive the binding.
  oldEntryPoints = [
    "uv run"
    "uvx"
    "FUTURE_WORK_SCRIPT"
    "PAPER_INPUT_SCRIPT"
    "PDF_RUNTIME_SCRIPT"
    "FACTS_SCRIPT"
    "scripts/paper_input.py"
    "scripts/pdf_runtime.py"
    "scripts/future_work.py"
    "scripts/facts.py"
    "`paper_input.py"
    "`pdf_runtime.py"
    "`future_work.py "
  ];

  # Nix must not add a second orchestration story; these markers only exist in a
  # copy that rewrote delegation, tool discovery, spawn/wait or failure rules.
  injectedOrchestration = [
    "## Codex 路由约定（Nix 生成的 Codex 投影）"
    "runtime-native subagent delegation"
    "native spawn capability"
    "delegating natively to the exact"
  ];

  # -------------------------------------------------------------------- agent

  agentSource = splitFrontmatter "paper-analysis.agent.md" ../.apm/agents/paper-analysis.agent.md;

  agentDescription = frontmatterScalar "paper-analysis.agent.md" "description" agentSource.frontmatter;

  agentSteps = [
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
      "2. 四个 helper 都以 `uv run \"<absolute-script>\" ...` 执行。`future_work.py` 与 `pdf_runtime.py` 用 PEP 723 自举正式 release 发行版 `scholar-workflow-pdfx`（exact pin `0.1.0`）；`paper_input.py` 与 `facts.py` 是无第三方依赖的 PEP 723 脚本。"
      "2. Nix 安装副本把四个 helper 绑定到上面的 `bin/*` 固定入口，参数与调用顺序不变；入口用固定 Python 与固定 `scholar-workflow-pdfx` 运行，不需要 uv、PEP 723 自举或宿主 Python。`bin/future-work` 与 `bin/pdf-runtime` 依赖正式 release 发行版 `scholar-workflow-pdfx`（exact pin `0.1.0`）；`bin/paper-input` 与 `bin/facts` 是无第三方依赖的 PEP 723 脚本。")

    (stepOnce
      "6. `pdfx` 不得假设全局安装。质量检查统一通过 uv 运行正式 release 发行版的公共 CLI："
      "6. `pdfx` 不得假设全局安装。质量检查在 Nix 安装副本中统一通过 `bin/pdfx` 运行正式 release 发行版的公共 CLI：")

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
      "好页保留 `PDF_RUNTIME_SCRIPT extract` 提取结果不动"
      "好页保留 `\"$PDF_RUNTIME\" extract` 提取结果不动")

    (stepOnce
      "**normalized JSON** → 必须先经过 `paper_input.py` 确定性校验"
      "**normalized JSON** → 必须先经过 `bin/paper-input` 确定性校验")

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
      "2. 调用 `vision-tools` 的 `glance <页图> --ocr`（"
      "2. 调用安装 skill 的 OCR wrapper `\"$VISION_GLANCE\" <页图> --ocr`（转发到 `vision-tools` 的固定 `vision-glance` app；")

    (stepRequire [
      "<skill_dir>/bin/paper-input"
      "<skill_dir>/bin/pdf-runtime"
      "<skill_dir>/bin/future-work"
      "<skill_dir>/bin/facts"
      "<skill_dir>/bin/pdfx"
      "<skill_dir>/bin/vision-glance"
      "绝不递归"
      "needs_input"
      "gap-only"
    ])

    (stepForbid (oldEntryPoints ++ injectedOrchestration))
  ];

  agentInstructions = applySteps "paper-analysis agent body" agentSteps (lstrip agentSource.body);

  # -------------------------------------------------------------------- skill

  skillSource = splitFrontmatter "SKILL.md" ../.apm/skills/paper-analysis/SKILL.md;

  skillSteps = [
    (stepOnce
      "The agent must run the absolute `scripts/paper_input.py` helper first"
      "The agent must run the installed `bin/paper-input` helper first")

    (stepAll "uv run \"$FACTS_SCRIPT\"" "<skill_dir>/bin/facts")

    (stepOnce
      "- Direct clone/development: run `uv sync --locked` at the repository root. The project dependency is `scholar-workflow-pdfx>=0.1.0,<0.2`, which supplies both `import pdfx` and PyMuPDF transitively."
      "- Nix installation: `<skill_dir>` below is the installed skill root (`<project>/.agents/skills/paper-analysis` for Codex). The `<skill_dir>/bin/*` entries are fixed launchers; each resolves its own installed skill root and runs the fixed Nix Python and `scholar-workflow-pdfx` runtime, so `uv`, PEP 723 bootstrap, a synced checkout, a host Python, and a global `pdfx`/`glance` are not required.\n- Direct clone/development: run `uv sync --locked` at the repository root. The project dependency is `scholar-workflow-pdfx>=0.1.0,<0.2`, which supplies both `import pdfx` and PyMuPDF transitively.")

    (stepOnce
      "- Normalized JSON validator: run `uv run <absolute paper_input.py> <absolute-json-path>` and use only its canonical output."
      "- Normalized JSON validator: run `<skill_dir>/bin/paper-input <absolute-json-path>` and use only its canonical output.")

    (stepOnce
      "- Full-mode PDF extraction/rendering: run `uv run <absolute pdf_runtime.py> extract ...` and `uv run <absolute pdf_runtime.py> render ...`. The PEP 723 helper bootstraps `scholar-workflow-pdfx==0.1.0`, so APM installations do not depend on host PyMuPDF."
      "- Full-mode PDF extraction/rendering: run `<skill_dir>/bin/pdf-runtime extract ...` and `<skill_dir>/bin/pdf-runtime render ...`. The fixed Nix runtime supplies `scholar-workflow-pdfx==0.1.0`, so installations do not depend on host PyMuPDF.")

    (stepOnce
      "- Standalone future-work helper: run `uv run <absolute future_work.py> ...`; PEP 723 metadata bootstraps `scholar-workflow-pdfx==0.1.0` without requiring a synced checkout."
      "- Standalone future-work helper: run `<skill_dir>/bin/future-work ...`; the fixed Nix runtime supplies `scholar-workflow-pdfx==0.1.0` without requiring a synced checkout.")

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

    (stepRequire [
      "registered `paper-analysis` agent"
      "<skill_dir>/bin/paper-input"
      "<skill_dir>/bin/pdf-runtime"
      "<skill_dir>/bin/future-work"
      "<skill_dir>/bin/facts"
      "<skill_dir>/bin/pdfx"
      "<skill_dir>/bin/vision-glance"
    ])

    (stepForbid (oldEntryPoints ++ injectedOrchestration ++ [
      "<absolute paper_input.py>"
      "<absolute pdf_runtime.py>"
      "<absolute future_work.py>"
      "<absolute facts.py>"
      "`future_work.py merge-ocr"
      "`future_work.py upgrade-full-sidecar"
    ]))
  ];

  skillText = applySteps "SKILL.md" skillSteps (joinFrontmatter skillSource skillSource.body);

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
