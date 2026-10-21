"""Test alembic migrations schema validity."""

import os
import tempfile
import pytest
from alembic.config import Config
from alembic import command
from sqlalchemy import create_engine, inspect


def test_alembic_upgrade_head_and_columns():
    """Verify that all alembic migrations apply cleanly and required columns exist."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    try:
        os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
        cfg = Config("alembic.ini")
        command.upgrade(cfg, "head")

        engine = create_engine(f"sqlite:///{db_path}")
        try:
            insp = inspect(engine)
            doctor_cols = {c["name"] for c in insp.get_columns("doctors")}
            assert "bio" in doctor_cols
            assert "photo" in doctor_cols
            assert "signature" in doctor_cols
            assert "tenant_id" in doctor_cols

            clinic_cols = {c["name"] for c in insp.get_columns("clinics")}
            assert "logo" in clinic_cols
            assert "razorpay_key_id" in clinic_cols
            assert "razorpay_key_secret" in clinic_cols
        finally:
            engine.dispose()
    finally:
        try:
            if os.path.exists(db_path):
                os.remove(db_path)
        except OSError:
            pass
