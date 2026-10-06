#!/usr/bin/env python3
from __future__ import annotations

import grp
import hashlib
import json
import os
import pwd
import shutil
import socket
import socketserver
import sqlite3
import struct
import uuid
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(os.environ.get(
    "PLAYABLE_OPERATOR_DB",
    "/var/lib/playable-universe/attestation-intake.sqlite3",
))
SOCKET_PATH = Path(os.environ.get(
    "PLAYABLE_OPERATOR_SOCKET",
    "/run/playable-universe/operator.sock",
))
POLICY_PATH = Path(os.environ.get(
    "PLAYABLE_OPERATOR_POLICY",
    "/etc/playable-universe/operator-policy.json",
))
INTERLOCK_PATH = Path(os.environ.get(
    "PLAYABLE_OPERATOR_INTERLOCK",
    "/etc/playable-universe/operator-interlock.json",
))
MEDIA_ROOT = Path(os.environ.get(
    "PLAYABLE_MEDIA_ROOT",
    "/var/lib/playable-universe/media",
))
SOCKET_GROUP = os.environ.get("PLAYABLE_OPERATOR_GROUP", "playable-ops")

MAX_REQUEST_BYTES = 64 * 1024
MAX_NOTE = 4000
MAX_SOURCE_REFS = 20


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH), timeout=8)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_operator_schema() -> None:
    with db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS operator_receipts (
                receipt_id TEXT PRIMARY KEY,
                request_id TEXT NOT NULL,
                recorded_at TEXT NOT NULL,
                actor_uid INTEGER NOT NULL,
                actor_user TEXT NOT NULL,
                actor_role TEXT NOT NULL,
                policy_version TEXT NOT NULL,
                interlock_state TEXT NOT NULL,
                operation TEXT NOT NULL,
                target TEXT,
                request_sha256 TEXT NOT NULL,
                decision TEXT NOT NULL,
                result_json TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_operator_receipts_time "
            "ON operator_receipts(recorded_at DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_operator_receipts_actor "
            "ON operator_receipts(actor_user, recorded_at DESC)"
        )


def load_json_file(path: Path) -> dict:
    raw = path.read_bytes()
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise RuntimeError(f"{path} must contain an object")
    return value


def load_policy() -> dict:
    policy = load_json_file(POLICY_PATH)
    if policy.get("schema") != "playable.operator-policy.v0":
        raise RuntimeError("unsupported operator policy schema")
    if not isinstance(policy.get("version"), str) or not policy["version"]:
        raise RuntimeError("operator policy version missing")
    if not isinstance(policy.get("principals"), dict):
        raise RuntimeError("operator policy principals missing")
    if not isinstance(policy.get("roles"), dict):
        raise RuntimeError("operator policy roles missing")
    return policy


def load_interlock() -> dict:
    state = load_json_file(INTERLOCK_PATH)
    if state.get("schema") != "playable.operator-interlock.v0":
        raise RuntimeError("unsupported interlock schema")
    if state.get("state") not in {"NORMAL", "CONSTRAINED"}:
        raise RuntimeError("invalid interlock state")
    return state


def peer_identity(sock: socket.socket) -> dict:
    raw = sock.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize("3i"))
    pid, uid, gid = struct.unpack("3i", raw)
    try:
        user = pwd.getpwuid(uid).pw_name
    except KeyError:
        user = f"uid:{uid}"
    return {"pid": pid, "uid": uid, "gid": gid, "user": user}


def clean_note(value, *, required=True) -> str | None:
    if value is None:
        if required:
            raise ValueError("note is required")
        return None
    if not isinstance(value, str):
        raise ValueError("note must be a string")
    value = value.strip()
    if required and not value:
        raise ValueError("note is required")
    if len(value) > MAX_NOTE:
        raise ValueError(f"note exceeds {MAX_NOTE} characters")
    return value


def clean_source_refs(value) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or len(value) > MAX_SOURCE_REFS:
        raise ValueError(f"source_refs must be an array of at most {MAX_SOURCE_REFS}")
    refs = []
    for item in value:
        if not isinstance(item, str):
            raise ValueError("source_refs items must be strings")
        item = item.strip()
        if not item or len(item) > 600:
            raise ValueError("invalid source_ref")
        refs.append(item)
    return refs


