"""Lock the issue #16 rewrite of the formal Codex runtime recipe.

``PA-CODEX-FULL-LEAF-01`` stays the only real-Codex runtime Merge Gate, but the
recipe must no longer treat a V1 capability characterization (A′/B′ probes,
``ALL_TOOLS``, ``multi_agent_v1``, Code Mode ``exec``) as an acceptance
prerequisite, must pin the runtime prerequisite configs required by the frozen
``root -> outer -> leaves`` topology, must define the ``CASE_STARTED`` boundary
and one verdict per terminal
machine state, and must replace the blanket "any SHA change invalidates the
acceptance" rule with impact-based revalidation.
"""

from pathlib import Path

RECIPE_PATH = (
    Path(__file__).resolve().parents[1]
    / "tests"
    / "runtime"
    / "CODEX_FULL_MODE_RUNTIME_RECIPE.md"
)


def _recipe_text() -> str:
    return RECIPE_PATH.read_text(encoding="utf-8")


def _slice(text: str, start_marker: str, end_marker: str) -> str:
    start = text.index(start_marker)
    end = text.index(end_marker, start)
    return text[start:end]


def _section(start_marker: str, end_marker: str) -> str:
    return _slice(_recipe_text(), start_marker, end_marker)


def test_retired_capability_characterization_is_no_longer_a_prerequisite() -> None:
    recipe = _recipe_text()
    for retired in (
        "verify_codex_nested_capability_probe",
        "depth_hypothesis",
        "INVALID_CHARACTERIZATION_DESIGN",
        "NOT YET ATTRIBUTABLE",
        "REFUTED_BY_DEFAULT",
        "CONFIRMED_BY_A_B",
    ):
        assert retired not in recipe, retired
    # The retired case may only appear as a superseded historical note.
    assert recipe.count("PA-CODEX-NESTED-CAP-00") == 1
    assert "不再是本 case 的前置" in recipe


def test_runtime_prerequisite_configs_are_pinned_and_derived_from_the_topology() -> None:
    execution = _section("## 10. Execution", "### CASE_STARTED 边界")
    assert '"--config", "agents.enabled=true"' in execution
    assert '"--config", "agents.max_concurrent_threads_per_session=4"' in execution
    assert '"--config", "agents.max_depth=2"' in execution
    config = _section("## 8. Runtime configuration", "## 9. Fixed input / prompt")
    assert "4 = 1 outer child + 3 nested leaves" in config
    assert "2 = outer child depth 1 + nested leaves depth 2" in config
    assert "避免结果依赖宿主配置或共享 app-server 的启动时快照" in config
    assert "不是对历史失败原因的归因" in config
    assert "test resource ceiling" in config
    assert "不是 `paper-analysis` 的产品业务上限" in config
    assert "不得临场提高 ceiling" in config


def test_resolved_config_record_states_what_the_pinned_surface_reports() -> None:
    config = _section("## 8. Runtime configuration", "## 9. Fixed input / prompt")
    assert "before_override" in config
    assert "after_override" in config
    assert "output.thread_start_effective" in config
    assert "not_reported_by_pinned_surface" in config
    assert "runtime-config-requested.json" in config
    assert "runtime-config-effective.json" in config
    pass_section = _section("### PASS", "### FAIL_PRODUCER")
    assert "不得声称「runtime 已确认 ceiling 生效」" in pass_section


def test_case_started_boundary_is_defined_and_precedes_every_verdict() -> None:
    recipe = _recipe_text()
    started = recipe.index("### CASE_STARTED 边界")
    verdict = recipe.index("## 15. Verdict")
    assert started < verdict
    boundary = _slice(recipe, "### CASE_STARTED 边界", "### 重要：本 case 不调用")
    assert "output.thread_id" in boundary
    assert "case-status.txt" in boundary
    bootstrap = _section("## 4. Exclusive run root / provenance", "## 5.")
    assert "CASE_NOT_STARTED" in bootstrap
    assert "不作产品 verdict" in " ".join(bootstrap.split())


