import json


def save_player_count(data: dict) -> None:
    with open(
        "player_counts.jsonl",
        "a",
        encoding="utf-8",
    ) as file:
        json.dump(data, file, ensure_ascii=False)
        file.write("\n")
