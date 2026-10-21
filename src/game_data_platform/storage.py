from datetime import datetime, timezone
from psycopg.rows import dict_row

from game_data_platform.database import get_connection

from sqlalchemy import asc, desc, select

from game_data_platform.database import SessionLocal
from game_data_platform.models import Game, PlayerCount

from psycopg.types.json import Jsonb

def save_player_count(data: dict) -> None:
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT game_id
                FROM games
                WHERE steam_app_id = %s
                """,
                (data["app_id"],),
            )

            row = cursor.fetchone()

            if row is None:
                raise ValueError(
                    f"등록되지 않은 Steam app_id입니다: {data['app_id']}"
                )

            game_id = row[0]

            cursor.execute(
                """
                INSERT INTO player_counts (
                    game_id,
                    player_count,
                    collected_at
                )
                VALUES (%s, %s, %s)
                """,
                (
                    game_id,
                    data["player_count"],
                    data["collected_at"],
                ),
            )

def get_games():
    statement = (
        select(Game)
        .order_by(Game.game_id)
    )

    with SessionLocal() as session:
        games = session.scalars(statement).all()

        return [
            {
                "game_id": game.game_id,
                "steam_app_id": game.steam_app_id,
                "name": game.name,
                "created_at": game.created_at,
                "header_image_url": game.header_image_url,
            }
            for game in games
        ]

def get_game(game_id: int):
    with SessionLocal() as session:
        game = session.get(Game, game_id)

        if game is None:
            return None

        return {
            "game_id": game.game_id,
            "steam_app_id": game.steam_app_id,
            "name": game.name,
            "created_at": game.created_at,
            "header_image_url": game.header_image_url,
        }

def get_player_counts(
    game_id: int,
    limit: int = 100,
    order: str = "desc",
):
    order_by = (
        desc(PlayerCount.collected_at)
        if order == "desc"
        else asc(PlayerCount.collected_at)
    )

    statement = (
        select(PlayerCount)
        .where(PlayerCount.game_id == game_id)
        .order_by(order_by)
        .limit(limit)
    )

    with SessionLocal() as session:
        player_counts = session.scalars(statement).all()

        return [
            {
                "player_count": item.player_count,
                "collected_at": item.collected_at,
            }
            for item in player_counts
        ]

def get_latest_player_count(game_id: int):
    statement = (
        select(PlayerCount)
        .where(PlayerCount.game_id == game_id)
        .order_by(desc(PlayerCount.collected_at))
        .limit(1)
    )

    with SessionLocal() as session:
        player_count = session.scalars(statement).first()

        if player_count is None:
            return None

        return {
            "game_id": player_count.game_id,
            "player_count": player_count.player_count,
            "collected_at": player_count.collected_at,
        }

def save_steam_news(data: dict) -> bool:
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT game_id
                FROM games
                WHERE steam_app_id = %s
                """,
                (data["app_id"],),
            )

            row = cursor.fetchone()

            if row is None:
                raise ValueError(
                    f"등록되지 않은 Steam app_id입니다: {data['app_id']}"
                )

            game_id = row[0]

            cursor.execute(
                """
                INSERT INTO steam_news (
                    game_id,
                    steam_gid,
                    title,
                    url,
                    is_external_url,
                    author,
                    contents,
                    feed_label,
                    feed_name,
                    feed_type,
                    published_at,
                    tags,
                    collected_at
                )
                VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s,
                    %s, %s, %s
                )
                ON CONFLICT (game_id, steam_gid)
                DO NOTHING
                RETURNING id
                """,
                (
                    game_id,
                    data["steam_gid"],
                    data["title"],
                    data["url"],
                    data["is_external_url"],
                    data.get("author"),
                    data.get("contents"),
                    data.get("feed_label"),
                    data.get("feed_name"),
                    data.get("feed_type"),
                    data["published_at"],
                    Jsonb(data.get("tags", [])),
                    data["collected_at"],
                ),
            )

            inserted = cursor.fetchone()

            return inserted is not None

