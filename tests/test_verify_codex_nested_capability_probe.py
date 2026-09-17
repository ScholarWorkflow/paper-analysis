import json
import pathlib
import subprocess
import sys

from verify_codex_nested_capability_probe import (
    CASE_ID,
    STATUS_BLOCKED,
    STATUS_INVALID_EVIDENCE,
    STATUS_NESTED_OK,
    STATUS_NO_NESTED,
    verify_probe,
)

ROOT_THREAD = "11111111-1111-7111-1111-111111111111"
DEPTH1_THREAD = "22222222-2222-7222-2222-222222222222"
DEPTH2_THREAD = "33333333-3333-7333-3333-333333333333"
OTHER_THREAD = "44444444-4444-7444-4444-444444444444"


def contract() -> dict:
    """Minimal mirror of the pinned codex-eval-adapter@9 contract surfaces."""

    return {
        "contract_id": "skills-test-fixtures/codex-eval-adapter@9",
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


def custom_tool_call(thread: str, name: str, action: str) -> dict:
    """Code Mode programmatic tool-calling item (the runtime's native
    multi-agent invocation surface); diagnostics only, never formal.

    The runtime records the program text in ``input``; ``action`` is kept as
    an alternative spelling for robustness.
    """

    return event(
        "rawResponseItem/completed",
        {"type": "custom_tool_call", "name": name, "status": "completed", "input": action},
        thread_id=thread,
    )


# --- NESTED_OK -----------------------------------------------------------------


def test_nested_ok_root_one_child_with_grandchild() -> None:
    events = [
        spawn(ROOT_THREAD, [], method="item/started"),
        spawn(ROOT_THREAD, [DEPTH1_THREAD]),
        spawn(DEPTH1_THREAD, [], method="item/started"),
        spawn(DEPTH1_THREAD, [DEPTH2_THREAD]),
    ]
    verdict = verify_probe(eval_response(events), contract())
    assert verdict["status"] == STATUS_NESTED_OK
    assert verdict["schema"] == 2
    assert verdict["case_id"] == CASE_ID
    assert verdict["root_thread_id"] == ROOT_THREAD
    assert verdict["root_direct_child_count"] == 1
    assert verdict["depth1_thread_id"] == DEPTH1_THREAD
    assert verdict["depth2_direct_child_count"] == 1
    assert verdict["depth2_child_thread_ids"] == [DEPTH2_THREAD]
    assert verdict["formal_spawn_relation_count"] == 2
    assert verdict["reasons"] == []
    assert verdict["provenance"] == {
        "eval_version": "codex-cli 0.154.0",
        "contract_id": "skills-test-fixtures/codex-eval-adapter@9",
    }


def test_nested_ok_any_positive_grandchild_count() -> None:
    # Characterization asks "can the depth-1 child spawn at all"; more than
    # one grandchild still confirms the capability surface.
    events = [
        spawn(ROOT_THREAD, [DEPTH1_THREAD]),
        spawn(DEPTH1_THREAD, [DEPTH2_THREAD, OTHER_THREAD]),
    ]
    verdict = verify_probe(eval_response(events), contract())
    assert verdict["status"] == STATUS_NESTED_OK
    assert verdict["depth2_child_thread_ids"] == [DEPTH2_THREAD, OTHER_THREAD]


# --- NO_NESTED -----------------------------------------------------------------


def test_no_nested_root_one_child_zero_grandchild() -> None:
    events = [
        spawn(ROOT_THREAD, [DEPTH1_THREAD]),
    ]
    verdict = verify_probe(eval_response(events), contract())
    assert verdict["status"] == STATUS_NO_NESTED
    assert verdict["root_direct_child_count"] == 1
    assert verdict["depth1_thread_id"] == DEPTH1_THREAD
    assert verdict["depth2_direct_child_count"] == 0
    assert verdict["depth2_child_thread_ids"] == []
    assert verdict["formal_spawn_relation_count"] == 1


# --- BLOCKED -------------------------------------------------------------------


def test_blocked_root_zero_children() -> None:
    verdict = verify_probe(eval_response([]), contract())
    assert verdict["status"] == STATUS_BLOCKED
    assert verdict["root_direct_child_count"] == 0


def test_blocked_root_multiple_children() -> None:
    events = [
        spawn(ROOT_THREAD, [DEPTH1_THREAD]),
        spawn(ROOT_THREAD, [OTHER_THREAD]),
    ]
    verdict = verify_probe(eval_response(events), contract())
    assert verdict["status"] == STATUS_BLOCKED
    assert verdict["root_direct_child_count"] == 2


def test_blocked_when_harness_reports_failure() -> None:
    response = eval_response([spawn(ROOT_THREAD, [DEPTH1_THREAD])])
    response["passed"] = False
    verdict = verify_probe(response, contract())
    assert verdict["status"] == STATUS_BLOCKED


def test_blocked_when_version_null() -> None:
    response = eval_response([spawn(ROOT_THREAD, [DEPTH1_THREAD])])
    response["version"] = None
    verdict = verify_probe(response, contract())
    assert verdict["status"] == STATUS_BLOCKED


# --- INVALID_EVIDENCE ----------------------------------------------------------


def test_invalid_evidence_completed_spawn_without_receivers() -> None:
    events = [
        spawn(ROOT_THREAD, [DEPTH1_THREAD]),
        spawn(DEPTH1_THREAD, None),
    ]
    verdict = verify_probe(eval_response(events), contract())
    assert verdict["status"] == STATUS_INVALID_EVIDENCE


def test_invalid_evidence_conflicting_ownership() -> None:
    events = [
        spawn(ROOT_THREAD, [DEPTH1_THREAD]),
        spawn(OTHER_THREAD, [DEPTH1_THREAD]),
    ]
    verdict = verify_probe(eval_response(events), contract())
    assert verdict["status"] == STATUS_INVALID_EVIDENCE


def test_invalid_evidence_malformed_relation_shape() -> None:
    events = [
        spawn(ROOT_THREAD, [DEPTH1_THREAD]),
        event(
            "item/completed",
            {
                "type": "collabAgentToolCall",
                "tool": "spawnAgent",
                "status": "completed",
                "senderThreadId": DEPTH1_THREAD,
                "receiverThreadIds": "oops",
            },
            thread_id=DEPTH1_THREAD,
        ),
    ]
    verdict = verify_probe(eval_response(events), contract())
    assert verdict["status"] == STATUS_INVALID_EVIDENCE


# --- dedup / identity indifference ----------------------------------------------


# --- tool-surface diagnostics (characterization only) ---------------------------


def test_child_code_mode_surface_is_diagnostic_not_gate() -> None:
    # The corrected probe lets the child use the runtime's observed native
    # invocation surface (Code Mode exec calling multi_agent_v1 tools).
    # Whether the child issued such calls is reported as diagnostics and
    # must never flip the formal status either way.
    events = [
        spawn(ROOT_THREAD, [DEPTH1_THREAD]),
        custom_tool_call(
            DEPTH1_THREAD,
            "exec",
            'const hits = ALL_TOOLS.filter(x => /multi_agent/i.test(x.name));\ntext(hits);\n',
        ),
    ]
    verdict = verify_probe(eval_response(events), contract())
    assert verdict["status"] == STATUS_NO_NESTED
    child = verdict["tool_surface_diagnostics"][DEPTH1_THREAD]
    assert child["custom_tool_call_count"] == 1
    assert child["custom_tool_names"] == ["exec"]
    assert child["queried_all_tools"] is True


def test_diagnostics_reported_on_nested_ok() -> None:
    events = [
        spawn(ROOT_THREAD, [DEPTH1_THREAD]),
        spawn(DEPTH1_THREAD, [DEPTH2_THREAD]),
        custom_tool_call(
            ROOT_THREAD,
            "exec",
            'await tools.multi_agent_v1__spawn_agent({message:"child"});\n',
        ),
    ]
    verdict = verify_probe(eval_response(events), contract())
    assert verdict["status"] == STATUS_NESTED_OK
    root = verdict["tool_surface_diagnostics"][ROOT_THREAD]
    assert root["custom_tool_call_count"] == 1
    assert root["custom_tool_names"] == ["exec"]
    assert root["queried_all_tools"] is False
    assert DEPTH1_THREAD not in verdict["tool_surface_diagnostics"]


def test_started_and_completed_of_same_edge_deduplicate() -> None:
    events = [
        spawn(ROOT_THREAD, [], method="item/started"),
        spawn(ROOT_THREAD, [DEPTH1_THREAD]),
        spawn(DEPTH1_THREAD, [], method="item/started"),
        spawn(DEPTH1_THREAD, [DEPTH2_THREAD]),
        spawn(DEPTH1_THREAD, [DEPTH2_THREAD]),
    ]
    verdict = verify_probe(eval_response(events), contract())
    assert verdict["status"] == STATUS_NESTED_OK
    assert verdict["formal_spawn_relation_count"] == 2


def test_identity_diagnostics_and_self_report_never_change_status() -> None:
    base_events = [
        spawn(ROOT_THREAD, [DEPTH1_THREAD]),
    ]
    decorated_events = base_events + [
        event(
            "item/completed",
            {
                "type": "subAgentActivity",
                "agentPath": ["paper-analysis/coordinator"],
                "agentType": "default",
                "agentRole": "paper-analysis",
            },
            thread_id=DEPTH1_THREAD,
        ),
        event(
            "item/completed",
            {
                "type": "agentMessage",
                "text": "我没有 nested spawn 工具，无法创建 grandchild。",
            },
            thread_id=DEPTH1_THREAD,
        ),
    ]
    plain = verify_probe(eval_response(base_events), contract())
    decorated = verify_probe(eval_response(decorated_events), contract())
    assert plain["status"] == STATUS_NO_NESTED
    assert decorated["status"] == plain["status"]
    assert decorated["depth2_direct_child_count"] == 0
    assert decorated["formal_spawn_relation_count"] == (
        plain["formal_spawn_relation_count"]
    )


def test_invalid_evidence_when_contract_is_not_pinned() -> None:
    bad_contract = contract()
    bad_contract["contract_id"] = "skills-test-fixtures/codex-eval-adapter@8"
    verdict = verify_probe(eval_response([spawn(ROOT_THREAD, [DEPTH1_THREAD])]), bad_contract)
    assert verdict["status"] == STATUS_INVALID_EVIDENCE


# --- CLI ------------------------------------------------------------------------


def test_cli_end_to_end_exit_codes(tmp_path: pathlib.Path) -> None:
    verifier = (
        pathlib.Path(__file__).resolve().parent
        / "runtime/verify_codex_nested_capability_probe.py"
    )
    contract_path = tmp_path / "contract.json"
    contract_path.write_text(json.dumps(contract()), encoding="utf-8")

    confirmed_events = eval_response(
        [spawn(ROOT_THREAD, [DEPTH1_THREAD]), spawn(DEPTH1_THREAD, [DEPTH2_THREAD])]
    )
    confirmed_response = tmp_path / "confirmed-response.json"
    confirmed_response.write_text(json.dumps(confirmed_events), encoding="utf-8")
    confirmed_out = tmp_path / "confirmed-verdict.json"
    confirmed = subprocess.run(
        [
            sys.executable,
            str(verifier),
            "--eval-response",
            str(confirmed_response),
            "--contract",
            str(contract_path),
            "--output",
            str(confirmed_out),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert confirmed.returncode == 0, confirmed.stderr
    assert json.loads(confirmed_out.read_text(encoding="utf-8"))["status"] == (
        STATUS_NESTED_OK
    )

    no_nested_response = tmp_path / "no-nested-response.json"
    no_nested_response.write_text(
        json.dumps(eval_response([spawn(ROOT_THREAD, [DEPTH1_THREAD])])),
        encoding="utf-8",
    )
    no_nested_out = tmp_path / "no-nested-verdict.json"
    no_nested = subprocess.run(
        [
            sys.executable,
            str(verifier),
            "--eval-response",
            str(no_nested_response),
            "--contract",
            str(contract_path),
            "--output",
            str(no_nested_out),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert no_nested.returncode == 1, no_nested.stderr
    assert json.loads(no_nested_out.read_text(encoding="utf-8"))["status"] == (
        STATUS_NO_NESTED
    )
