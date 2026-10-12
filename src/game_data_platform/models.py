from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
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

class SteamNewsPatchDetection(Base):
    __tablename__ = "steam_news_patch_detection"

    news_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("steam_news.id", ondelete="CASCADE"),
        primary_key=True,
    )

    is_patch: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
    )

    detection_reason: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    detector_version: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

class OverwatchPatchNote(Base):
    __tablename__ = "overwatch_patch_notes"

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )

    source_patch_id: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    locale: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
    )

    source_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    label_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    title: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    content_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    content_html: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    detected_language: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
    )

    source_url: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        UniqueConstraint(
            "source_patch_id",
            "locale",
            name="uq_overwatch_patch_source_locale",
        ),
    )

class GamePatch(Base):
    __tablename__ = "game_patches"

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )

    game_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("games.game_id", ondelete="CASCADE"),
        nullable=False,
    )

    source_provider: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    source_key: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    source_locale: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
    )

    source_language: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
    )

    source_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    title: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    content_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    source_url: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        UniqueConstraint(
            "source_provider",
            "source_key",
            name="uq_game_patches_source",
        ),
        Index(
            "idx_game_patches_game_date",
            "game_id",
            "source_date",
        ),
    )

class GamePatchProcessing(Base):
    __tablename__ = "game_patch_processing"

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )

    patch_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "game_patches.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    target_language: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
    )

    source_content_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    translation_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    translated_title: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    translated_content: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    translation_provider: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )

    translation_model: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    translation_prompt_version: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    translated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    translation_error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    summary_error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    summary_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    summary_provider: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )

    summary_model: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    summary_prompt_version: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    summarized_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        UniqueConstraint(
            "patch_id",
            "target_language",
            name="uq_game_patch_processing_target",
        ),
    )