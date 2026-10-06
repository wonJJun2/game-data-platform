from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
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

class SteamNews(Base):
    __tablename__ = "steam_news"

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
    )

    game_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("games.game_id"),
        nullable=False,
    )

    steam_gid: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    title: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    url: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    is_external_url: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
    )

    author: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    contents: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    feed_label: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    feed_name: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    feed_type: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    published_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    tags: Mapped[list | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "game_id",
            "steam_gid",
            name="uq_steam_news_game_gid",
        ),
    )

Index(
    "idx_steam_news_game_published_at",
    SteamNews.game_id,
    SteamNews.published_at.desc(),
)