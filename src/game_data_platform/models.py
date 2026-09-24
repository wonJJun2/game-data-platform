from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

class Game(Base):
    __tablename__ = "games"

    game_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
    )

    steam_app_id: Mapped[int] = mapped_column(
        Integer,
        unique=True,
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    genre: Mapped[str | None] = mapped_column(
    Text,
    nullable=True,
)

class PlayerCount(Base):
    __tablename__ = "player_counts"

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
    )

    game_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("games.game_id"),
        nullable=False,
    )

    player_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

Index(
    "idx_player_counts_game_collected_at",
    PlayerCount.game_id,
    PlayerCount.collected_at.desc(),
)