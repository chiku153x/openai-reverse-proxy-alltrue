#!/bin/bash

set -e

START_DIR=$(pwd)

# Utility: log with style
log() {
    echo -e "\033[1;34m[INFO]\033[0m $1"
}

error() {
    echo -e "\033[1;31m[ERROR]\033[0m $1"
}

# Validate OPENAI_API_KEY length in docker-compose.yml
validate_openai_key() {
    local key
    key=$(grep -E 'OPENAI_API_KEY[:=]' docker-compose.yml | head -n 1 | sed -E 's/.*[:=] *//;s/^["'\'']//;s/["'\'']$//')
    local key_length=${#key}

    if [ "$key_length" -le 30 ]; then
        error "OPENAI_API_KEY is missing or too short in docker-compose.yml"
        echo "→ Ensure it's in the format: OPENAI_API_KEY=your_api_key (length > 30)"
        exit 1
    fi

    log "OPENAI_API_KEY is set and valid (length: $key_length)."
}

# Generate TLS certificates
generate_cert() {
    local crt_file=$1
    local key_file=$2
    local conf_file=$3
    local name=$4

    if [ ! -f "$crt_file" ] || [ ! -f "$key_file" ]; then
        log "Generating $name certificates..."
        openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
            -keyout "$key_file" -out "$crt_file" \
            -config "$conf_file"
    fi
}

# Install everything from scratch
install() {
    log "Starting fresh installation..."
    log "Working directory: $START_DIR"

    if [ ! -d "$START_DIR/vllm/vllm-main" ]; then
        log "Cloning vllm main branch..."
        cd "$START_DIR/vllm"
        git clone --branch main https://github.com/vllm-project/vllm ./vllm-main

        log "Copying app.py..."
        cp "$START_DIR/vllm/app.py" ./vllm-main/

        log "Backing up original Dockerfile..."
        mv ./vllm-main/Dockerfile.cpu ./vllm-main/Dockerfile.cpu.back

        log "Applying modified Dockerfile..."
        cp "$START_DIR/vllm/Dockerfile.cpu.modified" ./vllm-main/Dockerfile.cpu
        cd "$START_DIR"
    fi

    generate_cert "$START_DIR/nginx/certs/server.crt" \
                  "$START_DIR/nginx/certs/server.key" \
                  "$START_DIR/nginx/certs/nginx_openssl.cnf" "server"

    generate_cert "$START_DIR/nginx/certs/guardian.crt" \
                  "$START_DIR/nginx/certs/guardian.key" \
                  "$START_DIR/nginx/certs/guardian_openssl.cnf" "guardian"
}

# Init: clean vllm-main and certs
init() {
    log "Resetting environment..."

    rm -rf "$START_DIR/vllm/vllm-main"
    rm -f "$START_DIR/nginx/certs/"*.crt "$START_DIR/nginx/certs/"*.key

    log "Environment cleaned."
}

# Commands
case "$1" in
    --all)
        validate_openai_key
        install
        log "Starting docker compose..."
        docker compose up --build
        ;;
    --start)
        log "Starting docker compose..."
        docker compose up --build
        ;;
    --stop)
        log "Stopping docker compose..."
        docker compose down -v
        ;;
    --init)
        init
        ;;
    *)
        echo -e "\033[1;33mUsage:\033[0m $0 [--all | --start | --stop | --init]"
        ;;
esac
