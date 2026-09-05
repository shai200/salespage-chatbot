#!/usr/bin/env bash
# One-way pull: cluster SQLite + sites → this machine.
# Merges into local state. Does not delete local conversations or slugs.
# Server rows/slugs that you do not already have are added.
#
#   ./deploy/pull-from-civo.sh
#
# Requires: kubectl, kubeconfig. Studio on this machine should be stopped
# so SQLite is not mid-write.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ -f "$ROOT/deploy/civo.env" ]]; then
  # shellcheck disable=SC1091
  set -a
  source "$ROOT/deploy/civo.env"
  set +a
fi

NAMESPACE="${NAMESPACE:-homerun}"
KUBECONFIG="${KUBECONFIG:-$ROOT/civo-love-kubeconfig}"
export KUBECONFIG

if [[ ! -f "$KUBECONFIG" ]]; then
  echo "kubeconfig not found: $KUBECONFIG" >&2
  exit 1
fi

if ! command -v kubectl >/dev/null 2>&1; then
  echo "missing kubectl" >&2
  exit 1
fi

POD="$(kubectl -n "$NAMESPACE" get pod -l app=studio -o jsonpath='{.items[0].metadata.name}')"
if [[ -z "$POD" ]]; then
  echo "no studio pod in namespace ${NAMESPACE}" >&2
  exit 1
fi

STAMP="$(date +%Y%m%d-%H%M%S)"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/homerun-pull.XXXXXX")"
trap 'rm -rf "$WORK"' EXIT

echo "pod:  ${NAMESPACE}/${POD}"
echo "work: ${WORK}"

mkdir -p "$WORK/data" "$WORK/sites" "$ROOT/data" "$ROOT/sites"

if kubectl -n "$NAMESPACE" exec "$POD" -- test -f /app/data/studio.sqlite; then
  kubectl cp "${NAMESPACE}/${POD}:/app/data/studio.sqlite" "$WORK/data/studio.sqlite"
  for extra in studio.sqlite-wal studio.sqlite-shm; do
    if kubectl -n "$NAMESPACE" exec "$POD" -- test -f "/app/data/${extra}"; then
      kubectl cp "${NAMESPACE}/${POD}:/app/data/${extra}" "$WORK/data/${extra}" || true
    fi
  done
  echo "pulled cluster studio.sqlite"
else
  echo "cluster has no /app/data/studio.sqlite" >&2
fi

kubectl -n "$NAMESPACE" exec -i "$POD" -- tar -C /app/sites --exclude='.staging' -cf - . \
  > "$WORK/sites.tar"
mkdir -p "$WORK/sites"
tar -C "$WORK/sites" -xf "$WORK/sites.tar"
echo "pulled cluster sites/"

if [[ -f "$ROOT/data/studio.sqlite" ]]; then
  cp "$ROOT/data/studio.sqlite" "$ROOT/data/studio.sqlite.bak-before-pull-${STAMP}"
  echo "backed up local sqlite → data/studio.sqlite.bak-before-pull-${STAMP}"
fi
if [[ -f "$WORK/data/studio.sqlite" ]]; then
  python3 "$ROOT/deploy/merge_studio_sqlite.py" \
    "$ROOT/data/studio.sqlite" \
    "$WORK/data/studio.sqlite"
fi

added=0
skipped=0
shopt -s nullglob
for dir in "$WORK/sites"/*/; do
  slug="$(basename "$dir")"
  [[ "$slug" == .* || "$slug" == "lost+found" ]] && continue
  dest="$ROOT/sites/$slug"
  if [[ -e "$dest" ]]; then
    echo "keep local sites/${slug}/"
    skipped=$((skipped + 1))
    continue
  fi
  mkdir -p "$dest"
  tar -C "$dir" -cf - . | tar -C "$dest" -xf -
  echo "added sites/${slug}/"
  added=$((added + 1))
done

echo
echo "Sites added:   ${added}"
echo "Sites kept:    ${skipped} (already on this machine)"
echo "Restart the local studio so it opens the merged sqlite."
