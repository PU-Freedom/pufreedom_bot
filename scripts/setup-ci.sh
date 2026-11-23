#!/usr/bin/env bash
# one-time setup for ci deploys: locked-down `ci` user running Forgejo runner
# whose only privilege is `sudo pufrb-deploy`. 
# idempotency ensured (safe to rerun; also re-installs deploy.sh)
set -euo pipefail

RUNNER_VERSION=13.1.0
CI_USER=ci
CI_HOME=/var/lib/forgejo-runner
RUNNER_NAME=pufrb-vps
INSTANCE=https://codeberg.org
TOKEN="${1:-}"

die() { echo "ERROR: $*" >&2; exit 1; }
[[ $EUID -eq 0 ]] || die "run as root (sudo)"
REPO_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)

echo "== deploy script"
install -o root -g root -m 0755 "$REPO_DIR/scripts/deploy.sh" /usr/local/bin/pufrb-deploy
if [[ ! -f /etc/pufrb-deploy.env ]]; then
    printf 'REPO_DIR=%s\n' "$REPO_DIR" > /etc/pufrb-deploy.env
    chmod 0644 /etc/pufrb-deploy.env
fi

echo "== ci user"
id "$CI_USER" &>/dev/null || useradd --system --create-home --home-dir "$CI_HOME" --shell /usr/sbin/nologin "$CI_USER"

echo "== sudo rule"
SUDOERS=$(mktemp)
echo "$CI_USER ALL=(root) NOPASSWD: /usr/local/bin/pufrb-deploy, /usr/local/bin/pufrb-deploy *" > "$SUDOERS"
visudo -cf "$SUDOERS" >/dev/null || die "generated sudoers rule is invalid"
install -o root -g root -m 0440 "$SUDOERS" /etc/sudoers.d/pufrb-deploy
rm -f "$SUDOERS"

echo "== forgejo-runner $RUNNER_VERSION"
if [[ "$(/usr/local/bin/forgejo-runner --version 2>/dev/null || true)" != *"$RUNNER_VERSION"* ]]; then
    case "$(uname -m)" in
        x86_64) ARCH=amd64 ;;
        aarch64) ARCH=arm64 ;;
        *) die "unsupported architecture $(uname -m)" ;;
    esac
    URL="https://code.forgejo.org/forgejo/runner/releases/download/v$RUNNER_VERSION/forgejo-runner-$RUNNER_VERSION-linux-$ARCH"
    TMP=$(mktemp -d)
    curl -fsSL -o "$TMP/runner" "$URL"
    curl -fsSL -o "$TMP/runner.sha256" "$URL.sha256"
    echo "$(cut -d' ' -f1 "$TMP/runner.sha256")  $TMP/runner" | sha256sum -c --quiet - || die "checksum mismatch"
    install -o root -g root -m 0755 "$TMP/runner" /usr/local/bin/forgejo-runner
    rm -rf "$TMP"
fi

echo "== runner config"
cat > "$CI_HOME/config.yml" <<EOF
log:
  level: info
runner:
  file: .runner
  capacity: 1
  timeout: 30m
  labels:
    - "$RUNNER_NAME:host"
cache:
  enabled: false
EOF
chown "$CI_USER:$CI_USER" "$CI_HOME/config.yml"

if [[ ! -f "$CI_HOME/.runner" ]]; then
    [[ -n "$TOKEN" ]] || die "not registered yet - pass the registration token"
    (cd "$CI_HOME" && runuser -u "$CI_USER" -- /usr/local/bin/forgejo-runner register --no-interactive \
        --config config.yml --instance "$INSTANCE" --token "$TOKEN" \
        --name "$RUNNER_NAME" --labels "$RUNNER_NAME:host")
fi

echo "== systemd service"
cat > /etc/systemd/system/forgejo-runner.service <<EOF
[Unit]
Description=Forgejo Actions runner
Wants=network-online.target
After=network-online.target

[Service]
User=$CI_USER
WorkingDirectory=$CI_HOME
ExecStart=/usr/local/bin/forgejo-runner daemon --config config.yml
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable --now forgejo-runner
systemctl restart forgejo-runner

echo
echo "done. deploy config: /etc/pufrb-deploy.env (REPO_DIR=$REPO_DIR)"
echo "runner status:  systemctl status forgejo-runner"
echo "manual deploy:  sudo pufrb-deploy"
