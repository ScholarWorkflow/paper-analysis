import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = REPO_ROOT / ".apm/skills/paper-analysis"
AGENT = REPO_ROOT / ".apm/agents/paper-analysis.agent.md"
SKILL = SKILL_ROOT / "SKILL.md"
APM_YML = REPO_ROOT / "apm.yml"
PYPROJECT = REPO_ROOT / "pyproject.toml"
UVLOCK = REPO_ROOT / "uv.lock"
PAPER_INPUT = SKILL_ROOT / "scripts/paper_input.py"
PDF_RUNTIME = SKILL_ROOT / "scripts/pdf_runtime.py"
FUTURE_WORK = SKILL_ROOT / "scripts/future_work.py"
FACTS = SKILL_ROOT / "scripts/facts.py"
FIXTURES = Path(__file__).parent / "fixtures"

RELEASE_DISTRIBUTION = "scholar-workflow-pdfx"
RELEASE_PIN = RELEASE_DISTRIBUTION + "==0.1.0"
RELEASE_RANGE = RELEASE_DISTRIBUTION + ">=0.1.0,<0.2"

# Forbidden moving-main patterns are composed at runtime so this test file
# never contains the contiguous strings: a repo-wide forbidden-pattern grep
# must stay clean while the gate itself still matches real occurrences.
FORBIDDEN_GIT_MAIN_DEP = "pdf-processing-core" + ".git@main"
FORBIDDEN_GIT_URL = "git+https://github.com/ScholarWorkflow/" + "pdf-processing-core"
FORBIDDEN_BRANCH_MAIN = 'branch ' + '= "main"'
FORBIDDEN_LOCK_GIT_SOURCE = (
    'source = { git = "https://github.com/ScholarWorkflow/' + 'pdf-processing-core'
)

CENTRAL_RUNTIME_MARKERS = (
    "scholarflow-codex",
    "central-launcher",
    "central normalizer",
    "consumer overlay",
)

PRODUCTION_FILES = (AGENT, SKILL, PAPER_INPUT, PDF_RUNTIME, FUTURE_WORK, FACTS, APM_YML, PYPROJECT)

REQUIRED_ORCHESTRATION_CONVENTIONS = (
    # (convention id, exact marker that must appear in the agent body)
    ("coordinator identity", "specialized coordinator child"),
    ("no-recursion", "不要加载 `paper-analysis` skill"),
    ("full leaf no-child-spawn", "不再分派子工作"),
    ("gap-only no full leaves", "绝不进入 Step 3 或 spawn"),
    ("codex full step3 native delegation",
     "Codex full Step 3 必须使用运行时原生 subagent delegation"),
    ("codex full step3 no inline replacement",
     "coordinator 不得 inline 执行三路分析来替代 delegation"),
    ("codex full step3 exactly three delegated units",
     "Step 3 必须恰好分派 exactly 3 个有界只读分析工作单元"),
    ("codex step3 direct native spawn_agent call",
     "required Step-3 child 必须靠直接调用当前 Codex 运行时暴露的公开 "
     "`spawn_agent` 多代理工具来分派三个有界只读分析工作单元，随后等待并消费三路结果"),
    ("codex step3 no private schema or event field",
     "只固定该公开工具名，不固定私有 namespace、参数 schema、request schema "
     "或未文档化的 runtime event 字段"),
    ("codex step3 no capability-probe precondition",
     "不得要求在三路分析之前先查询运行时工具目录、代码执行式调用面或任何能力探测结论"
     "来确认 `spawn_agent` 可用"),
    ("codex step3 probe evidence alone is not a blocker",
     "都不得单独作为 delegation blocker 依据"),
    ("codex step3 zero-attempt blocker forbidden",
     "**零次真实 native 委派尝试时禁止返回 `delegation unavailable` 或等价 blocker**"),
    ("codex step3 blocker needs machine-level delegation failure",
     "只有本次 full run 已按要求真实发起 `spawn_agent` 委派，且该调用返回 runtime "
     "machine-level delegation failure 时，才允许报告 delegation blocker"),
    ("codex step3 no shell curl eval fallback",
     "`exec_command` shell、`codex exec`、`opencode run`、curl、另起 `/eval` "
     "都不是 delegation fallback"),
    ("codex step3 required child failure explicit no guess",
     "任一 required child 失败都必须明确报告，coordinator 不得猜测、补写或伪造 child 结果"),
    ("codex step3 wait and consume before step4",
     "三路调用都发起后，等待并消费三路 child 返回的 Markdown，才进入 Step 4"),
    ("codex step3 attempt precedes analysis without probe verdict",
     "不得先等工具目录或能力探测出结论，也不因某处没列出该工具就改判能力不可用"),
    ("opencode native contract unchanged",
     "OpenCode 运行时继续保留其原生 `task` / `permission` / `question` contract"),
    ("codex step3 zero-attempt final check before return",
     "零次真实调用时禁止返回 `delegation unavailable` 或等价 blocker"),
    ("leaf failure no guessing", "任何分析单元失败都必须明确报告，不得用猜测补齐"),
    ("native question priority", "必须优先使用原生 `question`"),
    ("needs_input no silent default", "不得静默选择默认值"),
    ("needs_input same-thread resume", "resume 同一 coordinator"),
    ("convention not security boundary", "不是安全边界"),
)