def get_undetected_steam_news(
    detector_version: str,
) -> list[dict]:
    query = """
        SELECT
            sn.id,
            sn.title,
            sn.contents,
            sn.tags,
            sn.feed_name
        FROM steam_news sn
        LEFT JOIN steam_news_patch_detection pd
            ON pd.news_id = sn.id
        WHERE
            pd.news_id IS NULL
            OR pd.detector_version <> %s
        ORDER BY sn.published_at ASC
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                query,
                (detector_version,),
            )
            rows = cur.fetchall()

    return [
        {
            "id": row[0],
            "title": row[1],
            "contents": row[2],
            "tags": row[3],
            "feed_name": row[4],
        }
        for row in rows
    ]

def save_patch_detection(
    news_id: int,
    is_patch: bool,
    detection_reason: str,
    detector_version: str,
) -> None:
    query = """
        INSERT INTO steam_news_patch_detection (
            news_id,
            is_patch,
            detection_reason,
            detector_version
        )
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (news_id)
        DO UPDATE SET
            is_patch = EXCLUDED.is_patch,
            detection_reason = EXCLUDED.detection_reason,
            detector_version = EXCLUDED.detector_version,
            detected_at = NOW()
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                query,
                (
                    news_id,
                    is_patch,
                    detection_reason,
                    detector_version,
                ),
            )

        conn.commit()

def save_overwatch_patch_note(
    data: dict,
) -> bool:
    query = """
        INSERT INTO overwatch_patch_notes (
            source_patch_id,
            locale,
            source_date,
            label_text,
            title,
            content_text,
            content_html,
            detected_language,
            source_url
        )
        VALUES (
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s
        )
        ON CONFLICT (
            source_patch_id,
            locale
        )
        DO UPDATE SET
            source_date = EXCLUDED.source_date,
            label_text = EXCLUDED.label_text,
            title = EXCLUDED.title,
            content_text = EXCLUDED.content_text,
            content_html = EXCLUDED.content_html,
            detected_language = EXCLUDED.detected_language,
            source_url = EXCLUDED.source_url,
            collected_at = NOW()
        WHERE
            overwatch_patch_notes.source_date
                IS DISTINCT FROM EXCLUDED.source_date
            OR overwatch_patch_notes.label_text
                IS DISTINCT FROM EXCLUDED.label_text
            OR overwatch_patch_notes.title
                IS DISTINCT FROM EXCLUDED.title
            OR overwatch_patch_notes.content_text
                IS DISTINCT FROM EXCLUDED.content_text
            OR overwatch_patch_notes.content_html
                IS DISTINCT FROM EXCLUDED.content_html
            OR overwatch_patch_notes.detected_language
                IS DISTINCT FROM EXCLUDED.detected_language
            OR overwatch_patch_notes.source_url
                IS DISTINCT FROM EXCLUDED.source_url
        RETURNING id
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                query,
                (
                    data["source_patch_id"],
                    data["locale"],
                    data["source_date"],
                    data["label_text"],
                    data["title"],
                    data["content_text"],
                    data["content_html"],
                    data["detected_language"],
                    data["source_url"],
                ),
            )

            row = cur.fetchone()

        conn.commit()

    return row is not None

def save_pubg_patch_note(
    data: dict,
) -> bool:
    query = """
        INSERT INTO pubg_patch_notes (
            source_patch_id,
            locale,
            source_date,
            title,
            content_text,
            content_html,
            detected_language,
            source_url
        )
        VALUES (
            %s, %s, %s, %s,
            %s, %s, %s, %s
        )
        ON CONFLICT (
            source_patch_id,
            locale
        )
        DO UPDATE SET
            source_date = EXCLUDED.source_date,
            title = EXCLUDED.title,
            content_text = EXCLUDED.content_text,
            content_html = EXCLUDED.content_html,
            detected_language = EXCLUDED.detected_language,
            source_url = EXCLUDED.source_url,
            collected_at = NOW()
        WHERE
            pubg_patch_notes.source_date
                IS DISTINCT FROM EXCLUDED.source_date
            OR pubg_patch_notes.title
                IS DISTINCT FROM EXCLUDED.title
            OR pubg_patch_notes.content_text
                IS DISTINCT FROM EXCLUDED.content_text
            OR pubg_patch_notes.content_html
                IS DISTINCT FROM EXCLUDED.content_html
            OR pubg_patch_notes.detected_language
                IS DISTINCT FROM EXCLUDED.detected_language
            OR pubg_patch_notes.source_url
                IS DISTINCT FROM EXCLUDED.source_url
        RETURNING id
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                query,
                (
                    data["source_patch_id"],
                    data["locale"],
                    data["source_date"],
                    data["title"],
                    data["content_text"],
                    data["content_html"],
                    data["detected_language"],
                    data["source_url"],
                ),
            )

            row = cur.fetchone()

        conn.commit()

    return row is not None

