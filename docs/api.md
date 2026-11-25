# Game Data API

## 개요

Game Data Platform에 저장된 게임 정보를 조회하는 JSON 핸들러의 응답 구조입니다. 전체 FastAPI 앱에서 같은 경로를 요청하면 먼저 등록된 웹 라우터가 HTML을 반환합니다.

---

## 1. 게임 목록 조회

### Request

```http
GET /games
```

### Description

등록된 전체 게임 목록을 조회합니다.

### Response

**200 OK**

```json
[
  {
    "game_id": 1,
    "steam_app_id": 730,
    "name": "Counter-Strike 2",
    "created_at": "2026-09-25T03:00:00Z",
    "header_image_url": null
  }
]
```

---

## 2. 특정 게임 조회

### Request

```http
GET /games/{game_id}
```

### Path Parameters

* `game_id`: 조회할 게임의 ID

### Example

```http
GET /games/1
```

### Response

**200 OK**

```json
{
  "game_id": 1,
  "steam_app_id": 730,
  "name": "Counter-Strike 2",
  "created_at": "2026-09-25T03:00:00Z",
  "header_image_url": null
}
```

게임이 존재하지 않을 경우:

**404 Not Found**

```json
{
  "detail": "Game not found"
}
```

---

## HTTP Status Code

| Status Code | 의미           |
| ----------- | ------------ |
| 200         | 조회 성공        |
| 404         | 리소스를 찾을 수 없음 |
| 422         | 경로 매개변수 검증 실패 |

---

## Endpoint Summary

| Method | Endpoint                                | Description      |
| ------ | --------------------------------------- | ---------------- |
| GET    | `/games`                                | 전체 게임 목록 조회      |
| GET    | `/games/{game_id}`                      | 특정 게임 조회         |
