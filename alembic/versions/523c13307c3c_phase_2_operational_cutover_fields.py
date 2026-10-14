"""phase_2_operational_cutover_fields

Revision ID: 523c13307c3c
Revises: 7d231a392105
Create Date: 2026-10-13 20:49:43.846692

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '523c13307c3c'
down_revision: Union[str, Sequence[str], None] = '7d231a392105'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema to support full operational cutover."""
    # 1. Add status to patients table (supports patient deactivation & lifecycle)
    op.add_column(
        "patients",
        sa.Column("status", sa.String(length=50), server_default="Active", nullable=False),
    )
    op.create_index("ix_patients_status", "patients", ["status"])

    # 2. Add booked_patient_id and booked_token_no to appointment_slots
    op.add_column(
        "appointment_slots",
        sa.Column("booked_patient_id", sa.String(length=50), nullable=True),
    )
    op.create_index(
        "ix_appointment_slots_booked_patient_id",
        "appointment_slots",
        ["booked_patient_id"],
    )

    op.add_column(
        "appointment_slots",
        sa.Column("booked_token_no", sa.String(length=50), nullable=True),
    )
    op.create_index(
        "ix_appointment_slots_booked_token_no",
        "appointment_slots",
        ["booked_token_no"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_appointment_slots_booked_token_no", table_name="appointment_slots")
    op.drop_column("appointment_slots", "booked_token_no")
    op.drop_index("ix_appointment_slots_booked_patient_id", table_name="appointment_slots")
    op.drop_column("appointment_slots", "booked_patient_id")
    op.drop_index("ix_patients_status", table_name="patients")
    op.drop_column("patients", "status")