def save_game_patch(
    data: dict,
) -> bool:
    query = """
        INSERT INTO game_patches (
            game_id,
            source_provider,
            source_key,
            source_locale,
            source_language,
            source_date,
            published_at,
            title,
            content_text,
            source_url
        )
        VALUES (
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s
        )
        ON CONFLICT (
            source_provider,
            source_key
        )
        DO UPDATE SET
            game_id = EXCLUDED.game_id,
            source_locale = EXCLUDED.source_locale,
            source_language = EXCLUDED.source_language,
            source_date = EXCLUDED.source_date,
            published_at = EXCLUDED.published_at,
            title = EXCLUDED.title,
            content_text = EXCLUDED.content_text,
            source_url = EXCLUDED.source_url,
            synced_at = NOW()
                    WHERE
            game_patches.game_id
                IS DISTINCT FROM EXCLUDED.game_id
            OR game_patches.source_locale
                IS DISTINCT FROM EXCLUDED.source_locale
            OR game_patches.source_language
                IS DISTINCT FROM EXCLUDED.source_language
            OR game_patches.source_date
                IS DISTINCT FROM EXCLUDED.source_date
            OR game_patches.published_at
                IS DISTINCT FROM EXCLUDED.published_at
            OR game_patches.title
                IS DISTINCT FROM EXCLUDED.title
            OR game_patches.content_text
                IS DISTINCT FROM EXCLUDED.content_text
            OR game_patches.source_url
                IS DISTINCT FROM EXCLUDED.source_url
        RETURNING id
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                query,
                (
                    data["game_id"],
                    data["source_provider"],
                    data["source_key"],
                    data.get("source_locale"),
                    data["source_language"],
                    data.get("source_date"),
                    data.get("published_at"),
                    data["title"],
                    data["content_text"],
                    data["source_url"],
                ),
            )

            row = cur.fetchone()

        conn.commit()

    return row is not None

def get_detected_steam_patches(
    detector_version: str,
) -> list[dict]:
    query = """
        SELECT
            sn.id,
            sn.game_id,
            g.steam_app_id,
            sn.steam_gid,
            sn.title,
            sn.contents,
            sn.url,
            sn.is_external_url,
            sn.published_at
        FROM steam_news sn
        JOIN steam_news_patch_detection pd
            ON pd.news_id = sn.id
        JOIN games g
            ON g.game_id = sn.game_id
        WHERE pd.is_patch = true
            AND pd.detector_version = %s
        ORDER BY sn.published_at ASC
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                query,
                (detector_version,),
            )
            rows = cur.fetchall()

    return [
        {
            "news_id": row[0],
            "game_id": row[1],
            "steam_app_id": row[2],
            "steam_gid": row[3],
            "title": row[4],
            "contents": row[5],
            "url": row[6],
            "is_external_url": row[7],
            "published_at": row[8],
        }
        for row in rows
    ]

def get_canonical_overwatch_patches() -> list[dict]:
    query = """
        SELECT DISTINCT ON (source_patch_id)
            source_patch_id,
            locale,
            source_date,
            title,
            content_text,
            detected_language,
            source_url
        FROM overwatch_patch_notes
        ORDER BY
            source_patch_id,
            CASE
                WHEN locale = 'ko-KR'
                     AND detected_language = 'ko'
                THEN 0

                WHEN locale = 'en-US'
                THEN 1

                ELSE 2
            END
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            rows = cur.fetchall()

    return [
        {
            "source_patch_id": row[0],
            "locale": row[1],
            "source_date": row[2],
            "title": row[3],
            "content_text": row[4],
            "detected_language": row[5],
            "source_url": row[6],
        }
        for row in rows
    ]

def get_canonical_pubg_patches() -> list[dict]:
    query = """
        SELECT DISTINCT ON (source_patch_id)
            source_patch_id,
            locale,
            source_date,
            title,
            content_text,
            detected_language,
            source_url
        FROM pubg_patch_notes
        ORDER BY
            source_patch_id,
            CASE
                WHEN locale = 'ko-KR'
                     AND detected_language = 'ko'
                THEN 0

                ELSE 1
            END
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            rows = cur.fetchall()

    return [
        {
            "source_patch_id": row[0],
            "locale": row[1],
            "source_date": row[2],
            "title": row[3],
            "content_text": row[4],
            "detected_language": row[5],
            "source_url": row[6],
        }
        for row in rows
    ]

