#!/usr/bin/env python3
"""Producer-owned topology verifier for Codex full-mode case PA-CODEX-FULL-LEAF-01.

Consumes only structured machine evidence:

* the raw ``/eval`` response saved by the runtime recipe, and
* the adapter output produced by the shared ``skills-test-fixtures`` parser
  (``parse_codex_eval_evidence.py``) at the pinned adapter contract.

The verifier never executes Codex, never creates or modifies a consumer, and
never reads prompt text or model natural-language self-reports to guess
topology. Its single runtime PASS threshold (issue #13) is:

    the exact ``paper-analysis`` coordinator (a root direct child whose
    persisted role is machine-confirmed) has >= 1 formal direct nested
    ``spawnAgent`` analysis child.

Producer statuses:

* ``PASS``             the contract above holds on healthy machine evidence
* ``FAIL_PRODUCER``    evidence is healthy and the exact coordinator is
                       confirmed, but no formal direct nested analysis child
                       exists
* ``BLOCKED``          availability/harness capability gap: harness failure,
                       runtime version absent, adapter-reported dependency
                       blocker, dispatch mismatch, or an exact coordinator
                       identity that cannot be machine-confirmed
* ``INVALID_EVIDENCE`` malformed evidence or mutually contradictory machine
                       evidence (ambiguous coordinator, parent-ownership
                       conflict, adapter contract drift, ...)

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
PINNED_ADAPTER_CONTRACT_ID = "skills-test-fixtures/codex-eval-adapter@9"
# Pinned adapter@9 formal spawn tool (raw_identity_path.formal_spawn_relation
# .tool). Formal nested children come only from relations of this tool; other
# collab tools (wait, sendInput) stay lifecycle diagnostics.
FORMAL_SPAWN_TOOL = "spawnAgent"

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

ADAPTER_ROLE = "codex-eval-evidence"
ADAPTER_FIXTURE_STATUSES = (
    "FIXTURE_READY",
    "BLOCKED_DEPENDENCY",
    "HARNESS_DISPATCH_UNCONFIRMED",
    "HARNESS_DISPATCH_MISMATCH",
    "INVALID_EVIDENCE",
)
DELEGATION_STATES = ("confirmed", "unobservable")


def _verdict(
    producer_status: str,
    reasons: list[str],
    *,
    coordinator_thread_id: str | None = None,
    root_to_paper_analysis: bool = False,
    nested_child_thread_ids: list[str] | None = None,
    eval_version: str | None = None,
    adapter_contract_id: str | None = None,
    adapter_fixture_status: str | None = None,
    expected_agent: str | None = None,
) -> dict:
    nested = sorted(nested_child_thread_ids or [])
    return {
        "schema": SCHEMA,
        "case_id": CASE_ID,
        "producer_status": producer_status,
        "coordinator_thread_id": coordinator_thread_id,
        "root_to_paper_analysis": root_to_paper_analysis,
        "paper_analysis_direct_child_count": len(nested),
        "nested_child_thread_ids": nested,
        "reasons": list(reasons),
        "provenance": {
            "eval_version": eval_version,
            "adapter_contract_id": adapter_contract_id,
            "adapter_fixture_status": adapter_fixture_status,
            "expected_agent": expected_agent,
        },
    }


def verify_topology(
    eval_response: dict,
    adapter: dict,
    *,
    expected_agent: str = "paper-analysis",
    expected_contract_id: str = PINNED_ADAPTER_CONTRACT_ID,
) -> dict:
    """Evaluate structured evidence and return the producer verdict dict."""

    def done(status: str, reasons: list[str], **kwargs) -> dict:
        return _verdict(status, reasons, expected_agent=expected_agent, **kwargs)

    def invalid(*reasons: str, **kwargs) -> dict:
        return done(STATUS_INVALID_EVIDENCE, list(reasons), **kwargs)

    def blocked(*reasons: str, **kwargs) -> dict:
        return done(STATUS_BLOCKED, list(reasons), **kwargs)

    if not isinstance(eval_response, dict):
        return invalid("eval response must be a JSON object")
    if not isinstance(adapter, dict):
        return invalid("adapter output must be a JSON object")

    # --- adapter surface: pinned contract, known status, expected shapes ---
    if adapter.get("schema") != SCHEMA or adapter.get("role") != ADAPTER_ROLE:
        return invalid(
            "adapter output does not match the pinned adapter surface "
            f"(schema={adapter.get('schema')!r}, role={adapter.get('role')!r})"
        )
    contract_id = adapter.get("adapter_contract_id")
    if contract_id != expected_contract_id:
        return invalid(
            "adapter_contract_id "
            f"{contract_id!r} does not match the pinned {expected_contract_id!r}"
        )
    fixture_status = adapter.get("fixture_status")
    if fixture_status not in ADAPTER_FIXTURE_STATUSES:
        return invalid(f"unknown adapter fixture_status {fixture_status!r}")
    problems = adapter.get("problems")
    if not isinstance(problems, list):
        return invalid("adapter problems must be a list")
    adapter_problems = json.dumps(problems, ensure_ascii=False, sort_keys=True)
    dispatch = adapter.get("dispatch")
    if not isinstance(dispatch, dict) or not isinstance(
        dispatch.get("thread_relations"), list
    ):
        return invalid("adapter dispatch.thread_relations must be a list")
    if fixture_status == STATUS_INVALID_EVIDENCE:
        return invalid(
            "shared adapter reported INVALID_EVIDENCE: " + adapter_problems
        )
    if fixture_status == "BLOCKED_DEPENDENCY":
        return blocked(
            "shared adapter reported BLOCKED_DEPENDENCY: " + adapter_problems
        )

    # --- eval response common evidence gate ---
    version = eval_response.get("version")
    if version is None or (
        isinstance(version, str) and not version.strip()
    ):
        return blocked(
            "eval response records no usable runtime version; the run "
            "environment cannot be provenanced (version stays provenance "
            "only and is never a string gate)"
        )
    if not isinstance(version, str):
        return invalid(
            f"eval response version must be a string or null, got {type(version).__name__}"
        )
    passed = eval_response.get("passed", None)
    if passed is None or not isinstance(passed, bool):
        return invalid(
            "eval response top-level passed must be a boolean; without it the "
            "harness outcome is not machine-readable"
        )
    if passed is False:
        return blocked("eval harness reported passed=false; the run is a harness failure")
    output = eval_response.get("output")
    root_thread_id = output.get("thread_id") if isinstance(output, dict) else None
    if not isinstance(root_thread_id, str) or not root_thread_id:
        return invalid("eval response output.thread_id must be a non-empty string")
    if fixture_status == "HARNESS_DISPATCH_MISMATCH":
        return blocked(
            "shared adapter reported HARNESS_DISPATCH_MISMATCH: this run's "
            "formal spawn was routed to a different persisted role, so the "
            "exact coordinator dispatch is not machine-confirmed: "
            + adapter_problems
        )

    # --- exact coordinator identity (machine-confirmed persisted role) ---
    reads = adapter.get("child_thread_reads")
    if not isinstance(reads, dict) or not isinstance(reads.get("entries"), list):
        return blocked(
            "adapter output carries no child_thread_reads identity surface; "
            "the exact coordinator identity cannot be machine-confirmed"
        )
    candidates: dict[str, list[dict]] = {}
    for entry in reads["entries"]:
        if not isinstance(entry, dict):
            return invalid("child_thread_reads entry must be an object")
        if (
            entry.get("identity_eligible") is True
            and entry.get("effective_role") == expected_agent
        ):
            thread_id = entry.get("thread_id")
            if not isinstance(thread_id, str) or not thread_id:
                return invalid(
                    "identity-eligible candidate entry has no usable thread_id"
                )
            candidates.setdefault(thread_id, []).append(entry)
    if not candidates:
        return blocked(
            f"no identity-eligible child thread carries persisted role "
            f"{expected_agent!r}; the exact coordinator identity cannot be "
            "machine-confirmed"
        )
    if len(candidates) > 1:
        return invalid(
            "ambiguous exact coordinator identity: thread ids "
            f"{sorted(candidates)} all carry persisted role {expected_agent!r}"
        )
    coordinator_thread_id, coordinator_entries = next(iter(candidates.items()))
    root_to_paper_analysis = (
        coordinator_entries[0].get("parent_thread_id") == root_thread_id
    )
    if not root_to_paper_analysis:
        return blocked(
            f"thread {coordinator_thread_id!r} carries persisted role "
            f"{expected_agent!r} but its read attribution names parent "
            f"{coordinator_entries[0].get('parent_thread_id')!r}, not the eval "
            f"root thread {root_thread_id!r}; the exact coordinator dispatch "
            "is not machine-confirmed",
            coordinator_thread_id=coordinator_thread_id,
            eval_version=version,
            adapter_contract_id=contract_id,
            adapter_fixture_status=fixture_status,
        )

    # --- formal spawn relations: deduplicated concrete child threads ---
    child_senders: dict[str, set[str]] = {}
    for relation in dispatch["thread_relations"]:
        if not isinstance(relation, dict):
            return invalid("thread relation must be an object")
        if relation.get("tool") != FORMAL_SPAWN_TOOL:
            continue
        sender = relation.get("sender_thread_id")
        receivers = relation.get("receiver_thread_ids")
        if not isinstance(sender, str) or not sender:
            return invalid(
                "formal spawnAgent relation has no non-empty sender_thread_id"
            )
        if not isinstance(receivers, list) or not all(
            isinstance(receiver, str) and receiver for receiver in receivers
        ):
            return invalid(
                "formal spawnAgent relation has malformed receiver_thread_ids"
            )
        if not receivers:
            return invalid(
                "formal spawnAgent relation has empty receiver_thread_ids; a "
                "completed formal spawn without concrete children is corrupted "
                "evidence under the pinned adapter contract"
            )
        for receiver in receivers:
            child_senders.setdefault(receiver, set()).add(sender)
            if receiver == root_thread_id:
                return invalid(
                    f"root thread {root_thread_id!r} appears as a formal spawn "
                    "receiver; the eval root can never be a child thread"
                )
    conflicted = sorted(
        receiver
        for receiver, senders in child_senders.items()
        if len(senders) > 1
    )
    if conflicted:
        return invalid(
            "conflicting formal spawn ownership: child thread(s) "
            f"{conflicted} are claimed by formal spawnAgent relations with "
            "different sender_thread_id values"
        )
    nested = sorted(
        receiver
        for receiver, senders in child_senders.items()
        if coordinator_thread_id in senders
    )

    # --- delegation dimension consistency (defense in depth) ---
    delegation = adapter.get("delegation")
    if not isinstance(delegation, dict) or delegation.get("state") not in (
        DELEGATION_STATES
    ):
        return invalid(
            "adapter delegation dimension must be an object with state "
            f"confirmed|unobservable, got {delegation!r}"
        )
    delegation_children = delegation.get("child_thread_ids")
    if delegation.get("state") == "confirmed":
        if (
            not isinstance(delegation_children, list)
            or not delegation_children
            or not set(delegation_children) <= set(child_senders)
        ):
            return invalid(
                "delegation=confirmed without concrete child_thread_ids "
                "covered by formal spawnAgent relations contradicts the "
                "pinned adapter contract"
            )
    elif nested:
        return invalid(
            "adapter delegation=unobservable contradicts formal spawnAgent "
            f"relations naming children {nested}"
        )

    # --- cross-check nested children against read parent attribution ---
    for entry in reads["entries"]:
        if not isinstance(entry, dict):
            continue
        thread_id = entry.get("thread_id")
        if thread_id in nested and entry.get("parent_thread_id") != (
            coordinator_thread_id
        ):
            return invalid(
                "parent ownership conflict: thread "
                f"{thread_id!r} is a formal spawnAgent receiver of coordinator "
                f"{coordinator_thread_id!r} but its read attribution names "
                f"parent {entry.get('parent_thread_id')!r}",
                coordinator_thread_id=coordinator_thread_id,
                root_to_paper_analysis=True,
                nested_child_thread_ids=nested,
                eval_version=version,
                adapter_contract_id=contract_id,
                adapter_fixture_status=fixture_status,
            )

    if nested:
        return done(
            STATUS_PASS,
            [],
            coordinator_thread_id=coordinator_thread_id,
            root_to_paper_analysis=True,
            nested_child_thread_ids=nested,
            eval_version=version,
            adapter_contract_id=contract_id,
            adapter_fixture_status=fixture_status,
        )
    return done(
        STATUS_FAIL_PRODUCER,
        [
            "healthy machine evidence with a machine-confirmed exact "
            f"{expected_agent!r} coordinator ({coordinator_thread_id!r}), but "
            "the coordinator produced no formal direct nested analysis child; "
            "full-mode Step 3 was not delegated"
        ],
        coordinator_thread_id=coordinator_thread_id,
        root_to_paper_analysis=True,
        eval_version=version,
        adapter_contract_id=contract_id,
        adapter_fixture_status=fixture_status,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Producer topology verdict for PA-CODEX-FULL-LEAF-01 from "
            "structured /eval + shared adapter evidence (never runs Codex)."
        )
    )
    parser.add_argument(
        "--eval-response", required=True, help="raw /eval response JSON"
    )
    parser.add_argument(
        "--adapter",
        required=True,
        help="adapter output JSON from skills-test-fixtures "
        "parse_codex_eval_evidence.py",
    )
    parser.add_argument("--output", required=True, help="verdict JSON output path")
    parser.add_argument(
        "--expected-agent",
        default="paper-analysis",
        help="exact coordinator agent name (default: paper-analysis)",
    )
    parser.add_argument(
        "--expected-contract-id",
        default=PINNED_ADAPTER_CONTRACT_ID,
        help="pinned shared adapter contract id",
    )
    args = parser.parse_args(argv)

    try:
        with open(args.eval_response, encoding="utf-8") as handle:
            eval_response = json.load(handle)
        with open(args.adapter, encoding="utf-8") as handle:
            adapter = json.load(handle)
    except (OSError, json.JSONDecodeError) as error:
        verdict = _verdict(
            STATUS_INVALID_EVIDENCE,
            [f"cannot read eval response or adapter JSON: {error}"],
            expected_agent=args.expected_agent,
        )
    else:
        verdict = verify_topology(
            eval_response,
            adapter,
            expected_agent=args.expected_agent,
            expected_contract_id=args.expected_contract_id,
        )

    payload = json.dumps(verdict, ensure_ascii=False, indent=2) + "\n"
    output = pathlib.Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(payload, encoding="utf-8")
    print(payload, end="")
    print(f"producer_status: {verdict['producer_status']}", file=sys.stderr)
    return EXIT_CODES[verdict["producer_status"]]


if __name__ == "__main__":
    sys.exit(main())
