"""Deterministic unit tests for the PA-CODEX-FULL-LEAF-01 topology verifier.

The static JSON built here is a producer verifier test fixture only; it is
not the shared runtime fixture protocol. The verifier consumes the raw /eval
response plus the pinned codex-eval-adapter@9 contract, so these fixtures
mirror the contract's formal spawnAgent relation surface. Identity fields
may appear in the raw evidence; the verdict must never depend on them.
"""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys

from verify_codex_full_mode_topology import (
    CASE_ID,
    PINNED_CONTRACT_ID,
    STATUS_BLOCKED,
    STATUS_FAIL_PRODUCER,
    STATUS_INVALID_EVIDENCE,
    STATUS_PASS,
    verify_topology,
)

ROOT_THREAD = "11111111-1111-7111-1111-111111111111"
OUTER_THREAD = "22222222-2222-7222-2222-222222222222"
NESTED_A = "33333333-3333-7333-3333-333333333333"
NESTED_B = "44444444-4444-7444-4444-444444444444"
NESTED_C = "55555555-5555-7555-5555-555555555555"


def contract() -> dict:
    """Minimal mirror of the pinned codex-eval-adapter@9 contract surfaces."""

    return {
        "contract_id": PINNED_CONTRACT_ID,
        "response_field_map": {
            "codex_version": "version",
            "thread_id": "output.thread_id",
            "app_server_events": "output.app_server_events",
        },
        "dispatch_evidence_item_types": ["subAgentActivity", "collabAgentToolCall"],
        "app_server_event_envelope": {
            "dispatch_methods": ["item/started", "item/completed"],
            "item_source": "message.params.item",
        },
        "raw_identity_path": {"formal_spawn_relation": {"tool": "spawnAgent"}},
        "delegation": {"fail_closed": {}},
    }


def event(method: str, item: dict, thread_id: str | None = None) -> dict:
    params: dict = {"item": item}
    if thread_id is not None:
        params["threadId"] = thread_id
    return {
        "runtime_seq": 1,
        "direction": "recv",
        "message": {"method": method, "params": params},
    }


def spawn(
    sender: str,
    receivers: list[str] | None,
    *,
    method: str = "item/completed",
    tool: str = "spawnAgent",
    include_sender: bool = True,
) -> dict:
    item: dict = {"type": "collabAgentToolCall", "tool": tool, "status": "completed"}
    if include_sender:
        item["senderThreadId"] = sender
    if receivers is not None:
        item["receiverThreadIds"] = receivers
    return event(method, item, thread_id=sender)


def eval_response(events: list[dict] | None = None) -> dict:
    return {
        "passed": True,
        "version": "codex-cli 0.154.0",
        "output": {
            "thread_id": ROOT_THREAD,
            "app_server_events": events if events is not None else [],
        },
    }


def healthy_events() -> list[dict]:
    return [
        spawn(ROOT_THREAD, [], method="item/started"),
        spawn(ROOT_THREAD, [OUTER_THREAD]),
        spawn(OUTER_THREAD, [], method="item/started"),
        spawn(OUTER_THREAD, [NESTED_A]),
        spawn(OUTER_THREAD, [NESTED_B]),
        spawn(OUTER_THREAD, [NESTED_C]),
        spawn(OUTER_THREAD, [NESTED_A, NESTED_B], tool="wait"),
    ]


# --- PASS ---------------------------------------------------------------------


def test_pass_unique_outer_child_with_nested_children() -> None:
    verdict = verify_topology(eval_response(healthy_events()), contract())
    assert verdict["producer_status"] == STATUS_PASS
    assert verdict["case_id"] == CASE_ID
    assert verdict["root_thread_id"] == ROOT_THREAD
    assert verdict["root_direct_child_count"] == 1
    assert verdict["outer_thread_id"] == OUTER_THREAD
    assert verdict["nested_direct_child_count"] == 3
    assert verdict["nested_child_thread_ids"] == [NESTED_A, NESTED_B, NESTED_C]
    assert verdict["formal_spawn_relation_count"] == 4
    assert verdict["reasons"] == []
    assert verdict["provenance"] == {
        "eval_version": "codex-cli 0.154.0",
        "contract_id": PINNED_CONTRACT_ID,
    }