def get_game_by_steam_app_id(
    steam_app_id: int,
) -> dict | None:
    query = """
        SELECT
            game_id,
            steam_app_id,
            name
        FROM games
        WHERE steam_app_id = %s
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                query,
                (steam_app_id,),
            )
            row = cur.fetchone()

    if row is None:
        return None

    return {
        "game_id": row[0],
        "steam_app_id": row[1],
        "name": row[2],
    }

def create_game(
    *,
    steam_app_id: int,
    name: str,
    header_image_url: str | None,
) -> dict:
    game = Game(
        steam_app_id=steam_app_id,
        name=name,
        created_at=datetime.now(
            timezone.utc
        ),
        genre=None,
        header_image_url=header_image_url,
    )

    with SessionLocal() as session:
        session.add(game)
        session.commit()
        session.refresh(game)

        return {
            "game_id": game.game_id,
            "steam_app_id": game.steam_app_id,
            "name": game.name,
            "created_at": game.created_at,
            "header_image_url":
                game.header_image_url,
        }

def save_game_price(
    data: dict,
) -> dict:
    game = get_game_by_steam_app_id(
        data["steam_app_id"]
    )

    if game is None:
        raise ValueError(
            "Game is not registered: "
            f"steam_app_id={data['steam_app_id']}"
        )

    game_id = game["game_id"]

    update_game_image_query = """
        UPDATE games
        SET header_image_url = %s
        WHERE game_id = %s
        AND header_image_url
            IS DISTINCT FROM %s
    """

    select_query = """
        SELECT
            id,
            price_status,
            is_free,
            currency,
            initial_price,
            final_price,
            discount_percent
        FROM game_price_current
        WHERE game_id = %s
          AND provider = %s
          AND country_code = %s
        FOR UPDATE
    """

    insert_current_query = """
        INSERT INTO game_price_current (
            game_id,
            provider,
            country_code,
            price_status,
            is_free,
            currency,
            initial_price,
            final_price,
            discount_percent,
            checked_at,
            changed_at
        )
        VALUES (
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s,
            NOW(), NOW()
        )
        RETURNING id
    """

    update_current_query = """
        UPDATE game_price_current
        SET
            price_status = %s,
            is_free = %s,
            currency = %s,
            initial_price = %s,
            final_price = %s,
            discount_percent = %s,
            checked_at = NOW(),
            changed_at = NOW()
        WHERE id = %s
    """

    touch_current_query = """
        UPDATE game_price_current
        SET checked_at = NOW()
        WHERE id = %s
    """

    insert_history_query = """
        INSERT INTO game_price_history (
            game_id,
            provider,
            country_code,
            price_status,
            is_free,
            currency,
            initial_price,
            final_price,
            discount_percent,
            changed_at
        )
        VALUES (
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s,
            NOW()
        )
        RETURNING id
    """

    with get_connection() as conn:
        with conn.cursor() as cur:

            header_image_url = data.get(
                "header_image_url"
            )

            if header_image_url is not None:
                cur.execute(
                    update_game_image_query,
                    (
                        header_image_url,
                        game_id,
                        header_image_url,
                    ),
                )

            cur.execute(
                select_query,
                (
                    game_id,
                    data["provider"],
                    data["country_code"],
                ),
            )

            current = cur.fetchone()

            if current is None:
                cur.execute(
                    insert_current_query,
                    (
                        game_id,
                        data["provider"],
                        data["country_code"],
                        data["price_status"],
                        data["is_free"],
                        data["currency"],
                        data["initial_price"],
                        data["final_price"],
                        data["discount_percent"],
                    ),
                )

                current_id = cur.fetchone()[0]

                cur.execute(
                    insert_history_query,
                    (
                        game_id,
                        data["provider"],
                        data["country_code"],
                        data["price_status"],
                        data["is_free"],
                        data["currency"],
                        data["initial_price"],
                        data["final_price"],
                        data["discount_percent"],
                    ),
                )

                history_id = cur.fetchone()[0]

                conn.commit()

                return {
                    "game_id": game_id,
                    "current_id": current_id,
                    "history_id": history_id,
                    "changed": True,
                    "action": "created",
                }

            (
                current_id,
                current_price_status,
                current_is_free,
                current_currency,
                current_initial_price,
                current_final_price,
                current_discount_percent,
            ) = current

            has_changed = any(
                (
                    current_price_status
                    != data["price_status"],

                    current_is_free
                    != data["is_free"],

                    current_currency
                    != data["currency"],

                    current_initial_price
                    != data["initial_price"],

                    current_final_price
                    != data["final_price"],

                    current_discount_percent
                    != data["discount_percent"],
                )
            )

            if not has_changed:
                cur.execute(
                    touch_current_query,
                    (current_id,),
                )

                conn.commit()

                return {
                    "game_id": game_id,
                    "current_id": current_id,
                    "history_id": None,
                    "changed": False,
                    "action": "checked",
                }

            cur.execute(
                update_current_query,
                (
                    data["price_status"],
                    data["is_free"],
                    data["currency"],
                    data["initial_price"],
                    data["final_price"],
                    data["discount_percent"],
                    current_id,
                ),
            )

            cur.execute(
                insert_history_query,
                (
                    game_id,
                    data["provider"],
                    data["country_code"],
                    data["price_status"],
                    data["is_free"],
                    data["currency"],
                    data["initial_price"],
                    data["final_price"],
                    data["discount_percent"],
                ),
            )

            history_id = cur.fetchone()[0]

        conn.commit()

    return {
        "game_id": game_id,
        "current_id": current_id,
        "history_id": history_id,
        "changed": True,
        "action": "changed",
    }

def get_current_game_price(
    game_id: int,
    provider: str = "steam",
    country_code: str = "KR",
) -> dict | None:
    query = """
        SELECT
            game_id,
            provider,
            country_code,
            price_status,
            is_free,
            currency,
            initial_price,
            final_price,
            discount_percent,
            checked_at,
            changed_at
        FROM game_price_current
        WHERE game_id = %s
          AND provider = %s
          AND country_code = %s
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                query,
                (
                    game_id,
                    provider,
                    country_code,
                ),
            )

            row = cur.fetchone()

    if row is None:
        return None

    return {
        "game_id": row[0],
        "provider": row[1],
        "country_code": row[2],
        "price_status": row[3],
        "is_free": row[4],
        "currency": row[5],
        "initial_price": row[6],
        "final_price": row[7],
        "discount_percent": row[8],
        "checked_at": row[9],
        "changed_at": row[10],
    }