# The two load-bearing Codex full-mode Step 3 delegation markers (issue #13).
# They are duplicated here as standalone constants so the dedicated tests name
# them exactly; the mutation gate below keeps each one individually load
# bearing.
CODEX_FULL_DELEGATION_MARKERS = (
    "Codex full Step 3 必须使用运行时原生 subagent delegation",
    "coordinator 不得 inline 执行三路分析来替代 delegation",
    "Step 3 必须恰好分派 exactly 3 个有界只读分析工作单元",
)

# Direct-native delegation contract (issue #16): Codex full-mode Step 3 calls the
# public `spawn_agent` tool directly, never through a capability-probe preflight,
# and may only report a delegation blocker after that real call returns a
# machine-level failure. Shell/curl/new-eval remain non-fallbacks.
CODEX_STEP3_DIRECT_NATIVE_MARKERS = (
    "required Step-3 child 必须靠直接调用当前 Codex 运行时暴露的公开 "
    "`spawn_agent` 多代理工具来分派三个有界只读分析工作单元，随后等待并消费三路结果",
    "不得要求在三路分析之前先查询运行时工具目录、代码执行式调用面或任何能力探测结论"
    "来确认 `spawn_agent` 可用",
    "**零次真实 native 委派尝试时禁止返回 `delegation unavailable` 或等价 blocker**",
    "只有本次 full run 已按要求真实发起 `spawn_agent` 委派，且该调用返回 runtime "
    "machine-level delegation failure 时，才允许报告 delegation blocker",
    "`exec_command` shell、`codex exec`、`opencode run`、curl、另起 `/eval` "
    "都不是 delegation fallback",
)

# Retired runtime-specific mechanism (issue #16): reject the old
# discovery-as-prerequisite relationship and private tool identifiers. Ordinary
# words such as "discovery" or "programmatic" remain legal in diagnostics.
RETIRED_DISCOVERY_PREFLIGHT_CLAUSES = (
    "在执行任何三路分析内容前，必须先通过当前 Codex 运行时的 Code Mode "
    "/ programmatic tool-calling surface 发现实际可调用的原生 multi-agent "
    "delegation 工具",
    "Code Mode `exec` 作为 programmatic tool caller 是允许的",
    "明确返回 delegation-capability failure",
    "先发现后分派",
)
RETIRED_PRIVATE_TOOL_IDENTIFIERS = ("ALL_TOOLS", "multi_agent_v1")

# The three full-mode Step 3 semantic roles must survive unchanged; the Codex
# delegation contract changes the dispatch mechanism, never the business
# structure.
FULL_MODE_STEP3_SEMANTIC_ROLES = ("内容沉淀", "贡献与批判", "帮助评估")

