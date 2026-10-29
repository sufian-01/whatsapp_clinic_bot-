"""Seed test appointment slots for all doctors in XYZ Clinic (default tenant).

Generates 5 distinct slots per doctor per day across 33 upcoming days
(2026-10-29 to 2026-11-30, covering 1 Nov and the entire next month).
"""

from datetime import date, datetime, timedelta, timezone
import logging
from uuid import uuid4

from sqlalchemy import select, update

from app.db.models import AppointmentSlot, Clinic, Doctor
from app.db.session import get_session_factory

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DOCTOR_SCHEDULES = {
    "DOC001": [  # Dr. Arjun Mehta (General Physician) - Morning
        ("10:00 AM", "10:30 AM"),
        ("10:30 AM", "11:00 AM"),
        ("11:00 AM", "11:30 AM"),
        ("11:30 AM", "12:00 PM"),
        ("12:00 PM", "12:30 PM"),
    ],
    "DOC002": [  # Dr. Sana Khan (Gynecologist) - Evening
        ("04:00 PM", "04:30 PM"),
        ("04:30 PM", "05:00 PM"),
        ("05:00 PM", "05:30 PM"),
        ("05:30 PM", "06:00 PM"),
        ("06:00 PM", "06:30 PM"),
    ],
    "DOC003": [  # Dr. sufian (Cardiologist) - Late Afternoon
        ("03:00 PM", "03:30 PM"),
        ("03:30 PM", "04:00 PM"),
        ("04:00 PM", "04:30 PM"),
        ("04:30 PM", "05:00 PM"),
        ("05:00 PM", "05:30 PM"),
    ],
    "DOC004": [  # Dr. Neha Sharma (Dermatologist) - Mid-Day
        ("11:00 AM", "11:30 AM"),
        ("11:30 AM", "12:00 PM"),
        ("12:00 PM", "12:30 PM"),
        ("12:30 PM", "01:00 PM"),
        ("01:00 PM", "01:30 PM"),
    ],
    "DOC005": [  # Dr. Rahul Verma (Orthopedic) - Morning
        ("09:30 AM", "10:00 AM"),
        ("10:00 AM", "10:30 AM"),
        ("10:30 AM", "11:00 AM"),
        ("11:00 AM", "11:30 AM"),
        ("11:30 AM", "12:00 PM"),
    ],
    "DOC006": [  # Dr. Ayesha Khan (Pediatrician) - Early Afternoon
        ("01:30 PM", "02:00 PM"),
        ("02:00 PM", "02:30 PM"),
        ("02:30 PM", "03:00 PM"),
        ("03:00 PM", "03:30 PM"),
        ("03:30 PM", "04:00 PM"),
    ],
    "DOC007": [  # Dr. Vivek Singh (Cardiologist) - Late Evening
        ("04:30 PM", "05:00 PM"),
        ("05:00 PM", "05:30 PM"),
        ("05:30 PM", "06:00 PM"),
        ("06:00 PM", "06:30 PM"),
        ("06:30 PM", "07:00 PM"),
    ],
    "DOC008": [  # Dr. Priya Gupta (Gynecologist) - Late Morning
        ("10:30 AM", "11:00 AM"),
        ("11:00 AM", "11:30 AM"),
        ("11:30 AM", "12:00 PM"),
        ("12:00 PM", "12:30 PM"),
        ("12:30 PM", "01:00 PM"),
    ],
}

DEFAULT_TIMINGS = [
    ("10:00 AM", "10:30 AM"),
    ("11:00 AM", "11:30 AM"),
    ("12:00 PM", "12:30 PM"),
    ("04:00 PM", "04:30 PM"),
    ("05:00 PM", "05:30 PM"),
]


def seed_slots(
    tenant_id: str = "default",
    start_date: date = date(2026, 10, 29),
    num_days: int = 33,
) -> dict:
    dates = [start_date + timedelta(days=i) for i in range(num_days)]

    factory = get_session_factory()
    inserted_count = 0
    skipped_count = 0

    with factory() as session:
        # Ensure clinic is named XYZ Clinic
        clinic = session.get(Clinic, tenant_id)
        if clinic:
            clinic.name = "XYZ Clinic"
            clinic.is_active = True
        else:
            clinic = Clinic(
                id=tenant_id,
                name="XYZ Clinic",
                phone="6200126662",
                is_active=True,
            )
            session.add(clinic)

        doctors = session.execute(
            select(Doctor).where(Doctor.tenant_id == tenant_id)
        ).scalars().all()

        # Ensure all doctors in tenant are Active for testing
        for d in doctors:
            if d.status != "Active":
                d.status = "Active"

        doc_map = {d.doctor_id: d for d in doctors}
        logger.info("Found %d doctors for tenant '%s'", len(doc_map), tenant_id)

        # Loop through all doctors in the tenant
        for d_code, doc in doc_map.items():
            timings = DOCTOR_SCHEDULES.get(d_code, DEFAULT_TIMINGS)

            for target_date in dates:
                d_str = target_date.isoformat()
                clean_date = d_str.replace("-", "")

                for seq, (s_time, e_time) in enumerate(timings, 1):
                    # Check if slot already exists
                    existing = session.execute(
                        select(AppointmentSlot).where(
                            AppointmentSlot.tenant_id == tenant_id,
                            AppointmentSlot.doctor_id == doc.id,
                            AppointmentSlot.date == d_str,
                            AppointmentSlot.start_time == s_time,
                        )
                    ).scalars().first()

                    if existing:
                        skipped_count += 1
                        continue

                    slot_id_str = f"SLT-{d_code}-{clean_date}-{seq:02d}"
                    slot = AppointmentSlot(
                        id=uuid4().hex,
                        tenant_id=tenant_id,
                        slot_id=slot_id_str,
                        doctor_id=doc.id,
                        date=d_str,
                        start_time=s_time,
                        end_time=e_time,
                        status="available",
                        created_at=datetime.now(timezone.utc),
                        updated_at=datetime.now(timezone.utc),
                    )
                    session.add(slot)
                    inserted_count += 1

        session.commit()

    logger.info("Slot seeding complete: %d inserted, %d skipped", inserted_count, skipped_count)
    return {
        "inserted": inserted_count,
        "skipped": skipped_count,
        "days": num_days,
        "start_date": str(start_date),
        "end_date": str(dates[-1]),
        "doctors_count": len(doc_map),
    }


if __name__ == "__main__":
    result = seed_slots()
    print("Seed result:", result)