def get_game_price_history(
    game_id: int,
    provider: str = "steam",
    country_code: str = "KR",
    limit: int = 100,
    order: str = "desc",
) -> list[dict]:
    if order not in (
        "asc",
        "desc",
    ):
        raise ValueError(
            "order must be 'asc' or 'desc'"
        )

    query = f"""
        SELECT
            game_id,
            provider,
            country_code,
            price_status,
            is_free,
            currency,
            initial_price,
            final_price,
            discount_percent,
            changed_at
        FROM game_price_history
        WHERE game_id = %s
          AND provider = %s
          AND country_code = %s
        ORDER BY changed_at {order.upper()}
        LIMIT %s
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                query,
                (
                    game_id,
                    provider,
                    country_code,
                    limit,
                ),
            )

            rows = cur.fetchall()

    return [
        {
            "game_id": row[0],
            "provider": row[1],
            "country_code": row[2],
            "price_status": row[3],
            "is_free": row[4],
            "currency": row[5],
            "initial_price": row[6],
            "final_price": row[7],
            "discount_percent": row[8],
            "changed_at": row[9],
        }
        for row in rows
    ]

def get_game_patches_for_processing(
    limit: int = 20,
    offset: int = 0,
) -> list[dict]:
    query = """
        SELECT
            gp.id,
            gp.game_id,
            g.name,
            gp.source_provider,
            gp.source_language,
            gp.title,
            gp.content_text,

            gpp.source_content_hash,

            gpp.translation_status,
            gpp.translated_title,
            gpp.translated_content,
            gpp.translation_provider,
            gpp.translation_model,
            gpp.translation_prompt_version,
            gpp.translation_error,

            gpp.summary_status,
            gpp.summary,
            gpp.summary_provider,
            gpp.summary_model,
            gpp.summary_prompt_version,
            gpp.summary_error

        FROM game_patches gp

        JOIN games g
            ON g.game_id = gp.game_id

        LEFT JOIN game_patch_processing gpp
            ON gpp.patch_id = gp.id
            AND gpp.target_language = 'ko'

        ORDER BY
            gp.source_date DESC NULLS LAST,
            gp.id DESC

        LIMIT %s
        OFFSET %s
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                query,
                (
                    limit,
                    offset,
                ),
            )
            rows = cur.fetchall()

    return [
        {
            "patch_id": row[0],
            "game_id": row[1],
            "game_name": row[2],
            "source_provider": row[3],
            "source_language": row[4],
            "title": row[5],
            "content_text": row[6],

            "source_content_hash": row[7],

            "translation_status": row[8],
            "translated_title": row[9],
            "translated_content": row[10],
            "translation_provider": row[11],
            "translation_model": row[12],
            "translation_prompt_version": row[13],
            "translation_error": row[14],

            "summary_status": row[15],
            "summary": row[16],
            "summary_provider": row[17],
            "summary_model": row[18],
            "summary_prompt_version": row[19],
            "summary_error": row[20],
        }
        for row in rows
    ]