# Every production surface that owns the "a required child failure is reported,
# never guessed" invariant (issue #16 Gate 2 必须修改 5). Each entry is checked
# inside its own heading region so a rewrite of one section cannot silently drop
# the clause while another section keeps the gate green.
CHILD_FAILURE_SURFACES = (
    ("depth constraints", "## 深度约束", "## 交互与运行时兼容约定",
     "任何分析单元失败都必须明确报告，不得用猜测补齐"),
    ("orchestration convention", "## 交互与运行时兼容约定", "## 输入（由 task prompt 传入）",
     "任一 required child 失败都必须明确报告，coordinator 不得猜测、补写或伪造 child 结果"),
    ("step3 body", "### Step 3 — 并行子代理", "### Step 4",
     "某一路失败就明确报告，不得由 coordinator 猜测、补写或伪造该路结果"),
    ("troubleshooting", "## Troubleshooting", None,
     "明确报告失败原因，不用猜测内容替代"),
)


def _section(text: str, start: str, end: str | None) -> str:
    start_index = text.index(start)
    end_index = len(text) if end is None else text.index(end, start_index)
    return text[start_index:end_index]


def assert_no_retired_discovery_preflight(agent_text: str) -> None:
    """Reject only the retired delegation preflight contract, not diagnostic words."""
    private_hits = [
        marker for marker in RETIRED_PRIVATE_TOOL_IDENTIFIERS if marker in agent_text
    ]
    codex_contract = (
        _section(
            agent_text,
            "## 交互与运行时兼容约定",
            "## 输入（由 task prompt 传入）",
        )
        + _section(agent_text, "### Step 3 — 并行子代理", "### Step 4")
    )
    preflight_hits = [
        clause
        for clause in RETIRED_DISCOVERY_PREFLIGHT_CLAUSES
        if clause in codex_contract
    ]
    if private_hits or preflight_hits:
        raise AssertionError(
            "retired Codex discovery-preflight contract present: "
            + ", ".join(private_hits + preflight_hits)
        )


def assert_orchestration_contract(agent_text: str) -> None:
    """Raise AssertionError when a required orchestration convention is missing.

    This is the single gate for the producer-local coordination conventions that
    must survive every runtime projection (OpenCode native fields and the Codex
    developer_instructions body).
    """
    missing = [
        name
        for name, marker in REQUIRED_ORCHESTRATION_CONVENTIONS
        if marker not in agent_text
    ]
    if missing:
        raise AssertionError(
            "missing orchestration conventions: " + ", ".join(missing)
        )
    assert_no_retired_discovery_preflight(agent_text)


