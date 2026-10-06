#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import mimetypes
import os
import re
import sqlite3
import subprocess
import tempfile
import threading
import time
import uuid
from collections import defaultdict, deque
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

HOST = os.environ.get("PLAYABLE_INTAKE_HOST", "127.0.0.1")
PORT = int(os.environ.get("PLAYABLE_INTAKE_PORT", "18270"))
DB_PATH = os.environ.get(
    "PLAYABLE_INTAKE_DB",
    "/var/lib/playable-universe/attestation-intake.sqlite3",
)
MEDIA_ROOT = Path(os.environ.get(
    "PLAYABLE_MEDIA_ROOT",
    "/var/lib/playable-universe/media",
))
PRIVATE_MEDIA_ROOT = Path(os.environ.get(
    "PLAYABLE_PRIVATE_MEDIA_ROOT",
    "/var/lib/playable-universe/private-media",
))
WORLD_ROOT = Path(os.environ.get(
    "PLAYABLE_WORLD_ROOT",
    "/opt/playable-universe/world",
))
FFMPEG = os.environ.get("PLAYABLE_FFMPEG", "/usr/bin/ffmpeg")
PUBLIC_ORIGIN = os.environ.get(
    "PLAYABLE_PUBLIC_ORIGIN",
    "https://playable.quietwire.ai",
).rstrip("/")

MAX_BODY = 32 * 1024
MAX_PHOTO_BODY = 8 * 1024 * 1024
RATE_LIMIT = 30
RATE_WINDOW_SECONDS = 3600
PHOTO_RATE_LIMIT = 12
PHOTO_RATE_WINDOW_SECONDS = 3600

