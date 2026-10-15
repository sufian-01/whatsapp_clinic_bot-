"""saas_multi_tenant_features

Revision ID: 8b3c4d5e6f7a
Revises: fc0c663dee06
Create Date: 2026-10-14 23:55:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8b3c4d5e6f7a'
down_revision: Union[str, Sequence[str], None] = 'fc0c663dee06'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('clinics', sa.Column('whatsapp_phone_number', sa.String(length=50), nullable=True))
    op.add_column('clinics', sa.Column('whatsapp_phone_number_id', sa.String(length=100), nullable=True))
    op.add_column('clinics', sa.Column('whatsapp_waba_id', sa.String(length=100), nullable=True))
    op.add_column('clinics', sa.Column('subscription_plan', sa.String(length=50), server_default='STARTER', nullable=False))
    op.add_column('clinics', sa.Column('subscription_status', sa.String(length=50), server_default='ACTIVE', nullable=False))
    op.add_column('clinics', sa.Column('subscription_expires_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('clinics', sa.Column('feature_flags', sa.Text(), server_default='{}', nullable=True))
    op.create_index('ix_clinics_whatsapp_phone_number_id', 'clinics', ['whatsapp_phone_number_id'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_clinics_whatsapp_phone_number_id', table_name='clinics')
    op.drop_column('clinics', 'feature_flags')
    op.drop_column('clinics', 'subscription_expires_at')
    op.drop_column('clinics', 'subscription_status')
    op.drop_column('clinics', 'subscription_plan')
    op.drop_column('clinics', 'whatsapp_waba_id')
    op.drop_column('clinics', 'whatsapp_phone_number_id')
    op.drop_column('clinics', 'whatsapp_phone_number')

