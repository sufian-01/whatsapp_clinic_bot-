"""add_contacts_and_family_booking

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-10-27 23:05:00.000000

Additive, backward-compatible migration:
1. Creates contacts table scoped by tenant_id and phone.
2. Adds contact_id, relationship_type, and date_of_birth to patients.
3. Idempotently backfills contacts from existing patients and links contact_id.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create contacts table
    op.create_table(
        'contacts',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('phone', sa.String(length=50), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['clinics.id'], name='fk_contacts_tenant_id_clinics', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name='pk_contacts'),
        sa.UniqueConstraint('tenant_id', 'phone', name='uq_contact_tenant_phone')
    )
    op.create_index('ix_contact_tenant_phone', 'contacts', ['tenant_id', 'phone'], unique=False)
    op.create_index('ix_contacts_tenant_id', 'contacts', ['tenant_id'], unique=False)
    op.create_index('ix_contacts_phone', 'contacts', ['phone'], unique=False)

    # 2. Add nullable columns to patients
    with op.batch_alter_table('patients', schema=None) as batch_op:
        batch_op.add_column(sa.Column('contact_id', sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column('relationship_type', sa.String(length=50), nullable=True, server_default='Self'))
        batch_op.add_column(sa.Column('date_of_birth', sa.String(length=20), nullable=True))
        batch_op.create_foreign_key(
            'fk_patients_contact_id_contacts',
            'contacts',
            ['contact_id'],
            ['id'],
            ondelete='SET NULL'
        )
        batch_op.create_index('ix_patients_contact_id', ['contact_id'], unique=False)

    # 3. Idempotent Backfill: seed contacts from existing patients
    conn = op.get_bind()
    # Check dialect to use appropriate UUID function
    dialect_name = conn.dialect.name
    if dialect_name == 'postgresql':
        conn.execute(sa.text("""
            INSERT INTO contacts (id, tenant_id, phone, full_name, created_at, updated_at)
            SELECT
                gen_random_uuid()::text as id,
                p.tenant_id,
                p.phone,
                MIN(p.name) as full_name,
                NOW(),
                NOW()
            FROM patients p
            WHERE p.tenant_id IS NOT NULL AND p.phone IS NOT NULL AND p.phone != ''
            GROUP BY p.tenant_id, p.phone
            ON CONFLICT (tenant_id, phone) DO NOTHING;
        """))
        conn.execute(sa.text("""
            UPDATE patients p
            SET contact_id = c.id
            FROM contacts c
            WHERE p.tenant_id = c.tenant_id AND p.phone = c.phone AND p.contact_id IS NULL;
        """))


def downgrade() -> None:
    # 1. Drop foreign key, index, and columns from patients
    with op.batch_alter_table('patients', schema=None) as batch_op:
        batch_op.drop_constraint('fk_patients_contact_id_contacts', type_='foreignkey')
        batch_op.drop_index('ix_patients_contact_id')
        batch_op.drop_column('date_of_birth')
        batch_op.drop_column('relationship_type')
        batch_op.drop_column('contact_id')

    # 2. Drop contacts table
    op.drop_index('ix_contacts_phone', table_name='contacts')
    op.drop_index('ix_contacts_tenant_id', table_name='contacts')
    op.drop_index('ix_contact_tenant_phone', table_name='contacts')
    op.drop_table('contacts')