def get_game_patch_for_processing(
    patch_id: int,
) -> dict | None:
    query = """
        SELECT
            gp.id,
            gp.game_id,
            g.name,
            gp.source_provider,
            gp.source_language,
            gp.title,
            gp.content_text,

            gpp.source_content_hash,

            gpp.translation_status,
            gpp.translated_title,
            gpp.translated_content,
            gpp.translation_provider,
            gpp.translation_model,
            gpp.translation_prompt_version,
            gpp.translation_error,

            gpp.summary_status,
            gpp.summary,
            gpp.summary_provider,
            gpp.summary_model,
            gpp.summary_prompt_version,
            gpp.summary_error

        FROM game_patches gp

        JOIN games g
            ON g.game_id = gp.game_id

        LEFT JOIN game_patch_processing gpp
            ON gpp.patch_id = gp.id
            AND gpp.target_language = 'ko'

        WHERE gp.id = %s
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                query,
                (patch_id,),
            )
            row = cur.fetchone()

    if row is None:
        return None

    return {
        "patch_id": row[0],
        "game_id": row[1],
        "game_name": row[2],
        "source_provider": row[3],
        "source_language": row[4],
        "title": row[5],
        "content_text": row[6],

        "source_content_hash": row[7],

        "translation_status": row[8],
        "translated_title": row[9],
        "translated_content": row[10],
        "translation_provider": row[11],
        "translation_model": row[12],
        "translation_prompt_version": row[13],
        "translation_error": row[14],

        "summary_status": row[15],
        "summary": row[16],
        "summary_provider": row[17],
        "summary_model": row[18],
        "summary_prompt_version": row[19],
        "summary_error": row[20],
    }

def ensure_game_patch_processing(
    patch_id: int,
    target_language: str,
    source_content_hash: str,
    translation_status: str,
) -> None:
    query = """
        INSERT INTO game_patch_processing (
            patch_id,
            target_language,
            source_content_hash,
            translation_status,
            summary_status
        )
        VALUES (
            %s,
            %s,
            %s,
            %s,
            'pending'
        )

        ON CONFLICT (
            patch_id,
            target_language
        )

        DO UPDATE SET
            source_content_hash =
                EXCLUDED.source_content_hash,

            translation_status =
                EXCLUDED.translation_status,

            translated_title = NULL,
            translated_content = NULL,
            translation_provider = NULL,
            translation_model = NULL,
            translation_prompt_version = NULL,
            translation_error = NULL,
            translated_at = NULL,

            summary_status = 'pending',
            summary = NULL,
            summary_provider = NULL,
            summary_model = NULL,
            summary_prompt_version = NULL,
            summary_error = NULL,
            summarized_at = NULL,

            updated_at = NOW()

        WHERE
            game_patch_processing.source_content_hash
            IS DISTINCT FROM
            EXCLUDED.source_content_hash
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                query,
                (
                    patch_id,
                    target_language,
                    source_content_hash,
                    translation_status,
                ),
            )

        conn.commit()

