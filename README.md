# Game Data Platform

게임 패치노트를 수집해 한국어로 제공하고, 사용자가 설정한 Steam 목표 가격에 도달하면 Discord로 알립니다. Airflow가 수집을 예약하고 PostgreSQL이 데이터와 발송 대기 작업을 저장합니다. FastAPI 웹에서는 등록 게임, 최신 가격, 패치 원문·번역·요약을 조회할 수 있습니다.

## 수집과 알림

| Airflow DAG | 실행 시각 (KST) | 동작 |
| --- | --- | --- |
| `patch_collection` | 매일 07:30, 19:30 | Steam 뉴스와 공식 패치 수집, 패치 탐지·통합, 한국어 LLM 처리, 채널 알림 등록 |
| `price_collection` | 매일 09:00 | 활성 가격 구독 게임의 Steam 한국 스토어 가격 수집 및 목표 가격 판정 |

- **패치 알림** — 등록 게임의 Steam 뉴스에서 패치를 탐지하고 오버워치·배틀그라운드 공식 패치와 함께 공통 패치 테이블로 통합합니다. LLM은 필요한 패치를 한국어로 번역하고 요약합니다. DAG의 LLM 처리 한도는 실행당 기본 6건이며 `PATCH_LLM_PROCESS_LIMIT`으로 조정합니다. 수집 태스크가 성공하면 한국어 본문이 준비된 패치 중 구독 시작 기준 이후의 항목을 서버별 Outbox에 등록합니다. 봇은 서버에서 설정한 채널로 알림을 발송합니다.
- **가격 알림** — 활성 구독이 있는 게임마다 한 번씩 가격을 조회하고 게임별 최신 관측값을 저장합니다. 수집에 성공하면 가격이 그대로인 경우에도 방금 저장한 관측값으로 활성 구독을 평가합니다. KRW 판매가가 목표 가격 이하이고 구독이 알림 가능 상태이면 발송 작업을 등록합니다. 가격이 목표를 다시 초과하면 다음 가격 하락에 대해 알림을 받을 수 있도록 구독을 알림 가능 상태로 되돌립니다.

## 발송 처리

Transactional Outbox는 패치 채널 알림과 가격 DM의 발송 요청과 상태를 PostgreSQL에 기록합니다. 가격 알림 작업 등록과 해당 구독의 알림 가능 상태 해제는 같은 트랜잭션에서 커밋됩니다.

- 패치 Outbox는 패치와 서버 조합으로, 가격 Outbox는 구독과 알림 세대(`alert_generation`) 조합으로 중복 등록을 막습니다.
- Worker는 `FOR UPDATE SKIP LOCKED`로 작업을 선점합니다. Lease가 만료되면 작업을 다시 선점할 수 있습니다. 상태 갱신에는 유효한 Lease와 해당 선점의 Fencing Token(`attempt_count`)이 필요합니다.
- 발송 경로에서 구독 및 발송 조건을 다시 확인합니다. 재시도 가능한 오류에는 발송 시도 한도와 지수 백오프를 적용합니다. Discord가 요청을 받은 뒤 DB에 발송 결과를 기록하기 전에 장애가 발생하면 재시도로 메시지가 중복 발송될 수 있습니다.

## PostgreSQL 운영 테이블

| 용도 | 테이블 |
| --- | --- |
| 게임 카탈로그 | `games` |
| Steam 뉴스·패치 탐지 | `steam_news`, `steam_news_patch_detection` |
| 공식 패치 원본 | `overwatch_patch_notes`, `pubg_patch_notes` |
| 통합 패치·LLM 처리 | `game_patches`, `game_patch_processing` |
| 최신 가격 | `game_price_current` |
| 서버별 패치 채널·구독·발송 | `discord_patch_channels`, `discord_patch_game_subscriptions`, `discord_patch_notification_outbox` |
| 사용자별 가격 구독·발송 | `discord_price_subscriptions`, `discord_price_notification_outbox` |

가격 Outbox에는 해당 DM에서 사용할 가격과 목표가가 함께 저장됩니다. 웹 게임 상세의 가격은 최신 가격 테이블에서 조회합니다.

## Discord 명령어