def append_candidate_event(
    conn: sqlite3.Connection,
    candidate_id: str,
    event_type: str,
    actor_kind: str,
    payload: dict,
) -> dict:
    event = {
        "event_id": "cevent:" + str(uuid.uuid4()),
        "candidate_id": candidate_id,
        "event_type": event_type,
        "recorded_at": utcnow(),
        "actor_kind": actor_kind,
        "payload": payload,
    }
    conn.execute(
        "INSERT INTO candidate_events "
        "(event_id,candidate_id,event_type,recorded_at,actor_kind,payload_json) "
        "VALUES (?,?,?,?,?,?)",
        (
            event["event_id"],
            candidate_id,
            event_type,
            event["recorded_at"],
            actor_kind,
            canonical_bytes(payload).decode("utf-8"),
        ),
    )
    return event


def candidate_row(conn: sqlite3.Connection, candidate_id: str) -> sqlite3.Row:
    row = conn.execute(
        "SELECT candidate_id,received_at,status,visibility,packet_json,"
        "packet_sha256,receipt_sha256 "
        "FROM candidates WHERE candidate_id=?",
        (candidate_id,),
    ).fetchone()
    if not row:
        raise ValueError("candidate_not_found")
    return row


def candidate_lifecycle(conn: sqlite3.Connection, candidate_id: str) -> list[dict]:
    rows = conn.execute(
        "SELECT event_id,event_type,recorded_at,actor_kind,payload_json "
        "FROM candidate_events WHERE candidate_id=? "
        "ORDER BY recorded_at,event_id",
        (candidate_id,),
    ).fetchall()
    return [
        {
            "event_id": row["event_id"],
            "event_type": row["event_type"],
            "recorded_at": row["recorded_at"],
            "actor_kind": row["actor_kind"],
            "payload": json.loads(row["payload_json"]),
        }
        for row in rows
    ]