def save_patch_translation(
    patch_id: int,
    translated_title: str,
    translated_content: str,
    provider: str,
    model: str,
    prompt_version: str,
) -> None:
    query = """
        UPDATE game_patch_processing
        SET
            translation_status = 'completed',
            translated_title = %s,
            translated_content = %s,
            translation_provider = %s,
            translation_model = %s,
            translation_prompt_version = %s,
            translation_error = NULL,
            translated_at = NOW(),
            updated_at = NOW()
        WHERE
            patch_id = %s
            AND target_language = 'ko'
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                query,
                (
                    translated_title,
                    translated_content,
                    provider,
                    model,
                    prompt_version,
                    patch_id,
                ),
            )

        conn.commit()

def save_patch_summary(
    patch_id: int,
    summary: str,
    provider: str,
    model: str,
    prompt_version: str,
) -> None:
    query = """
        UPDATE game_patch_processing
        SET
            summary_status = 'completed',
            summary = %s,
            summary_provider = %s,
            summary_model = %s,
            summary_prompt_version = %s,
            summary_error = NULL,
            summarized_at = NOW(),
            updated_at = NOW()
        WHERE
            patch_id = %s
            AND target_language = 'ko'
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                query,
                (
                    summary,
                    provider,
                    model,
                    prompt_version,
                    patch_id,
                ),
            )

        conn.commit()

def start_patch_translation(
    patch_id: int,
) -> None:
    query = """
        UPDATE game_patch_processing
        SET
            translation_status = 'pending',
            translated_title = NULL,
            translated_content = NULL,
            translation_provider = NULL,
            translation_model = NULL,
            translation_prompt_version = NULL,
            translation_error = NULL,
            translated_at = NULL,

            summary_status = 'pending',
            summary = NULL,
            summary_provider = NULL,
            summary_model = NULL,
            summary_prompt_version = NULL,
            summary_error = NULL,
            summarized_at = NULL,

            updated_at = NOW()

        WHERE patch_id = %s
          AND target_language = 'ko'
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                query,
                (patch_id,),
            )

        conn.commit()

def mark_patch_translation_failed(
    patch_id: int,
    error: str,
) -> None:
    query = """
        UPDATE game_patch_processing
        SET
            translation_status = 'failed',
            translation_error = %s,
            updated_at = NOW()

        WHERE patch_id = %s
          AND target_language = 'ko'
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                query,
                (
                    error[:4000],
                    patch_id,
                ),
            )

        conn.commit()

def mark_patch_translation_skipped(
    patch_id: int,
) -> None:
    query = """
        UPDATE game_patch_processing
        SET
            translation_status = 'skipped',
            translated_title = NULL,
            translated_content = NULL,
            translation_provider = NULL,
            translation_model = NULL,
            translation_prompt_version = NULL,
            translation_error = NULL,
            translated_at = NULL,
            updated_at = NOW()

        WHERE patch_id = %s
          AND target_language = 'ko'
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                query,
                (patch_id,),
            )

        conn.commit()

def start_patch_summary(
    patch_id: int,
) -> None:
    query = """
        UPDATE game_patch_processing
        SET
            summary_status = 'pending',
            summary = NULL,
            summary_provider = NULL,
            summary_model = NULL,
            summary_prompt_version = NULL,
            summary_error = NULL,
            summarized_at = NULL,
            updated_at = NOW()

        WHERE patch_id = %s
          AND target_language = 'ko'
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                query,
                (patch_id,),
            )

        conn.commit()


