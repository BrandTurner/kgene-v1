"""Initial migration - create organisms and genes tables

Revision ID: 001
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create organisms table
    op.create_table(
        'organisms',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('job_error', sa.String(length=1000), nullable=True),
        sa.Column('job_id', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_organisms_id'), 'organisms', ['id'], unique=False)
    op.create_index(op.f('ix_organisms_code'), 'organisms', ['code'], unique=True)

    # Create genes table
    op.create_table(
        'genes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organism_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.String(length=1000), nullable=True),
        sa.Column('ortholog_name', sa.String(), nullable=True),
        sa.Column('ortholog_description', sa.String(length=1000), nullable=True),
        sa.Column('ortholog_species', sa.String(length=1000), nullable=True),
        sa.Column('ortholog_length', sa.Integer(), nullable=True),
        sa.Column('ortholog_sw_score', sa.Integer(), nullable=True),
        sa.Column('ortholog_identity', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['organism_id'], ['organisms.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_genes_id'), 'genes', ['id'], unique=False)
    op.create_index(op.f('ix_genes_name'), 'genes', ['name'], unique=False)
    op.create_index('idx_organism_ortholog', 'genes', ['organism_id', 'ortholog_name'], unique=False)


def downgrade() -> None:
    op.drop_index('idx_organism_ortholog', table_name='genes')
    op.drop_index(op.f('ix_genes_name'), table_name='genes')
    op.drop_index(op.f('ix_genes_id'), table_name='genes')
    op.drop_table('genes')
    op.drop_index(op.f('ix_organisms_code'), table_name='organisms')
    op.drop_index(op.f('ix_organisms_id'), table_name='organisms')
    op.drop_table('organisms')
