# Game Data Platform

Steam 게임 데이터를 수집하고 동접자 추이, 패치노트, 가격 정보를 분석하는 개인 프로젝트입니다.

단순히 기능을 빠르게 구현하는 것보다, 실제 데이터를 다루는 프로젝트를 진행하면서 Data Engineering, Backend, System Design을 단계적으로 학습하는 것을 목표로 합니다.

## Goals

프로젝트는 크게 세 가지 기능을 목표로 합니다.

### 1. Game Analytics

Steam 게임의 동접자 데이터를 주기적으로 수집하고 시계열로 저장하여 게임별 트렌드를 분석합니다.

향후 다음과 같은 분석을 진행할 예정입니다.

* 일별 / 주별 / 월별 동접자 추이
* 업데이트 전후 동접자 변화
* 패치 D+1 / D+7 / D+30 영향
* 할인 이벤트와 동접자 변화
* 평일 / 주말 및 시간대별 패턴

### 2. Patch Alert

Steam News에서 새로운 패치노트를 감지하고 한국어로 번역 또는 요약하여 Discord로 전달하는 기능을 구현할 예정입니다.

예상 흐름:

```text
Steam News
→ 신규 패치 감지
→ 번역 / 요약
→ Discord 알림
```

### 3. Price Alert

Steam 및 게임 가격 API를 활용하여 가격 변화를 추적하고 목표 가격이나 할인 조건을 만족할 경우 Discord 알림을 제공할 예정입니다.

예상 기능:

* 현재 가격
* 할인율
* 역대 최저가
* 목표 가격
* 가격 변화 이력
* Discord 가격 알림

## Current Progress

### Day 1

개발 환경을 구성하고 Steam API를 이용한 현재 동접자 조회 기능을 구현했습니다.

완료한 내용:

* Windows + WSL2 Ubuntu 개발 환경 구성
* `uv` 기반 Python 프로젝트 생성
* Python 3.12 프로젝트 환경 구성
* `httpx`를 이용한 Steam Web API 호출
* Steam App ID 기반 현재 동접자 조회
* 여러 게임의 동접자 데이터 조회
* GitHub Repository 생성 및 첫 Push

현재 테스트 중인 게임:

* THE FINALS
* Overwatch 2
* PUBG: BATTLEGROUNDS
* Counter-Strike 2
* Apex Legends
* Marvel Rivals
* Dota 2
* The First Descendant

현재 출력 예시:

```text
THE FINALS | 2073850 | 5,683
PUBG: BATTLEGROUNDS | 578080 | 324,300
Counter-Strike 2 | 730 | 649,854
```

동접자 데이터는 실시간 값이므로 실행 시점마다 달라집니다.

## Project Structure

현재 프로젝트 구조는 다음과 같습니다.

```text
game-data-platform/
├── README.md
├── pyproject.toml
├── uv.lock
└── src/
    └── game_data_platform/
        ├── __init__.py
        └── steam.py
```

### `steam.py`

Steam Web API와 통신하여 게임의 현재 동접자를 가져오는 기능을 담당합니다.

### `__init__.py`

현재 프로그램의 실행 진입점 역할을 합니다.

## Development Environment

* Windows
* WSL2
* Ubuntu
* Python 3.12
* uv
* httpx
* Git / GitHub

## Run

프로젝트를 실행합니다.

```bash
uv run game-data-platform
```

현재는 등록된 여러 Steam 게임의 동접자를 조회하여 터미널에 출력합니다.

## Roadmap

프로젝트는 기능이 필요해지는 시점에 기술을 단계적으로 추가할 예정입니다.

```text
Steam API
    ↓
Python Collector
    ↓
PostgreSQL
    ↓
FastAPI
    ↓
Docker / Docker Compose
    ↓
Redis
    ↓
Airflow
    ↓
Data Modeling / dbt
    ↓
Kafka
    ↓
Spark
    ↓
CI/CD / System Design
```

예정된 주요 단계:

* [x] Steam 현재 동접자 조회
* [x] 여러 게임 동접자 조회
* [ ] 수집 코드 구조 개선
* [ ] 예외 처리 및 Logging
* [ ] PostgreSQL 저장
* [ ] 동접자 시계열 수집
* [ ] FastAPI 조회 API
* [ ] Steam News 수집
* [ ] 패치노트 감지 및 번역/요약
* [ ] Discord Patch Alert
* [ ] 가격 데이터 수집
* [ ] Price Alert
* [ ] Airflow 기반 데이터 파이프라인
* [ ] dbt 기반 데이터 모델링
* [ ] Kafka 기반 이벤트 처리
* [ ] Spark 기반 데이터 분석
* [ ] CI/CD 구성

## Learning Focus

이 프로젝트에서는 단순히 기술을 사용하는 것보다 다음 내용을 이해하는 것을 중요하게 생각합니다.

* 왜 해당 기술이 필요한가
* 기존 방식의 어떤 문제를 해결하는가
* 어떤 Trade-off가 있는가
* 장애가 발생했을 때 어떻게 원인을 좁혀가는가
* 데이터가 증가했을 때 구조를 어떻게 변경해야 하는가
* 기능이 커질 때 서비스를 어떤 기준으로 분리해야 하는가

## Commit Convention

커밋 메시지는 Conventional Commits 형식을 사용한다.

- `feat`: 새로운 기능 추가
- `fix`: 버그 수정
- `refactor`: 기능 변화 없는 코드 구조 개선
- `docs`: 문서 수정
- `test`: 테스트 추가/수정
- `chore`: 환경 설정, 의존성, 기타 작업
- `perf`: 성능 개선
- `ci`: CI/CD 설정 변경

예시:

```text
feat: add Steam player count collector
fix: handle Steam API timeout
refactor: separate Steam API client
docs: update README
test: add player count tests
chore: update dependencies

## Status

🚧 Work in progress

현재 개인 학습 목적으로 개발 중인 프로젝트입니다.
