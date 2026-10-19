"""razorpay_and_doctor_profile_branding

Revision ID: 9c4d5e6f7a8b
Revises: 8b3c4d5e6f7a
Create Date: 2026-10-19 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9c4d5e6f7a8b'
down_revision: Union[str, Sequence[str], None] = '8b3c4d5e6f7a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Clinic Razorpay gateway credentials
    op.add_column('clinics', sa.Column('razorpay_key_id', sa.String(length=100), nullable=True))
    op.add_column('clinics', sa.Column('razorpay_key_secret', sa.String(length=100), nullable=True))

    # Doctor photo & digital signature for prescription branding
    op.add_column('doctors', sa.Column('photo', sa.String(length=500), nullable=True))
    op.add_column('doctors', sa.Column('signature', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('doctors', 'signature')
    op.drop_column('doctors', 'photo')
    op.drop_column('clinics', 'razorpay_key_secret')
    op.drop_column('clinics', 'razorpay_key_id')

