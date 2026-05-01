#!/usr/bin/env bash

set -euo pipefail

cd "$(dirname "$0")"

mode="docker"
profile="${DB_PROFILE:-default}"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --nodocker)
            mode="local"
            shift
            ;;
        --test)
            mode="test"
            shift
            ;;
        --profile)
            if [[ -z "${2:-}" ]]; then
                echo "ERROR: --profile requires a value."
                exit 1
            fi
            profile="$2"
            shift 2
            ;;
        *)
            echo "ERROR: Unknown option '$1'"
            echo "Usage: ./start.sh [--nodocker] [--test] [--profile NAME]"
            exit 1
            ;;
    esac
done

profile="$(printf '%s' "$profile" | sed 's/[^A-Za-z0-9._-]/_/g; s/^[._-]*//; s/[._-]*$//')"
if [[ -z "$profile" ]]; then
    profile="default"
fi

export DB_PROFILE="$profile"
if [[ -z "${DB_PATH:-}" && -z "${DATABASE_URL:-}" ]]; then
    if [[ "$profile" == "default" ]]; then
        export DB_PATH="data/accounting.db"
    else
        export DB_PATH="data/accounting_${profile}.db"
    fi
fi

mkdir -p data/receipts split_output
if [[ -f accounting.db && ! -f data/accounting.db ]]; then
    mv accounting.db data/accounting.db
fi
if [[ ! -f "$DB_PATH" ]]; then
    : > "$DB_PATH"
fi
if [[ -d receipts ]]; then
    find receipts -mindepth 1 -maxdepth 1 -exec mv {} data/receipts/ \;
    rmdir receipts 2>/dev/null || true
fi

echo "Using database profile: $DB_PROFILE"
echo "Database file: ${DB_PATH:-from DATABASE_URL}"

open_browser() {
    if command -v xdg-open >/dev/null 2>&1; then
        xdg-open "http://127.0.0.1:8000" >/dev/null 2>&1 || true
    elif command -v open >/dev/null 2>&1; then
        open "http://127.0.0.1:8000" >/dev/null 2>&1 || true
    fi
}

run_local() {
    echo "Starting Accounting Application without Docker..."
    open_browser
    .venv/bin/uvicorn app.main:app --reload --reload-exclude ".venv/*" --reload-exclude "data/receipts/*" --reload-exclude "split_output/*" --reload-exclude "*.db"
}

run_tests() {
    echo "Running tests with Docker (isolated database)..."
    compose_cmd=""
    if docker compose version >/dev/null 2>&1; then
        compose_cmd="docker compose"
    elif command -v docker-compose >/dev/null 2>&1 && docker-compose version >/dev/null 2>&1; then
        compose_cmd="docker-compose"
    fi
    
    if [[ -z "$compose_cmd" ]]; then
        echo "ERROR: Docker Compose not found."
        echo "Install Docker and ensure 'docker compose' or 'docker-compose' is available."
        exit 1
    fi
    
    DATABASE_URL=sqlite:////tmp/kirjanpito_test_docker.db $compose_cmd run --rm accounting-app pytest tests/ -v
}

if [[ "$mode" == "local" ]]; then
    run_local
    exit 0
fi

if [[ "$mode" == "test" ]]; then
    run_tests
    exit 0
fi

compose_cmd=""
if docker compose version >/dev/null 2>&1; then
    compose_cmd="docker compose"
elif command -v docker-compose >/dev/null 2>&1 && docker-compose version >/dev/null 2>&1; then
    compose_cmd="docker-compose"
fi

if [[ -z "$compose_cmd" ]]; then
    echo "ERROR: Docker Compose not found."
    echo "Install Docker and ensure 'docker compose' or 'docker-compose' is available."
    exit 1
fi

echo "Starting Accounting Application with Docker..."
open_browser
$compose_cmd up --build
