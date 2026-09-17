#!/usr/bin/env python3
"""Producer-owned topology verifier for Codex full-mode case PA-CODEX-FULL-LEAF-01.

Consumes only structured machine evidence:

* the raw ``/eval`` response saved by the runtime recipe, and
* the pinned ``skills-test-fixtures/codex-eval-adapter@9`` contract JSON that
  defines the formal ``spawnAgent`` relation rules.

The verifier never executes Codex, never creates or modifies a consumer, and
never calls the shared adapter. Runtime agent identity is out of scope by
contract: the verifier does not read ``child_thread_reads``, ``agent_type``,
``agentRole``, ``agentPath`` or any requested/loaded/effective role surface,
and identity diagnostics can never create, modify or deny the verdict.

The single runtime PASS threshold (issue #13) is the formal topology:

    root thread
      -> exactly 1 formal direct outer child
           -> >= 1 formal direct nested child

where formal children come only from contract-defined ``spawnAgent``
relations inside ``output.app_server_events``. Prompt text, assistant/model
self-reports and script text are never topology evidence.

Producer statuses:

* ``PASS``             the formal topology threshold holds on healthy evidence
* ``FAIL_PRODUCER``    evidence is healthy and the unique formal outer child
                       exists, but it spawned no formal direct nested child
* ``BLOCKED``          availability/harness gap: harness failure, runtime
                       version absent, or the root thread has zero or multiple
                       formal direct children
* ``INVALID_EVIDENCE`` malformed evidence or mutually contradictory formal
                       ownership (completed spawn without concrete receivers,
                       malformed relation shape, one child claimed by
                       different senders, contract without the formal
                       spawn declaration)

The runtime ``version`` string is recorded as provenance only; a version
change alone never blocks, fails or passes a run. Exit codes: 0 PASS,
1 FAIL_PRODUCER, 2 BLOCKED, 3 INVALID_EVIDENCE.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

SCHEMA = 1
CASE_ID = "PA-CODEX-FULL-LEAF-01"
PINNED_CONTRACT_ID = "skills-test-fixtures/codex-eval-adapter@9"

STATUS_PASS = "PASS"
STATUS_FAIL_PRODUCER = "FAIL_PRODUCER"
STATUS_BLOCKED = "BLOCKED"
STATUS_INVALID_EVIDENCE = "INVALID_EVIDENCE"
EXIT_CODES = {
    STATUS_PASS: 0,
    STATUS_FAIL_PRODUCER: 1,
    STATUS_BLOCKED: 2,
    STATUS_INVALID_EVIDENCE: 3,
}

# Pinned @9 contract surfaces this verifier requires before it runs: the
# envelope dispatch declaration, the formal item type in the dispatch evidence
# set, and the delegation dimension with its fail-closed rules (the contract
# itself refuses parsers that run without the formal spawn declaration).
ENVELOPE_KEY = "app_server_event_envelope"
DISPATCH_METHODS_KEY = "dispatch_methods"
ITEM_SOURCE_KEY = "item_source"
DISPATCH_ITEM_TYPES_KEY = "dispatch_evidence_item_types"
FORMAL_ITEM_TYPE = "collabAgentToolCall"
FORMAL_SPAWN_DECLARATION_KEYS = (
    "raw_identity_path",
    "formal_spawn_relation",
    "tool",
)
DELEGATION_KEY = "delegation"


def _lookup(source: dict, dotted: str):
    """Resolve a contract dotted path like ``message.params.item``."""

    current = source
    for part in dotted.split("."):
        if not isinstance(current, dict) or part not in current:
            return None, False
        current = current[part]
    return current, True


def _verdict(
    producer_status: str,
    reasons: list[str],
    *,
    root_thread_id: str | None = None,
    root_direct_child_count: int = 0,
    outer_thread_id: str | None = None,
    nested_child_thread_ids: list[str] | None = None,
    formal_spawn_relation_count: int = 0,
    eval_version: str | None = None,
    contract_id: str | None = None,
) -> dict:
    nested = sorted(nested_child_thread_ids or [])
    return {
        "schema": SCHEMA,
        "case_id": CASE_ID,
        "producer_status": producer_status,
        "root_thread_id": root_thread_id,
        "root_direct_child_count": root_direct_child_count,
        "outer_thread_id": outer_thread_id,
        "nested_direct_child_count": len(nested),
        "nested_child_thread_ids": nested,
        "formal_spawn_relation_count": formal_spawn_relation_count,
        "reasons": list(reasons),
        "provenance": {
            "eval_version": eval_version,
            "contract_id": contract_id,
        },
    }


def _contract_rules(contract: dict) -> tuple[dict, list[str]]:
    """Extract formal relation rules; return (rules, problems)."""

    problems: list[str] = []
    if contract.get("contract_id") != PINNED_CONTRACT_ID:
        problems.append(
            f"contract_id {contract.get('contract_id')!r} is not the pinned "
            f"{PINNED_CONTRACT_ID!r}"
        )
    envelope = contract.get(ENVELOPE_KEY)
    if not isinstance(envelope, dict):
        return {}, problems + [f"contract lacks {ENVELOPE_KEY}"]
    methods = envelope.get(DISPATCH_METHODS_KEY)
    if (
        not isinstance(methods, list)
        or not methods
        or not all(isinstance(method, str) and method for method in methods)
    ):
        problems.append(f"contract {DISPATCH_METHODS_KEY} must be a non-empty string list")
    item_source = envelope.get(ITEM_SOURCE_KEY)
    if not isinstance(item_source, str) or not item_source:
        problems.append(f"contract {ITEM_SOURCE_KEY} must be a dotted path string")
    item_types = contract.get(DISPATCH_ITEM_TYPES_KEY)
    if not isinstance(item_types, list) or FORMAL_ITEM_TYPE not in item_types:
        problems.append(
            f"contract {DISPATCH_ITEM_TYPES_KEY} does not declare {FORMAL_ITEM_TYPE}"
        )
    spawn_declaration: dict = contract
    for key in FORMAL_SPAWN_DECLARATION_KEYS:
        if not isinstance(spawn_declaration, dict):
            problems.append(
                "contract lacks the formal spawn relation declaration "
                f"({'.'.join(FORMAL_SPAWN_DECLARATION_KEYS)})"
            )
            spawn_declaration = {}
            break
        spawn_declaration = spawn_declaration.get(key, None)  # type: ignore[assignment]
    formal_tool = spawn_declaration if isinstance(spawn_declaration, str) else None
    if not formal_tool:
        problems.append(
            "contract lacks the formal spawn tool declaration "
            f"({'.'.join(FORMAL_SPAWN_DECLARATION_KEYS)})"
        )
    delegation = contract.get(DELEGATION_KEY)
    if not isinstance(delegation, dict) or not isinstance(
        delegation.get("fail_closed"), dict
    ):
        problems.append(
            f"contract lacks the {DELEGATION_KEY} dimension with fail_closed rules"
        )
    if problems:
        return {}, problems
    return {
        "methods": set(methods),
        "item_source": item_source,
        "formal_tool": formal_tool,
    }, []


def _formal_edges(
    events, rules: dict, method_completed: str | None
) -> tuple[dict[str, set[str]], dict[str, set[str]], list[str]]:
    """Parse formal spawn edges.

    Returns (children_by_sender, senders_by_child, problems); both maps hold
    deduplicated directed edges across started/completed lifecycles.
    """

    problems: list[str] = []
    children_by_sender: dict[str, set[str]] = {}
    senders_by_child: dict[str, set[str]] = {}
    if not isinstance(events, list):
        return {}, {}, ["output.app_server_events must be a list when present"]
    for index, event in enumerate(events):
        if not isinstance(event, dict):
            problems.append(f"app_server_events[{index}] must be an object")
            continue
        message = event.get("message")
        if not isinstance(message, dict):
            continue
        method = message.get("method")
        if method not in rules["methods"]:
            continue
        item, found = _lookup(event, rules["item_source"])
        if not found:
            problems.append(
                f"app_server_events[{index}]: dispatch method {method!r} "
                f"is missing the contract item source {rules['item_source']!r}"
            )
            continue
        if not isinstance(item, dict):
            problems.append(
                f"app_server_events[{index}]: dispatch method {method!r} "
                "has a non-object contract item"
            )
            continue
        if item.get("type") != FORMAL_ITEM_TYPE:
            continue
        if item.get("tool") != rules["formal_tool"]:
            continue
        sender = item.get("senderThreadId")
        if not isinstance(sender, str) or not sender:
            problems.append(
                f"app_server_events[{index}]: formal {rules['formal_tool']} "
                "relation has no non-empty string senderThreadId"
            )
            continue
        receivers = item.get("receiverThreadIds")
        if receivers is None or receivers == []:
            if method == method_completed:
                problems.append(
                    f"app_server_events[{index}]: completed formal "
                    f"{rules['formal_tool']} relation has no concrete "
                    "receiverThreadIds"
                )
            continue
        if not isinstance(receivers, list) or not all(
            isinstance(receiver, str) and receiver for receiver in receivers
        ):
            problems.append(
                f"app_server_events[{index}]: formal {rules['formal_tool']} "
                "relation has malformed receiverThreadIds"
            )
            continue
        for receiver in receivers:
            children_by_sender.setdefault(sender, set()).add(receiver)
            senders_by_child.setdefault(receiver, set()).add(sender)
    return children_by_sender, senders_by_child, problems


def verify_topology(eval_response: dict, contract: dict) -> dict:
    """Evaluate structured evidence against the contract and return the verdict."""

    if not isinstance(contract, dict):
        return _verdict(
            STATUS_INVALID_EVIDENCE, ["contract must be a JSON object"]
        )
    rules, problems = _contract_rules(contract)
    if problems:
        return _verdict(
            STATUS_INVALID_EVIDENCE,
            ["contract does not declare the formal spawn relation rules: " + "; ".join(problems)],
            contract_id=contract.get("contract_id")
            if isinstance(contract.get("contract_id"), str)
            else None,
        )

    if not isinstance(eval_response, dict):
        return _verdict(
            STATUS_INVALID_EVIDENCE,
            ["eval response must be a JSON object"],
            contract_id=contract["contract_id"],
        )

    # --- common evidence gate (issue #13 §5.9 steps 1-3) ---
    passed = eval_response.get("passed")
    if not isinstance(passed, bool):
        return _verdict(
            STATUS_INVALID_EVIDENCE,
            [
                "eval response top-level passed must be a boolean; without it "
                "the harness outcome is not machine-readable"
            ],
            contract_id=contract["contract_id"],
        )
    version = eval_response.get("version")
    if version is None or (isinstance(version, str) and not version.strip()):
        return _verdict(
            STATUS_BLOCKED,
            [
                "eval response records no usable runtime version; the run "
                "environment cannot be provenanced (version stays provenance "
                "only and is never a string gate)"
            ],
            contract_id=contract["contract_id"],
        )
    if not isinstance(version, str):
        return _verdict(
            STATUS_INVALID_EVIDENCE,
            [
                "eval response version must be a string or null, got "
                f"{type(version).__name__}"
            ],
            contract_id=contract["contract_id"],
        )
    if passed is False:
        return _verdict(
            STATUS_BLOCKED,
            ["eval harness reported passed=false; the run is a harness failure"],
            eval_version=version,
            contract_id=contract["contract_id"],
        )
    field_map = contract.get("response_field_map", {})
    thread_path = (
        field_map.get("thread_id") if isinstance(field_map, dict) else None
    )
    events_path = (
        field_map.get("app_server_events")
        if isinstance(field_map, dict)
        else None
    )
    root_thread_id, _ = (
        _lookup(eval_response, thread_path)
        if isinstance(thread_path, str)
        else (None, False)
    )
    if not isinstance(root_thread_id, str) or not root_thread_id:
        return _verdict(
            STATUS_INVALID_EVIDENCE,
            ["eval response output.thread_id must be a non-empty string"],
            eval_version=version,
            contract_id=contract["contract_id"],
        )
    events, _ = (
        _lookup(eval_response, events_path)
        if isinstance(events_path, str)
        else (None, False)
    )
    if events is None:
        events = []

    # --- formal topology (issue #13 §5.9 steps 4-8) ---
    completed = "item/completed" if "item/completed" in rules["methods"] else None
    children_by_sender, senders_by_child, parse_problems = _formal_edges(
        events, rules, completed
    )
    if parse_problems:
        return _verdict(
            STATUS_INVALID_EVIDENCE,
            parse_problems,
            root_thread_id=root_thread_id,
            eval_version=version,
            contract_id=contract["contract_id"],
        )
    conflicted = sorted(
        receiver
        for receiver, senders in senders_by_child.items()
        if len(senders) > 1
    )
    if conflicted:
        return _verdict(
            STATUS_INVALID_EVIDENCE,
            [
                "conflicting formal ownership: child thread(s) "
                f"{conflicted} are claimed by formal {rules['formal_tool']} "
                "relations with different senderThreadId values"
            ],
            root_thread_id=root_thread_id,
            eval_version=version,
            contract_id=contract["contract_id"],
        )
    edge_count = sum(len(children) for children in children_by_sender.values())
    root_children = sorted(children_by_sender.get(root_thread_id, ()))
    if len(root_children) == 0:
        return _verdict(
            STATUS_BLOCKED,
            [
                "root thread has no formal direct child; the fixed outer "
                "dispatch never entered the installed producer path"
            ],
            root_thread_id=root_thread_id,
            root_direct_child_count=0,
            formal_spawn_relation_count=edge_count,
            eval_version=version,
            contract_id=contract["contract_id"],
        )
    if len(root_children) > 1:
        return _verdict(
            STATUS_BLOCKED,
            [
                "root thread has multiple different formal direct children "
                f"{root_children}; the fixed outer dispatch cannot be "
                "uniquely attributed"
            ],
            root_thread_id=root_thread_id,
            root_direct_child_count=len(root_children),
            formal_spawn_relation_count=edge_count,
            eval_version=version,
            contract_id=contract["contract_id"],
        )
    outer_thread_id = root_children[0]
    nested = sorted(children_by_sender.get(outer_thread_id, ()))
    if not nested:
        return _verdict(
            STATUS_FAIL_PRODUCER,
            [
                "healthy evidence with exactly one formal outer child "
                f"({outer_thread_id!r}), but the outer child produced no "
                f"formal direct nested {rules['formal_tool']} child; full-mode "
                "Step 3 was not delegated"
            ],
            root_thread_id=root_thread_id,
            root_direct_child_count=1,
            outer_thread_id=outer_thread_id,
            formal_spawn_relation_count=edge_count,
            eval_version=version,
            contract_id=contract["contract_id"],
        )
    return _verdict(
        STATUS_PASS,
        [],
        root_thread_id=root_thread_id,
        root_direct_child_count=1,
        outer_thread_id=outer_thread_id,
        nested_child_thread_ids=nested,
        formal_spawn_relation_count=edge_count,
        eval_version=version,
        contract_id=contract["contract_id"],
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Producer formal-topology verdict for PA-CODEX-FULL-LEAF-01 from "
            "the raw /eval response and the pinned adapter contract (never "
            "runs Codex, never reads identity fields)."
        )
    )
    parser.add_argument(
        "--eval-response", required=True, help="raw /eval response JSON"
    )
    parser.add_argument(
        "--contract",
        required=True,
        help="pinned skills-test-fixtures codex-eval-adapter contract JSON",
    )
    parser.add_argument("--output", required=True, help="verdict JSON output path")
    args = parser.parse_args(argv)

    try:
        with open(args.eval_response, encoding="utf-8") as handle:
            eval_response = json.load(handle)
        with open(args.contract, encoding="utf-8") as handle:
            contract = json.load(handle)
    except (OSError, json.JSONDecodeError) as error:
        verdict = _verdict(
            STATUS_INVALID_EVIDENCE,
            [f"cannot read eval response or contract JSON: {error}"],
        )
    else:
        verdict = verify_topology(eval_response, contract)

    payload = json.dumps(verdict, ensure_ascii=False, indent=2) + "\n"
    output = pathlib.Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(payload, encoding="utf-8")
    print(payload, end="")
    print(f"producer_status: {verdict['producer_status']}", file=sys.stderr)
    return EXIT_CODES[verdict["producer_status"]]


if __name__ == "__main__":
    sys.exit(main())
