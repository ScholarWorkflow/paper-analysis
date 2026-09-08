import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).parents[1]
REPO_ROOT = Path(__file__).parents[4]
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
    ("native question priority", "必须优先使用原生 `question`"),
    ("needs_input no silent default", "不得静默选择默认值"),
    ("needs_input same-thread resume", "resume 同一 coordinator"),
    ("convention not security boundary", "不是安全边界"),
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


if __name__ == "__main__":
    unittest.main()
