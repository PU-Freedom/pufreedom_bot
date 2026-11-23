#!/usr/bin/env bash
#   sudo pufrb-deploy [commit-sha]  # no sha = latest origin/$BRANCH
set -euo pipefail

REPO_DIR=/home/opc/apps/pufreedom_bot
COMPOSE_DIR=/home/opc/apps
BRANCH=master
SERVICE=bot
CONTAINER=pufreedom-bot
IMAGE=localhost/pufreedom-bot:light
PREVIOUS=localhost/pufreedom-bot:previous
EXTRAS=""                      # "--extra nsfw" to bake in automatic NSFW detection
COMPOSE=/usr/local/bin/docker-compose
export DOCKER_HOST=unix:///run/podman/podman.sock
HEALTH_WAIT=20
[[ -f /etc/pufrb-deploy.env ]] && source /etc/pufrb-deploy.env

log() { echo "[deploy $(date +%H:%M:%S)] $*"; }
die() { log "ERROR: $*"; exit 1; }

[[ $EUID -eq 0 ]] || die "run as root (sudo)"
SHA="${1:-}"
[[ -z "$SHA" || "$SHA" =~ ^[0-9a-f]{40}$ ]] || die "expected a full commit sha, got '$SHA'"

exec 9>/run/lock/pufrb-deploy.lock
flock -w 900 9 || die "another deploy is still running"

OWNER=$(stat -c %U "$REPO_DIR")
repo() { runuser -u "$OWNER" -- git -C "$REPO_DIR" "$@"; }
compose() { (cd "$COMPOSE_DIR" && "$COMPOSE" "$@"); }

log "updating $REPO_DIR"
repo fetch --quiet origin "$BRANCH"
TARGET="${SHA:-$(repo rev-parse "origin/$BRANCH")}"
repo merge-base --is-ancestor "$TARGET" "origin/$BRANCH" || die "$TARGET is not on origin/$BRANCH"
repo checkout --quiet "$BRANCH"
# ff-only: refuses to clobber local edits or diverged history on the server
repo merge --ff-only --quiet "$TARGET"
log "at $(repo log -1 --format='%h %s')"

log "building $IMAGE"
podman image exists "$IMAGE" && podman tag "$IMAGE" "$PREVIOUS"
podman build --pull=missing --build-arg EXTRAS="$EXTRAS" -t "$IMAGE" "$REPO_DIR"

restorePrevious() { podman image exists "$PREVIOUS" && podman tag "$PREVIOUS" "$IMAGE"; }

log "migrating"
compose run --rm "$SERVICE" alembic upgrade head || { restorePrevious; die "migration failed - bot left running on the previous image"; }

log "restarting $SERVICE"
compose up -d --no-deps --force-recreate "$SERVICE"
sleep "$HEALTH_WAIT"
state=$(podman inspect -f '{{.State.Running}} {{.RestartCount}}' "$CONTAINER" 2>/dev/null || echo "missing")
if [[ "$state" != "true 0" ]]; then
    podman logs --tail 40 "$CONTAINER" 2>&1 || true
    log "bot not healthy after ${HEALTH_WAIT}s (running/restarts: $state) - rolling back"
    restorePrevious && compose up -d --no-deps --force-recreate "$SERVICE"
    die "deploy failed - rolled back to the previous image (migrations are kept, they're additive)"
fi

podman image prune -f >/dev/null
log "done - $(repo log -1 --format='%h')"
