#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import shutil
import sqlite3
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
            "SELECT media_id, status, path FROM media WHERE media_id=?",
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
        conn.execute(
            "UPDATE media SET status='approved', reviewed_at=?, path=? "
            "WHERE media_id=?",
            (utcnow(),str(dst),media_id),
        )
    print("MEDIA_APPROVED=true")
    print("media_id="+media_id)
    print("public_url=/playable/api/v0/media/"+media_id)


def reject(media_id: str):
    with db() as conn:
        row=conn.execute(
            "SELECT status,path FROM media WHERE media_id=?",
            (media_id,),
        ).fetchone()
        if not row:
            raise SystemExit("NOT_FOUND")
        if row["status"] == "approved":
            raise SystemExit("REFUSED: approved media requires separate withdrawal process")
        path=Path(row["path"])
        if path.is_file():
            path.unlink()
        conn.execute(
            "UPDATE media SET status='rejected', reviewed_at=? WHERE media_id=?",
            (utcnow(),media_id),
        )
    print("MEDIA_REJECTED=true")
    print("media_id="+media_id)


def main():
    parser=argparse.ArgumentParser()
    sub=parser.add_subparsers(dest="command",required=True)
    sub.add_parser("list")
    a=sub.add_parser("approve")
    a.add_argument("media_id")
    r=sub.add_parser("reject")
    r.add_argument("media_id")
    args=parser.parse_args()
    if args.command=="list":
        list_pending()
    elif args.command=="approve":
        approve(args.media_id)
    else:
        reject(args.media_id)


if __name__=="__main__":
    main()
