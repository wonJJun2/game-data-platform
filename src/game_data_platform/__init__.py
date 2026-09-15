import logging
from datetime import datetime

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
<<<<<<< HEAD
		{"name": "PUBG: BATTLEGROUNDS", "app_id": 578080},
		{"name": "Counter-Strike 2", "app_id": 730},
		{"name": "Apex 레전드", "app_id": 1172470},
		{"name": "마블 라이벌즈", "app_id": 2767030},
		{"name": "Dota 2", "app_id": 570},
		{"name": "퍼스트 디센던트", "app_id": 2074920}
=======
        {"name": "PUBG: BATTLEGROUNDS", "app_id": 578080},
        {"name": "Counter-Strike 2", "app_id": 730},
        {"name": "Apex 레전드", "app_id": 1172470},
        {"name": "마블 라이벌즈", "app_id": 2767030},
        {"name": "Dota 2", "app_id": 570},
        {"name": "퍼스트 디센던트", "app_id": 2074920},
>>>>>>> 4817797 (feat: add error handling and data persistence)
    ]

    for game in games:
        try:
            player_count = get_current_players(game["app_id"])

            data = {
                "app_id": game["app_id"],
                "name": game["name"],
                "player_count": player_count,
                "collected_at": datetime.now().astimezone().isoformat(),
            }

            save_player_count(data)

            logging.info(
                "%s | app_id=%s | player_count=%s",
                game["name"],
                game["app_id"],
                player_count,
            )

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
