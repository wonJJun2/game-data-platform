from psycopg.rows import dict_row

from game_data_platform.database import get_connection

from sqlalchemy import asc, desc, select

from game_data_platform.database import SessionLocal
from game_data_platform.models import Game, PlayerCount

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