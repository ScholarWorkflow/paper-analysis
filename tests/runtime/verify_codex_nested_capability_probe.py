#!/usr/bin/env python3
"""Producer-owned nested-capability probe verifier for PA-CODEX-NESTED-CAP-00.

Characterization gate that runs BEFORE the formal PA-CODEX-FULL-LEAF-01
acceptance: it decides whether a depth-1 child in this runtime can emit a
formal depth-2 ``spawnAgent`` grandchild. Codex V1 defaults
``agents.max_depth=1`` and hides the collab tool surface beyond that depth,
so a formal ``outer nested=0`` observation is only attributable to producer
instructions once this probe has characterized the nested spawn capability.

Consumes only structured machine evidence:

* the raw ``/eval`` response saved by the runtime recipe, and
* the pinned ``skills-test-fixtures/codex-eval-adapter@9`` contract JSON that
  defines the formal ``spawnAgent`` relation rules.

The formal-edge parser is shared with the topology verifier so both verdicts
rest on the same ownership rules; this module never changes the main
verifier's exactly-3 acceptance semantics and never runs Codex. Runtime
agent identity is out of scope by contract: the verifier does not read
``child_thread_reads``, ``agent_type``, ``agentRole``, ``agentPath`` or any
requested/loaded/effective role surface, and the child's own textual
self-report ("I have no such tool") is never capability evidence.

This runtime invokes the native V1 multi-agent tools through the Code Mode
programmatic tool-calling surface (``custom_tool_call`` items running
``await tools.multi_agent_v1__spawn_agent(...)``), so the corrected probe
prompt must allow that surface. Whether a thread issued such calls is
reported in the verdict's ``tool_surface_diagnostics`` as characterization
context only and never gates the status: capability is decided exclusively
by formal ``spawnAgent`` relations.

Probe statuses:

* ``NESTED_OK``         root has exactly one formal direct child and that
                        child has >= 1 distinct formal direct grandchild
* ``NO_NESTED``         root has exactly one formal direct child and that
                        child has 0 formal direct grandchildren
* ``BLOCKED``           availability/harness gap: harness failure, runtime
                        version absent, or the root thread has zero or
                        multiple formal direct children (the probe never
                        entered the target path)
* ``INVALID_EVIDENCE``  malformed evidence or mutually contradictory formal
                        ownership

Exit codes: 0 NESTED_OK, 1 NO_NESTED, 2 BLOCKED, 3 INVALID_EVIDENCE.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

from verify_codex_full_mode_topology import (
    _contract_rules,
    _formal_edges,
    _lookup,
)

SCHEMA = 2
CASE_ID = "PA-CODEX-NESTED-CAP-00"

STATUS_NESTED_OK = "NESTED_OK"
STATUS_NO_NESTED = "NO_NESTED"
STATUS_BLOCKED = "BLOCKED"
STATUS_INVALID_EVIDENCE = "INVALID_EVIDENCE"
EXIT_CODES = {
    STATUS_NESTED_OK: 0,
    STATUS_NO_NESTED: 1,
    STATUS_BLOCKED: 2,
    STATUS_INVALID_EVIDENCE: 3,
}


def _tool_surface_diagnostics(events: object) -> dict:
    """Summarize observed Code Mode tool calls per thread.

    Characterization context only: the result never gates the verdict and
    carries counts, tool names and the ALL_TOOLS query flag — no free text.
    """

    if not isinstance(events, list):
        return {}
    surface: dict[str, dict] = {}
    for entry in events:
        if not isinstance(entry, dict):
            continue
        message = entry.get("message")
        params = message.get("params") if isinstance(message, dict) else None
        item = params.get("item") if isinstance(params, dict) else None
        if not isinstance(item, dict) or item.get("type") != "custom_tool_call":
            continue
        thread = params.get("threadId")
        if not isinstance(thread, str) or not thread:
            sender = item.get("senderThreadId")
            thread = sender if isinstance(sender, str) else ""
        record = surface.setdefault(
            thread,
            {
                "custom_tool_call_count": 0,
                "custom_tool_names": [],
                "queried_all_tools": False,
            },
        )
        record["custom_tool_call_count"] += 1
        name = item.get("name")
        if isinstance(name, str) and name and name not in record["custom_tool_names"]:
            record["custom_tool_names"].append(name)
        action = item.get("action")
        if isinstance(action, str) and "ALL_TOOLS" in action:
            record["queried_all_tools"] = True
    for record in surface.values():
        record["custom_tool_names"] = sorted(record["custom_tool_names"])
    return dict(sorted(surface.items()))


def _verdict(
    probe_status: str,
    reasons: list[str],
    *,
    root_thread_id: str | None = None,
    root_direct_child_count: int = 0,
    depth1_thread_id: str | None = None,
    depth2_child_thread_ids: list[str] | None = None,
    formal_spawn_relation_count: int = 0,
    eval_version: str | None = None,
    contract_id: str | None = None,
    tool_surface_diagnostics: dict | None = None,
) -> dict:
    depth2 = sorted(depth2_child_thread_ids or [])
    return {
        "schema": SCHEMA,
        "case_id": CASE_ID,
        "status": probe_status,
        "root_thread_id": root_thread_id,
        "root_direct_child_count": root_direct_child_count,
        "depth1_thread_id": depth1_thread_id,
        "depth2_direct_child_count": len(depth2),
        "depth2_child_thread_ids": depth2,
        "formal_spawn_relation_count": formal_spawn_relation_count,
        "tool_surface_diagnostics": tool_surface_diagnostics or {},
        "reasons": list(reasons),
        "provenance": {
            "eval_version": eval_version,
            "contract_id": contract_id,
        },
    }


def verify_probe(eval_response: dict, contract: dict) -> dict:
    """Evaluate probe evidence against the contract and return the verdict."""

    if not isinstance(contract, dict):
        return _verdict(
            STATUS_INVALID_EVIDENCE, ["contract must be a JSON object"]
        )
    rules, problems = _contract_rules(contract)
    if problems:
        return _verdict(
            STATUS_INVALID_EVIDENCE,
            [
                "contract does not declare the formal spawn relation rules: "
                + "; ".join(problems)
            ],
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

    # --- common evidence gate (same harness health rules as the formal case) ---
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
                "eval response records no usable runtime version; the probe "
                "environment cannot be provenanced"
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
            ["eval harness reported passed=false; the probe run is a harness failure"],
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
    diagnostics = _tool_surface_diagnostics(events)

    # --- formal capability topology ---
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
            tool_surface_diagnostics=diagnostics,
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
            tool_surface_diagnostics=diagnostics,
        )
    edge_count = sum(len(children) for children in children_by_sender.values())
    root_children = sorted(children_by_sender.get(root_thread_id, ()))
    if len(root_children) == 0:
        return _verdict(
            STATUS_BLOCKED,
            [
                "root thread has no formal direct child; the probe never "
                "entered the target dispatch path"
            ],
            root_thread_id=root_thread_id,
            root_direct_child_count=0,
            formal_spawn_relation_count=edge_count,
            eval_version=version,
            contract_id=contract["contract_id"],
            tool_surface_diagnostics=diagnostics,
        )
    if len(root_children) > 1:
        return _verdict(
            STATUS_BLOCKED,
            [
                "root thread has multiple different formal direct children "
                f"{root_children}; the probe dispatch cannot be uniquely "
                "attributed"
            ],
            root_thread_id=root_thread_id,
            root_direct_child_count=len(root_children),
            formal_spawn_relation_count=edge_count,
            eval_version=version,
            contract_id=contract["contract_id"],
            tool_surface_diagnostics=diagnostics,
        )
    depth1_thread_id = root_children[0]
    depth2_children = sorted(children_by_sender.get(depth1_thread_id, ()))
    if depth2_children:
        return _verdict(
            STATUS_NESTED_OK,
            [],
            root_thread_id=root_thread_id,
            root_direct_child_count=1,
            depth1_thread_id=depth1_thread_id,
            depth2_child_thread_ids=depth2_children,
            formal_spawn_relation_count=edge_count,
            eval_version=version,
            contract_id=contract["contract_id"],
            tool_surface_diagnostics=diagnostics,
        )
    return _verdict(
        STATUS_NO_NESTED,
        [
            "root has exactly one formal direct child "
            f"({depth1_thread_id!r}), but that depth-1 child produced 0 "
            f"formal direct nested {rules['formal_tool']} grandchildren"
        ],
        root_thread_id=root_thread_id,
        root_direct_child_count=1,
        depth1_thread_id=depth1_thread_id,
        depth2_child_thread_ids=[],
        formal_spawn_relation_count=edge_count,
        eval_version=version,
        contract_id=contract["contract_id"],
        tool_surface_diagnostics=diagnostics,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Producer nested-capability probe verdict for "
            "PA-CODEX-NESTED-CAP-00 from the raw /eval response and the "
            "pinned adapter contract (never runs Codex, never reads "
            "identity fields)."
        )
    )
    parser.add_argument(
        "--eval-response", required=True, help="raw /eval response JSON"
    )
    parser.add_argument(
        "--contract",
        required=True,
        help="pinned codex-eval-adapter contract JSON",
    )
    parser.add_argument(
        "--output", required=True, help="path to write the probe verdict JSON"
    )
    args = parser.parse_args(argv)

    eval_response = json.loads(
        pathlib.Path(args.eval_response).read_text(encoding="utf-8")
    )
    contract = json.loads(pathlib.Path(args.contract).read_text(encoding="utf-8"))
    verdict = verify_probe(eval_response, contract)
    output = pathlib.Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(verdict, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(verdict, ensure_ascii=False, indent=2))
    return EXIT_CODES[verdict["status"]]


if __name__ == "__main__":
    sys.exit(main())
