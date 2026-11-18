"""add delivery attempt count to discord patch outbox

Revision ID: 76b857e8d48e
Revises: 9546715a65bc
Create Date: 2026-11-18 19:33:46.825220

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '76b857e8d48e'
down_revision: Union[str, Sequence[str], None] = '9546715a65bc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "discord_patch_notification_outbox",
        sa.Column(
            "delivery_attempt_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )


def downgrade() -> None:
    op.drop_column(
        "discord_patch_notification_outbox",
        "delivery_attempt_count",
    )