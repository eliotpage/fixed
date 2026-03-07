#!/bin/bash

cd "$(dirname "$0")"
cd app

if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo "POPMAP server launcher"
    echo "Usage: ./start_server.sh [options] [--port <port>] [--tile-dir <path>]"
    echo ""
    echo "Options:"
    echo "  -h, --help              Show this help message"
    echo "  -s, --setup-auth        Force reconfiguration of auth secrets"
    echo "  -n, --ngrok             Auto-install and setup ngrok tunnel"
    echo "  -l, --logs <0|1>        0=quiet (default), 1=show HTTP request logs"
    echo "  -t, --tiles-dir <path>  Path to tile root directory (must contain zoom folders)"
    echo ""
    echo "Examples:"
    echo "  ./start_server.sh                              # Start normally (quiet)"
    echo "  ./start_server.sh -s -n                       # Setup auth and ngrok"
    echo "  ./start_server.sh -l 1                        # Show logs"
    echo "  ./start_server.sh -s -n -l 1 --port 5001      # Full setup with verbose logs"
    echo "  ./start_server.sh -t /path/to/tiles            # Start with custom tile directory"
    exit 0
fi

ENV_FILE=".env"
FORCE_AUTH_SETUP=0
WANTS_NGROK=0
LOGS_VALUE=0
TILES_DIR=""
FORWARD_ARGS=()

while [ $# -gt 0 ]; do
    case "$1" in
        -n|--ngrok)
            WANTS_NGROK=1
            FORWARD_ARGS+=("--ngrok")
            shift
            ;;
        -s|--setup-auth)
            FORCE_AUTH_SETUP=1
            shift
            ;;
        -l|--logs)
            if [ $# -gt 1 ]; then
                LOGS_VALUE="$2"
                shift 2
            else
                echo "Error: -l/--logs requires a value (0 or 1)"
                exit 1
            fi
            ;;
        -t|--tiles-dir)
            if [ $# -gt 1 ]; then
                TILES_DIR="$2"
                FORWARD_ARGS+=("--tile-dir" "$2")
                shift 2
            else
                echo "Error: -t/--tiles-dir requires a path"
                exit 1
            fi
            ;;
        *)
            FORWARD_ARGS+=("$1")
            shift
            ;;
    esac
done

get_env_value() {
    local key="$1"
    if [ ! -f "$ENV_FILE" ]; then
        return 0
    fi
    grep -E "^${key}=" "$ENV_FILE" | tail -n 1 | cut -d '=' -f2-
}

upsert_env_value() {
    local key="$1"
    local value="$2"
    touch "$ENV_FILE"
    if grep -qE "^${key}=" "$ENV_FILE"; then
        sed -i "s|^${key}=.*|${key}=${value}|" "$ENV_FILE"
    else
        printf "%s=%s\n" "$key" "$value" >> "$ENV_FILE"
    fi
}

generate_secret() {
    if command -v openssl >/dev/null 2>&1; then
        openssl rand -hex 32
    else
        python3 -c "import secrets; print(secrets.token_hex(32))"
    fi
}

setup_auth_env_if_missing() {
    local existing_secret existing_conn_secret existing_mail_user existing_mail_pass
    existing_secret="$(get_env_value SECRET_KEY)"
    existing_conn_secret="$(get_env_value POPMAP_CONNECTION_SECRET)"
    existing_mail_user="$(get_env_value MAIL_USERNAME)"
    existing_mail_pass="$(get_env_value MAIL_PASSWORD)"

    if [ "$FORCE_AUTH_SETUP" -eq 1 ]; then
        echo "[Server Setup] --setup-auth detected: forcing auth environment prompts."
        existing_secret=""
        existing_conn_secret=""
        existing_mail_user=""
        existing_mail_pass=""
    fi

    if [ -n "$existing_secret" ] && [ -n "$existing_conn_secret" ] && [ -n "$existing_mail_user" ] && [ -n "$existing_mail_pass" ]; then
        return 0
    fi

    if [ ! -t 0 ]; then
        echo "[Server Setup] Missing auth env values in app/.env, but no interactive terminal is available."
        echo "[Server Setup] Add SECRET_KEY, POPMAP_CONNECTION_SECRET, MAIL_USERNAME, MAIL_PASSWORD to app/.env."
        return 0
    fi

    echo ""
    echo "============================================================"
    echo "  POPMAP SERVER - Environment Setup"
    echo "============================================================"
    echo ""
    echo "[Server Setup] Missing values will be generated/prompted and"
    echo "[Server Setup] saved to app/.env"
    echo ""

    if [ -z "$existing_secret" ]; then
        generated_secret="$(generate_secret)"
        printf "SECRET_KEY is missing. Use generated value? [Y/n]: "
        read -r use_generated
        if [ "$use_generated" = "n" ] || [ "$use_generated" = "N" ]; then
            printf "Enter SECRET_KEY: "
            read -r user_secret
            if [ -n "$user_secret" ]; then
                upsert_env_value SECRET_KEY "$user_secret"
            else
                upsert_env_value SECRET_KEY "$generated_secret"
            fi
        else
            upsert_env_value SECRET_KEY "$generated_secret"
        fi
    fi

    if [ -z "$existing_conn_secret" ]; then
        generated_conn_secret="$(generate_secret)"
        printf "POPMAP_CONNECTION_SECRET is missing. Use generated value? [Y/n]: "
        read -r use_generated_conn
        if [ "$use_generated_conn" = "n" ] || [ "$use_generated_conn" = "N" ]; then
            printf "Enter POPMAP_CONNECTION_SECRET: "
            read -r user_conn_secret
            if [ -n "$user_conn_secret" ]; then
                upsert_env_value POPMAP_CONNECTION_SECRET "$user_conn_secret"
            else
                upsert_env_value POPMAP_CONNECTION_SECRET "$generated_conn_secret"
            fi
        else
            upsert_env_value POPMAP_CONNECTION_SECRET "$generated_conn_secret"
        fi
    fi

    if [ -z "$existing_mail_user" ]; then
        printf "Enter MAIL_USERNAME (email for OTP), or leave blank to skip email setup: "
        read -r mail_user
        if [ -n "$mail_user" ]; then
            upsert_env_value MAIL_USERNAME "$mail_user"
        fi
    fi

    if [ -z "$existing_mail_pass" ]; then
        current_mail_user="$(get_env_value MAIL_USERNAME)"
        if [ -n "$current_mail_user" ]; then
            printf "Enter MAIL_PASSWORD (app password) for %s: " "$current_mail_user"
            read -rs mail_pass
            printf "\n"
            if [ -n "$mail_pass" ]; then
                upsert_env_value MAIL_PASSWORD "$mail_pass"
            fi
        fi
    fi
    
    echo ""
    echo "[Server Setup] Configuration saved to app/.env"
    echo ""
}