def test_pass_minimal_single_nested_child() -> None:
    events = [spawn(ROOT_THREAD, [OUTER_THREAD]), spawn(OUTER_THREAD, [NESTED_A])]
    verdict = verify_topology(eval_response(events), contract())
    assert verdict["producer_status"] == STATUS_PASS
    assert verdict["formal_spawn_relation_count"] == 2
    assert verdict["nested_child_thread_ids"] == [NESTED_A]


def test_started_and_completed_of_same_edge_deduplicate() -> None:
    events = [
        spawn(ROOT_THREAD, [], method="item/started"),
        spawn(ROOT_THREAD, [OUTER_THREAD]),
        spawn(OUTER_THREAD, [], method="item/started"),
        spawn(OUTER_THREAD, [NESTED_A]),
        spawn(OUTER_THREAD, [NESTED_A]),
    ]
    verdict = verify_topology(eval_response(events), contract())
    assert verdict["producer_status"] == STATUS_PASS
    assert verdict["formal_spawn_relation_count"] == 2


def test_started_without_concrete_receivers_is_ignored() -> None:
    events = [
        spawn(ROOT_THREAD, [], method="item/started"),
        spawn(ROOT_THREAD, [OUTER_THREAD]),
        spawn(OUTER_THREAD, [NESTED_A]),
    ]
    verdict = verify_topology(eval_response(events), contract())
    assert verdict["producer_status"] == STATUS_PASS


def test_non_spawn_collab_tools_never_contribute_formal_children() -> None:
    events = [
        spawn(ROOT_THREAD, [OUTER_THREAD]),
        spawn(ROOT_THREAD, [NESTED_A], tool="wait"),
        spawn(ROOT_THREAD, [NESTED_B], tool="sendInput"),
        spawn(OUTER_THREAD, [NESTED_A]),
    ]
    verdict = verify_topology(eval_response(events), contract())
    assert verdict["producer_status"] == STATUS_PASS
    assert verdict["nested_child_thread_ids"] == [NESTED_A]
    assert verdict["formal_spawn_relation_count"] == 2


def test_identity_diagnostics_never_change_pass_verdict() -> None:
    """The §4.1 identity-independence regression: the verdict stays PASS."""

    events = healthy_events()
    identity_surfaces = [
        eval_response(events),
        {
            **eval_response(events),
            "output": {
                **eval_response(events)["output"],
                "child_thread_reads": {
                    "entry_count": 4,
                    "identity_eligible_thread_ids": [],
                    "entries": [
                        {
                            "thread_id": OUTER_THREAD,
                            "parent_thread_id": ROOT_THREAD,
                            "relation_kind": "spawn",
                            "outcome": "ok",
                            "identity_eligible": True,
                            "effective_role": "default",
                        },
                        {
                            "thread_id": NESTED_A,
                            "parent_thread_id": OUTER_THREAD,
                            "relation_kind": "spawn",
                            "outcome": "ok",
                            "identity_eligible": True,
                            "effective_role": "default",
                        },
                    ],
                },
                "dispatch": {
                    "agent_identity": {
                        "requested_role": "paper-analysis",
                        "loaded_identity": None,
                        "effective_role": "default",
                    }
                },
            },
        },
    ]
    for response in identity_surfaces:
        verdict = verify_topology(response, contract())
        assert verdict["producer_status"] == STATUS_PASS
        serialized = json.dumps(verdict)
        for forbidden in (
            "child_thread_reads",
            "agentRole",
            "agent_type",
            "agentPath",
            "effective_role",
            "coordinator_identity",
            "paper_analysis_thread_id",
        ):
            assert forbidden not in serialized


# --- BLOCKED ------------------------------------------------------------------


def test_blocked_root_has_no_formal_direct_child() -> None:
    events = [spawn(OUTER_THREAD, [NESTED_A])]
    verdict = verify_topology(eval_response(events), contract())
    assert verdict["producer_status"] == STATUS_BLOCKED
    assert verdict["root_direct_child_count"] == 0
    assert verdict["outer_thread_id"] is None


