"""Lock the producer-checkout provenance contract (PA-RECIPE-PRODUCER-PROVENANCE-01).

The formal Codex acceptance reads producer-owned fixtures, capability/topology
verifiers, and the pytest suite directly from the local ``$PRODUCER_REPO``
checkout. Recording ``FINAL_HEAD_SHA`` alone does not prove those files match
that SHA, so the recipe must machine-record the producer worktree as clean
(tracked + untracked) before consuming any producer-owned asset. A dirty
producer checkout may only produce ``BLOCKED / NOT TESTED``; it can never
back a ``PASS`` or ``FAIL_PRODUCER`` verdict.
"""

from pathlib import Path

RECIPE_PATH = (
    Path(__file__).resolve().parents[1]
    / "tests"
    / "runtime"
    / "CODEX_FULL_MODE_RUNTIME_RECIPE.md"
)

SECTION_4_START = "## 4. Exclusive run root / provenance"
SECTION_5_START = "## 5. Explicit Git-pinned install"


def _recipe_text() -> str:
    return RECIPE_PATH.read_text(encoding="utf-8")


def _slice(text: str, start_marker: str, end_marker: str) -> str:
    start = text.index(start_marker)
    end = text.index(end_marker, start)
    return text[start:end]


def _section_4() -> str:
    return _slice(_recipe_text(), SECTION_4_START, SECTION_5_START)


def test_producer_dirty_preflight_follows_run_root_creation_in_section_4() -> None:
    section4 = _section_4()
    run_root_pos = section4.index(
        'RUN_ROOT="$(mktemp -d /tmp/paper-analysis-full-leaf.XXXXXX)"'
    )
    preflight_pos = section4.index('git -C "$PRODUCER_REPO" status --porcelain')
    assert run_root_pos < preflight_pos


def test_producer_dirty_preflight_covers_tracked_and_untracked_and_fails_closed() -> None:
    section4 = _section_4()
    assert 'PRODUCER_DIRTY="$(git -C "$PRODUCER_REPO" status --porcelain)"' in section4
    assert "producer_repo_dirty=yes" in section4
    assert "producer-repo-status.txt" in section4
    assert "exit 1" in section4
    assert "producer_repo_dirty=no" in section4
    assert "producer-repo-dirty.txt" in section4


def test_fixture_dirty_check_remains_so_producer_check_is_additive() -> None:
    section4 = _section_4()
    assert 'test -z "$(git -C "$FIXTURES_DIR" status --porcelain)"' in section4


def test_producer_dirty_evidence_is_required_and_status_is_dirty_branch_diagnostic() -> None:
    evidence = _slice(_recipe_text(), "## 18. Evidence", "## 19. Verdict")
    assert "output/producer-repo-dirty.txt" in evidence
    assert "producer-repo-status.txt" in evidence


def test_pass_requires_clean_producer_checkout() -> None:
    pass_section = _slice(_recipe_text(), "### PASS", "### FAIL_PRODUCER")
    assert "producer_repo_dirty=no" in pass_section


def test_fail_producer_shares_clean_producer_precondition() -> None:
    fail_section = _slice(_recipe_text(), "### FAIL_PRODUCER", "### BLOCKED")
    assert "producer_repo_dirty=no" in fail_section


def test_blocked_covers_dirty_producer_as_not_tested() -> None:
    blocked_section = _slice(_recipe_text(), "### BLOCKED", "### INVALID_EVIDENCE")
    assert "producer checkout dirty" in blocked_section
    assert "BLOCKED / NOT TESTED" in blocked_section
