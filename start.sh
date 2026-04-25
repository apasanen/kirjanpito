#!/usr/bin/env bash

set -euo pipefail

cd "$(dirname "$0")"

mkdir -p data/receipts split_output
if [[ -f accounting.db && ! -f data/accounting.db ]]; then
    mv accounting.db data/accounting.db
fi
if [[ ! -f data/accounting.db ]]; then
    : > data/accounting.db
fi
if [[ -d receipts ]]; then
    find receipts -mindepth 1 -maxdepth 1 -exec mv {} data/receipts/ \;
    rmdir receipts 2>/dev/null || true
fi

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

if [[ "${1:-}" == "--nodocker" ]]; then
    run_local
    exit 0
fi

if [[ "${1:-}" == "--test" ]]; then
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
