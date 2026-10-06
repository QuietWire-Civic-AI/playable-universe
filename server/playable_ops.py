#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import socket
import sys
import uuid

SOCKET_PATH = os.environ.get(
    "PLAYABLE_OPERATOR_SOCKET",
    "/run/playable-universe/operator.sock",
)


def call(operation, target=None, payload=None):
    request = {
        "schema": "playable.operator-request.v0",
        "request_id": "opreq:" + str(uuid.uuid4()),
        "operation": operation,
        "target": target,
        "payload": payload or {},
    }
    raw = (
        json.dumps(
            request,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        + "\n"
    ).encode("utf-8")

    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.settimeout(12)
    try:
        sock.connect(SOCKET_PATH)
        sock.sendall(raw)
        chunks = []
        while True:
            part = sock.recv(65536)
            if not part:
                break
            chunks.append(part)
            if b"\n" in part:
                break
    finally:
        sock.close()

    response = json.loads(b"".join(chunks).split(b"\n", 1)[0])
    print(json.dumps(response, indent=2, sort_keys=True))
    return 0 if response.get("ok") else 2


def main():
    parser = argparse.ArgumentParser(
        prog="playable-ops",
        description="Bounded local client for the Playable Universe operator plane.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status")
    rec = sub.add_parser("receipts")
    rec.add_argument("--limit", type=int, default=20)

    ins = sub.add_parser("inspect")
    ins.add_argument("candidate_id")

    un = sub.add_parser("report-unavailable")
    un.add_argument("candidate_id")
    un.add_argument("source_sha256")
    un.add_argument("--note", required=True)

    co = sub.add_parser("corroborate")
    co.add_argument("candidate_id")
    co.add_argument("--note", required=True)
    co.add_argument("--source-ref", action="append", default=[])

    di = sub.add_parser("dispute")
    di.add_argument("candidate_id")
    di.add_argument("--note", required=True)
    di.add_argument("--source-ref", action="append", default=[])

    pr = sub.add_parser("propose-cap")
    pr.add_argument("candidate_id")
    pr.add_argument("--note", required=True)
    pr.add_argument("--source-ref", action="append", default=[])

    ap = sub.add_parser("approve-media")
    ap.add_argument("media_id")
    ap.add_argument("expected_derivative_sha256")
    ap.add_argument("--note", required=True)

    rj = sub.add_parser("reject-media")
    rj.add_argument("media_id")
    rj.add_argument("expected_derivative_sha256")
    rj.add_argument("--note", required=True)

    args = parser.parse_args()

    if args.command == "status":
        return call("operator.status")
    if args.command == "receipts":
        return call("operator.receipts", payload={"limit": args.limit})
    if args.command == "inspect":
        return call("candidate.inspect", target=args.candidate_id)
    if args.command == "report-unavailable":
        return call(
            "evidence.report_unavailable",
            target=args.candidate_id,
            payload={
                "source_sha256": args.source_sha256,
                "note": args.note,
            },
        )
    if args.command == "corroborate":
        return call(
            "candidate.corroborate",
            target=args.candidate_id,
            payload={
                "note": args.note,
                "source_refs": args.source_ref,
            },
        )
    if args.command == "dispute":
        return call(
            "candidate.dispute",
            target=args.candidate_id,
            payload={
                "note": args.note,
                "source_refs": args.source_ref,
            },
        )
    if args.command == "propose-cap":
        return call(
            "promotion.propose_cap",
            target=args.candidate_id,
            payload={
                "note": args.note,
                "source_refs": args.source_ref,
            },
        )
    if args.command == "approve-media":
        return call(
            "media.review.approve",
            target=args.media_id,
            payload={
                "expected_derivative_sha256": args.expected_derivative_sha256,
                "note": args.note,
            },
        )
    if args.command == "reject-media":
        return call(
            "media.review.reject",
            target=args.media_id,
            payload={
                "expected_derivative_sha256": args.expected_derivative_sha256,
                "note": args.note,
            },
        )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