def test_blocked_root_has_multiple_formal_direct_children() -> None:
    events = [
        spawn(ROOT_THREAD, [OUTER_THREAD]),
        spawn(ROOT_THREAD, [NESTED_A]),
        spawn(OUTER_THREAD, [NESTED_B]),
    ]
    verdict = verify_topology(eval_response(events), contract())
    assert verdict["producer_status"] == STATUS_BLOCKED
    assert verdict["root_direct_child_count"] == 2


def test_blocked_when_eval_reports_passed_false() -> None:
    response = {**eval_response(healthy_events()), "passed": False}
    verdict = verify_topology(response, contract())
    assert verdict["producer_status"] == STATUS_BLOCKED


def test_blocked_when_version_is_null() -> None:
    response = {**eval_response(healthy_events()), "version": None}
    verdict = verify_topology(response, contract())
    assert verdict["producer_status"] == STATUS_BLOCKED


def test_blocked_when_version_is_blank_string() -> None:
    response = {**eval_response(healthy_events()), "version": "  "}
    verdict = verify_topology(response, contract())
    assert verdict["producer_status"] == STATUS_BLOCKED


def test_missing_app_server_events_blocks_via_empty_topology() -> None:
    response = eval_response()
    response["output"].pop("app_server_events")
    verdict = verify_topology(response, contract())
    assert verdict["producer_status"] == STATUS_BLOCKED
    assert verdict["root_direct_child_count"] == 0


# --- FAIL_PRODUCER ------------------------------------------------------------


def test_fail_producer_outer_child_without_nested_children() -> None:
    events = [spawn(ROOT_THREAD, [OUTER_THREAD])]
    verdict = verify_topology(eval_response(events), contract())
    assert verdict["producer_status"] == STATUS_FAIL_PRODUCER
    assert verdict["outer_thread_id"] == OUTER_THREAD
    assert verdict["nested_direct_child_count"] == 0
    assert verdict["reasons"]


# --- INVALID_EVIDENCE ---------------------------------------------------------


def test_invalid_completed_spawn_without_concrete_receivers() -> None:
    events = [
        spawn(ROOT_THREAD, [OUTER_THREAD]),
        spawn(OUTER_THREAD, [], method="item/completed"),
    ]
    verdict = verify_topology(eval_response(events), contract())
    assert verdict["producer_status"] == STATUS_INVALID_EVIDENCE


def test_invalid_missing_receiver_thread_ids_on_completed_spawn() -> None:
    events = [
        spawn(ROOT_THREAD, [OUTER_THREAD]),
        spawn(OUTER_THREAD, None),
    ]
    verdict = verify_topology(eval_response(events), contract())
    assert verdict["producer_status"] == STATUS_INVALID_EVIDENCE


def test_invalid_same_child_claimed_by_different_senders() -> None:
    events = [
        spawn(ROOT_THREAD, [OUTER_THREAD]),
        spawn(OUTER_THREAD, [NESTED_A]),
        spawn(ROOT_THREAD, [NESTED_A]),
    ]
    verdict = verify_topology(eval_response(events), contract())
    assert verdict["producer_status"] == STATUS_INVALID_EVIDENCE


def test_invalid_malformed_event_shapes() -> None:
    cases = {
        "empty sender": [spawn(ROOT_THREAD, [OUTER_THREAD]), spawn("", [NESTED_A])],
        "missing sender": [
            spawn(ROOT_THREAD, [OUTER_THREAD]),
            spawn(OUTER_THREAD, [NESTED_A], include_sender=False),
        ],
        "non-string receiver": [
            spawn(ROOT_THREAD, [OUTER_THREAD]),
            spawn(OUTER_THREAD, [NESTED_A]),
            spawn(ROOT_THREAD, [42]),
        ],
        "empty-string receiver": [
            spawn(ROOT_THREAD, [OUTER_THREAD]),
            spawn(ROOT_THREAD, [""]),
        ],
        "receivers not a list": [
            spawn(ROOT_THREAD, [OUTER_THREAD]),
            spawn(ROOT_THREAD, "not-a-list"),
        ],
    }
    for label, events in cases.items():
        response = eval_response(events)
        verdict = verify_topology(response, contract())
        assert verdict["producer_status"] == STATUS_INVALID_EVIDENCE, label
    response = eval_response()
    response["output"]["app_server_events"] = "nope"
    verdict = verify_topology(response, contract())
    assert verdict["producer_status"] == STATUS_INVALID_EVIDENCE, "events not a list"


