from game_data_platform.steam import get_current_players


def main() -> None:
    games = [
        {"name": "THE FINALS", "app_id": 2073850},
        {"name": "Overwatch", "app_id": 2357570},
	{"name": "PUBG: BATTLEGROUNDS", "app_id": 578080},
	{"name": "Counter-Strike 2", "app_id": 730},
	{"name": "Apex 레전드", "app_id": 1172470},
	{"name": "마블 라이벌즈", "app_id": 2767030},
	{"name": "Dota 2", "app_id": 570},
	{"name": "퍼스트 디센던트", "app_id": 2074920}
    ]

    for game in games:
        player_count = get_current_players(game["app_id"])

        print(
            f'{game["name"]} | '
            f'{game["app_id"]} | '
            f'{player_count:,}'
        )
