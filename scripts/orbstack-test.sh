#!/usr/bin/env bash

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
GIT_COMMON_DIR="$(git -C "$ROOT" rev-parse --path-format=absolute --git-common-dir)"
PROJECT_ROOT="$(cd "$GIT_COMMON_DIR/.." && pwd)"
COMPOSE_FILE="$ROOT/compose.orbstack.yml"
RUNTIME_DIR="$ROOT/.runtime-test"
SHARED_RUNTIME_DIR="$PROJECT_ROOT/.runtime-test-shared"
CONFIG_DIR="$SHARED_RUNTIME_DIR/config"
MEDIA_DIR="$RUNTIME_DIR/media-run"
ENV_FILE="$RUNTIME_DIR/runtime.env"
FIXTURE_DIR="$ROOT/tests/fixtures/orbstack-library"
DEFAULT_RELEASE_IMAGE="ghcr.io/salutaris91/mediawerkzeug:main"
APP_URL="http://127.0.0.1:5812"

usage() {
    cat <<'EOF'
Usage: scripts/orbstack-test.sh <command> [options]

Commands:
  init                 Create shared test settings and copy the local fixture once.
  reset [--yes|--dry-run]
                       Replace media-run with a fresh fixture copy.
  build                Build the current Git branch as the local test image.
  start                Start the currently selected test image.
  smoke                Check health endpoint and Docker runtime capabilities.
  release [image]      Pull and start a registry image (default: GHCR main).
  status               Show paths, image source, Compose status, and published port.
  logs                 Follow logs of the test container only.
  stop                 Stop the test Compose project only.

The runtime never mounts the NAS. Settings are shared across Git worktrees;
resettable media stays below each worktree's .runtime-test/ directory.
EOF
}

assert_safe_media_dir() {
    if [[ "$MEDIA_DIR" != "$ROOT/.runtime-test/media-run" ]]; then
        echo "ERROR: Unsafe reset target rejected: $MEDIA_DIR" >&2
        exit 1
    fi
}

assert_safe_config_dir() {
    if [[ "$CONFIG_DIR" != "$PROJECT_ROOT/.runtime-test-shared/config" ]]; then
        echo "ERROR: Unsafe shared config target rejected: $CONFIG_DIR" >&2
        exit 1
    fi
}

write_runtime_env() {
    local image="$1"
    local source="$2"
    mkdir -p "$RUNTIME_DIR"
    {
        printf 'MW_TEST_UID=%s\n' "$(id -u)"
        printf 'MW_TEST_GID=%s\n' "$(id -g)"
        printf 'MW_TEST_IMAGE=%s\n' "$image"
        printf 'MW_TEST_SOURCE=%s\n' "$source"
        printf 'MW_TEST_CONFIG_DIR=%s\n' "$CONFIG_DIR"
    } > "$ENV_FILE"
}

ensure_runtime_env() {
    local image="medienwerkzeug:orbstack-local"
    local source="not-built"
    if [[ -f "$ENV_FILE" ]]; then
        image="$(awk -F= '$1 == "MW_TEST_IMAGE" {sub(/^[^=]*=/, ""); print; exit}' "$ENV_FILE")"
        source="$(awk -F= '$1 == "MW_TEST_SOURCE" {sub(/^[^=]*=/, ""); print; exit}' "$ENV_FILE")"
        image="${image:-medienwerkzeug:orbstack-local}"
        source="${source:-not-built}"
    fi
    if [[ ! -f "$ENV_FILE" ]] || ! grep -q '^MW_TEST_CONFIG_DIR=' "$ENV_FILE"; then
        write_runtime_env "$image" "$source"
    fi
}

compose() {
    ensure_runtime_env
    docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" "$@"
}

require_docker() {
    if ! docker info >/dev/null 2>&1; then
        echo "ERROR: Docker is unavailable. Start OrbStack and try again." >&2
        exit 1
    fi
}

copy_fixture() {
    mkdir -p "$MEDIA_DIR"
    cp -R "$FIXTURE_DIR"/. "$MEDIA_DIR"/
}