ensure_ngrok() {
    if command -v ngrok >/dev/null 2>&1; then
        return 0
    fi

    echo "[Setup] --ngrok detected and ngrok is missing. Attempting install..."

    if command -v brew >/dev/null 2>&1; then
        brew install ngrok/ngrok/ngrok >/dev/null 2>&1 || brew install ngrok >/dev/null 2>&1
    elif command -v apt-get >/dev/null 2>&1; then
        if command -v sudo >/dev/null 2>&1; then
            sudo apt-get update >/dev/null 2>&1 && (sudo apt-get install -y ngrok >/dev/null 2>&1 || sudo apt-get install -y ngrok-client >/dev/null 2>&1)
        else
            apt-get update >/dev/null 2>&1 && (apt-get install -y ngrok >/dev/null 2>&1 || apt-get install -y ngrok-client >/dev/null 2>&1)
        fi
    fi

    if command -v ngrok >/dev/null 2>&1; then
        echo "[Setup] ngrok installed successfully."
        return 0
    fi

    echo "[Setup] Could not auto-install ngrok."
    echo "[Setup] Install ngrok manually from https://ngrok.com/download and rerun with --ngrok."
    return 1
}

setup_tiles_dir_if_missing() {
    if [ -n "$TILES_DIR" ]; then
        return 0
    fi

    DEFAULT_TILES_DIR="static/tiles"
    if [ -d "$DEFAULT_TILES_DIR" ]; then
        echo "[Setup] Using default tiles directory: $DEFAULT_TILES_DIR"
        TILES_DIR="$DEFAULT_TILES_DIR"
        FORWARD_ARGS+=("--tile-dir" "$TILES_DIR")
        return 0
    fi

    if [ ! -t 0 ]; then
        echo "[Setup] No tiles directory provided and no interactive terminal available."
        echo "[Setup] Provide the tiles directory using: -t <path> or --tiles-dir <path>"
        return 1
    fi

    echo "[Setup] Tiles directory configuration"
    printf "Enter path to tiles root directory (contains zoom folders): "
    read -r user_tiles_dir
    
    if [ -z "$user_tiles_dir" ]; then
        echo "[Setup] No tiles directory provided. Using default: $DEFAULT_TILES_DIR"
        TILES_DIR="$DEFAULT_TILES_DIR"
    else
        if [ ! -d "$user_tiles_dir" ]; then
            echo "[Setup] Warning: Directory does not exist: $user_tiles_dir"
            echo "[Setup] Proceeding anyway - app will handle validation."
        fi
        TILES_DIR="$user_tiles_dir"
    fi
    
    FORWARD_ARGS+=("--tile-dir" "$TILES_DIR")
}

if [ "$WANTS_NGROK" -eq 1 ]; then
    ensure_ngrok || true
fi

# Check if .env exists or needs setup
if [ ! -f "$ENV_FILE" ] || [ "$FORCE_AUTH_SETUP" -eq 1 ]; then
    if [ ! -f "$ENV_FILE" ]; then
        echo "[Server] No .env file found."
        if [ -t 0 ]; then
            echo "[Server] Would you like to set it up now? (Y/n)"
            read -r setup_response
            if [ "$setup_response" != "n" ] && [ "$setup_response" != "N" ]; then
                FORCE_AUTH_SETUP=1
            fi
        fi
    fi
    
    if [ "$FORCE_AUTH_SETUP" -eq 1 ]; then
        setup_auth_env_if_missing
    elif [ ! -f "$ENV_FILE" ]; then
        echo "[Server] .env file is required. Options:"
        echo "  1. Run: ./start_server.sh -s (to set up interactively)"
        echo "  2. Copy app/.env.example to app/.env and edit it manually"
        exit 1
    fi
else
    setup_auth_env_if_missing
fi

setup_tiles_dir_if_missing

if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate

export PIP_DISABLE_PIP_VERSION_CHECK=1
pip install -q -r requirements.txt

export APP_MODE=server

if [ "$LOGS_VALUE" -eq 1 ]; then
    export QUIET_HTTP_LOGS=0
else
    export QUIET_HTTP_LOGS=1
fi

python3 app.py --server "${FORWARD_ARGS[@]}"