def mark_patch_summary_failed(
    patch_id: int,
    error: str,
) -> None:
    query = """
        UPDATE game_patch_processing
        SET
            summary_status = 'failed',
            summary_error = %s,
            updated_at = NOW()

        WHERE patch_id = %s
          AND target_language = 'ko'
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                query,
                (
                    error[:4000],
                    patch_id,
                ),
            )

        conn.commit()

def _build_patch_viewer_filters(
    game_name: str | None = None,
    query_text: str | None = None,
) -> tuple[str, list[str]]:
    conditions = []
    params = []

    if game_name:
        conditions.append(
            "g.name = %s"
        )
        params.append(game_name)

    if query_text:
        keyword = f"%{query_text}%"

        conditions.append(
            """
            (
                COALESCE(
                    gpp.translated_title,
                    gp.title
                ) ILIKE %s

                OR gp.title ILIKE %s

                OR COALESCE(
                    gpp.translated_content,
                    ''
                ) ILIKE %s

                OR gp.content_text ILIKE %s

                OR COALESCE(
                    gpp.summary,
                    ''
                ) ILIKE %s
            )
            """
        )

        params.extend(
            [
                keyword,
                keyword,
                keyword,
                keyword,
                keyword,
            ]
        )

    if not conditions:
        return "", params

    where_clause = (
        "WHERE "
        + " AND ".join(conditions)
    )

    return where_clause, params


def get_patch_viewer_list(
    limit: int = 10,
    offset: int = 0,
    game_name: str | None = None,
    query_text: str | None = None,
) -> list[dict]:
    where_clause, params = (
        _build_patch_viewer_filters(
            game_name=game_name,
            query_text=query_text,
        )
    )

    query = f"""
        SELECT
            gp.id,
            g.name,

            COALESCE(
                gpp.translated_title,
                gp.title
            ) AS display_title,

            gp.title AS original_title,

            gp.source_provider,
            gp.source_language,
            gp.source_date,

            gpp.summary,
            gpp.translation_status,
            gpp.summary_status

        FROM game_patches gp

        JOIN games g
            ON g.game_id = gp.game_id

        LEFT JOIN game_patch_processing gpp
            ON gpp.patch_id = gp.id
            AND gpp.target_language = 'ko'

        {where_clause}

        ORDER BY
            gp.source_date DESC NULLS LAST,
            gp.id DESC

        LIMIT %s
        OFFSET %s
    """

    query_params = [
        *params,
        limit,
        offset,
    ]

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                query,
                tuple(query_params),
            )

            rows = cur.fetchall()

    return [
        {
            "patch_id": row[0],
            "game_name": row[1],
            "display_title": row[2],
            "original_title": row[3],
            "source_provider": row[4],
            "source_language": row[5],
            "source_date": row[6],
            "summary": row[7],
            "translation_status": row[8],
            "summary_status": row[9],
        }
        for row in rows
    ]


def get_patch_viewer_count(
    game_name: str | None = None,
    query_text: str | None = None,
) -> int:
    where_clause, params = (
        _build_patch_viewer_filters(
            game_name=game_name,
            query_text=query_text,
        )
    )

    query = f"""
        SELECT
            COUNT(*)

        FROM game_patches gp

        JOIN games g
            ON g.game_id = gp.game_id

        LEFT JOIN game_patch_processing gpp
            ON gpp.patch_id = gp.id
            AND gpp.target_language = 'ko'

        {where_clause}
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                query,
                tuple(params),
            )

            row = cur.fetchone()

    return row[0]

def get_patch_viewer_detail(
    patch_id: int,
) -> dict | None:
    query = """
        SELECT
            gp.id,
            g.name,

            COALESCE(
                gpp.translated_title,
                gp.title
            ) AS display_title,

            gp.title AS original_title,

            COALESCE(
                gpp.translated_content,
                gp.content_text
            ) AS display_content,

            gp.content_text AS original_content,

            gp.source_provider,
            gp.source_language,
            gp.source_date,
            gp.source_url,

            gpp.summary,
            gpp.translation_status,
            gpp.summary_status

        FROM game_patches gp

        JOIN games g
            ON g.game_id = gp.game_id

        LEFT JOIN game_patch_processing gpp
            ON gpp.patch_id = gp.id
            AND gpp.target_language = 'ko'

        WHERE gp.id = %s
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                query,
                (patch_id,),
            )

            row = cur.fetchone()

    if row is None:
        return None

    return {
        "patch_id": row[0],
        "game_name": row[1],
        "display_title": row[2],
        "original_title": row[3],
        "display_content": row[4],
        "original_content": row[5],
        "source_provider": row[6],
        "source_language": row[7],
        "source_date": row[8],
        "source_url": row[9],
        "summary": row[10],
        "translation_status": row[11],
        "summary_status": row[12],
    }

def get_patch_viewer_games() -> list[dict]:
    query = """
        SELECT
            g.name,
            COUNT(gp.id) AS patch_count
        FROM game_patches gp

        JOIN games g
            ON g.game_id = gp.game_id

        GROUP BY
            g.name

        ORDER BY
            g.name
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query)

            rows = cur.fetchall()

    return [
        {
            "name": row[0],
            "count": row[1],
        }
        for row in rows
    ]