def test_each_terminal_machine_state_maps_to_exactly_one_verdict() -> None:
    table = _section("## 15. Verdict", "### PASS")
    for row in (
        "| `root_direct_child_count != 1` | `BLOCKED` |",
        "| `root_direct_child_count == 1` 且 nested `== 3`，ownership valid | `PASS` |",
        "| `root_direct_child_count == 1` 且 nested `in {1,2}` | `FAIL_PRODUCER` |",
        "| `root_direct_child_count == 1` 且 nested `> 3` | `FAIL_PRODUCER` |",
        "| `root_direct_child_count == 1` 且 nested `== 0` | `NOT TESTED` |",
        "| 未越过 §4–§8、§10 `CASE_STARTED` 边界 | `CASE_NOT_STARTED` |",
    ):
        assert row in table, row
    assert "不得为它发明 reason code" in table
    assert "| `passed == false`" not in table


def test_topology_absence_is_not_tested_and_never_a_producer_failure() -> None:
    not_tested = _section("### NOT TESTED", "### CASE_NOT_STARTED")
    assert "unobservable" in not_tested
    assert "不产生 PASS/FAIL" in not_tested
    fail = _section("### FAIL_PRODUCER", "### BLOCKED")
    assert "`nested == 0` 不属于本 verdict" in fail
    verifier = _section("## 11. Producer topology verifier", "## 12.")
    assert "`==0` → `NOT_TESTED`" in verifier
    assert "4` NOT_TESTED" in verifier or "`4` NOT_TESTED" in verifier


def test_proven_topology_pass_is_not_reversed_by_out_of_scope_failure() -> None:
    pass_section = _section("### PASS", "### FAIL_PRODUCER")
    assert "都不反转" in pass_section
    assert "scope 外的 child、business 或 provider failure" in pass_section
    assert "`/eval.passed == false` 单独也不是" in pass_section


def test_projection_check_locks_new_contract_and_retired_mechanism() -> None:
    projection = _section("## 7. Generated projection check", "## 8.")
    required = projection.split("required = {", 1)[1].split("\n}", 1)[0]
    retired = projection.split("retired = {", 1)[1].split("\n}", 1)[0]
    assert required.count('": "') == 15
    assert retired.count('": "') == 6
    assert "assert all(checks.values())" in projection
    assert "assert not any(retired_found.values())" in projection
    assert '"code_mode": "Code Mode"' not in retired
    assert '"programmatic": "programmatic"' not in retired
    assert '"discovery": "discovery"' not in retired
    assert '"legacy_preflight"' in retired
    assert '"executable_false_probe"' in retired
    assert "先绑定当前调用面实际提供的 subagent spawn capability" in projection
    assert "从 `ALL_TOOLS` 按工具说明定位 spawn capability" in projection


def test_pass_checklist_matches_projection_checker_counts() -> None:
    text = _recipe_text()
    passed = _slice(text, "### PASS", "### FAIL_PRODUCER")
    assert "15 条 direct/deferred-surface" in passed
    assert "6 条 retired false-failure clauses" in passed
    assert "12 条 direct-native" not in passed
    assert "7 条 retired discovery-preflight/private-mechanism" not in passed


def test_identity_and_prose_surfaces_stay_out_of_the_verdict() -> None:
    recipe = _recipe_text()
    basis = _section("## 2. Basis", "## 3. Prerequisites")
    assert "tool catalog / Code Mode / assistant prose（不得进入任何 verdict）" in basis
    assert "没有** native-spawn-failure machine state" in basis
    verifier = _section("## 11. Producer topology verifier", "## 12.")
    assert "verifier 不得读取 `child_thread_reads` 或任何 identity 字段" in verifier