TOP_LEVEL_KEYS = {
    "schema", "client_id", "created_at", "claim", "witness",
    "assurance", "provenance", "evidence", "location", "sharing", "refs", "notes",
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
PROVENANCE_MODES = {
    "direct_observation", "own_capture", "relayed_report",
    "source_material", "derived_inference", "unknown", "unspecified",
}
VISIBILITIES = {"receipt-only", "public-candidate"}
LOCATION_MODES = {"none", "coarse", "exact-private"}
EVIDENCE_KINDS = {
    "photo_hash", "audio_hash", "video_hash", "document_hash", "other_hash",
}
CUSTODY = {"device-local", "qwos-private", "external-reference", "not-retained"}
PHOTO_MIME = {"image/jpeg", "image/png", "image/webp"}
HEX64 = re.compile(r"^[0-9a-f]{64}$")
SAFE_MEDIA_ID = re.compile(r"^media:[0-9a-f-]{36}$")

_rate_lock = threading.Lock()
_rate: dict[tuple[str, str], deque[float]] = defaultdict(deque)


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def public_url(path: str) -> str:
    if not path.startswith("/"):
        path = "/" + path
    return PUBLIC_ORIGIN + path if PUBLIC_ORIGIN else path


def db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=5)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
    PRIVATE_MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
    os.chmod(PRIVATE_MEDIA_ROOT, 0o700)
    (MEDIA_ROOT / "pending").mkdir(parents=True, exist_ok=True)
    (MEDIA_ROOT / "approved").mkdir(parents=True, exist_ok=True)
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
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS media (
                media_id TEXT PRIMARY KEY,
                candidate_id TEXT NOT NULL,
                source_sha256 TEXT NOT NULL,
                derivative_sha256 TEXT NOT NULL,
                created_at TEXT NOT NULL,
                reviewed_at TEXT,
                status TEXT NOT NULL,
                content_type TEXT NOT NULL,
                bytes INTEGER NOT NULL,
                path TEXT NOT NULL,
                FOREIGN KEY(candidate_id) REFERENCES candidates(candidate_id)
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_media_candidate "
            "ON media(candidate_id, status, created_at DESC)"
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS private_media (
                private_media_id TEXT PRIMARY KEY,
                candidate_id TEXT NOT NULL,
                source_sha256 TEXT NOT NULL,
                created_at TEXT NOT NULL,
                content_type TEXT NOT NULL,
                bytes INTEGER NOT NULL,
                path TEXT NOT NULL,
                UNIQUE(candidate_id, source_sha256),
                FOREIGN KEY(candidate_id) REFERENCES candidates(candidate_id)
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_private_media_candidate "
            "ON private_media(candidate_id, created_at DESC)"
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS candidate_events (
                event_id TEXT PRIMARY KEY,
                candidate_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                recorded_at TEXT NOT NULL,
                actor_kind TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                FOREIGN KEY(candidate_id) REFERENCES candidates(candidate_id)
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_candidate_events "
            "ON candidate_events(candidate_id, recorded_at ASC)"
        )
        existing = conn.execute(
            "SELECT candidate_id, received_at, visibility, packet_sha256 "
            "FROM candidates"
        ).fetchall()
        for row in existing:
            already = conn.execute(
                "SELECT 1 FROM candidate_events "
                "WHERE candidate_id=? AND event_type='candidate.received' LIMIT 1",
                (row["candidate_id"],),
            ).fetchone()
            if already:
                continue
            event_id = "cevent:" + str(uuid.uuid4())
            payload = {
                "packet_sha256": row["packet_sha256"],
                "visibility": row["visibility"],
                "backfilled": True,
            }
            conn.execute(
                "INSERT INTO candidate_events "
                "(event_id, candidate_id, event_type, recorded_at, actor_kind, payload_json) "
                "VALUES (?, ?, 'candidate.received', ?, 'system', ?)",
                (
                    event_id,
                    row["candidate_id"],
                    row["received_at"],
                    canonical_bytes(payload).decode("utf-8"),
                ),
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

    provenance = packet.get("provenance")
    if provenance is None:
        provenance = {
            "mode": "unspecified",
            "source_refs": [],
            "note": None,
        }
    if not isinstance(provenance, dict):
        raise ValueError("provenance must be an object")
    provenance_unknown = set(provenance) - {"mode", "source_refs", "note"}
    if provenance_unknown:
        raise ValueError(
            "unknown provenance fields: " +
            ", ".join(sorted(provenance_unknown))
        )
    provenance_mode = provenance.get("mode")
    if provenance_mode not in PROVENANCE_MODES:
        raise ValueError("invalid provenance mode")
    provenance_refs = provenance.get("source_refs") or []
    if not isinstance(provenance_refs, list) or len(provenance_refs) > 12:
        raise ValueError(
            "provenance source_refs must be an array of at most 12 items"
        )
    provenance_refs = [
        clean_str(value, max_len=500)
        for value in provenance_refs
    ]
    provenance_note = provenance.get("note")
    if provenance_note is not None:
        provenance_note = clean_str(provenance_note, max_len=500)

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
        if not HEX64.match(digest):
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
        "provenance": {
            "mode": provenance_mode,
            "source_refs": provenance_refs,
            "note": provenance_note,
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


def public_packet(packet: dict) -> dict:
    projected = json.loads(json.dumps(packet))
    projected.pop("client_id", None)
    return projected


def rate_allowed(ip: str, bucket: str, limit: int, window: int) -> bool:
    now = time.monotonic()
    cutoff = now - window
    key = (bucket, ip)
    with _rate_lock:
        q = _rate[key]
        while q and q[0] < cutoff:
            q.popleft()
        if len(q) >= limit:
            return False
        q.append(now)
        return True


def append_candidate_event(
    conn: sqlite3.Connection,
    candidate_id: str,
    event_type: str,
    actor_kind: str,
    payload: dict,
    *,
    recorded_at: str | None = None,
) -> dict:
    event = {
        "event_id": "cevent:" + str(uuid.uuid4()),
        "candidate_id": candidate_id,
        "event_type": event_type,
        "recorded_at": recorded_at or utcnow(),
        "actor_kind": actor_kind,
        "payload": payload,
    }
    conn.execute(
        "INSERT INTO candidate_events "
        "(event_id, candidate_id, event_type, recorded_at, actor_kind, payload_json) "
        "VALUES (?, ?, ?, ?, ?, ?)",
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


def candidate_events_for(conn: sqlite3.Connection, candidate_id: str) -> list[dict]:
    rows = conn.execute(
        "SELECT event_id, event_type, recorded_at, actor_kind, payload_json "
        "FROM candidate_events WHERE candidate_id=? "
        "ORDER BY recorded_at ASC, event_id ASC",
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


def private_media_for(conn: sqlite3.Connection, candidate_id: str) -> list[dict]:
    rows = conn.execute(
        "SELECT private_media_id, source_sha256, created_at, content_type, bytes "
        "FROM private_media WHERE candidate_id=? ORDER BY created_at ASC",
        (candidate_id,),
    ).fetchall()
    return [
        {
            "private_media_id": row["private_media_id"],
            "source_sha256": row["source_sha256"],
            "created_at": row["created_at"],
            "content_type": row["content_type"],
            "bytes": row["bytes"],
        }
        for row in rows
    ]


def evidence_summary_for(conn: sqlite3.Connection, candidate_id: str, packet: dict) -> dict:
    bound = [
        item for item in packet.get("evidence", [])
        if item.get("kind") == "photo_hash"
    ]
    private = private_media_for(conn, candidate_id)
    public = approved_media_for(conn, candidate_id)
    events = candidate_events_for(conn, candidate_id)
    unavailable = [
        event for event in events
        if event["event_type"] == "evidence.source_unavailable_reported"
    ]
    return {
        "bound_photo_count": len(bound),
        "private_retained_count": len(private),
        "public_derivative_count": len(public),
        "source_unavailable_reported_count": len(unavailable),
    }


def approved_media_for(conn: sqlite3.Connection, candidate_id: str) -> list[dict]:
    rows = conn.execute(
        "SELECT media_id, source_sha256, derivative_sha256, created_at, "
        "content_type, bytes FROM media "
        "WHERE candidate_id=? AND status='approved' ORDER BY created_at",
        (candidate_id,),
    ).fetchall()
    return [
        {
            "media_id": row["media_id"],
            "kind": "public_photo_derivative",
            "source_sha256": row["source_sha256"],
            "sha256": row["derivative_sha256"],
            "content_type": row["content_type"],
            "bytes": row["bytes"],
            "url": public_url(f"/api/v0/media/{row['media_id']}"),
        }
        for row in rows
    ]


def row_to_public_candidate(conn: sqlite3.Connection, row: sqlite3.Row) -> dict:
    packet = public_packet(json.loads(row["packet_json"]))
    return {
        "candidate_id": row["candidate_id"],
        "received_at": row["received_at"],
        "status": row["status"],
        "packet": packet,
        "packet_sha256": row["packet_sha256"],
        "receipt_sha256": row["receipt_sha256"],
        "media": approved_media_for(conn, row["candidate_id"]),
        "evidence_summary": evidence_summary_for(
            conn, row["candidate_id"], packet
        ),
        "lifecycle": candidate_events_for(conn, row["candidate_id"]),
    }


def photo_hashes(packet: dict) -> set[str]:
    return {
        item["sha256"] for item in packet.get("evidence", [])
        if item.get("kind") == "photo_hash" and HEX64.match(item.get("sha256", ""))
    }


def make_derivative(source: Path, output: Path) -> None:
    cmd = [
        FFMPEG,
        "-v", "error",
        "-nostdin",
        "-y",
        "-threads", "1",
        "-i", str(source),
        "-vf", "scale='min(1600,iw)':-2",
        "-map_metadata", "-1",
        "-frames:v", "1",
        "-q:v", "3",
        str(output),
    ]
    subprocess.run(
        cmd,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        timeout=15,
    )


def read_world_json(relative: str):
    path = (WORLD_ROOT / relative).resolve()
    root = WORLD_ROOT.resolve()
    if root not in path.parents and path != root:
        raise ValueError("invalid world path")
    return json.loads(path.read_text())


def world_scene_catalog() -> list[dict]:
    items = []
    fixtures = [
        ("past-binbrook", "examples/past-binbrook/scene.json"),
        ("present-room", "examples/present-room/scene.json"),
        ("future-transparent-authority", "examples/future-transparent-authority/scene.json"),
    ]
    for slug, path in fixtures:
        try:
            scene = read_world_json(path)
        except Exception:
            continue
        items.append({
            "slug": slug,
            "scene_id": scene.get("scene_id"),
            "title": scene.get("title"),
            "description": scene.get("description"),
            "temporal_mode": scene.get("temporal_mode"),
            "at": scene.get("at"),
            "branch_id": scene.get("branch_id"),
            "manifest_url": public_url(f"/api/v0/scenes/{slug}"),
        })
    return items


def world_scene(slug: str):
    mapping = {
        "past-binbrook": "examples/past-binbrook/scene.json",
        "present-room": "examples/present-room/scene.json",
        "future-transparent-authority": "examples/future-transparent-authority/scene.json",
    }
    path = mapping.get(slug)
    if not path:
        return None
    try:
        return read_world_json(path)
    except Exception:
        return None


def world_state(slug: str):
    if slug == "present-room":
        try:
            return read_world_json("examples/present-room/state.json")
        except Exception:
            return None
    scene = world_scene(slug)
    if not scene:
        return None
    entities = {}
    for entity in scene.get("entities", []):
        entities[entity["entity_id"]] = {
            "persona_id": entity.get("persona_id"),
            "transform": entity.get("transform") or {},
            "state": {},
            "truth_class": entity.get("truth_class", "reconstructed"),
            "last_event_id": None,
        }
    return {
        "schema": "playable.world-state.v0",
        "scene_id": scene["scene_id"],
        "temporal_mode": scene["temporal_mode"],
        "branch_id": scene.get("branch_id"),
        "as_of": scene.get("at") or utcnow(),
        "sequence": 0,
        "entities": entities,
        "provenance_refs": scene.get("provenance_refs", []),
    }


def candidate_world_events(conn: sqlite3.Connection, limit: int = 200) -> list[dict]:
    rows = conn.execute(
        "SELECT candidate_id, received_at, packet_json, packet_sha256 "
        "FROM candidates WHERE visibility='public-candidate' "
        "ORDER BY received_at ASC LIMIT 100",
    ).fetchall()

    pending = []
    for row in rows:
        packet = public_packet(json.loads(row["packet_json"]))
        actor_name = packet.get("witness", {}).get("display_name")
        witness_actor = "witness:anonymous"
        if actor_name:
            witness_actor = "witness:self-asserted:" + hashlib.sha256(
                actor_name.encode("utf-8")
            ).hexdigest()[:16]

        lifecycle = candidate_events_for(conn, row["candidate_id"])
        for event in lifecycle:
            etype = event["event_type"]
            if etype == "candidate.received":
                payload = {
                    "candidate_id": row["candidate_id"],
                    "claim": packet.get("claim"),
                    "witness": packet.get("witness"),
                    "assurance": packet.get("assurance"),
                    "provenance": packet.get("provenance"),
                    "location": packet.get("location"),
                    "media": approved_media_for(conn, row["candidate_id"]),
                    "evidence_summary": evidence_summary_for(
                        conn, row["candidate_id"], packet
                    ),
                    "packet_sha256": row["packet_sha256"],
                }
                actor = {
                    "entity_id": witness_actor,
                    "persona_id": None,
                    "control_mode": "human",
                }
                world_type = "attestation.candidate_received"
                truth_class = "reported"
                effective_at = packet.get("created_at")
            else:
                payload = {
                    "candidate_id": row["candidate_id"],
                    **event["payload"],
                    "evidence_summary": evidence_summary_for(
                        conn, row["candidate_id"], packet
                    ),
                    "media": approved_media_for(conn, row["candidate_id"]),
                }
                actor = {
                    "entity_id": (
                        "system:playable-intake"
                        if event["actor_kind"] == "system"
                        else "operator:local"
                    ),
                    "persona_id": None,
                    "control_mode": "system",
                }
                world_type = etype
                truth_class = "reported"
                effective_at = event["recorded_at"]

            pending.append({
                "_sort": event["recorded_at"],
                "schema": "playable.world-event.v0",
                "event_id": "world-" + event["event_id"],
                "scene_id": "scene:present-room:fixture-v0",
                "branch_id": None,
                "event_type": world_type,
                "truth_class": truth_class,
                "temporal_mode": "present",
                "recorded_at": event["recorded_at"],
                "effective_at": effective_at,
                "sequence": None,
                "actor": actor,
                "targets": [row["candidate_id"]],
                "payload": payload,
                "source_refs": [row["candidate_id"]],
                "attestation_refs": [],
                "rights_refs": [],
                "intent_ref": None,
                "supersedes": [],
                "notes": [
                    "Lifecycle events append to the candidate record; the original attestation packet is not rewritten."
                ],
            })

    pending.sort(key=lambda item: (item["_sort"], item["event_id"]))
    events = []
    for sequence, item in enumerate(pending[:limit], start=1):
        item.pop("_sort", None)
        item["sequence"] = sequence
        events.append(item)
    return events


class Handler(BaseHTTPRequestHandler):
    server_version = "PlayableAttestationIntake/1"

    def log_message(self, fmt, *args):
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

    def send_file(self, path: Path, content_type: str):
        size = path.stat().st_size
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(size))
        self.send_header("Cache-Control", "public, max-age=31536000, immutable")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'none'")
        self.end_headers()
        with path.open("rb") as fh:
            while True:
                chunk = fh.read(64 * 1024)
                if not chunk:
                    break
                self.wfile.write(chunk)

    def client_ip(self) -> str:
        return (
            self.headers.get("X-Real-IP")
            or self.headers.get("X-Forwarded-For", "").split(",")[0].strip()
            or self.client_address[0]
        )

    def do_GET(self):
        parsed = urlparse(self.path)
        request_path = unquote(parsed.path)

        if request_path == "/healthz":
            return self.send_json(200, {
                "status": "ok",
                "service": "playable-attestation-intake",
                "schema": "playable.attestation-intake-health.v1",
                "world_root": str(WORLD_ROOT),
                "media": "pending-review",
            })

        if request_path == "/v0/world/tiles":
            try:
                tiles = read_world_json("data/tiles.json")
            except Exception as exc:
                return self.send_json(503, {
                    "error": "world_tiles_unavailable",
                    "detail": str(exc)[:200],
                })
            return self.send_json(200, {
                "schema": "playable.world-tile-feed.v0",
                "items": tiles,
            })

        if request_path == "/v0/scenes":
            return self.send_json(200, {
                "schema": "playable.scene-catalog.v0",
                "items": world_scene_catalog(),
            })

        scene_match = re.match(r"^/v0/scenes/([a-z0-9-]+)$", request_path)
        if scene_match:
            slug = scene_match.group(1)
            scene = world_scene(slug)
            if not scene:
                return self.send_json(404, {"error": "scene_not_found"})
            return self.send_json(200, scene)

        state_match = re.match(r"^/v0/scenes/([a-z0-9-]+)/state$", request_path)
        if state_match:
            slug = state_match.group(1)
            state = world_state(slug)
            if not state:
                return self.send_json(404, {"error": "scene_not_found"})
            return self.send_json(200, state)

        events_match = re.match(r"^/v0/scenes/([a-z0-9-]+)/events$", request_path)
        if events_match:
            slug = events_match.group(1)
            if slug != "present-room":
                return self.send_json(200, {
                    "schema": "playable.world-event-feed.v0",
                    "items": [],
                })
            with db() as conn:
                events = candidate_world_events(conn)
            return self.send_json(200, {
                "schema": "playable.world-event-feed.v0",
                "items": events,
            })

        if request_path == "/v0/attestations/public":
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
                items = [row_to_public_candidate(conn, row) for row in rows]
            return self.send_json(200, {
                "schema": "playable.public-attestation-feed.v0",
                "items": items,
            })

        media_match = re.match(r"^/v0/media/(media:[0-9a-f-]{36})$", request_path)
        if media_match:
            media_id = media_match.group(1)
            with db() as conn:
                row = conn.execute(
                    "SELECT status, content_type, path FROM media WHERE media_id=?",
                    (media_id,),
                ).fetchone()
            if not row or row["status"] != "approved":
                return self.send_json(404, {"error": "media_not_found"})
            path = Path(row["path"])
            if not path.is_file():
                return self.send_json(404, {"error": "media_file_missing"})
            return self.send_file(path, row["content_type"])

        prefix = "/v0/attestations/"
        if request_path.startswith(prefix):
            candidate_id = request_path[len(prefix):]
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
                item = row_to_public_candidate(conn, row)
            return self.send_json(200, {
                "schema": "playable.public-attestation-candidate.v0",
                **item,
            })

        return self.send_json(404, {"error": "not_found"})

    def do_POST(self):
        parsed = urlparse(self.path)
        request_path = unquote(parsed.path)

        publish_match = re.match(
            r"^/v0/attestations/(attest:[0-9a-f-]{36})/photo/publish$",
            request_path,
        )
        if publish_match:
            return self.handle_publish_private_photo(publish_match.group(1))

        media_match = re.match(
            r"^/v0/attestations/(attest:[0-9a-f-]{36})/photo$",
            request_path,
        )
        if media_match:
            return self.handle_photo_upload(media_match.group(1))

        if request_path != "/v0/attestations":
            return self.send_json(404, {"error": "not_found"})

        if not rate_allowed(
            self.client_ip(), "attest", RATE_LIMIT, RATE_WINDOW_SECONDS
        ):
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
            append_candidate_event(
                conn,
                candidate_id,
                "candidate.received",
                "system",
                {
                    "packet_sha256": packet_sha,
                    "visibility": visibility,
                    "backfilled": False,
                },
                recorded_at=received_at,
            )

        return self.send_json(HTTPStatus.CREATED, receipt)

    def handle_photo_upload(self, candidate_id: str):
        if not rate_allowed(
            self.client_ip(), "photo", PHOTO_RATE_LIMIT, PHOTO_RATE_WINDOW_SECONDS
        ):
            return self.send_json(429, {
                "error": "photo_rate_limited",
                "limit": PHOTO_RATE_LIMIT,
                "window_seconds": PHOTO_RATE_WINDOW_SECONDS,
            })

        content_type = self.headers.get("Content-Type", "").split(";")[0].strip()
        if content_type not in PHOTO_MIME:
            return self.send_json(415, {
                "error": "unsupported_photo_type",
                "allowed": sorted(PHOTO_MIME),
            })

        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            return self.send_json(400, {"error": "invalid_content_length"})
        if length <= 0 or length > MAX_PHOTO_BODY:
            return self.send_json(413, {
                "error": "photo_size_out_of_bounds",
                "max_bytes": MAX_PHOTO_BODY,
            })

        claimed_source = self.headers.get("X-Photo-Sha256", "").strip().lower()
        if not HEX64.match(claimed_source):
            return self.send_json(400, {"error": "x_photo_sha256_required"})

        with db() as conn:
            candidate = conn.execute(
                "SELECT visibility, packet_json FROM candidates WHERE candidate_id=?",
                (candidate_id,),
            ).fetchone()
        if not candidate:
            return self.send_json(404, {"error": "candidate_not_found"})
        custody_mode = self.headers.get(
            "X-Evidence-Custody", "public-review"
        ).strip().lower()
        if custody_mode not in {"private-retain", "public-review"}:
            return self.send_json(400, {
                "error": "invalid_evidence_custody",
                "allowed": ["private-retain", "public-review"],
            })
        if (
            custody_mode == "public-review"
            and candidate["visibility"] != "public-candidate"
        ):
            return self.send_json(409, {
                "error": "photo_publication_requires_public_candidate"
            })
        packet = json.loads(candidate["packet_json"])
        matches = [
            item for item in packet.get("evidence", [])
            if item.get("kind") == "photo_hash"
            and item.get("sha256") == claimed_source
        ]
        if not matches:
            return self.send_json(409, {
                "error": "photo_digest_not_bound_to_attestation"
            })
        bound = matches[0]
        bound_bytes = bound.get("bytes")
        if bound_bytes is not None and bound_bytes != length:
            return self.send_json(409, {
                "error": "photo_byte_count_mismatch",
                "expected": bound_bytes,
                "actual": length,
            })
        bound_mime = bound.get("mime")
        if bound_mime and bound_mime != content_type:
            return self.send_json(409, {
                "error": "photo_mime_mismatch",
                "expected": bound_mime,
                "actual": content_type,
            })

        temp_dir = MEDIA_ROOT / "pending"
        temp_dir.mkdir(parents=True, exist_ok=True)
        upload_path = temp_dir / (".upload-" + str(uuid.uuid4()))
        derivative_temp = temp_dir / (".derivative-" + str(uuid.uuid4()) + ".jpg")

        hasher = hashlib.sha256()
        remaining = length
        try:
            with upload_path.open("wb") as out:
                while remaining:
                    chunk = self.rfile.read(min(64 * 1024, remaining))
                    if not chunk:
                        raise ValueError("unexpected end of upload")
                    out.write(chunk)
                    hasher.update(chunk)
                    remaining -= len(chunk)

            actual_source = hasher.hexdigest()
            if actual_source != claimed_source:
                return self.send_json(409, {
                    "error": "uploaded_photo_hash_mismatch",
                    "expected": claimed_source,
                    "actual": actual_source,
                })

            if custody_mode == "private-retain":
                private_id = "private-media:" + str(uuid.uuid4())
                suffix = mimetypes.guess_extension(content_type) or ".bin"
                final_private = PRIVATE_MEDIA_ROOT / (
                    private_id.split(":", 1)[1] + suffix
                )
                existing = None
                with db() as conn:
                    existing = conn.execute(
                        "SELECT private_media_id, created_at, content_type, bytes "
                        "FROM private_media "
                        "WHERE candidate_id=? AND source_sha256=?",
                        (candidate_id, claimed_source),
                    ).fetchone()
                    if existing is None:
                        upload_path.replace(final_private)
                        os.chmod(final_private, 0o600)
                        created_at = utcnow()
                        conn.execute(
                            "INSERT INTO private_media "
                            "(private_media_id, candidate_id, source_sha256, "
                            "created_at, content_type, bytes, path) "
                            "VALUES (?, ?, ?, ?, ?, ?, ?)",
                            (
                                private_id,
                                candidate_id,
                                claimed_source,
                                created_at,
                                content_type,
                                length,
                                str(final_private),
                            ),
                        )
                        append_candidate_event(
                            conn,
                            candidate_id,
                            "evidence.private_custody_received",
                            "system",
                            {
                                "source_sha256": claimed_source,
                                "bytes": length,
                                "content_type": content_type,
                            },
                        )
                    else:
                        private_id = existing["private_media_id"]
                        created_at = existing["created_at"]
                return self.send_json(HTTPStatus.CREATED, {
                    "schema": "playable.private-media-custody-receipt.v0",
                    "private_media_id": private_id,
                    "candidate_id": candidate_id,
                    "status": "privately-retained",
                    "source_sha256": claimed_source,
                    "bytes": length,
                    "content_type": content_type,
                    "created_at": created_at,
                    "public": False,
                    "note": "The exact original is retained under private FC custody and is not exposed by the public media API.",
                })

            try:
                make_derivative(upload_path, derivative_temp)
            except subprocess.TimeoutExpired:
                return self.send_json(422, {"error": "photo_processing_timeout"})
            except subprocess.CalledProcessError as exc:
                detail = (exc.stderr or b"").decode("utf-8", "replace")[:300]
                return self.send_json(422, {
                    "error": "photo_processing_failed",
                    "detail": detail,
                })

            derivative_bytes = derivative_temp.read_bytes()
            derivative_sha = sha256_hex(derivative_bytes)
            media_id = "media:" + str(uuid.uuid4())
            final_path = temp_dir / (media_id.split(":", 1)[1] + ".jpg")
            derivative_temp.replace(final_path)
            created_at = utcnow()

            with db() as conn:
                conn.execute(
                    "INSERT INTO media "
                    "(media_id, candidate_id, source_sha256, derivative_sha256, "
                    "created_at, reviewed_at, status, content_type, bytes, path) "
                    "VALUES (?, ?, ?, ?, ?, NULL, 'pending', 'image/jpeg', ?, ?)",
                    (
                        media_id,
                        candidate_id,
                        claimed_source,
                        derivative_sha,
                        created_at,
                        len(derivative_bytes),
                        str(final_path),
                    ),
                )
                append_candidate_event(
                    conn,
                    candidate_id,
                    "evidence.public_derivative_pending",
                    "system",
                    {
                        "media_id": media_id,
                        "source_sha256": claimed_source,
                        "derivative_sha256": derivative_sha,
                        "derivative_bytes": len(derivative_bytes),
                    },
                )

            return self.send_json(HTTPStatus.CREATED, {
                "schema": "playable.media-intake-receipt.v0",
                "media_id": media_id,
                "candidate_id": candidate_id,
                "status": "pending",
                "source_sha256": claimed_source,
                "derivative_sha256": derivative_sha,
                "derivative_bytes": len(derivative_bytes),
                "created_at": created_at,
                "review_required": True,
                "note": "Original upload was used only to verify the sealed digest and create a metadata-stripped derivative; it was not retained by this service.",
            })
        except ValueError as exc:
            return self.send_json(400, {
                "error": "photo_upload_failed",
                "detail": str(exc)[:200],
            })
        finally:
            try:
                upload_path.unlink(missing_ok=True)
            except Exception:
                pass
            try:
                derivative_temp.unlink(missing_ok=True)
            except Exception:
                pass


    def handle_publish_private_photo(self, candidate_id: str):
        if not rate_allowed(
            self.client_ip(), "photo-publish", PHOTO_RATE_LIMIT, PHOTO_RATE_WINDOW_SECONDS
        ):
            return self.send_json(429, {
                "error": "photo_publish_rate_limited",
                "limit": PHOTO_RATE_LIMIT,
                "window_seconds": PHOTO_RATE_WINDOW_SECONDS,
            })

        claimed_source = self.headers.get("X-Photo-Sha256", "").strip().lower()
        if not HEX64.match(claimed_source):
            return self.send_json(400, {"error": "x_photo_sha256_required"})

        with db() as conn:
            candidate = conn.execute(
                "SELECT visibility, packet_json FROM candidates WHERE candidate_id=?",
                (candidate_id,),
            ).fetchone()
            if not candidate:
                return self.send_json(404, {"error": "candidate_not_found"})
            if candidate["visibility"] != "public-candidate":
                return self.send_json(409, {
                    "error": "photo_publication_requires_public_candidate"
                })
            packet = json.loads(candidate["packet_json"])
            if claimed_source not in photo_hashes(packet):
                return self.send_json(409, {
                    "error": "photo_digest_not_bound_to_attestation"
                })
            private = conn.execute(
                "SELECT private_media_id, content_type, bytes, path "
                "FROM private_media "
                "WHERE candidate_id=? AND source_sha256=?",
                (candidate_id, claimed_source),
            ).fetchone()
            if not private:
                return self.send_json(409, {
                    "error": "private_source_media_not_retained"
                })
            existing = conn.execute(
                "SELECT media_id, status, derivative_sha256, bytes, created_at "
                "FROM media WHERE candidate_id=? AND source_sha256=? "
                "AND status IN ('pending','approved') "
                "ORDER BY created_at DESC LIMIT 1",
                (candidate_id, claimed_source),
            ).fetchone()
            if existing:
                return self.send_json(200, {
                    "schema": "playable.media-intake-receipt.v0",
                    "media_id": existing["media_id"],
                    "candidate_id": candidate_id,
                    "status": existing["status"],
                    "source_sha256": claimed_source,
                    "derivative_sha256": existing["derivative_sha256"],
                    "derivative_bytes": existing["bytes"],
                    "created_at": existing["created_at"],
                    "review_required": existing["status"] == "pending",
                    "note": "A public derivative already exists for this bound source.",
                })

        source = Path(private["path"])
        if not source.is_file():
            return self.send_json(409, {
                "error": "private_source_media_file_missing"
            })

        temp_dir = MEDIA_ROOT / "pending"
        temp_dir.mkdir(parents=True, exist_ok=True)
        derivative_temp = temp_dir / (
            ".derivative-" + str(uuid.uuid4()) + ".jpg"
        )
        try:
            make_derivative(source, derivative_temp)
            derivative_bytes = derivative_temp.read_bytes()
            derivative_sha = sha256_hex(derivative_bytes)
            media_id = "media:" + str(uuid.uuid4())
            final_path = temp_dir / (media_id.split(":", 1)[1] + ".jpg")
            derivative_temp.replace(final_path)
            created_at = utcnow()
            with db() as conn:
                conn.execute(
                    "INSERT INTO media "
                    "(media_id, candidate_id, source_sha256, derivative_sha256, "
                    "created_at, reviewed_at, status, content_type, bytes, path) "
                    "VALUES (?, ?, ?, ?, ?, NULL, 'pending', 'image/jpeg', ?, ?)",
                    (
                        media_id,
                        candidate_id,
                        claimed_source,
                        derivative_sha,
                        created_at,
                        len(derivative_bytes),
                        str(final_path),
                    ),
                )
                append_candidate_event(
                    conn,
                    candidate_id,
                    "evidence.public_derivative_pending",
                    "system",
                    {
                        "media_id": media_id,
                        "source_sha256": claimed_source,
                        "derivative_sha256": derivative_sha,
                        "derivative_bytes": len(derivative_bytes),
                    },
                )
            return self.send_json(HTTPStatus.CREATED, {
                "schema": "playable.media-intake-receipt.v0",
                "media_id": media_id,
                "candidate_id": candidate_id,
                "status": "pending",
                "source_sha256": claimed_source,
                "derivative_sha256": derivative_sha,
                "derivative_bytes": len(derivative_bytes),
                "created_at": created_at,
                "review_required": True,
                "note": "Public derivative created from the exact privately retained original. Local review is required before display.",
            })
        except subprocess.TimeoutExpired:
            return self.send_json(422, {"error": "photo_processing_timeout"})
        except subprocess.CalledProcessError as exc:
            detail = (exc.stderr or b"").decode("utf-8", "replace")[:300]
            return self.send_json(422, {
                "error": "photo_processing_failed",
                "detail": detail,
            })
        finally:
            derivative_temp.unlink(missing_ok=True)



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
            "world_root": str(WORLD_ROOT),
            "media_root": str(MEDIA_ROOT),
        }),
        flush=True,
    )
    server.serve_forever()


if __name__ == "__main__":
    main()
