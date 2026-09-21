# Game Data API

## 개요

Game Data Platform에 저장된 게임 정보와 동시 접속자 데이터를 조회하기 위한 REST API 명세입니다.

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

## 3. 게임 동시 접속자 이력 조회

### Request

```http
GET /games/{game_id}/player-counts
```

### Path Parameters

* `game_id`: 조회할 게임의 ID

### Query Parameters

* `limit`: 반환할 최대 데이터 개수
* `order`: 정렬 순서

  * `asc`
  * `desc`

### Example

```http
GET /games/1/player-counts?limit=100&order=desc
```

### Response

**200 OK**

```json
[
  {
    "player_count": 1285034,
    "collected_at": "2026-09-21T18:00:00"
  },
  {
    "player_count": 1278441,
    "collected_at": "2026-09-21T17:00:00"
  }
]
```

게임이 존재하지 않을 경우:

**404 Not Found**

```json
{
  "detail": "Game not found"
}
```

---

## 4. 최신 동시 접속자 조회

### Request

```http
GET /games/{game_id}/player-counts/latest
```

### Path Parameters

* `game_id`: 조회할 게임의 ID

### Example

```http
GET /games/1/player-counts/latest
```

### Response

**200 OK**

```json
{
  "game_id": 1,
  "player_count": 1285034,
  "collected_at": "2026-09-21T18:00:00"
}
```

최신 동시 접속자 데이터가 존재하지 않을 경우:

**404 Not Found**

```json
{
  "detail": "Player count not found"
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
| GET    | `/games/{game_id}/player-counts`        | 특정 게임의 동접자 이력 조회 |
| GET    | `/games/{game_id}/player-counts/latest` | 특정 게임의 최신 동접자 조회 |
