"""empty message

Revision ID: c9179b3f8689
Revises: 6d7beb3315a4
Create Date: 2016-03-21 08:44:11.065750

"""

# revision identifiers, used by Alembic.
revision = 'c9179b3f8689'
down_revision = '6d7beb3315a4'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('comments', 'assetID',
               existing_type=sa.INTEGER(),
               type_=sa.BIGINT(),
               existing_nullable=True)
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('comments', 'assetID',
               existing_type=sa.BIGINT(),
               type_=sa.INTEGER(),
               existing_nullable=True)
    ### end Alembic commands ###
