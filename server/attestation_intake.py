#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import threading
import time
import uuid
from collections import defaultdict, deque
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

HOST = os.environ.get("PLAYABLE_INTAKE_HOST", "127.0.0.1")
PORT = int(os.environ.get("PLAYABLE_INTAKE_PORT", "18270"))
DB_PATH = os.environ.get(
    "PLAYABLE_INTAKE_DB",
    "/var/lib/playable-universe/attestation-intake.sqlite3",
)
MAX_BODY = 32 * 1024
RATE_LIMIT = 30
RATE_WINDOW_SECONDS = 3600

TOP_LEVEL_KEYS = {
    "schema", "client_id", "created_at", "claim", "witness",
    "assurance", "evidence", "location", "sharing", "refs", "notes",
}
WITNESS_MODES = {
    "anonymous", "self_asserted_name", "qwos_device", "institutional_identity"
}
ASSURANCE_CLASSES = {
    "browser-self-asserted", "browser-device-key",
    "qwos-device-signed", "institution-signed",
}
CLAIM_KINDS = {
    "witness_statement", "condition_statement", "event_statement",
    "place_statement", "object_statement", "other",
}
VISIBILITIES = {"receipt-only", "public-candidate"}
LOCATION_MODES = {"none", "coarse", "exact-private"}
EVIDENCE_KINDS = {
    "photo_hash", "audio_hash", "video_hash", "document_hash", "other_hash",
}
CUSTODY = {"device-local", "qwos-private", "external-reference", "not-retained"}

_rate_lock = threading.Lock()
_rate: dict[str, deque[float]] = defaultdict(deque)


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=5)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS candidates (
                candidate_id TEXT PRIMARY KEY,
                received_at TEXT NOT NULL,
                status TEXT NOT NULL,
                visibility TEXT NOT NULL,
                packet_json TEXT NOT NULL,
                packet_sha256 TEXT NOT NULL,
                receipt_sha256 TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_candidates_public "
            "ON candidates(visibility, received_at DESC)"
        )


def clean_str(value, *, max_len: int, allow_empty: bool = False):
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("expected string")
    value = value.strip()
    if not allow_empty and not value:
        raise ValueError("string must not be empty")
    if len(value) > max_len:
        raise ValueError(f"string exceeds {max_len} characters")
    return value


def finite_number(value, *, min_value: float, max_value: float):
    if value is None:
        return None
    if not isinstance(value, (int, float)):
        raise ValueError("expected number")
    value = float(value)
    if value < min_value or value > max_value:
        raise ValueError("number out of range")
    return value