def test_pre_case_started_bootstrap_is_fail_closed_through_one_status_path() -> None:
    """Gate 2: every formal bootstrap failure is classified before CASE_STARTED."""
    recipe = _recipe_text()
    pre_started = _slice(
        recipe,
        "## 4. Exclusive run root / provenance",
        "### CASE_STARTED 边界",
    )

    # The run root and the one classification helper exist before formal checks.
    assert pre_started.index('RUN_ROOT="$(mktemp -d') < pre_started.index(
        "case_not_started() {"
    )
    assert pre_started.index("case_not_started() {") < pre_started.index(
        "FIXTURES_SHA="
    )
    section4_shell = pre_started.split("```bash", 1)[1].split("```", 1)[0]
    assert "set -u -o pipefail" in section4_shell
    assert "set -euo pipefail" not in section4_shell

    # Required paths must be classified explicitly instead of letting ``set -u``
    # terminate the shell before the common CASE_NOT_STARTED path can run.
    for required_var in ("PRODUCER_REPO", "FIXTURES_DIR", "EVAL_SERVER_DIR"):
        assert (
            f'case_not_started "required prerequisite {required_var} is unset"'
            in pre_started
        )

    # Provenance writes are formal bootstrap steps too: a failed write cannot
    # be ignored while the recipe continues toward CASE_STARTED.
    assert "write_evidence() {" in pre_started
    for evidence_path in (
        "fixture-repo-sha.txt",
        "fixture-repo-dirty.txt",
        "producer-repo-dirty.txt",
        "producer-sha.txt",
        "recipe-run-id.txt",
        "consumer-path.txt",
        "consumer-newly-created.txt",
        "manual-patch.txt",
        "eval-server-checkout-sha.txt",
        "install-command.txt",
    ):
        marker = f'"$RUN_ROOT/output/{evidence_path}"'
        marker_pos = pre_started.index(marker)
        helper_pos = pre_started.rfind("write_evidence", 0, marker_pos)
        assert helper_pos >= 0
        assert marker_pos - helper_pos < 160

    # One compact regression owns the specific bootstrap stages that previously
    # escaped through bare `set -e`: revision, locked env, install, projection,
    # and HTTP transport. No extra runtime smoke is needed for these shell paths.
    for classified_failure in (
        'case_not_started "fixture revision does not match pinned SHA"',
        'case_not_started "locked producer environment bootstrap failed"',
        'case_not_started "APM install failed"',
        'case_not_started "generated Codex projection contract check failed"',
        'case_not_started "eval transport failed before root runtime provenance"',
    ):
        assert classified_failure in pre_started, classified_failure
    assert "if ! curl --fail-with-body" in pre_started

    config = _section("## 8. Runtime configuration", "## 9. Fixed input / prompt")
    assert "唯一状态是" in config
    assert "`CASE_NOT_STARTED` 或 `BLOCKED`" not in config

    boundary = _slice(recipe, "### CASE_STARTED 边界", "### 重要：本 case 不调用")
    assert boundary.index(
        'case_not_started "no root runtime provenance attributable to this run"'
    ) < boundary.index("printf 'CASE_STARTED\\n'")
    assert boundary.index("printf 'CASE_STARTED\\n'") < boundary.index(
        "set -euo pipefail"
    )


def test_every_python_step_uses_the_locked_producer_environment() -> None:
    """A host ``python3`` may predate tomllib; the recipe must not depend on it."""
    recipe = _recipe_text()
    after_preamble = recipe[recipe.index("## 5. Explicit Git-pinned install"):]
    assert "python3" not in after_preamble, (
        "no python step may invoke a bare host python3"
    )
    assert "verify_codex_full_mode_topology.py" in after_preamble
    assert "uv run --locked python" in recipe
    assert recipe.count("uv run --locked python - <<'PY'") == 3
    assert (
        "uv run --locked python tests/runtime/verify_codex_full_mode_topology.py"
        in recipe
    )
    assert "uv run --locked pytest" in recipe
    assert 'uv sync --locked' in _section(
        "## 4. Exclusive run root / provenance", "## 5."
    )


def test_revalidation_is_impact_based_not_blanket() -> None:
    recipe = _recipe_text()
    revalidation = recipe[recipe.index("## 17. Impact-based revalidation"):]
    assert "取代旧的 blanket" in revalidation
    assert "SHA 单独改变不自动使无关 PASS 失效" in revalidation
    for decision in ("EXECUTE_CURRENT", "REJUDGE_PRIOR_EVIDENCE", "REUSE_PRIOR_PASS"):
        assert decision in revalidation
    assert "intervening diff" in revalidation
    assert "declared revalidation dependencies" in revalidation
    # The retired blanket rule must not survive anywhere in the recipe.
    assert "变化后旧 acceptance evidence 失效" not in recipe
    prerequisites = _section("## 3. Prerequisites", "## 4.")
    assert "revision 变化不自动触发整案重跑" in prerequisites


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__, "-q"]))