def candidate_private_media(conn: sqlite3.Connection, candidate_id: str) -> list[dict]:
    rows = conn.execute(
        "SELECT private_media_id,source_sha256,created_at,content_type,bytes "
        "FROM private_media WHERE candidate_id=? ORDER BY created_at",
        (candidate_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def candidate_public_media(conn: sqlite3.Connection, candidate_id: str) -> list[dict]:
    rows = conn.execute(
        "SELECT media_id,source_sha256,derivative_sha256,created_at,reviewed_at,"
        "status,content_type,bytes "
        "FROM media WHERE candidate_id=? ORDER BY created_at",
        (candidate_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def inspect_candidate(candidate_id: str) -> dict:
    with db() as conn:
        row = candidate_row(conn, candidate_id)
        packet = json.loads(row["packet_json"])
        return {
            "candidate_id": candidate_id,
            "received_at": row["received_at"],
            "status": row["status"],
            "visibility": row["visibility"],
            "packet_sha256": row["packet_sha256"],
            "receipt_sha256": row["receipt_sha256"],
            "packet": packet,
            "lifecycle": candidate_lifecycle(conn, candidate_id),
            "private_media": candidate_private_media(conn, candidate_id),
            "public_media": candidate_public_media(conn, candidate_id),
        }


def operation_status(ctx: dict, target: str | None, payload: dict) -> dict:
    return {
        "service": "playable-operator-plane",
        "status": "ok",
        "actor": {
            "user": ctx["identity"]["user"],
            "uid": ctx["identity"]["uid"],
            "role": ctx["role"],
        },
        "policy_version": ctx["policy"]["version"],
        "interlock": ctx["interlock"],
        "allowed_operations": ctx["allowed_operations"],
    }


def operation_receipts(ctx: dict, target: str | None, payload: dict) -> dict:
    limit = payload.get("limit", 20)
    if not isinstance(limit, int) or limit < 1 or limit > 100:
        raise ValueError("limit must be 1..100")
    with db() as conn:
        rows = conn.execute(
            "SELECT receipt_id,request_id,recorded_at,actor_uid,actor_user,"
            "actor_role,policy_version,interlock_state,operation,target,"
            "request_sha256,decision,result_json "
            "FROM operator_receipts ORDER BY recorded_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return {
        "items": [
            {
                **{k: row[k] for k in row.keys() if k != "result_json"},
                "result": json.loads(row["result_json"]),
            }
            for row in rows
        ]
    }


def operation_candidate_inspect(ctx: dict, target: str | None, payload: dict) -> dict:
    if not target or not target.startswith("attest:"):
        raise ValueError("target must be an attestation candidate id")
    return inspect_candidate(target)


def operation_report_unavailable(ctx: dict, target: str | None, payload: dict) -> dict:
    if not target or not target.startswith("attest:"):
        raise ValueError("target must be an attestation candidate id")
    source_sha256 = payload.get("source_sha256")
    if not isinstance(source_sha256, str) or len(source_sha256) != 64:
        raise ValueError("source_sha256 is required")
    source_sha256 = source_sha256.lower()
    note = clean_note(payload.get("note"))

    with db() as conn:
        row = candidate_row(conn, target)
        packet = json.loads(row["packet_json"])
        bound = {
            item.get("sha256")
            for item in packet.get("evidence", [])
            if item.get("kind") == "photo_hash"
        }
        if source_sha256 not in bound:
            raise ValueError("source_digest_not_bound_to_candidate")

        prior = conn.execute(
            "SELECT event_id,recorded_at,payload_json "
            "FROM candidate_events "
            "WHERE candidate_id=? "
            "AND event_type='evidence.source_unavailable_reported' "
            "AND json_extract(payload_json,'$.source_sha256')=? "
            "ORDER BY recorded_at LIMIT 1",
            (target, source_sha256),
        ).fetchone()
        if prior:
            return {
                "state": "already-recorded",
                "event_id": prior["event_id"],
                "recorded_at": prior["recorded_at"],
                "payload": json.loads(prior["payload_json"]),
            }

        event = append_candidate_event(
            conn,
            target,
            "evidence.source_unavailable_reported",
            "playable-" + ctx["role"],
            {
                "source_sha256": source_sha256,
                "note": note,
                "operator_actor": ctx["identity"]["user"],
                "operator_role": ctx["role"],
                "policy_version": ctx["policy"]["version"],
            },
        )
    return {"state": "recorded", "event": event}


def operation_corroborate(ctx: dict, target: str | None, payload: dict) -> dict:
    if not target or not target.startswith("attest:"):
        raise ValueError("target must be an attestation candidate id")
    note = clean_note(payload.get("note"))
    refs = clean_source_refs(payload.get("source_refs"))
    if not refs:
        raise ValueError("corroboration requires at least one source_ref")

    with db() as conn:
        candidate_row(conn, target)
        event = append_candidate_event(
            conn,
            target,
            "candidate.corroboration_recorded",
            "playable-" + ctx["role"],
            {
                "note": note,
                "source_refs": refs,
                "operator_actor": ctx["identity"]["user"],
                "operator_role": ctx["role"],
                "policy_version": ctx["policy"]["version"],
            },
        )
    return {"state": "recorded", "event": event}


def operation_dispute(ctx: dict, target: str | None, payload: dict) -> dict:
    if not target or not target.startswith("attest:"):
        raise ValueError("target must be an attestation candidate id")
    note = clean_note(payload.get("note"))
    refs = clean_source_refs(payload.get("source_refs"))

    with db() as conn:
        candidate_row(conn, target)
        event = append_candidate_event(
            conn,
            target,
            "candidate.dispute_recorded",
            "playable-" + ctx["role"],
            {
                "note": note,
                "source_refs": refs,
                "operator_actor": ctx["identity"]["user"],
                "operator_role": ctx["role"],
                "policy_version": ctx["policy"]["version"],
            },
        )
    return {"state": "recorded", "event": event}


def operation_propose_cap(ctx: dict, target: str | None, payload: dict) -> dict:
    if not target or not target.startswith("attest:"):
        raise ValueError("target must be an attestation candidate id")
    note = clean_note(payload.get("note"))
    refs = clean_source_refs(payload.get("source_refs"))

    with db() as conn:
        candidate_row(conn, target)
        event = append_candidate_event(
            conn,
            target,
            "promotion.cap_proposed",
            "playable-" + ctx["role"],
            {
                "note": note,
                "source_refs": refs,
                "operator_actor": ctx["identity"]["user"],
                "operator_role": ctx["role"],
                "policy_version": ctx["policy"]["version"],
                "effect": "proposal-only",
            },
        )
    return {
        "state": "proposal-recorded",
        "event": event,
        "cap_mutated": False,
    }


def _media_row(conn: sqlite3.Connection, media_id: str) -> sqlite3.Row:
    row = conn.execute(
        "SELECT media_id,candidate_id,source_sha256,derivative_sha256,"
        "created_at,reviewed_at,status,content_type,bytes,path "
        "FROM media WHERE media_id=?",
        (media_id,),
    ).fetchone()
    if not row:
        raise ValueError("media_not_found")
    return row


def operation_media_approve(ctx: dict, target: str | None, payload: dict) -> dict:
    if not target or not target.startswith("media:"):
        raise ValueError("target must be a media id")
    expected = payload.get("expected_derivative_sha256")
    note = clean_note(payload.get("note"))
    if not isinstance(expected, str) or len(expected) != 64:
        raise ValueError("expected_derivative_sha256 is required")

    approved_dir = MEDIA_ROOT / "approved"
    approved_dir.mkdir(parents=True, exist_ok=True)

    with db() as conn:
        row = _media_row(conn, target)
        if row["derivative_sha256"] != expected.lower():
            raise ValueError("derivative_digest_mismatch")
        if row["status"] == "approved":
            return {
                "state": "already-approved",
                "media_id": target,
                "candidate_id": row["candidate_id"],
            }
        if row["status"] != "pending":
            raise ValueError("media_not_pending")
        src = Path(row["path"])
        if not src.is_file():
            raise ValueError("media_file_missing")
        dst = approved_dir / (target.split(":", 1)[1] + ".jpg")
        shutil.move(str(src), str(dst))
        reviewed = utcnow()
        conn.execute(
            "UPDATE media SET status='approved',reviewed_at=?,path=? "
            "WHERE media_id=?",
            (reviewed, str(dst), target),
        )
        event = append_candidate_event(
            conn,
            row["candidate_id"],
            "evidence.public_derivative_approved",
            "playable-operator",
            {
                "media_id": target,
                "source_sha256": row["source_sha256"],
                "derivative_sha256": row["derivative_sha256"],
                "reviewed_at": reviewed,
                "note": note,
                "operator_actor": ctx["identity"]["user"],
                "operator_role": ctx["role"],
                "policy_version": ctx["policy"]["version"],
            },
        )
    return {
        "state": "approved",
        "media_id": target,
        "candidate_id": row["candidate_id"],
        "event": event,
    }


def operation_media_reject(ctx: dict, target: str | None, payload: dict) -> dict:
    if not target or not target.startswith("media:"):
        raise ValueError("target must be a media id")
    expected = payload.get("expected_derivative_sha256")
    note = clean_note(payload.get("note"))
    if not isinstance(expected, str) or len(expected) != 64:
        raise ValueError("expected_derivative_sha256 is required")

    with db() as conn:
        row = _media_row(conn, target)
        if row["derivative_sha256"] != expected.lower():
            raise ValueError("derivative_digest_mismatch")
        if row["status"] == "rejected":
            return {
                "state": "already-rejected",
                "media_id": target,
                "candidate_id": row["candidate_id"],
            }
        if row["status"] == "approved":
            raise ValueError("approved_media_requires_withdrawal_flow")
        if row["status"] != "pending":
            raise ValueError("media_not_pending")
        path = Path(row["path"])
        if path.is_file():
            path.unlink()
        reviewed = utcnow()
        conn.execute(
            "UPDATE media SET status='rejected',reviewed_at=? WHERE media_id=?",
            (reviewed, target),
        )
        event = append_candidate_event(
            conn,
            row["candidate_id"],
            "evidence.public_derivative_rejected",
            "playable-operator",
            {
                "media_id": target,
                "source_sha256": row["source_sha256"],
                "derivative_sha256": row["derivative_sha256"],
                "reviewed_at": reviewed,
                "note": note,
                "operator_actor": ctx["identity"]["user"],
                "operator_role": ctx["role"],
                "policy_version": ctx["policy"]["version"],
            },
        )
    return {
        "state": "rejected",
        "media_id": target,
        "candidate_id": row["candidate_id"],
        "event": event,
    }


OPERATIONS = {
    "operator.status": operation_status,
    "operator.receipts": operation_receipts,
    "interlock.inspect": operation_status,
    "candidate.inspect": operation_candidate_inspect,
    "evidence.report_unavailable": operation_report_unavailable,
    "candidate.corroborate": operation_corroborate,
    "candidate.dispute": operation_dispute,
    "promotion.propose_cap": operation_propose_cap,
    "media.review.approve": operation_media_approve,
    "media.review.reject": operation_media_reject,
}


def resolve_context(identity: dict, policy: dict, interlock: dict) -> dict:
    principal = policy["principals"].get(identity["user"])
    if not isinstance(principal, dict):
        role = "none"
        allowed = []
    else:
        role = principal.get("role", "none")
        role_def = policy["roles"].get(role, {})
        allowed = role_def.get("allow", [])
        if not isinstance(allowed, list):
            allowed = []

    if interlock["state"] == "CONSTRAINED":
        constrained = policy.get("constrained_allow", [])
        allowed = [op for op in allowed if op in constrained]

    return {
        "identity": identity,
        "policy": policy,
        "interlock": interlock,
        "role": role,
        "allowed_operations": sorted(set(allowed)),
    }


def receipt_projection(request: dict, result: dict) -> dict:
    operation = request["operation"]
    if operation == "candidate.inspect":
        return {
            "candidate_id": result.get("candidate_id"),
            "status": result.get("status"),
            "visibility": result.get("visibility"),
            "lifecycle_count": len(result.get("lifecycle", [])),
            "private_media_count": len(result.get("private_media", [])),
            "public_media_count": len(result.get("public_media", [])),
        }
    if operation == "operator.receipts":
        return {"item_count": len(result.get("items", []))}
    if operation in {"operator.status", "interlock.inspect"}:
        return {
            "status": result.get("status"),
            "actor_role": result.get("actor", {}).get("role"),
            "policy_version": result.get("policy_version"),
            "interlock_state": result.get("interlock", {}).get("state"),
            "allowed_operation_count": len(result.get("allowed_operations", [])),
        }
    event = result.get("event") if isinstance(result, dict) else None
    projected = {
        "state": result.get("state") if isinstance(result, dict) else None,
    }
    for key in ("media_id", "candidate_id", "cap_mutated"):
        if isinstance(result, dict) and key in result:
            projected[key] = result[key]
    if isinstance(event, dict):
        projected["event_id"] = event.get("event_id")
        projected["event_type"] = event.get("event_type")
        projected["recorded_at"] = event.get("recorded_at")
    if isinstance(result, dict) and result.get("event_id"):
        projected["event_id"] = result.get("event_id")
    return projected


def record_receipt(
    ctx: dict,
    request: dict,
    request_sha: str,
    decision: str,
    result: dict,
) -> dict:
    projected_result = receipt_projection(request, result)
    receipt = {
        "schema": "playable.operator-receipt.v0",
        "receipt_id": "opreceipt:" + str(uuid.uuid4()),
        "request_id": request["request_id"],
        "recorded_at": utcnow(),
        "actor_uid": ctx["identity"]["uid"],
        "actor_user": ctx["identity"]["user"],
        "actor_role": ctx["role"],
        "policy_version": ctx["policy"]["version"],
        "interlock_state": ctx["interlock"]["state"],
        "operation": request["operation"],
        "target": request.get("target"),
        "request_sha256": request_sha,
        "decision": decision,
        "result": projected_result,
    }
    with db() as conn:
        conn.execute(
            "INSERT INTO operator_receipts "
            "(receipt_id,request_id,recorded_at,actor_uid,actor_user,actor_role,"
            "policy_version,interlock_state,operation,target,request_sha256,"
            "decision,result_json) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                receipt["receipt_id"],
                receipt["request_id"],
                receipt["recorded_at"],
                receipt["actor_uid"],
                receipt["actor_user"],
                receipt["actor_role"],
                receipt["policy_version"],
                receipt["interlock_state"],
                receipt["operation"],
                receipt["target"],
                receipt["request_sha256"],
                receipt["decision"],
                canonical_bytes(projected_result).decode("utf-8"),
            ),
        )
    return receipt


def normalize_request(value: object) -> dict:
    if not isinstance(value, dict):
        raise ValueError("request must be an object")
    if value.get("schema") != "playable.operator-request.v0":
        raise ValueError("unsupported request schema")
    request_id = value.get("request_id")
    if not isinstance(request_id, str) or not request_id.strip():
        raise ValueError("request_id is required")
    operation = value.get("operation")
    if not isinstance(operation, str) or operation not in OPERATIONS:
        raise ValueError("unknown operation")
    target = value.get("target")
    if target is not None and (not isinstance(target, str) or len(target) > 300):
        raise ValueError("invalid target")
    payload = value.get("payload", {})
    if not isinstance(payload, dict):
        raise ValueError("payload must be an object")
    return {
        "schema": "playable.operator-request.v0",
        "request_id": request_id.strip()[:160],
        "operation": operation,
        "target": target,
        "payload": payload,
    }


def handle_request(identity: dict, raw_request: object) -> dict:
    policy = load_policy()
    interlock = load_interlock()

    try:
        request = normalize_request(raw_request)
    except ValueError as exc:
        return {
            "schema": "playable.operator-response.v0",
            "ok": False,
            "error": "invalid_request",
            "detail": str(exc),
        }

    request_sha = sha256_hex(canonical_bytes(request))
    ctx = resolve_context(identity, policy, interlock)

    if request["operation"] not in ctx["allowed_operations"]:
        result = {
            "error": "operation_not_admitted",
            "allowed_operations": ctx["allowed_operations"],
        }
        receipt = record_receipt(
            ctx, request, request_sha, "refused", result
        )
        return {
            "schema": "playable.operator-response.v0",
            "ok": False,
            "error": "operation_not_admitted",
            "receipt": receipt,
        }

    try:
        result = OPERATIONS[request["operation"]](
            ctx, request.get("target"), request["payload"]
        )
        receipt = record_receipt(
            ctx, request, request_sha, "admitted", result
        )
        return {
            "schema": "playable.operator-response.v0",
            "ok": True,
            "result": result,
            "receipt": receipt,
        }
    except ValueError as exc:
        result = {"error": str(exc)}
        receipt = record_receipt(
            ctx, request, request_sha, "refused", result
        )
        return {
            "schema": "playable.operator-response.v0",
            "ok": False,
            "error": str(exc),
            "receipt": receipt,
        }
    except Exception as exc:
        result = {
            "error": "operator_internal_error",
            "detail": type(exc).__name__,
        }
        try:
            receipt = record_receipt(
                ctx, request, request_sha, "error", result
            )
        except Exception:
            receipt = None
        return {
            "schema": "playable.operator-response.v0",
            "ok": False,
            "error": "operator_internal_error",
            "receipt": receipt,
        }


class UnixServer(socketserver.ThreadingUnixStreamServer):
    daemon_threads = True
    allow_reuse_address = False


class Handler(socketserver.StreamRequestHandler):
    def handle(self):
        identity = peer_identity(self.connection)
        line = self.rfile.readline(MAX_REQUEST_BYTES + 1)
        if not line:
            return
        if len(line) > MAX_REQUEST_BYTES:
            response = {
                "schema": "playable.operator-response.v0",
                "ok": False,
                "error": "request_too_large",
            }
        else:
            try:
                request = json.loads(line.decode("utf-8"))
            except Exception:
                response = {
                    "schema": "playable.operator-response.v0",
                    "ok": False,
                    "error": "invalid_json",
                }
            else:
                response = handle_request(identity, request)
        self.wfile.write(canonical_bytes(response) + b"\n")
        self.wfile.flush()


def main():
    init_operator_schema()
    policy = load_policy()
    load_interlock()

    SOCKET_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        SOCKET_PATH.unlink()
    except FileNotFoundError:
        pass

    gid = grp.getgrnam(SOCKET_GROUP).gr_gid
    os.chown(SOCKET_PATH.parent, -1, gid)
    os.chmod(SOCKET_PATH.parent, 0o750)

    server = UnixServer(str(SOCKET_PATH), Handler)
    os.chown(SOCKET_PATH, -1, gid)
    os.chmod(SOCKET_PATH, 0o660)

    print(json.dumps({
        "service": "playable-operator-plane",
        "status": "listening",
        "socket": str(SOCKET_PATH),
        "socket_group": SOCKET_GROUP,
        "policy_version": policy["version"],
    }), flush=True)

    try:
        server.serve_forever()
    finally:
        server.server_close()
        try:
            SOCKET_PATH.unlink()
        except FileNotFoundError:
            pass


if __name__ == "__main__":
    main()