def validate_packet(packet: object) -> dict:
    if not isinstance(packet, dict):
        raise ValueError("packet must be an object")
    unknown = set(packet) - TOP_LEVEL_KEYS
    if unknown:
        raise ValueError("unknown top-level fields: " + ", ".join(sorted(unknown)))
    if packet.get("schema") != "playable.mobile-attestation.v0":
        raise ValueError("unsupported schema")

    client_id = clean_str(packet.get("client_id"), max_len=128)
    if len(client_id) < 8:
        raise ValueError("client_id too short")
    created_at = clean_str(packet.get("created_at"), max_len=64)

    claim = packet.get("claim")
    if not isinstance(claim, dict):
        raise ValueError("claim must be an object")
    claim_text = clean_str(claim.get("text"), max_len=2000)
    claim_kind = claim.get("kind")
    if claim_kind not in CLAIM_KINDS:
        raise ValueError("invalid claim kind")

    witness = packet.get("witness")
    if not isinstance(witness, dict):
        raise ValueError("witness must be an object")
    witness_mode = witness.get("mode")
    if witness_mode not in WITNESS_MODES:
        raise ValueError("invalid witness mode")
    display_name = witness.get("display_name")
    if display_name is not None:
        display_name = clean_str(display_name, max_len=120)
    identity_ref = witness.get("identity_ref")
    if identity_ref is not None:
        identity_ref = clean_str(identity_ref, max_len=300)

    assurance = packet.get("assurance")
    if not isinstance(assurance, dict):
        raise ValueError("assurance must be an object")
    assurance_class = assurance.get("class")
    if assurance_class not in ASSURANCE_CLASSES:
        raise ValueError("invalid assurance class")
    signature = assurance.get("signature")
    if signature is not None and not isinstance(signature, dict):
        raise ValueError("signature must be an object or null")

    evidence = packet.get("evidence")
    if not isinstance(evidence, list) or len(evidence) > 12:
        raise ValueError("evidence must be an array of at most 12 items")
    clean_evidence = []
    for item in evidence:
        if not isinstance(item, dict):
            raise ValueError("evidence item must be an object")
        kind = item.get("kind")
        if kind not in EVIDENCE_KINDS:
            raise ValueError("invalid evidence kind")
        digest = clean_str(item.get("sha256"), max_len=64)
        if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise ValueError("invalid evidence sha256")
        custody = item.get("custody")
        if custody not in CUSTODY:
            raise ValueError("invalid evidence custody")
        mime = item.get("mime")
        if mime is not None:
            mime = clean_str(mime, max_len=120)
        label = item.get("label")
        if label is not None:
            label = clean_str(label, max_len=160)
        size = item.get("bytes")
        if size is not None:
            if not isinstance(size, int) or size < 0:
                raise ValueError("invalid evidence bytes")
        clean_evidence.append({
            "kind": kind,
            "sha256": digest,
            "mime": mime,
            "bytes": size,
            "label": label,
            "custody": custody,
        })

    location = packet.get("location")
    if not isinstance(location, dict):
        raise ValueError("location must be an object")
    location_mode = location.get("mode")
    if location_mode not in LOCATION_MODES:
        raise ValueError("invalid location mode")
    lat = finite_number(location.get("latitude"), min_value=-90, max_value=90)
    lon = finite_number(location.get("longitude"), min_value=-180, max_value=180)
    acc = location.get("accuracy_m")
    if acc is not None:
        acc = finite_number(acc, min_value=0, max_value=1000000)
    place_label = location.get("place_label")
    if place_label is not None:
        place_label = clean_str(place_label, max_len=160)

    sharing = packet.get("sharing")
    if not isinstance(sharing, dict):
        raise ValueError("sharing must be an object")
    visibility = sharing.get("candidate_visibility")
    if visibility not in VISIBILITIES:
        raise ValueError("invalid candidate visibility")
    if sharing.get("media_disposition") != "hash-only-v0":
        raise ValueError("v0 accepts hash-only media disposition")
    if visibility == "public-candidate" and location_mode == "exact-private":
        raise ValueError("exact-private location cannot be public")

    refs = packet.get("refs") or []
    if not isinstance(refs, list) or len(refs) > 24:
        raise ValueError("refs must be an array of at most 24 items")
    refs = [clean_str(v, max_len=500) for v in refs]

    notes = packet.get("notes") or []
    if not isinstance(notes, list) or len(notes) > 24:
        raise ValueError("notes must be an array of at most 24 items")
    notes = [clean_str(v, max_len=500) for v in notes]

    return {
        "schema": "playable.mobile-attestation.v0",
        "client_id": client_id,
        "created_at": created_at,
        "claim": {"text": claim_text, "kind": claim_kind},
        "witness": {
            "mode": witness_mode,
            "display_name": display_name,
            "identity_ref": identity_ref,
        },
        "assurance": {
            "class": assurance_class,
            "signature": signature,
        },
        "evidence": clean_evidence,
        "location": {
            "mode": location_mode,
            "latitude": lat,
            "longitude": lon,
            "accuracy_m": acc,
            "place_label": place_label,
        },
        "sharing": {
            "candidate_visibility": visibility,
            "media_disposition": "hash-only-v0",
        },
        "refs": refs,
        "notes": notes,
    }


def rate_allowed(ip: str) -> bool:
    now = time.monotonic()
    cutoff = now - RATE_WINDOW_SECONDS
    with _rate_lock:
        q = _rate[ip]
        while q and q[0] < cutoff:
            q.popleft()
        if len(q) >= RATE_LIMIT:
            return False
        q.append(now)
        return True


