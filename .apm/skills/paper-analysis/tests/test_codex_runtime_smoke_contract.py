import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).parents[1]
REPO_ROOT = Path(__file__).parents[4]
AGENT = REPO_ROOT / ".apm/agents/paper-analysis.agent.md"
CODEX_SMOKE = Path(__file__).parent / "CODEX_RUNTIME_SMOKE.md"


class CodexRuntimeSmokeContractTests(unittest.TestCase):
    def test_full_mode_business_contract_still_has_three_analysis_units(self):
        """Light runtime smoke must not weaken the real three-way full workflow."""
        text = AGENT.read_text(encoding="utf-8")
        step3 = text.split("### Step 3 — 并行子代理", 1)[1].split(
            "### Step 4 — 组装", 1
        )[0]

        self.assertIn("分派三个只读分析工作单元", step3)
        for row in (
            "| ① | 内容沉淀 |",
            "| ② | 贡献与批判 |",
            "| ③ | 帮助评估 |",
        ):
            self.assertIn(row, step3)
        self.assertIn("接收这三路结果", step3)

    def test_c1_uses_persisted_spawn_evidence_not_stdout_identity_fields(self):
        text = CODEX_SMOKE.read_text(encoding="utf-8")

        self.assertIn("persisted root rollout", text)
        self.assertIn("`agent_type = paper-analysis`", text)
        self.assertIn("`task_name` is only a child task/path label", text)
        self.assertIn(
            "The absence of `agent_type`, role, or custom-agent identity fields from `codex exec --json` stdout",
            text,
        )

    def test_c3_is_single_nested_leaf_capability_smoke(self):
        text = CODEX_SMOKE.read_text(encoding="utf-8")

        self.assertIn("## C3 — single nested-leaf orchestration smoke", text)
        self.assertIn("-> exactly one read-only leaf", text)
        self.assertIn("`NESTED_LEAF_OK`", text)
        self.assertIn(
            "Do **not** require all three business analysis leaves to start.", text
        )
        self.assertIn(
            "no second or third live analysis leaf is required for this smoke", text
        )

    def test_c4_resumes_root_and_reuses_existing_coordinator_without_leaf_fanout(self):
        text = CODEX_SMOKE.read_text(encoding="utf-8")

        self.assertIn("`codex exec resume <ROOT_SESSION_ID> ...`", text)
        self.assertIn(
            "must not create a second fresh `paper-analysis` coordinator", text
        )
        self.assertIn("Do not require any analysis leaf during C4.", text)


if __name__ == "__main__":
    unittest.main()
