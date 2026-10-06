#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = os.environ.get(
    "PLAYABLE_INTAKE_DB",
    "/var/lib/playable-universe/attestation-intake.sqlite3",
)
MEDIA_ROOT = Path(os.environ.get(
    "PLAYABLE_MEDIA_ROOT",
    "/var/lib/playable-universe/media",
))


def utcnow():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def db():
    conn = sqlite3.connect(DB_PATH, timeout=5)
    conn.row_factory = sqlite3.Row
    return conn


def append_event(conn, candidate_id, event_type, payload, actor_kind="local-operator"):
    event_id="cevent:"+str(uuid.uuid4())
    conn.execute(
        "INSERT INTO candidate_events "
        "(event_id,candidate_id,event_type,recorded_at,actor_kind,payload_json) "
        "VALUES (?,?,?,?,?,?)",
        (
            event_id,
            candidate_id,
            event_type,
            utcnow(),
            actor_kind,
            json.dumps(payload,sort_keys=True,separators=(",",":")),
        ),
    )
    return event_id


def list_pending():
    with db() as conn:
        rows = conn.execute(
            "SELECT m.media_id, m.candidate_id, m.source_sha256, "
            "m.derivative_sha256, m.created_at, m.bytes, c.packet_json "
            "FROM media m JOIN candidates c ON c.candidate_id=m.candidate_id "
            "WHERE m.status='pending' ORDER BY m.created_at"
        ).fetchall()
    if not rows:
        print("PENDING_MEDIA=0")
        return
    import json
    print("PENDING_MEDIA="+str(len(rows)))
    for row in rows:
        packet=json.loads(row["packet_json"])
        print("---")
        print("media_id="+row["media_id"])
        print("candidate_id="+row["candidate_id"])
        print("created_at="+row["created_at"])
        print("bytes="+str(row["bytes"]))
        print("source_sha256="+row["source_sha256"])
        print("derivative_sha256="+row["derivative_sha256"])
        print("claim="+packet.get("claim",{}).get("text",""))
        print("witness="+str(packet.get("witness",{}).get("display_name")))


def approve(media_id: str):
    approved_dir = MEDIA_ROOT / "approved"
    approved_dir.mkdir(parents=True, exist_ok=True)
    with db() as conn:
        row = conn.execute(
            "SELECT media_id, candidate_id, source_sha256, derivative_sha256, "
            "status, path FROM media WHERE media_id=?",
            (media_id,),
        ).fetchone()
        if not row:
            raise SystemExit("NOT_FOUND")
        if row["status"] == "approved":
            print("ALREADY_APPROVED=true")
            return
        if row["status"] != "pending":
            raise SystemExit("REFUSED: status="+row["status"])
        src=Path(row["path"])
        if not src.is_file():
            raise SystemExit("REFUSED: media file missing")
        dst=approved_dir/(media_id.split(":",1)[1]+".jpg")
        shutil.move(str(src),str(dst))
        reviewed=utcnow()
        conn.execute(
            "UPDATE media SET status='approved', reviewed_at=?, path=? "
            "WHERE media_id=?",
            (reviewed,str(dst),media_id),
        )
        append_event(
            conn,
            row["candidate_id"],
            "evidence.public_derivative_approved",
            {
                "media_id": media_id,
                "source_sha256": row["source_sha256"],
                "derivative_sha256": row["derivative_sha256"],
                "reviewed_at": reviewed,
            },
        )
    print("MEDIA_APPROVED=true")
    print("media_id="+media_id)
    print("public_url=/playable/api/v0/media/"+media_id)


def reject(media_id: str):
    with db() as conn:
        row=conn.execute(
            "SELECT media_id,candidate_id,source_sha256,derivative_sha256,status,path "
            "FROM media WHERE media_id=?",
            (media_id,),
        ).fetchone()
        if not row:
            raise SystemExit("NOT_FOUND")
        if row["status"] == "approved":
            raise SystemExit("REFUSED: approved media requires separate withdrawal process")
        path=Path(row["path"])
        if path.is_file():
            path.unlink()
        reviewed=utcnow()
        conn.execute(
            "UPDATE media SET status='rejected', reviewed_at=? WHERE media_id=?",
            (reviewed,media_id),
        )
        append_event(
            conn,
            row["candidate_id"],
            "evidence.public_derivative_rejected",
            {
                "media_id": media_id,
                "source_sha256": row["source_sha256"],
                "derivative_sha256": row["derivative_sha256"],
                "reviewed_at": reviewed,
            },
        )
    print("MEDIA_REJECTED=true")
    print("media_id="+media_id)


def report_unavailable(candidate_id: str, source_sha256: str, note: str):
    with db() as conn:
        row=conn.execute(
            "SELECT packet_json FROM candidates WHERE candidate_id=?",
            (candidate_id,),
        ).fetchone()
        if not row:
            raise SystemExit("NOT_FOUND")
        packet=json.loads(row["packet_json"])
        bound={
            item.get("sha256")
            for item in packet.get("evidence",[])
            if item.get("kind")=="photo_hash"
        }
        if source_sha256 not in bound:
            raise SystemExit("REFUSED: source digest is not bound to candidate")
        prior=conn.execute(
            "SELECT 1 FROM candidate_events "
            "WHERE candidate_id=? AND event_type='evidence.source_unavailable_reported' "
            "AND json_extract(payload_json,'$.source_sha256')=? LIMIT 1",
            (candidate_id,source_sha256),
        ).fetchone()
        if prior:
            print("ALREADY_REPORTED=true")
            return
        event_id=append_event(
            conn,
            candidate_id,
            "evidence.source_unavailable_reported",
            {
                "source_sha256": source_sha256,
                "note": note,
            },
        )
    print("EVIDENCE_UNAVAILABLE_RECORDED=true")
    print("candidate_id="+candidate_id)
    print("source_sha256="+source_sha256)
    print("event_id="+event_id)


def list_private():
    with db() as conn:
        rows=conn.execute(
            "SELECT p.private_media_id,p.candidate_id,p.source_sha256,p.created_at,"
            "p.content_type,p.bytes,c.packet_json "
            "FROM private_media p JOIN candidates c ON c.candidate_id=p.candidate_id "
            "ORDER BY p.created_at DESC"
        ).fetchall()
    print("PRIVATE_MEDIA="+str(len(rows)))
    for row in rows:
        packet=json.loads(row["packet_json"])
        print("---")
        print("private_media_id="+row["private_media_id"])
        print("candidate_id="+row["candidate_id"])
        print("created_at="+row["created_at"])
        print("bytes="+str(row["bytes"]))
        print("content_type="+row["content_type"])
        print("source_sha256="+row["source_sha256"])
        print("claim="+packet.get("claim",{}).get("text",""))


def main():
    parser=argparse.ArgumentParser()
    sub=parser.add_subparsers(dest="command",required=True)
    sub.add_parser("list")
    sub.add_parser("list-private")
    a=sub.add_parser("approve")
    a.add_argument("media_id")
    r=sub.add_parser("reject")
    r.add_argument("media_id")
    u=sub.add_parser("report-unavailable")
    u.add_argument("candidate_id")
    u.add_argument("source_sha256")
    u.add_argument("--note",required=True)
    args=parser.parse_args()
    if args.command=="list":
        list_pending()
    elif args.command=="list-private":
        list_private()
    elif args.command=="approve":
        approve(args.media_id)
    elif args.command=="reject":
        reject(args.media_id)
    else:
        report_unavailable(args.candidate_id,args.source_sha256,args.note)


if __name__=="__main__":
    main()