init_runtime() {
    assert_safe_media_dir
    assert_safe_config_dir
    mkdir -p "$CONFIG_DIR" "$MEDIA_DIR"
    ensure_runtime_env
    if [[ -z "$(find "$MEDIA_DIR" -mindepth 1 -print -quit)" ]]; then
        copy_fixture
        echo "Fixture copied to $MEDIA_DIR"
    else
        echo "Existing media-run preserved: $MEDIA_DIR"
    fi
    echo "Shared persistent test config: $CONFIG_DIR"
    echo "Worktree-local test media: $MEDIA_DIR"
}

reset_runtime() {
    local mode="confirm"
    case "${1:-}" in
        --yes) mode="yes" ;;
        --dry-run) mode="dry-run" ;;
        "") ;;
        *) echo "ERROR: Unknown reset option: $1" >&2; exit 2 ;;
    esac

    assert_safe_media_dir
    echo "Reset target: $MEDIA_DIR"
    echo "Fixture source: $FIXTURE_DIR"
    if [[ "$mode" == "dry-run" ]]; then
        echo "Dry run: no files changed."
        return
    fi
    if [[ "$mode" != "yes" ]]; then
        if [[ ! -t 0 ]]; then
            echo "ERROR: Interactive confirmation required; use --yes explicitly." >&2
            exit 2
        fi
        read -r -p "Replace all files in media-run? [y/N] " answer
        if [[ "$answer" != "y" && "$answer" != "Y" ]]; then
            echo "Reset cancelled."
            return
        fi
    fi

    mkdir -p "$MEDIA_DIR"
    find "$MEDIA_DIR" -mindepth 1 -maxdepth 1 -exec rm -rf -- {} +
    copy_fixture
    echo "media-run restored from fixture. Persistent config was not changed."
}

wait_for_health() {
    local attempt=1
    while (( attempt <= 30 )); do
        if curl --fail --silent "$APP_URL/api/healthz" >/dev/null; then
            echo "Application is ready: $APP_URL"
            return
        fi
        sleep 1
        ((attempt += 1))
    done
    echo "ERROR: Application did not become healthy. Run: scripts/orbstack-test.sh logs" >&2
    exit 1
}

smoke_test() {
    local health capabilities
    health="$(curl --fail --silent "$APP_URL/api/healthz")"
    capabilities="$(curl --fail --silent "$APP_URL/api/system/capabilities")"
    if [[ "$health" != *'"ok":true'* ]]; then
        echo "ERROR: Unexpected health response: $health" >&2
        exit 1
    fi
    if [[ "$capabilities" != *'"runtime":"docker"'* ]]; then
        echo "ERROR: Container does not report Docker runtime: $capabilities" >&2
        exit 1
    fi
    echo "Smoke test passed: health=ok, runtime=docker, url=$APP_URL"
}

build_branch() {
    local ref sha
    require_docker
    init_runtime
    ref="$(git -C "$ROOT" branch --show-current)"
    sha="$(git -C "$ROOT" rev-parse --short HEAD)"
    write_runtime_env "medienwerkzeug:orbstack-local" "branch-${ref}-${sha}"
    compose build
    echo "Built current branch: $ref ($sha)"
}

start_runtime() {
    require_docker
    init_runtime
    compose up -d --no-build
    wait_for_health
    smoke_test
}

start_release() {
    local image="${1:-$DEFAULT_RELEASE_IMAGE}"
    require_docker
    init_runtime
    docker pull "$image"
    write_runtime_env "$image" "registry-${image}"
    compose up -d --no-build
    wait_for_health
    smoke_test
}

show_status() {
    ensure_runtime_env
    echo "Shared test config: $CONFIG_DIR"
    echo "Worktree-local media: $MEDIA_DIR"
    echo "Runtime metadata:"
    sed 's/^/  /' "$ENV_FILE"
    if docker info >/dev/null 2>&1; then
        compose ps
        docker port medienwerkzeug-orbstack-test 2>/dev/null || true
    else
        echo "Docker is unavailable; OrbStack may be stopped."
    fi
}

command="${1:-}"
case "$command" in
    init) init_runtime ;;
    reset) reset_runtime "${2:-}" ;;
    build) build_branch ;;
    start) start_runtime ;;
    smoke) smoke_test ;;
    release) start_release "${2:-}" ;;
    status) show_status ;;
    logs) require_docker; compose logs --follow medienwerkzeug ;;
    stop) require_docker; compose down ;;
    help|-h|--help) usage ;;
    "") usage; exit 2 ;;
    *) echo "ERROR: Unknown command: $command" >&2; usage; exit 2 ;;
esac