class AgentRuntimeContractTests(unittest.TestCase):
    def test_normalized_json_uses_deterministic_helper(self):
        text = AGENT.read_text(encoding="utf-8")
        self.assertIn("PAPER_INPUT_SCRIPT", text)
        self.assertIn('uv run "$PAPER_INPUT_SCRIPT"', text)
        self.assertIn("paper_input.canonical.json", text)
        self.assertIn("只消费", text)

    def test_supported_input_contract_is_zotero_free(self):
        agent = AGENT.read_text(encoding="utf-8")
        skill = SKILL.read_text(encoding="utf-8")
        self.assertIn("四种之一", agent)
        self.assertIn("四选一", agent)
        self.assertNotIn("旧版 Zotero item key", agent)
        self.assertNotIn("deprecated compatibility", agent)
        self.assertNotIn("zotero-read", agent)
        self.assertNotIn("migration window", skill)
        self.assertNotIn("deprecated Zotero-item", skill)
        self.assertNotIn("zotero-read", skill)

    def test_normalized_zotero_provenance_is_inert(self):
        agent = AGENT.read_text(encoding="utf-8")
        skill = SKILL.read_text(encoding="utf-8")
        self.assertIn("`source` 与 `item_key` 只允许停留在原输入里", agent)
        self.assertIn("不得根据 `source`/`item_key` 回查 Zotero", agent)
        self.assertIn("provenance only", skill)
        self.assertIn("never uses them to open Zotero or an MCP session", skill)

    def test_pdf_runtime_does_not_depend_on_host_pymupdf(self):
        text = AGENT.read_text(encoding="utf-8")
        self.assertIn("PDF_RUNTIME_SCRIPT", text)
        self.assertIn('uv run "$PDF_RUNTIME_SCRIPT" extract', text)
        self.assertIn('uv run "$PDF_RUNTIME_SCRIPT" render', text)
        self.assertNotIn("用 PyMuPDF 提取全文", text)
        self.assertNotIn("用 PyMuPDF 把", text)

    def test_text_input_contract_remains_supported(self):
        text = AGENT.read_text(encoding="utf-8")
        fixture = (FIXTURES / "paper.txt").read_text(encoding="utf-8")
        self.assertIn("本地文本文件绝对路径（.txt/.md）", text)
        self.assertIn("TITLE: <标题>", text)
        self.assertIn("AUTHORS: <a, b>", text)
        self.assertIn("This is a deterministic text input fixture", fixture)

    def test_gap_only_fail_closed_contract_is_preserved(self):
        text = AGENT.read_text(encoding="utf-8")
        self.assertIn("失败即修正临时 JSON，绝不手工绕过", text)
        self.assertIn("任一检查失败即返回 error", text)
        self.assertIn("不得手写 Markdown", text)
        self.assertIn("不得把没有 sidecar 的状态说成完成", text)
        self.assertIn("sidecar 存在且 `status: ok`", text)

    def test_ocr_authorization_cache_and_failure_contract_is_preserved(self):
        text = AGENT.read_text(encoding="utf-8")
        self.assertIn("说明页码和逐页耗时，用户同意才 OCR", text)
        self.assertIn("先查命中缓存", text)
        self.assertIn("要我自动重识别这些页", text)
        self.assertIn("只识别坏页", text)
        self.assertIn("某页连续失败：记录失败页，不重试死磕", text)
        self.assertIn("失败页内容**不脑补**", text)

    def test_full_mode_facts_sidecar_is_pdf_only_same_pass_and_deterministic(self):
        agent = AGENT.read_text(encoding="utf-8")
        skill = SKILL.read_text(encoding="utf-8")
        self.assertIn("FACTS_SCRIPT=<skill_dir>/scripts/facts.py", agent)
        self.assertIn('uv run "$FACTS_SCRIPT" validate', agent)
        self.assertIn('uv run "$FACTS_SCRIPT" finalize', agent)
        self.assertIn("facts-draft.json", agent)
        self.assertIn("不得触发第二次全文模型调用", agent)
        self.assertIn("不得在最终 Markdown 落盘后用 regex/grep 反向提取 facts", agent)
        self.assertIn("保存的本地 PDF `full`", agent)
        self.assertIn("非 PDF full 输入", agent)
        self.assertIn("same analysis/evidence level/PDF fingerprint", skill)
        self.assertIn("three-artifact contract is intentionally limited to local-PDF full mode", skill)
        self.assertIn("future_work_ids", skill)
        self.assertIn("input_fingerprint", skill)
        self.assertIn("generator_version", skill)
        self.assertIn("upgrade-full-sidecar", skill)

    def test_saved_pdf_full_writes_analysis_before_sidecar_finalizers(self):
        text = AGENT.read_text(encoding="utf-8")
        write_marker = "先把 Step 4 已组装完成的 Markdown 写到最终 analysis 路径"
        upgrade_marker = 'uv run "$FUTURE_WORK_SCRIPT" upgrade-full-sidecar'
        facts_marker = 'uv run "$FACTS_SCRIPT" finalize'
        success_marker = "三者都存在"
        self.assertLess(text.index(write_marker), text.index(upgrade_marker))
        self.assertLess(text.index(upgrade_marker), text.index(facts_marker))
        self.assertLess(text.index(facts_marker), text.index(success_marker))
        self.assertIn("analysis.is_file()", text)
        self.assertIn("不得在 analysis 文件尚未写入时调用 `upgrade-full-sidecar`", text)

    def test_saved_pdf_full_reuses_page_ocr_before_future_work_upgrade(self):
        text = AGENT.read_text(encoding="utf-8")
        self.assertIn(".llm_ocr.pages.json", text)
        self.assertIn("future-work-ocr.json", text)
        self.assertIn("不得对已经识别成功的页再次 OCR", text)
        merge_marker = 'uv run "$FUTURE_WORK_SCRIPT" merge-ocr'
        upgrade_marker = 'uv run "$FUTURE_WORK_SCRIPT" upgrade-full-sidecar'
        self.assertLess(text.index(merge_marker), text.index(upgrade_marker))
        self.assertIn("ocr_required_pages` 为空", text)

    def test_persistent_page_ocr_cache_is_fingerprint_bound_before_reuse(self):
        text = AGENT.read_text(encoding="utf-8")
        validate_marker = 'uv run "$PDF_RUNTIME_SCRIPT" validate-ocr-cache'
        merge_marker = 'uv run "$FUTURE_WORK_SCRIPT" merge-ocr'
        self.assertIn("pdf_sha256", text)
        self.assertIn("validated-ocr-cache.json", text)
        self.assertIn("该持久 cache 整体作废，不得读取其中任何页文本", text)
        self.assertIn('uv run "$PDF_RUNTIME_SCRIPT" update-ocr-cache', text)
        validate_index = text.index(validate_marker)
        saved_full_merge_index = text.index(merge_marker, validate_index)
        self.assertLess(validate_index, saved_full_merge_index)

    def test_persistent_fulltext_ocr_cache_is_fingerprint_bound_before_step3(self):
        text = AGENT.read_text(encoding="utf-8")
        validate_marker = 'uv run "$PDF_RUNTIME_SCRIPT" validate-fulltext-ocr-cache'
        step3_marker = "### Step 3 — 并行子代理"
        self.assertIn(".llm_ocr.txt.meta.json", text)
        self.assertIn("持久完整正文 cache 禁止直接读取", text)
        self.assertIn("validated-fulltext-ocr.txt", text)
        self.assertIn('uv run "$PDF_RUNTIME_SCRIPT" update-fulltext-ocr-cache', text)
        self.assertIn('--expected-sha256 "<prepare.pdf_sha256>"', text)
        self.assertIn("不得进入 Step 3", text)
        self.assertLess(text.index(validate_marker), text.index(step3_marker))

    def test_all_runtime_helpers_are_script_native(self):
        for path in (PAPER_INPUT, PDF_RUNTIME, FUTURE_WORK, FACTS):
            text = path.read_text(encoding="utf-8")
            self.assertIn("# /// script", text, path.name)
            self.assertIn("# requires-python", text, path.name)

    # ------------------------------------------------------------------
    # Dependency distribution contract (release package, no moving main)
    # ------------------------------------------------------------------

    def test_pep723_helpers_pin_release_distribution_exactly(self):
        for path in (PDF_RUNTIME, FUTURE_WORK):
            text = path.read_text(encoding="utf-8")
            self.assertIn(f'#   "{RELEASE_PIN}"', text, path.name)
            self.assertNotIn(FORBIDDEN_GIT_MAIN_DEP, text, path.name)
            self.assertNotIn(FORBIDDEN_GIT_URL, text, path.name)

    def test_public_pdfx_import_surface_is_preserved(self):
        text = FUTURE_WORK.read_text(encoding="utf-8")
        self.assertIn("from pdfx.quality import score_page", text)

    def test_root_project_depends_on_release_range(self):
        text = PYPROJECT.read_text(encoding="utf-8")
        self.assertIn(f'dependencies = ["{RELEASE_RANGE}"]', text)
        self.assertNotIn("[tool.uv.sources]", text)
        self.assertNotIn(FORBIDDEN_GIT_URL, text)

    def test_lockfile_pins_registry_release_resolution(self):
        text = UVLOCK.read_text(encoding="utf-8")
        self.assertIn(f'name = "{RELEASE_DISTRIBUTION}"', text)
        self.assertIn('source = { registry = "https://pypi.org/simple" }', text)
        self.assertNotIn(FORBIDDEN_LOCK_GIT_SOURCE, text)
        self.assertNotIn('name = "pdf-processing-core"', text)

    def test_apm_manifest_targets_both_runtimes_without_git_main_dependency(self):
        text = APM_YML.read_text(encoding="utf-8")
        self.assertIn("targets: [opencode, codex]", text)
        self.assertNotIn("pdf-processing-core", text)

    def test_no_moving_main_dependency_in_production_text(self):
        forbidden = (
            FORBIDDEN_GIT_MAIN_DEP,
            FORBIDDEN_GIT_URL,
            FORBIDDEN_BRANCH_MAIN,
        )
        for path in PRODUCTION_FILES:
            text = path.read_text(encoding="utf-8")
            for pattern in forbidden:
                self.assertNotIn(
                    pattern,
                    text,
                    f"{path.name} contains moving-main dependency: {pattern!r}",
                )

    def test_no_central_runtime_or_consumer_overlay_dependency(self):
        for path in PRODUCTION_FILES:
            text = path.read_text(encoding="utf-8")
            for marker in CENTRAL_RUNTIME_MARKERS:
                self.assertNotIn(
                    marker,
                    text,
                    f"{path.name} must not depend on central runtime {marker!r}",
                )

    def test_pdfx_quality_cli_uses_release_distribution(self):
        agent = AGENT.read_text(encoding="utf-8")
        skill = SKILL.read_text(encoding="utf-8")
        expected = f'uvx --from "{RELEASE_PIN}" pdfx quality'
        self.assertIn(expected, agent)
        self.assertIn(expected, skill)
        self.assertNotIn('pdfx quality "<PDF 绝对路径>" --json`', agent)

    # ------------------------------------------------------------------
    # Producer-local orchestration contract
    # ------------------------------------------------------------------

    def test_apm_openagent_frontmatter_keeps_opencode_native_contract(self):
        text = AGENT.read_text(encoding="utf-8")
        self.assertIn("mode: subagent", text)
        self.assertIn("hidden: true", text)
        self.assertIn("temperature: 0.2", text)
        self.assertIn("permission:", text)
        for tool in ("read", "glob", "grep", "edit", "write", "bash", "task", "skill", "question", "todowrite", "external_directory"):
            self.assertIn(f"{tool}: allow", text)

    def test_helpers_are_located_from_installed_skill_absolute_dir(self):
        text = AGENT.read_text(encoding="utf-8")
        for line in (
            "FUTURE_WORK_SCRIPT=<skill_dir>/scripts/future_work.py",
            "PAPER_INPUT_SCRIPT=<skill_dir>/scripts/paper_input.py",
            "PDF_RUNTIME_SCRIPT=<skill_dir>/scripts/pdf_runtime.py",
            "FACTS_SCRIPT=<skill_dir>/scripts/facts.py",
        ):
            self.assertIn(line, text)
        self.assertIn("不假设当前工作目录位于仓库根目录", text)

    def test_opencode_native_question_path_takes_priority(self):
        text = AGENT.read_text(encoding="utf-8")
        self.assertIn("question` 工具", text)
        assert_orchestration_contract(text)

    def test_orchestration_contract_holds_for_canonical_agent(self):
        assert_orchestration_contract(AGENT.read_text(encoding="utf-8"))

    def test_orchestration_conventions_are_load_bearing(self):
        """Mutation-style check: deleting any convention line must fail the gate."""
        text = AGENT.read_text(encoding="utf-8")
        for name, marker in REQUIRED_ORCHESTRATION_CONVENTIONS:
            with self.subTest(convention=name):
                mutated = "\n".join(
                    line for line in text.splitlines() if marker not in line
                )
                self.assertNotIn(marker, mutated)
                with self.assertRaises(AssertionError):
                    assert_orchestration_contract(mutated)

    def test_convention_gate_is_not_vacuous(self):
        with self.assertRaises(AssertionError):
            assert_orchestration_contract("")

    def test_full_mode_step3_keeps_three_semantic_roles(self):
        text = AGENT.read_text(encoding="utf-8")
        self.assertIn("### Step 3 — 并行子代理", text)
        step3 = text.split("### Step 3 — 并行子代理", 1)[1].split("### Step 4", 1)[0]
        for role in FULL_MODE_STEP3_SEMANTIC_ROLES:
            self.assertIn(role, step3)

    def test_codex_full_delegation_markers_are_gated_conventions(self):
        gated_markers = {marker for _, marker in REQUIRED_ORCHESTRATION_CONVENTIONS}
        for marker in CODEX_FULL_DELEGATION_MARKERS:
            self.assertIn(marker, gated_markers)
        assert_orchestration_contract(AGENT.read_text(encoding="utf-8"))

    def test_codex_full_delegation_markers_are_load_bearing(self):
        """Mutation-style check: deleting either exact marker line must fail the gate."""
        text = AGENT.read_text(encoding="utf-8")
        for marker in CODEX_FULL_DELEGATION_MARKERS:
            with self.subTest(marker=marker):
                marker_lines = [line for line in text.splitlines() if marker in line]
                self.assertEqual(len(marker_lines), 1, marker)
                mutated = "\n".join(
                    line for line in text.splitlines() if marker not in line
                )
                self.assertNotIn(marker, mutated)
                with self.assertRaises(AssertionError):
                    assert_orchestration_contract(mutated)

    def test_codex_delegation_wording_does_not_use_opencode_task_as_codex_api(self):
        text = AGENT.read_text(encoding="utf-8")
        self.assertNotIn("task(", text)
        for marker in CODEX_FULL_DELEGATION_MARKERS:
            marker_line = next(line for line in text.splitlines() if marker in line)
            self.assertNotIn("Task", marker_line, marker)

    def test_codex_full_step3_requires_three_children_and_child_owned_results(self):
        text = AGENT.read_text(encoding="utf-8")
        step3 = text.split("### Step 3 — 并行子代理", 1)[1].split("### Step 4", 1)[0]
        self.assertIn("Step 3 必须恰好分派 exactly 3 个有界只读分析工作单元", step3)
        self.assertIn("三路结果必须全部来自 delegated child", step3)
        self.assertNotIn("至少", step3)

    def test_delegation_gate_rejects_generic_subagent_wording(self):
        generic = (
            "Step 3 使用 subagent delegation 分派三路分析，"
            "运行时提供原生 delegation workflow 时必须使用它。"
        )
        with self.assertRaises(AssertionError):
            assert_orchestration_contract(generic)

    def test_codex_step3_direct_native_markers_are_gated_conventions(self):
        gated_markers = {marker for _, marker in REQUIRED_ORCHESTRATION_CONVENTIONS}
        for marker in CODEX_STEP3_DIRECT_NATIVE_MARKERS:
            self.assertIn(marker, gated_markers)
        assert_orchestration_contract(AGENT.read_text(encoding="utf-8"))

    def test_codex_step3_direct_native_markers_are_load_bearing(self):
        """Mutation-style check: deleting any direct-native contract line fails the gate."""
        text = AGENT.read_text(encoding="utf-8")
        for marker in CODEX_STEP3_DIRECT_NATIVE_MARKERS:
            with self.subTest(marker=marker):
                mutated = "\n".join(
                    line for line in text.splitlines() if marker not in line
                )
                self.assertNotIn(marker, mutated)
                with self.assertRaises(AssertionError):
                    assert_orchestration_contract(mutated)

    def test_codex_step3_delegation_attempt_precedes_step4_assembly(self):
        text = AGENT.read_text(encoding="utf-8")
        step3 = text.split("### Step 3 — 并行子代理", 1)[1].split("### Step 4", 1)[0]
        self.assertIn(
            "required Step-3 child 必须直接调用当前 Codex 运行时暴露的"
            "公开 `spawn_agent` 多代理工具",
            step3,
        )
        self.assertIn("不得先等工具目录或能力探测出结论", step3)
        self.assertIn("三路调用都发起后，等待并消费三路 child 返回的 Markdown", step3)
        attempt_order = (
            step3.index("required Step-3 child 必须直接调用"),
            step3.index("三路调用都发起后，等待并消费三路 child 返回的 Markdown"),
            step3.index("才进入 Step 4"),
        )
        self.assertEqual(
            list(attempt_order), sorted(attempt_order),
            "the real delegation attempt must be ordered before waiting, consuming "
            "and Step 4 assembly",
        )

    def test_codex_step3_attempt_requirement_precedes_blocker_permission(self):
        """PA-DIRECT-03: the attempt requirement is stated before, and gates, the
        only condition under which a delegation blocker is allowed."""
        text = AGENT.read_text(encoding="utf-8")
        conventions = _section(text, "## 交互与运行时兼容约定", "## 输入（由 task prompt 传入）")
        attempt = conventions.index(
            "只有本次 full run 已按要求真实发起 `spawn_agent` 委派"
        )
        blocker = conventions.index("才允许报告 delegation blocker")
        self.assertLess(attempt, blocker, "blocker permission may only follow the attempt")
        self.assertLess(
            conventions.index(
                "**零次真实 native 委派尝试时禁止返回 `delegation unavailable` 或等价 blocker**"
            ),
            text.index("### Step 3 — 并行子代理"),
            "the zero-attempt prohibition must be stated before the Step 3 call point",
        )
        self.assertLess(
            text.index("### Step 4"),
            text.index("零次真实调用时禁止返回 `delegation unavailable` 或等价 blocker"),
            "the pre-return zero-attempt check must sit after the Step 3 call point",
        )

    def test_production_agent_has_no_capability_probe_preflight_contract(self):
        text = AGENT.read_text(encoding="utf-8")
        assert_no_retired_discovery_preflight(text)

    def test_legacy_discovery_preflight_is_rejected(self):
        text = AGENT.read_text(encoding="utf-8")
        legacy = RETIRED_DISCOVERY_PREFLIGHT_CLAUSES[0]
        mutated = text.replace(
            "## 输入（由 task prompt 传入）",
            legacy + "\n\n## 输入（由 task prompt 传入）",
            1,
        )
        with self.assertRaises(AssertionError):
            assert_orchestration_contract(mutated)

    def test_diagnostic_discovery_wording_is_not_globally_forbidden(self):
        text = AGENT.read_text(encoding="utf-8")
        diagnostic = (
            "Code Mode / programmatic discovery 可以作为 runtime diagnostics 记录，"
            "但绝不能作为 delegation prerequisite 或 blocker 依据。"
        )
        mutated = text.replace(
            "## 输入（由 task prompt 传入）",
            diagnostic + "\n\n## 输入（由 task prompt 传入）",
            1,
        )
        assert_orchestration_contract(mutated)

    def test_direct_native_contract_does_not_hardcode_private_tool_surface(self):
        """The contract names the public tool only: no call signature, private
        namespace, request schema or undocumented event field."""
        text = AGENT.read_text(encoding="utf-8")
        self.assertIn("`spawn_agent`", text)
        self.assertNotIn("multi_agent_v1__", text)
        self.assertNotIn("ALL_TOOLS", text)
        self.assertNotIn("spawn_agent(", text)
        self.assertNotIn("functions.exec", text)

    def test_required_child_failure_never_gets_a_guessed_result(self):
        """PA-DIRECT-04: every surface that owns the child-failure invariant keeps
        its explicit-report / no-guess clause."""
        text = AGENT.read_text(encoding="utf-8")
        for name, start, end, marker in CHILD_FAILURE_SURFACES:
            with self.subTest(surface=name):
                self.assertIn(marker, _section(text, start, end))

    def test_required_child_failure_clauses_are_load_bearing(self):
        text = AGENT.read_text(encoding="utf-8")
        for name, start, end, marker in CHILD_FAILURE_SURFACES:
            with self.subTest(surface=name):
                mutated = "\n".join(
                    line for line in text.splitlines() if marker not in line
                )
                self.assertNotIn(marker, _section(mutated, start, end))


if __name__ == "__main__":
    unittest.main()
