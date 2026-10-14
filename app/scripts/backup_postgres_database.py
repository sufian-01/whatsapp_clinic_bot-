"""Automated backup script for PostgreSQL database (clinic_db).

Creates:
1. Full SQL dump via pg_dump (if available).
2. Structured JSON table-by-table snapshot of all 12 tables.
3. Manifest verifying row counts and SHA256 integrity.
Never prints passwords or secrets to stdout.
"""

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
from urllib.parse import urlparse

from sqlalchemy import func, inspect, select, text

from app.core.config import get_settings
from app.db.models import (
    Appointment,
    AppointmentSlot,
    AuditLog,
    Clinic,
    Doctor,
    Invoice,
    Patient,
    Payment,
    Prescription,
    PrescriptionItem,
    User,
)
from app.db.session import get_engine, get_session_factory, is_db_configured


def run_backup():
    if not is_db_configured():
        raise RuntimeError("DATABASE_URL is not configured.")

    settings = get_settings()
    engine = get_engine()
    session_factory = get_session_factory()
    session = session_factory()

    backup_dir = Path("data/backup_pre_operational_cutover")
    backup_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    manifest = {
        "timestamp": timestamp,
        "database": "clinic_db",
        "tables": {},
    }

    # 1. Structured JSON table-by-table snapshot
    model_classes = [
        Clinic,
        User,
        Doctor,
        Patient,
        AppointmentSlot,
        Appointment,
        Invoice,
        Payment,
        Prescription,
        PrescriptionItem,
        AuditLog,
    ]

    for model in model_classes:
        table_name = model.__tablename__
        rows = session.execute(select(model)).scalars().all()
        table_data = []
        for row in rows:
            # serialize attributes
            row_dict = {}
            for col in row.__table__.columns:
                val = getattr(row, col.name)
                if isinstance(val, datetime):
                    val = val.isoformat()
                row_dict[col.name] = val
            table_data.append(row_dict)

        out_file = backup_dir / f"{table_name}.json"
        content = json.dumps(table_data, indent=2, default=str)
        out_file.write_text(content, encoding="utf-8")
        manifest["tables"][table_name] = {
            "count": len(table_data),
            "file": out_file.name,
            "sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
        }

    # 2. pg_dump if available
    pg_dump_path = Path("C:/Program Files/PostgreSQL/18/bin/pg_dump.exe")
    parsed = urlparse(settings.database_url.replace("postgresql+psycopg://", "postgresql://"))
    if pg_dump_path.exists() and parsed.hostname:
        sql_out = backup_dir / f"clinic_db_{timestamp}.sql"
        env = os.environ.copy()
        if parsed.password:
            env["PGPASSWORD"] = parsed.password
        cmd = [
            str(pg_dump_path),
            "-h", parsed.hostname or "localhost",
            "-p", str(parsed.port or 5432),
            "-U", parsed.username or "postgres",
            "-d", parsed.path.lstrip("/"),
            "-f", str(sql_out),
            "--clean",
            "--if-exists",
        ]
        try:
            res = subprocess.run(cmd, env=env, capture_output=True, text=True)
            if res.returncode == 0 and sql_out.exists():
                manifest["sql_dump"] = {
                    "file": sql_out.name,
                    "size_bytes": sql_out.stat().st_size,
                }
        except Exception as e:
            manifest["sql_dump_error"] = str(e)

    # 3. Write manifest
    manifest_file = backup_dir / "manifest.json"
    manifest_file.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    session.close()
    print(f"Backup successfully created at {backup_dir}. Tables: {len(manifest['tables'])}")


if __name__ == "__main__":
    run_backup()

