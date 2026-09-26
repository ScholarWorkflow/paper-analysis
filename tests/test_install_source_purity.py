"""Lock the producer install-source layout (PA-CODEX-FULL-LEAF-01 purity).

The packaged skill tree under ``.apm/skills/paper-analysis/`` must contain
only production assets. Producer-owned test artifacts (the runtime recipe,
the topology verifier, pytest modules, fixtures) live in the repo-level
``tests/`` tree and are never distributed with the skill, so a clean
consumer cannot read test execution knowledge and change its formal entry
behavior.
"""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_TREE = REPO_ROOT / ".apm" / "skills" / "paper-analysis"

FORBIDDEN_NAMES = {
    "CODEX_FULL_MODE_RUNTIME_RECIPE.md",
    "verify_codex_full_mode_topology.py",
}


def test_skill_tree_has_no_tests_directory() -> None:
    assert (REPO_ROOT / "tests").is_dir()
    assert not (SKILL_TREE / "tests").exists()


def test_skill_tree_has_no_test_only_artifacts() -> None:
    leaks = [
        path
        for path in sorted(SKILL_TREE.rglob("*"))
        if path.name in FORBIDDEN_NAMES
        or (path.name.startswith("test_") and path.suffix == ".py")
    ]
    assert leaks == []


def test_skill_tree_keeps_production_assets() -> None:
    assert (SKILL_TREE / "SKILL.md").is_file()
    assert (SKILL_TREE / "scripts").is_dir()
