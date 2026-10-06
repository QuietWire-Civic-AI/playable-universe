#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

RULES = {
    "playable_operator_status": ["hands.read"],
    "playable_operator_receipts": ["hands.read"],
    "playable_candidate_inspect": ["hands.read"],
    "playable_evidence_report_unavailable": ["hands.execute"],
    "playable_candidate_corroborate": ["hands.execute"],
    "playable_candidate_dispute": ["hands.execute"],
    "playable_promotion_propose_cap": ["hands.execute"],
}


def main() -> int:
    if len(sys.argv) != 3:
        print(
            "usage: build-fc-oauth-playable-policy.py SOURCE_POLICY DEST_POLICY",
            file=sys.stderr,
        )
        return 2

    src = Path(sys.argv[1])
    dst = Path(sys.argv[2])
    policy = json.loads(src.read_text())

    if policy.get("schema") != "quiet-hands-oauth-executor-policy/v0":
        raise SystemExit("REFUSED: unsupported OAuth executor policy schema")
    if policy.get("enabled") is not True:
        raise SystemExit("REFUSED: source OAuth executor policy is not enabled")

    principals = policy.get("principals")
    if not isinstance(principals, list) or not principals:
        raise SystemExit("REFUSED: no principals in source policy")

    eligible = []
    changes = 0
    for principal in principals:
        nodes = principal.get("nodes") or []
        tools = principal.get("tools")
        if "qwos:fc" not in nodes or not isinstance(tools, dict):
            continue
        eligible.append(principal)
        for name, scopes in RULES.items():
            if tools.get(name) != scopes:
                tools[name] = scopes
                changes += 1

    if not eligible:
        raise SystemExit("REFUSED: no FC principal eligible for Playable tool admission")

    dst.write_text(json.dumps(policy, indent=2, sort_keys=False) + "\n")
    print(f"eligible_fc_principals={len(eligible)}")
    print(f"semantic_policy_rules={len(RULES)}")
    print(f"semantic_policy_changes={changes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
