#!/bin/sh
# Local edge smoke: studio at /, a fixture slug, 404 for a missing slug,
# and reserved paths answered by the studio rather than the sites volume.
set -eu

ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
cd "$ROOT"

compose() {
  docker compose "$@"
}

cleanup() {
  compose down -v >/dev/null 2>&1 || true
}
trap cleanup EXIT

compose up -d --build --force-recreate

ready=0
i=0
while [ "$i" -lt 60 ]; do
  if curl -fsS --max-time 5 http://localhost:8081/health >/dev/null 2>&1; then
    ready=1
    break
  fi
  i=$((i + 1))
  sleep 2
done
if [ "$ready" -ne 1 ]; then
  echo "studio health check did not become ready" >&2
  compose logs || true
  exit 1
fi

home=$(curl -fsS http://localhost:8081/)
printf '%s' "$home" | grep -q "Homerun" || {
  echo "GET / did not serve the Homerun studio" >&2
  exit 1
}

health=$(curl -fsS http://localhost:8081/health)
printf '%s' "$health" | grep -q '"status"' || {
  echo "GET /health was not the studio health JSON" >&2
  exit 1
}

compose exec -T studio python - <<'PY'
from pathlib import Path
root = Path("/app/persist/sites")
demo = root / "demo-slug"
demo.mkdir(parents=True, exist_ok=True)
(demo / "index.html").write_text("<html>fixture-page</html>", encoding="utf-8")
(demo / "hero.png").write_bytes(b"png-bytes")
for name in ("api", "assets", "health", "static"):
    planted = root / name
    planted.mkdir(parents=True, exist_ok=True)
    (planted / "index.html").write_text(f"<html>planted-{name}</html>", encoding="utf-8")
PY

page=$(curl -fsS http://localhost:8081/demo-slug/)
printf '%s' "$page" | grep -q "fixture-page" || {
  echo "GET /demo-slug/ did not return the fixture page" >&2
  exit 1
}

hero=$(curl -fsS http://localhost:8081/demo-slug/hero.png)
printf '%s' "$hero" | grep -q "png-bytes" || {
  echo "GET /demo-slug/hero.png did not return the fixture asset" >&2
  exit 1
}

missing_body=$(mktemp)
missing_code=$(curl -sS -o "$missing_body" -w '%{http_code}' http://localhost:8081/missing-slug/)
if [ "$missing_code" != "404" ]; then
  echo "GET /missing-slug/ returned $missing_code, expected 404" >&2
  exit 1
fi
if grep -q "Homerun" "$missing_body"; then
  echo "GET /missing-slug/ returned the studio UI" >&2
  exit 1
fi
rm -f "$missing_body"

api=$(curl -fsS http://localhost:8081/api/conversations)
printf '%s' "$api" | grep -q "planted-api" && {
  echo "GET /api/conversations served a planted site" >&2
  exit 1
}
printf '%s' "$api" | grep -q '\[' || {
  echo "GET /api/conversations was not the studio API" >&2
  exit 1
}

for path in /assets/ /static/ /static /health; do
  body=$(curl -sS "http://localhost:8081$path" || true)
  printf '%s' "$body" | grep -q "planted-" && {
    echo "GET $path served a planted site" >&2
    exit 1
  }
done

echo "compose smoke ok"
