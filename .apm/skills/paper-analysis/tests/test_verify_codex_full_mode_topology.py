"""Deterministic unit tests for the PA-CODEX-FULL-LEAF-01 topology verifier.

The static JSON built here is a producer verifier test fixture only; it is
not the shared runtime fixture protocol. The verifier consumes the raw /eval
response plus the shared adapter output, so these fixtures mirror the pinned
adapter@9 output surface (fixture_status, delegation, dispatch,
child_thread_reads).
"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import verify_codex_full_mode_topology as verifier

SCRIPT = Path(__file__).with_name("verify_codex_full_mode_topology.py")

ROOT_THREAD = "thread-root-1"
COORDINATOR_THREAD = "thread-coordinator-1"
NESTED_LEAF_THREAD = "thread-leaf-1"
SECOND_ROLE_THREAD = "thread-second-role-1"
EXPECTED_AGENT = "paper-analysis"


def spawn_relation(sender, receivers, parent, *, call_id="exec-1", runtime_seq=7):
    return {
        "receiver_thread_ids": list(receivers),
        "call_id": call_id,
        "status": "completed",
        "parent_thread_id": parent,
        "tool": "spawnAgent",
        "sender_thread_id": sender,
        "runtime_seq": runtime_seq,
    }


def read_entry(thread_id, parent_thread_id, *, effective_role, identity_eligible=True):
    return {
        "thread_id": thread_id,
        "parent_thread_id": parent_thread_id,
        "relation_kind": "collabAgentToolCall.receiverThreadIds",
        "outcome": "success",
        "identity_eligible": identity_eligible,
        "effective_role": effective_role,
    }


def healthy_eval_response():
    return {
        "passed": True,
        "version": "codex-cli 0.153.4 (provenance only)",
        "output": {
            "backend": "codex",
            "runtime_generation": "gen-1",
            "thread_id": ROOT_THREAD,
            "turn_id": "turn-1",
            "termination_reason": "end_turn",
        },
    }


def healthy_adapter():
    return {
        "schema": 1,
        "role": "codex-eval-evidence",
        "adapter": "skills-test-fixtures parse_codex_eval_evidence.py",
        "adapter_contract_id": "skills-test-fixtures/codex-eval-adapter@9",
        "fixture_status": "FIXTURE_READY",
        "problems": [],
        "delegation": {
            "state": "confirmed",
            "formal_child_count": 2,
            "child_thread_ids": sorted([COORDINATOR_THREAD, NESTED_LEAF_THREAD]),
            "basis": ["formal_spawn_relation"],
            "reason_code": None,
        },
        "dispatch": {
            "expected_agents": [EXPECTED_AGENT],
            "thread_relations": [
                spawn_relation(ROOT_THREAD, [COORDINATOR_THREAD], ROOT_THREAD),
                spawn_relation(
                    COORDINATOR_THREAD, [NESTED_LEAF_THREAD], COORDINATOR_THREAD
                ),
            ],
        },
        "child_thread_reads": {
            "entry_count": 2,
            "identity_eligible_thread_ids": sorted(
                [COORDINATOR_THREAD, NESTED_LEAF_THREAD]
            ),
            "entries": [
                read_entry(
                    COORDINATOR_THREAD, ROOT_THREAD, effective_role=EXPECTED_AGENT
                ),
                read_entry(NESTED_LEAF_THREAD, COORDINATOR_THREAD, effective_role="general"),
            ],
        },
    }


class VerifyTopologyTests(unittest.TestCase):
    def verify(self, eval_response, adapter, **kwargs):
        return verifier.verify_topology(
            eval_response, adapter, expected_agent=EXPECTED_AGENT, **kwargs
        )

    # ------------------------------------------------------------------
    # PASS
    # ------------------------------------------------------------------

    def test_pass_exact_coordinator_has_direct_nested_child(self):
        verdict = self.verify(healthy_eval_response(), healthy_adapter())
        self.assertEqual(verdict["producer_status"], "PASS")
        self.assertEqual(verdict["case_id"], "PA-CODEX-FULL-LEAF-01")
        self.assertEqual(verdict["coordinator_thread_id"], COORDINATOR_THREAD)
        self.assertIs(verdict["root_to_paper_analysis"], True)
        self.assertEqual(verdict["paper_analysis_direct_child_count"], 1)
        self.assertEqual(verdict["nested_child_thread_ids"], [NESTED_LEAF_THREAD])
        self.assertEqual(verdict["reasons"], [])
        self.assertEqual(verdict["provenance"]["eval_version"], "codex-cli 0.153.4 (provenance only)")

    # ------------------------------------------------------------------
    # FAIL_PRODUCER
    # ------------------------------------------------------------------

    def test_fail_producer_when_healthy_coordinator_spawns_no_nested_child(self):
        adapter = healthy_adapter()
        adapter["dispatch"]["thread_relations"] = [
            spawn_relation(ROOT_THREAD, [COORDINATOR_THREAD], ROOT_THREAD)
        ]
        adapter["delegation"] = {
            "state": "confirmed",
            "formal_child_count": 1,
            "child_thread_ids": [COORDINATOR_THREAD],
            "basis": ["formal_spawn_relation"],
            "reason_code": None,
        }
        adapter["child_thread_reads"] = {
            "entry_count": 1,
            "identity_eligible_thread_ids": [COORDINATOR_THREAD],
            "entries": [
                read_entry(
                    COORDINATOR_THREAD, ROOT_THREAD, effective_role=EXPECTED_AGENT
                )
            ],
        }
        verdict = self.verify(healthy_eval_response(), adapter)
        self.assertEqual(verdict["producer_status"], "FAIL_PRODUCER")
        self.assertEqual(verdict["coordinator_thread_id"], COORDINATOR_THREAD)
        self.assertIs(verdict["root_to_paper_analysis"], True)
        self.assertEqual(verdict["nested_child_thread_ids"], [])
        self.assertEqual(verdict["paper_analysis_direct_child_count"], 0)
        self.assertTrue(verdict["reasons"])

    def test_fail_producer_when_only_a_generic_sibling_spawns_children(self):
        adapter = healthy_adapter()
        generic = "thread-generic-1"
        adapter["dispatch"]["thread_relations"] = [
            spawn_relation(ROOT_THREAD, [COORDINATOR_THREAD], ROOT_THREAD),
            spawn_relation(ROOT_THREAD, [generic], ROOT_THREAD, call_id="exec-2"),
        ]
        adapter["delegation"]["child_thread_ids"] = sorted(
            [COORDINATOR_THREAD, generic]
        )
        adapter["delegation"]["formal_child_count"] = 2
        reads = adapter["child_thread_reads"]
        reads["entries"] = [
            read_entry(
                COORDINATOR_THREAD, ROOT_THREAD, effective_role=EXPECTED_AGENT
            ),
            read_entry(generic, ROOT_THREAD, effective_role=None),
        ]
        reads["entry_count"] = 2
        reads["identity_eligible_thread_ids"] = sorted([COORDINATOR_THREAD, generic])
        verdict = self.verify(healthy_eval_response(), adapter)
        self.assertEqual(verdict["producer_status"], "FAIL_PRODUCER")
        self.assertEqual(verdict["coordinator_thread_id"], COORDINATOR_THREAD)
        self.assertEqual(verdict["nested_child_thread_ids"], [])

    # ------------------------------------------------------------------
    # BLOCKED
    # ------------------------------------------------------------------

    def test_blocked_when_coordinator_persisted_role_not_machine_confirmable(self):
        adapter = healthy_adapter()
        adapter["child_thread_reads"]["entries"][0]["effective_role"] = None
        verdict = self.verify(healthy_eval_response(), adapter)
        self.assertEqual(verdict["producer_status"], "BLOCKED")

    def test_blocked_when_child_thread_reads_surface_absent(self):
        adapter = healthy_adapter()
        del adapter["child_thread_reads"]
        verdict = self.verify(healthy_eval_response(), adapter)
        self.assertEqual(verdict["producer_status"], "BLOCKED")

    def test_blocked_when_adapter_reports_blocked_dependency(self):
        adapter = healthy_adapter()
        adapter["fixture_status"] = "BLOCKED_DEPENDENCY"
        adapter["problems"] = ["eval-server recorded no usable codex --version"]
        verdict = self.verify(healthy_eval_response(), adapter)
        self.assertEqual(verdict["producer_status"], "BLOCKED")
        self.assertIn("BLOCKED_DEPENDENCY", verdict["reasons"][0])

    def test_blocked_when_eval_version_is_null(self):
        eval_response = healthy_eval_response()
        eval_response["version"] = None
        verdict = self.verify(eval_response, healthy_adapter())
        self.assertEqual(verdict["producer_status"], "BLOCKED")

    def test_blocked_when_eval_harness_reports_failure(self):
        eval_response = healthy_eval_response()
        eval_response["passed"] = False
        verdict = self.verify(eval_response, healthy_adapter())
        self.assertEqual(verdict["producer_status"], "BLOCKED")

    def test_blocked_when_adapter_reports_dispatch_mismatch(self):
        adapter = healthy_adapter()
        adapter["fixture_status"] = "HARNESS_DISPATCH_MISMATCH"
        adapter["problems"] = ["expected_agent_role_mismatch"]
        verdict = self.verify(healthy_eval_response(), adapter)
        self.assertEqual(verdict["producer_status"], "BLOCKED")

    def test_blocked_when_role_thread_is_not_a_root_child(self):
        adapter = healthy_adapter()
        adapter["child_thread_reads"]["entries"][0]["parent_thread_id"] = (
            "thread-unrelated"
        )
        adapter["dispatch"]["thread_relations"][0] = spawn_relation(
            "thread-unrelated", [COORDINATOR_THREAD], "thread-unrelated"
        )
        adapter["delegation"]["child_thread_ids"] = sorted(
            [COORDINATOR_THREAD, NESTED_LEAF_THREAD]
        )
        verdict = self.verify(healthy_eval_response(), adapter)
        self.assertEqual(verdict["producer_status"], "BLOCKED")
        self.assertIs(verdict["root_to_paper_analysis"], False)
        self.assertEqual(verdict["coordinator_thread_id"], COORDINATOR_THREAD)

    # ------------------------------------------------------------------
    # INVALID_EVIDENCE
    # ------------------------------------------------------------------

    def test_invalid_evidence_when_nested_child_parent_attribution_conflicts(self):
        adapter = healthy_adapter()
        adapter["child_thread_reads"]["entries"][1]["parent_thread_id"] = ROOT_THREAD
        verdict = self.verify(healthy_eval_response(), adapter)
        self.assertEqual(verdict["producer_status"], "INVALID_EVIDENCE")

    def test_invalid_evidence_when_coordinator_identity_is_ambiguous(self):
        adapter = healthy_adapter()
        adapter["dispatch"]["thread_relations"].append(
            spawn_relation(ROOT_THREAD, [SECOND_ROLE_THREAD], ROOT_THREAD, call_id="exec-2")
        )
        adapter["delegation"]["child_thread_ids"] = sorted(
            [COORDINATOR_THREAD, NESTED_LEAF_THREAD, SECOND_ROLE_THREAD]
        )
        adapter["delegation"]["formal_child_count"] = 3
        adapter["child_thread_reads"]["entries"].append(
            read_entry(
                SECOND_ROLE_THREAD, ROOT_THREAD, effective_role=EXPECTED_AGENT
            )
        )
        adapter["child_thread_reads"]["entry_count"] = 3
        verdict = self.verify(healthy_eval_response(), adapter)
        self.assertEqual(verdict["producer_status"], "INVALID_EVIDENCE")

    def test_invalid_evidence_when_adapter_reports_invalid_evidence(self):
        adapter = healthy_adapter()
        adapter["fixture_status"] = "INVALID_EVIDENCE"
        adapter["problems"] = ["corrupted app-server dispatch evidence fails closed"]
        verdict = self.verify(healthy_eval_response(), adapter)
        self.assertEqual(verdict["producer_status"], "INVALID_EVIDENCE")

    def test_invalid_evidence_on_malformed_shapes(self):
        cases = []
        cases.append(("eval response not an object", [], healthy_adapter()))
        cases.append(("adapter not an object", healthy_eval_response(), []))

        adapter = healthy_adapter()
        adapter["schema"] = 2
        cases.append(("adapter schema drift", healthy_eval_response(), adapter))

        adapter = healthy_adapter()
        adapter["adapter_contract_id"] = "skills-test-fixtures/codex-eval-adapter@8"
        cases.append(("adapter contract drift", healthy_eval_response(), adapter))

        adapter = healthy_adapter()
        adapter["fixture_status"] = "SOMETHING_ELSE"
        cases.append(("unknown fixture_status", healthy_eval_response(), adapter))

        adapter = healthy_adapter()
        adapter["problems"] = "not-a-list"
        cases.append(("problems not a list", healthy_eval_response(), adapter))

        adapter = healthy_adapter()
        del adapter["dispatch"]
        cases.append(("dispatch missing", healthy_eval_response(), adapter))

        eval_response = healthy_eval_response()
        del eval_response["output"]
        cases.append(("output missing", eval_response, healthy_adapter()))

        eval_response = healthy_eval_response()
        eval_response["passed"] = "yes"
        cases.append(("passed not a boolean", eval_response, healthy_adapter()))

        eval_response = healthy_eval_response()
        eval_response["version"] = 5
        cases.append(("version not a string", eval_response, healthy_adapter()))

        adapter = healthy_adapter()
        adapter["dispatch"]["thread_relations"][1] = spawn_relation(
            None, [NESTED_LEAF_THREAD], COORDINATOR_THREAD
        )
        cases.append(("spawn relation without sender", healthy_eval_response(), adapter))

        adapter = healthy_adapter()
        adapter["dispatch"]["thread_relations"][1] = spawn_relation(
            COORDINATOR_THREAD, [], COORDINATOR_THREAD
        )
        cases.append(("spawn relation without receivers", healthy_eval_response(), adapter))

        adapter = healthy_adapter()
        del adapter["delegation"]
        cases.append(("delegation missing", healthy_eval_response(), adapter))

        adapter = healthy_adapter()
        adapter["delegation"]["state"] = "unobservable"
        cases.append(
            ("delegation unobservable with nested children", healthy_eval_response(), adapter)
        )

        adapter = healthy_adapter()
        adapter["delegation"]["child_thread_ids"] = ["thread-never-spawned"]
        cases.append(
            ("delegation children without formal ownership", healthy_eval_response(), adapter)
        )

        adapter = healthy_adapter()
        adapter["dispatch"]["thread_relations"][1] = spawn_relation(
            COORDINATOR_THREAD, [ROOT_THREAD], COORDINATOR_THREAD
        )
        cases.append(("root as spawn receiver", healthy_eval_response(), adapter))

        for name, eval_response, broken_adapter in cases:
            with self.subTest(case=name):
                verdict = self.verify(eval_response, broken_adapter)
                self.assertEqual(verdict["producer_status"], "INVALID_EVIDENCE", name)
                self.assertTrue(verdict["reasons"], name)

    # ------------------------------------------------------------------
    # Contract id override + CLI
    # ------------------------------------------------------------------

    def test_expected_contract_id_override_is_honored(self):
        adapter = healthy_adapter()
        adapter["adapter_contract_id"] = "skills-test-fixtures/codex-eval-adapter@10"
        verdict = self.verify(
            healthy_eval_response(),
            adapter,
            expected_contract_id="skills-test-fixtures/codex-eval-adapter@10",
        )
        self.assertEqual(verdict["producer_status"], "PASS")

    def test_cli_writes_verdict_and_exit_code(self):
        for expected_status, expected_exit, adapter in (
            ("PASS", 0, healthy_adapter()),
            ("FAIL_PRODUCER", 1, self._fail_producer_adapter()),
        ):
            with self.subTest(status=expected_status):
                with tempfile.TemporaryDirectory() as tmp:
                    tmp_path = Path(tmp)
                    eval_path = tmp_path / "eval-response.json"
                    adapter_path = tmp_path / "adapter.json"
                    output_path = tmp_path / "runtime-topology.json"
                    eval_path.write_text(
                        json.dumps(healthy_eval_response()), encoding="utf-8"
                    )
                    adapter_path.write_text(json.dumps(adapter), encoding="utf-8")
                    result = subprocess.run(
                        [
                            sys.executable,
                            str(SCRIPT),
                            "--eval-response",
                            str(eval_path),
                            "--adapter",
                            str(adapter_path),
                            "--output",
                            str(output_path),
                        ],
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                    self.assertEqual(result.returncode, expected_exit, result.stderr)
                    verdict = json.loads(output_path.read_text(encoding="utf-8"))
                    self.assertEqual(verdict["producer_status"], expected_status)
                    self.assertIn(
                        f"producer_status: {expected_status}", result.stderr
                    )

    @staticmethod
    def _fail_producer_adapter():
        adapter = healthy_adapter()
        adapter["dispatch"]["thread_relations"] = [
            spawn_relation(ROOT_THREAD, [COORDINATOR_THREAD], ROOT_THREAD)
        ]
        adapter["delegation"] = {
            "state": "confirmed",
            "formal_child_count": 1,
            "child_thread_ids": [COORDINATOR_THREAD],
            "basis": ["formal_spawn_relation"],
            "reason_code": None,
        }
        adapter["child_thread_reads"] = {
            "entry_count": 1,
            "identity_eligible_thread_ids": [COORDINATOR_THREAD],
            "entries": [
                read_entry(
                    COORDINATOR_THREAD, ROOT_THREAD, effective_role=EXPECTED_AGENT
                )
            ],
        }
        return adapter


if __name__ == "__main__":
    unittest.main()