class Handler(BaseHTTPRequestHandler):
    server_version = "PlayableAttestationIntake/0"

    def log_message(self, fmt, *args):
        # Do not log packet contents. The default line contains only request metadata.
        super().log_message(fmt, *args)

    def send_json(self, status: int, payload: object):
        body = canonical_bytes(payload)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def client_ip(self) -> str:
        return (
            self.headers.get("X-Real-IP")
            or self.headers.get("X-Forwarded-For", "").split(",")[0].strip()
            or self.client_address[0]
        )

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/healthz":
            return self.send_json(200, {
                "status": "ok",
                "service": "playable-attestation-intake",
                "schema": "playable.attestation-intake-health.v0",
            })

        if parsed.path == "/v0/attestations/public":
            qs = parse_qs(parsed.query)
            try:
                limit = min(max(int((qs.get("limit") or ["30"])[0]), 1), 100)
            except ValueError:
                return self.send_json(400, {"error": "invalid_limit"})
            with db() as conn:
                rows = conn.execute(
                    "SELECT candidate_id, received_at, status, packet_json, "
                    "packet_sha256, receipt_sha256 "
                    "FROM candidates WHERE visibility='public-candidate' "
                    "ORDER BY received_at DESC LIMIT ?",
                    (limit,),
                ).fetchall()
            return self.send_json(200, {
                "schema": "playable.public-attestation-feed.v0",
                "items": [
                    {
                        "candidate_id": row["candidate_id"],
                        "received_at": row["received_at"],
                        "status": row["status"],
                        "packet": json.loads(row["packet_json"]),
                        "packet_sha256": row["packet_sha256"],
                        "receipt_sha256": row["receipt_sha256"],
                    }
                    for row in rows
                ],
            })

        prefix = "/v0/attestations/"
        if parsed.path.startswith(prefix):
            candidate_id = parsed.path[len(prefix):]
            if not candidate_id or "/" in candidate_id:
                return self.send_json(404, {"error": "not_found"})
            with db() as conn:
                row = conn.execute(
                    "SELECT candidate_id, received_at, status, visibility, "
                    "packet_json, packet_sha256, receipt_sha256 "
                    "FROM candidates WHERE candidate_id=?",
                    (candidate_id,),
                ).fetchone()
            if not row or row["visibility"] != "public-candidate":
                return self.send_json(404, {"error": "not_found"})
            return self.send_json(200, {
                "schema": "playable.public-attestation-candidate.v0",
                "candidate_id": row["candidate_id"],
                "received_at": row["received_at"],
                "status": row["status"],
                "packet": json.loads(row["packet_json"]),
                "packet_sha256": row["packet_sha256"],
                "receipt_sha256": row["receipt_sha256"],
            })

        return self.send_json(404, {"error": "not_found"})

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path != "/v0/attestations":
            return self.send_json(404, {"error": "not_found"})

        if not rate_allowed(self.client_ip()):
            return self.send_json(429, {
                "error": "rate_limited",
                "limit": RATE_LIMIT,
                "window_seconds": RATE_WINDOW_SECONDS,
            })

        content_type = self.headers.get("Content-Type", "").split(";")[0].strip()
        if content_type != "application/json":
            return self.send_json(415, {"error": "application_json_required"})

        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            return self.send_json(400, {"error": "invalid_content_length"})
        if length <= 0 or length > MAX_BODY:
            return self.send_json(413, {
                "error": "body_size_out_of_bounds",
                "max_bytes": MAX_BODY,
            })

        try:
            raw = self.rfile.read(length)
            supplied = json.loads(raw.decode("utf-8"))
            packet = validate_packet(supplied)
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            return self.send_json(400, {
                "error": "invalid_attestation_packet",
                "detail": str(exc)[:300],
            })

        packet_bytes = canonical_bytes(packet)
        packet_sha = sha256_hex(packet_bytes)
        candidate_id = "attest:" + str(uuid.uuid4())
        received_at = utcnow()
        visibility = packet["sharing"]["candidate_visibility"]

        receipt_core = {
            "schema": "playable.attestation-receipt.v0",
            "candidate_id": candidate_id,
            "status": "candidate",
            "received_at": received_at,
            "packet_sha256": packet_sha,
            "public_candidate": visibility == "public-candidate",
        }
        receipt_sha = sha256_hex(canonical_bytes(receipt_core))
        receipt = dict(receipt_core)
        receipt["receipt_sha256"] = receipt_sha

        with db() as conn:
            conn.execute(
                "INSERT INTO candidates "
                "(candidate_id, received_at, status, visibility, packet_json, "
                "packet_sha256, receipt_sha256) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    candidate_id,
                    received_at,
                    "candidate",
                    visibility,
                    packet_bytes.decode("utf-8"),
                    packet_sha,
                    receipt_sha,
                ),
            )

        return self.send_json(HTTPStatus.CREATED, receipt)


def main() -> None:
    init_db()
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(
        json.dumps({
            "service": "playable-attestation-intake",
            "status": "listening",
            "host": HOST,
            "port": PORT,
            "db": DB_PATH,
        }),
        flush=True,
    )
    server.serve_forever()


if __name__ == "__main__":
    main()
