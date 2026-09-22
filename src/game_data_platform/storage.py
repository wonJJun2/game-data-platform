from psycopg.rows import dict_row

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

def get_games():
    query = """
        SELECT
            game_id,
            steam_app_id,
            name,
            created_at
        FROM games
        ORDER BY game_id
    """

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(query)
            return cursor.fetchall()

def get_game(game_id: int):
    query = """
        SELECT
            game_id,
            steam_app_id,
            name,
            created_at
        FROM games
        WHERE game_id = %s
    """

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(query, (game_id,))
            return cursor.fetchone()

def get_player_counts(
    game_id: int,
    limit: int = 100,
    order: str = "desc",
):
    order_sql = "DESC" if order == "desc" else "ASC"

    query = f"""
        SELECT
            player_count,
            collected_at
        FROM player_counts
        WHERE game_id = %s
        ORDER BY collected_at {order_sql}
        LIMIT %s
    """

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(query, (game_id, limit))
            return cursor.fetchall()

def get_latest_player_count(game_id: int):
    query = """
        SELECT
            game_id,
            player_count,
            collected_at
        FROM player_counts
        WHERE game_id = %s
        ORDER BY collected_at DESC
        LIMIT 1
    """

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(query, (game_id,))
            return cursor.fetchone()