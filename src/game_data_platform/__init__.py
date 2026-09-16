import logging
from datetime import datetime
import psycopg
import httpx

from game_data_platform.steam import get_current_players
from game_data_platform.storage import save_player_count


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("app.log", encoding="utf-8"),
    ],
)

# httpx가 정상 요청까지 INFO 로그로 출력하는 것을 숨김
logging.getLogger("httpx").setLevel(logging.WARNING)


def main() -> None:
    games = [
        {"name": "THE FINALS", "app_id": 2073850},
        {"name": "Overwatch", "app_id": 2357570},
        {"name": "PUBG: BATTLEGROUNDS", "app_id": 578080},
        {"name": "Counter-Strike 2", "app_id": 730},
        {"name": "Apex 레전드", "app_id": 1172470},
        {"name": "마블 라이벌즈", "app_id": 2767030},
        {"name": "Dota 2", "app_id": 570},
        {"name": "퍼스트 디센던트", "app_id": 2074920},
    ]

    for game in games:
        try:
            player_count = get_current_players(game["app_id"])

            data = {
                    "app_id": game["app_id"],
                    "name": game["name"],
                    "player_count": player_count,
                    "collected_at": datetime.now().astimezone(),
                }

            try:
                save_player_count(data)

            except ValueError as exc:
                logger.error(
                    "게임 기준정보 오류 - %s (%s): %s",
                    game["name"],
                    game["app_id"],
                    exc,
                )
                continue

            except psycopg.Error as exc:
                logger.error(
                    "DB 저장 실패 - %s (%s): %s",
                    game["name"],
                    game["app_id"],
                    exc,
                )
                continue

        except httpx.TimeoutException:
            logging.error(
                "%s | request timeout",
                game["name"],
            )

        except httpx.HTTPStatusError as error:
            logging.error(
                "%s | status_code=%s",
                game["name"],
                error.response.status_code,
            )

        except httpx.RequestError as error:
            logging.error(
                "%s | request_error=%s",
                game["name"],
                error,
            )