def test_invalid_malformed_dispatch_envelopes_fail_closed() -> None:
    """Recognized dispatch methods must carry an object at the contract item path."""

    for method in ("item/started", "item/completed"):
        cases = {
            "params missing": {"message": {"method": method}},
            "params non-object": {
                "message": {"method": method, "params": "not-an-object"}
            },
            "item missing": {"message": {"method": method, "params": {}}},
            "item null": {
                "message": {"method": method, "params": {"item": None}}
            },
            "item non-object": {
                "message": {"method": method, "params": {"item": []}}
            },
        }
        for label, malformed in cases.items():
            response = eval_response(
                [spawn(ROOT_THREAD, [OUTER_THREAD]), malformed]
            )
            verdict = verify_topology(response, contract())
            assert verdict["producer_status"] == STATUS_INVALID_EVIDENCE, (
                method,
                label,
            )


def test_invalid_common_gate_shapes() -> None:
    base = eval_response(healthy_events())
    cases = {
        "passed missing": {k: v for k, v in base.items() if k != "passed"},
        "passed not bool": {**base, "passed": "true"},
        "version not string": {**base, "version": 154},
        "thread_id missing": {
            **base,
            "output": {"app_server_events": base["output"]["app_server_events"]},
        },
        "response not object": [base],
    }
    for label, response in cases.items():
        verdict = verify_topology(response, contract())
        assert verdict["producer_status"] == STATUS_INVALID_EVIDENCE, label


def test_invalid_when_contract_lacks_formal_spawn_declaration() -> None:
    broken = contract()
    del broken["raw_identity_path"]
    verdict = verify_topology(eval_response(healthy_events()), broken)
    assert verdict["producer_status"] == STATUS_INVALID_EVIDENCE


def test_invalid_when_contract_is_not_pinned_revision() -> None:
    drifted = {**contract(), "contract_id": "skills-test-fixtures/codex-eval-adapter@8"}
    verdict = verify_topology(eval_response(healthy_events()), drifted)
    assert verdict["producer_status"] == STATUS_INVALID_EVIDENCE


# --- CLI ----------------------------------------------------------------------


def _write_contract(tmp_path: pathlib.Path) -> pathlib.Path:
    path = tmp_path / "contract.json"
    path.write_text(json.dumps(contract()), encoding="utf-8")
    return path


def test_cli_end_to_end_exit_codes(tmp_path: pathlib.Path) -> None:
    verifier = pathlib.Path(__file__).parent / "verify_codex_full_mode_topology.py"
    contract_path = _write_contract(tmp_path)

    pass_response = tmp_path / "pass-response.json"
    pass_response.write_text(
        json.dumps(eval_response(healthy_events())), encoding="utf-8"
    )
    pass_out = tmp_path / "pass-verdict.json"
    passed = subprocess.run(
        [
            sys.executable,
            str(verifier),
            "--eval-response",
            str(pass_response),
            "--contract",
            str(contract_path),
            "--output",
            str(pass_out),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert passed.returncode == 0, passed.stderr
    assert json.loads(pass_out.read_text(encoding="utf-8"))["producer_status"] == (
        STATUS_PASS
    )

    fail_response = tmp_path / "fail-response.json"
    fail_response.write_text(
        json.dumps(eval_response([spawn(ROOT_THREAD, [OUTER_THREAD])])),
        encoding="utf-8",
    )
    fail_out = tmp_path / "fail-verdict.json"
    failed = subprocess.run(
        [
            sys.executable,
            str(verifier),
            "--eval-response",
            str(fail_response),
            "--contract",
            str(contract_path),
            "--output",
            str(fail_out),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert failed.returncode == 1, failed.stderr
    assert json.loads(fail_out.read_text(encoding="utf-8"))["producer_status"] == (
        STATUS_FAIL_PRODUCER
    )
