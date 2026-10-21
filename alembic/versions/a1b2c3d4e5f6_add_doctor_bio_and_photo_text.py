"""add_doctor_bio_and_photo_text

Revision ID: a1b2c3d4e5f6
Revises: 9c4d5e6f7a8b
Create Date: 2026-10-21 13:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '9c4d5e6f7a8b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add doctor bio column for clinician profiles & alter photo to Text
    with op.batch_alter_table('doctors', schema=None) as batch_op:
        batch_op.add_column(sa.Column('bio', sa.Text(), nullable=True))
        batch_op.alter_column('photo', existing_type=sa.String(length=500), type_=sa.Text(), nullable=True)

    # 2. Ensure clinic logo column accommodates long URLs or base64 data URIs
    with op.batch_alter_table('clinics', schema=None) as batch_op:
        batch_op.alter_column('logo', existing_type=sa.String(length=500), type_=sa.Text(), nullable=True)


def downgrade() -> None:
    with op.batch_alter_table('clinics', schema=None) as batch_op:
        batch_op.alter_column('logo', existing_type=sa.Text(), type_=sa.String(length=500), nullable=True)

    with op.batch_alter_table('doctors', schema=None) as batch_op:
        batch_op.alter_column('photo', existing_type=sa.Text(), type_=sa.String(length=500), nullable=True)
        batch_op.drop_column('bio')
