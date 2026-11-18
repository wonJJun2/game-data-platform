
#!/usr/bin/env bash
set -euo pipefail

# 프로젝트 루트로 이동
PROJECT_ROOT="$(
    cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd
)"

cd "$PROJECT_ROOT"

SERVICE="airflow-dag-processor"
MIGRATION_DIR="/tmp/game-data-alembic"

if [[ $# -eq 0 ]]; then
    echo "Usage:"
    echo "  bash scripts/alembic_docker.sh current"
    echo "  bash scripts/alembic_docker.sh heads"
    echo "  bash scripts/alembic_docker.sh upgrade head"
    exit 1
fi

# 실행 중인 Airflow 컨테이너 확인
CID="$(docker compose ps -q "$SERVICE")"

if [[ -z "$CID" ]]; then
    echo "ERROR: $SERVICE container is not running"
    exit 1
fi

echo "[Alembic] Docker container: $SERVICE"

# 이전에 복사한 마이그레이션 파일 제거 후 디렉터리 생성
docker compose exec -T "$SERVICE" \
    sh -c "rm -rf '$MIGRATION_DIR' && mkdir -p '$MIGRATION_DIR'"

# 최신 Alembic 파일 복사
docker cp \
    "$PROJECT_ROOT/alembic" \
    "$CID:$MIGRATION_DIR/"

docker cp \
    "$PROJECT_ROOT/alembic.ini" \
    "$CID:$MIGRATION_DIR/alembic.ini"

echo "[Alembic] Running: $*"

# Docker의 DB 연결 환경을 그대로 사용
docker compose exec -T \
    -w "$MIGRATION_DIR" \
    -e PYTHONPATH=/opt/game-data/src \
    "$SERVICE" \
    python -m alembic -c alembic.ini "$@"
