# Game Data API

## 개요

Game Data Platform에 저장된 게임 정보를 조회하는 JSON 핸들러의 명세입니다. 전체 FastAPI 앱에서 같은 경로를 요청하면 먼저 등록된 웹 라우터가 HTML을 반환합니다.

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
    "id": 1,
    "steam_app_id": 730,
    "name": "Counter-Strike 2"
  },
  {
    "id": 2,
    "steam_app_id": 570,
    "name": "Dota 2"
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
  "id": 1,
  "steam_app_id": 730,
  "name": "Counter-Strike 2"
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
| 201         | 리소스 생성 성공    |
| 400         | 잘못된 요청       |
| 404         | 리소스를 찾을 수 없음 |
| 500         | 서버 내부 오류     |

---

## Endpoint Summary

| Method | Endpoint                                | Description      |
| ------ | --------------------------------------- | ---------------- |
| GET    | `/games`                                | 전체 게임 목록 조회      |
| GET    | `/games/{game_id}`                      | 특정 게임 조회         |