봇은 `DISCORD_GUILD_ID`로 지정한 서버에 명령어를 등록합니다. 패치 채널과 구독을 관리하는 명령에는 서버 관리 권한이 필요합니다.

| 명령어 | 입력 옵션 | 동작 |
| --- | --- | --- |
| `/상태확인` | | 봇 응답 상태 확인 |
| `/게임검색` | `게임명` | 등록 게임 검색 |
| `/패치채널설정` | `채널` | 서버의 패치 알림 채널 설정 |
| `/패치구독` | `게임` | 서버에서 오버워치 또는 배틀그라운드 패치 알림 구독 |
| `/패치해제` | `게임` | 서버 패치 구독 해제 |
| `/패치목록` | | 서버 패치 구독 목록 확인 |
| `/가격설정` | `게임`, `목표가격` | 등록 게임의 개인 목표 가격 등록·변경 (정수 KRW) |
| `/가격목록` | | 자신의 활성 가격 구독 목록 확인 |
| `/가격해제` | `게임` | 자신의 가격 구독 해제 |

## 웹

- `/games`에서 게임 목록을 확인하고 Steam 스토어 URL로 등록 미리보기를 열 수 있습니다. 게임 상세 페이지에는 최신 가격과 관련 패치가 표시됩니다.
- `/patches`에서 패치 목록과 상세 내용을 조회합니다. 상세 화면에서는 원문, 한국어 번역 및 요약을 확인하고 LLM 재처리를 요청할 수 있습니다.
- 게임 조회 JSON 핸들러의 응답 구조와 HTML 경로의 우선순위는 [API 문서](docs/api.md)를 참고하세요.

## 로컬 실행

기존 로컬 운영은 Docker Compose로 Airflow(LocalExecutor)와 PostgreSQL을 구성합니다. Airflow 이미지는 `Dockerfile.airflow`와 `requirements-airflow.txt`를 사용합니다. 웹 이미지용 `dockerfile`은 `uv.lock`의 의존성을 설치하고 Uvicorn으로 FastAPI 앱을 실행합니다. 기존 로컬 설정과 준비된 DB를 사용하는 환경에서 서비스 목록을 확인한 뒤, `docker compose up -d`에 실행할 서비스명을 지정합니다.

```bash
docker compose config --services
docker compose ps
```

Airflow UI에서 `patch_collection`과 `price_collection`의 활성화 여부와 다음 실행 시각을 확인합니다. `patch_collection`은 처음 등록할 때 일시 정지 상태로 생성됩니다.

Python 3.12와 `uv`를 사용하는 로컬 셸에서는 DB, Discord, LLM 설정을 준비한 뒤 필요한 명령만 실행합니다.

```bash
uv sync --locked
uv run uvicorn game_data_platform.api:app
```

| CLI | 용도 |
| --- | --- |
| `uv run game-data-discord` | Discord 봇 실행. 자동 발송은 `DISCORD_PATCH_WORKER_ENABLED=1`, `DISCORD_PRICE_WORKER_ENABLED=1`로 각각 활성화 |
| `uv run game-data-patches` | 통합 패치 수집·LLM 처리 수동 실행. 패치 채널 Outbox 등록은 Airflow의 후속 태스크가 담당 |
| `uv run game-data-patch-llm` | 패치 LLM 처리만 수동 실행. `PATCH_LLM_PROCESS_LIMIT` 미지정 시 처리 건수 제한 없음 |
| `uv run game-data-price` | 활성 구독 게임 가격 수동 수집 및 목표 가격 판정. 조건 충족 시 DM 발송 작업 등록 |

스키마 변경 이력은 `alembic/versions/`에 있습니다. 기존 DB 지원 도구는 `scripts/alembic_docker.sh`, ORM 테이블 생성 스크립트는 `scripts/init_db.py`에 있습니다. 빈 DB 초기화 절차 개선은 별도 작업으로 진행합니다.

## 향후 계획

FastAPI 웹을 운영 모니터링과 설정 관리를 위한 관리자 도구로 발전시킬 계획입니다. 현재 웹에는 관리자 인증 및 접근 제어가 구현되어 있지 않습니다. 클라우드 배포도 향후 작업입니다.
