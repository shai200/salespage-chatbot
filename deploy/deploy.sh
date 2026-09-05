#!/usr/bin/env bash
# Repeatable Civo deploy for Homerun.
# Builds a versioned image, applies deploy/k8s, updates the studio Deployment.
#
#   ./deploy/deploy.sh
#   ./deploy/deploy.sh --skip-build   # apply + rollout current IMAGE_TAG only
#
# Requires: docker, kubectl, kubeconfig, registry login, OPENROUTER_API_KEY in .env
# This Ingress claims homerun.love for the studio and /<slug>/ pages (same Service).

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

SKIP_BUILD=0
SKIP_PUSH=0
DRY_RUN=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-build) SKIP_BUILD=1 ;;
    --skip-push) SKIP_PUSH=1 ;;
    --dry-run) DRY_RUN=1 ;;
    -h|--help)
      sed -n '2,12p' "$0"
      exit 0
      ;;
    *)
      echo "unknown flag: $1" >&2
      exit 1
      ;;
  esac
  shift
done

if [[ -f "$ROOT/deploy/civo.env" ]]; then
  # shellcheck disable=SC1091
  set -a
  source "$ROOT/deploy/civo.env"
  set +a
fi

IMAGE_REPO="${IMAGE_REPO:-ghcr.io/shai200/salespage-chatbot}"
IMAGE_TAG="${IMAGE_TAG:-$(git -C "$ROOT" rev-parse --short HEAD)}"
IMAGE="${IMAGE_REPO}:${IMAGE_TAG}"
HOST="${HOST:-homerun.love}"
PUBLIC_BASE_URL="${PUBLIC_BASE_URL:-https://${HOST}}"
PAGE_RSYNC_TARGET="${PAGE_RSYNC_TARGET:-}"
PAGE_SSH_KEY_FILE="${PAGE_SSH_KEY_FILE:-}"
SERVE_SITES="${SERVE_SITES:-1}"
NAMESPACE="${NAMESPACE:-homerun}"
KUBECONFIG="${KUBECONFIG:-$ROOT/civo-love-kubeconfig}"
export KUBECONFIG

need() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "missing required command: $1" >&2
    exit 1
  }
}

read_openrouter_key() {
  if [[ -n "${OPENROUTER_API_KEY:-}" ]]; then
    printf '%s' "$OPENROUTER_API_KEY"
    return
  fi
  if [[ -f "$ROOT/.env" ]]; then
    python3 - <<PY
from pathlib import Path
for line in Path(r"$ROOT/.env").read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    key, value = line.split("=", 1)
    if key.strip() == "OPENROUTER_API_KEY":
        print(value.strip().strip("'").strip('"'), end="")
        break
PY
  fi
}

need kubectl
if [[ "$SKIP_BUILD" -eq 0 ]]; then
  need docker
fi

if [[ ! -f "$KUBECONFIG" ]]; then
  echo "kubeconfig not found: $KUBECONFIG" >&2
  exit 1
fi

KEY="$(read_openrouter_key)"
if [[ -z "$KEY" ]]; then
  echo "OPENROUTER_API_KEY is empty (set it in .env or the environment)" >&2
  exit 1
fi

echo "image:     $IMAGE"
echo "namespace: $NAMESPACE"
echo "studio:    https://${HOST}/"
echo "pages:     ${PUBLIC_BASE_URL}/<slug>/"
echo "serve:     SERVE_SITES=${SERVE_SITES}"

if [[ "$SKIP_BUILD" -eq 0 ]]; then
  docker build -t "$IMAGE" -t "${IMAGE_REPO}:latest" "$ROOT"
  if [[ "$SKIP_PUSH" -eq 0 ]]; then
    docker push "$IMAGE"
    docker push "${IMAGE_REPO}:latest"
  fi
fi

kubectl_apply() {
  if [[ "$DRY_RUN" -eq 1 ]]; then
    kubectl apply --dry-run=server -f "$1"
  else
    kubectl apply -f "$1"
  fi
}

kubectl_apply "$ROOT/deploy/k8s/namespace.yaml"
kubectl_apply "$ROOT/deploy/k8s/configmap.yaml"
kubectl_apply "$ROOT/deploy/k8s/pvc.yaml"
kubectl_apply "$ROOT/deploy/k8s/deployment.yaml"
kubectl_apply "$ROOT/deploy/k8s/service.yaml"
kubectl_apply "$ROOT/deploy/k8s/ingress.yaml"

kubectl patch configmap studio -n "$NAMESPACE" --type merge -p \
  "{\"data\":{\"PUBLIC_BASE_URL\":\"${PUBLIC_BASE_URL}\",\"PAGE_RSYNC_TARGET\":\"${PAGE_RSYNC_TARGET}\",\"SERVE_SITES\":\"${SERVE_SITES}\"}}"

if [[ "$DRY_RUN" -eq 0 ]]; then
  kubectl create secret generic openrouter \
    --namespace "$NAMESPACE" \
    --from-literal="OPENROUTER_API_KEY=${KEY}" \
    --dry-run=client -o yaml | kubectl apply -f -
  if [[ -n "$PAGE_SSH_KEY_FILE" ]]; then
    if [[ ! -f "$PAGE_SSH_KEY_FILE" ]]; then
      echo "PAGE_SSH_KEY_FILE not found: $PAGE_SSH_KEY_FILE" >&2
      exit 1
    fi
    kubectl create secret generic pages-ssh \
      --namespace "$NAMESPACE" \
      --from-file="id_ed25519=${PAGE_SSH_KEY_FILE}" \
      --dry-run=client -o yaml | kubectl apply -f -
  fi
  if [[ -n "${IMAGE_PULL_SECRET:-}" ]]; then
    kubectl patch deployment studio -n "$NAMESPACE" --type strategic -p \
      "{\"spec\":{\"template\":{\"spec\":{\"imagePullSecrets\":[{\"name\":\"${IMAGE_PULL_SECRET}\"}]}}}}"
  fi
  kubectl -n "$NAMESPACE" set image deployment/studio "studio=${IMAGE}"
  kubectl -n "$NAMESPACE" rollout status deployment/studio --timeout=180s
fi

echo
echo "Deployed ${IMAGE}"
echo "Studio: https://${HOST}/"
echo "Health: https://${HOST}/health"
echo "Pages:  ${PUBLIC_BASE_URL}/<slug>/"
