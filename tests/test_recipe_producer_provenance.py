"""Lock the producer-checkout provenance contract (PA-RECIPE-PRODUCER-PROVENANCE-01).

The formal Codex acceptance reads producer-owned fixtures, the topology
verifier, and the pytest suite directly from the local ``$PRODUCER_REPO``
checkout. Recording ``FINAL_HEAD_SHA`` alone does not prove those files match
that SHA, so the recipe must machine-record the producer worktree as clean
(tracked + untracked) before consuming any producer-owned asset. A dirty
producer checkout is a bootstrap failure that stops before ``CASE_STARTED``: it
may only produce ``CASE_NOT_STARTED`` and can never back a ``PASS`` or
``FAIL_PRODUCER`` verdict (issue #16 Test Plan, ``CASE_STARTED`` boundary).
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
EVIDENCE_START = "## 14. Evidence"
VERDICT_START = "## 15. Verdict"



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
    evidence = _slice(_recipe_text(), EVIDENCE_START, VERDICT_START)
    assert "output/producer-repo-dirty.txt" in evidence
    assert "producer-repo-status.txt" in evidence


def test_pass_requires_clean_producer_checkout() -> None:
    pass_section = _slice(_recipe_text(), "### PASS", "### FAIL_PRODUCER")
    assert "producer_repo_dirty=no" in pass_section


def test_fail_producer_shares_clean_producer_precondition() -> None:
    fail_section = _slice(_recipe_text(), "### FAIL_PRODUCER", "### BLOCKED")
    assert "producer_repo_dirty=no" in fail_section


def test_dirty_producer_is_case_not_started_and_not_a_case_verdict() -> None:
    recipe = _recipe_text()
    case_not_started = _slice(recipe, "### CASE_NOT_STARTED", "## 16.")
    assert "producer checkout dirty" in case_not_started
    assert "CASE_NOT_STARTED" in case_not_started
    # A bootstrap stop must not be re-labelled as a runtime case verdict: the
    # BLOCKED list may not claim the dirty-producer branch back.
    blocked = _slice(recipe, "### BLOCKED", "### INVALID_EVIDENCE")
    assert "producer checkout dirty" not in blocked
    assert "producer checkout dirty" not in _slice(
        recipe, "### FAIL_PRODUCER", "### BLOCKED"
    )
    assert "BLOCKED / NOT TESTED" not in recipe
