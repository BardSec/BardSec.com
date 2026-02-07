"""Initial schema for Student Data Risk Mapper.

Revision ID: 001
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum types
    user_role_enum = postgresql.ENUM('user', 'admin', 'auditor', name='userrole', create_type=False)
    user_role_enum.create(op.get_bind(), checkfirst=True)

    purpose_category_enum = postgresql.ENUM(
        'Instruction', 'Assessment', 'Communication', 'Operations', 'Other',
        name='purposecategory', create_type=False
    )
    purpose_category_enum.create(op.get_bind(), checkfirst=True)

    risk_tier_enum = postgresql.ENUM('Low', 'Moderate', 'High', 'Critical', name='risktier', create_type=False)
    risk_tier_enum.create(op.get_bind(), checkfirst=True)

    audit_action_enum = postgresql.ENUM(
        'system.create', 'system.update', 'system.delete',
        'assessment.create', 'export.pdf', 'export.csv',
        'user.login', 'user.logout',
        name='auditaction', create_type=False
    )
    audit_action_enum.create(op.get_bind(), checkfirst=True)

    # Create users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('entra_oid', sa.String(36), nullable=False, unique=True, index=True),
        sa.Column('email', sa.String(255), nullable=False, index=True),
        sa.Column('display_name', sa.String(255), nullable=False),
        sa.Column('role', user_role_enum, nullable=False, server_default='user'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('last_login', sa.DateTime(), nullable=True),
    )

    # Create systems table
    op.create_table(
        'systems',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False, index=True),
        sa.Column('vendor', sa.String(255), nullable=True),
        sa.Column('owner_department', sa.String(255), nullable=True),
        sa.Column('owner_contact', sa.String(255), nullable=True),
        sa.Column('purpose_category', purpose_category_enum, nullable=False, server_default='Other'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_by_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # Create risk_assessments table
    op.create_table(
        'risk_assessments',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('system_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('systems.id', ondelete='CASCADE'), nullable=False),
        sa.Column('assessed_by_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id'), nullable=False),
        sa.Column('assessed_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('answers_json', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('score_total', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('score_breakdown_json', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('reason_codes_json', postgresql.JSONB(), nullable=False, server_default='[]'),
        sa.Column('risk_tier', risk_tier_enum, nullable=False, server_default='Low'),
    )
    op.create_index('ix_risk_assessments_system_id', 'risk_assessments', ['system_id'])

    # Create audit_logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id'), nullable=True),
        sa.Column('action', audit_action_enum, nullable=False),
        sa.Column('target_type', sa.String(50), nullable=True),
        sa.Column('target_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False, server_default=sa.func.now(), index=True),
        sa.Column('metadata_json', postgresql.JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table('audit_logs')
    op.drop_table('risk_assessments')
    op.drop_table('systems')
    op.drop_table('users')

    # Drop enum types
    op.execute('DROP TYPE IF EXISTS auditaction')
    op.execute('DROP TYPE IF EXISTS risktier')
    op.execute('DROP TYPE IF EXISTS purposecategory')
    op.execute('DROP TYPE IF EXISTS userrole')
