"""Test seed_initial_data execution and restoration of clinic data."""

import os
import tempfile
import pytest
from alembic.config import Config
from alembic import command
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import sessionmaker

from app.db.models import Clinic, Doctor, Patient, Appointment, AppointmentSlot, User
from app.db.session import reset_db_state
from app.scripts.seed_initial_data import seed_database


def test_seed_initial_data_populates_empty_database():
    reset_db_state()
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    try:
        os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
        reset_db_state()
        cfg = Config("alembic.ini")
        command.upgrade(cfg, "head")

        # Run seed
        seed_database()

        engine = create_engine(f"sqlite:///{db_path}")
        Session = sessionmaker(bind=engine)
        with Session() as session:
            # 1. Clinic default exists
            c = session.execute(select(Clinic).where(Clinic.id == "default")).scalar_one_or_none()
            assert c is not None
            assert c.name == "XYZ Clinic" or "XYZ" in c.name

            # 2. Doctors exist
            doc_cnt = session.execute(select(func.count(Doctor.id))).scalar()
            assert doc_cnt >= 8

            # 3. Patients exist
            pat_cnt = session.execute(select(func.count(Patient.id))).scalar()
            assert pat_cnt >= 12

            # 4. Slots exist
            slot_cnt = session.execute(select(func.count(AppointmentSlot.id))).scalar()
            assert slot_cnt >= 21

            # 5. Appointments exist
            appt_cnt = session.execute(select(func.count(Appointment.id))).scalar()
            assert appt_cnt >= 10

            # 6. Admin user exists
            admin = session.execute(select(User).where(User.username == "admin")).scalar_one_or_none()
            assert admin is not None
            assert admin.role in ("TENANT_ADMIN", "admin")

        engine.dispose()

        # Run seed a second time to ensure idempotency (no DuplicateKey errors)
        seed_database()

    finally:
        reset_db_state()
        try:
            if os.path.exists(db_path):
                os.remove(db_path)
        except OSError:
            pass
