from game_data_platform.database import get_connection


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