#!/bin/bash

cd "$(dirname "$0")"
cd app

if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo "POPMAP client launcher"
    echo "Usage: ./start_client.sh -u <connection-id> [options] [--port <port>]"
    echo ""
    echo "Options:"
    echo "  -h, --help              Show this help message"
    echo "  -s, --setup-env         Setup/configure .env file for client"
    echo "  -u, --uid <id>          Connection ID (required - share with server)"
    echo "  -l, --logs <0|1>        0=quiet (default), 1=show HTTP request logs"
    echo "  -p, --port <port>       Port to run client on (default: 5000)"
    echo ""
    echo "Examples:"
    echo "  ./start_client.sh -s                          # Setup .env file first time"
    echo "  ./start_client.sh -u abc123def                # Basic usage"
    echo "  ./start_client.sh -u abc123def -l 1           # Show logs"
    echo "  ./start_client.sh -u abc123def -p 5002        # Custom port"
    echo "  ./start_client.sh -u abc123def -l 1 -p 5002   # Both options"
    exit 0
fi

ENV_FILE=".env"
FORCE_ENV_SETUP=0
LOGS_VALUE=0
FORWARD_ARGS=()

while [ $# -gt 0 ]; do
    case "$1" in
        -s|--setup-env)
            FORCE_ENV_SETUP=1
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
        -u|--uid)
            if [ $# -gt 1 ]; then
                FORWARD_ARGS+=("--uid" "$2")
                shift 2
            else
                echo "Error: -u/--uid requires a connection ID"
                exit 1
            fi
            ;;
        -p|--port)
            if [ $# -gt 1 ]; then
                FORWARD_ARGS+=("--port" "$2")
                shift 2
            else
                echo "Error: -p/--port requires a port number"
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

setup_client_env() {
    local existing_secret existing_conn_secret existing_mail_user existing_mail_pass
    existing_secret="$(get_env_value SECRET_KEY)"
    existing_conn_secret="$(get_env_value POPMAP_CONNECTION_SECRET)"
    existing_mail_user="$(get_env_value MAIL_USERNAME)"
    existing_mail_pass="$(get_env_value MAIL_PASSWORD)"

    if [ "$FORCE_ENV_SETUP" -eq 1 ]; then
        echo "[Client Setup] --setup-env detected: forcing environment configuration."
        existing_secret=""
        existing_conn_secret=""
        existing_mail_user=""
        existing_mail_pass=""
    fi

    if [ -n "$existing_secret" ] && [ -n "$existing_conn_secret" ]; then
        return 0
    fi

    if [ ! -t 0 ]; then
        echo "[Client Setup] Missing required values in app/.env, but no interactive terminal is available."
        echo "[Client Setup] Required: SECRET_KEY, POPMAP_CONNECTION_SECRET"
        echo "[Client Setup] Copy the .env file from your server, or run with -s flag in interactive mode."
        return 0
    fi

    echo ""
    echo "============================================================"
    echo "  POPMAP CLIENT - Environment Setup"
    echo "============================================================"
    echo ""
    echo "The client needs the same .env values as your server."
    echo "You should have already set up a server and received these"
    echo "values from it."
    echo ""
    
    if [ -z "$existing_secret" ]; then
        echo "Enter SECRET_KEY (from server's .env file):"
        read -r secret_key
        if [ -n "$secret_key" ]; then
            upsert_env_value SECRET_KEY "$secret_key"
        else
            echo "[Client Setup] SECRET_KEY is required. Exiting."
            exit 1
        fi
    fi

    if [ -z "$existing_conn_secret" ]; then
        echo ""
        echo "Enter POPMAP_CONNECTION_SECRET (from server's .env file):"
        echo "(This MUST match the server's secret exactly)"
        read -r conn_secret
        if [ -n "$conn_secret" ]; then
            upsert_env_value POPMAP_CONNECTION_SECRET "$conn_secret"
        else
            echo "[Client Setup] POPMAP_CONNECTION_SECRET is required. Exiting."
            exit 1
        fi
    fi

    if [ -z "$existing_mail_user" ]; then
        echo ""
        echo "Enter MAIL_USERNAME (optional, press Enter to skip):"
        read -r mail_user
        if [ -n "$mail_user" ]; then
            upsert_env_value MAIL_USERNAME "$mail_user"
        fi
    fi

    if [ -z "$existing_mail_pass" ]; then
        current_mail_user="$(get_env_value MAIL_USERNAME)"
        if [ -n "$current_mail_user" ]; then
            echo ""
            echo "Enter MAIL_PASSWORD for $current_mail_user (optional, press Enter to skip):"
            read -rs mail_pass
            echo ""
            if [ -n "$mail_pass" ]; then
                upsert_env_value MAIL_PASSWORD "$mail_pass"
            fi
        fi
    fi

    echo ""
    echo "[Client Setup] Configuration saved to app/.env"
    echo ""
}

# Check if .env exists or needs setup
if [ ! -f "$ENV_FILE" ] || [ "$FORCE_ENV_SETUP" -eq 1 ]; then
    if [ ! -f "$ENV_FILE" ]; then
        echo "[Client] No .env file found."
        if [ -t 0 ]; then
            echo "[Client] Would you like to set it up now? (Y/n)"
            read -r setup_response
            if [ "$setup_response" != "n" ] && [ "$setup_response" != "N" ]; then
                FORCE_ENV_SETUP=1
            fi
        fi
    fi
    
    if [ "$FORCE_ENV_SETUP" -eq 1 ]; then
        setup_client_env
    elif [ ! -f "$ENV_FILE" ]; then
        echo "[Client] .env file is required. Options:"
        echo "  1. Copy .env file from your server to app/.env"
        echo "  2. Run: ./start_client.sh -s (to set up interactively)"
        echo "  3. Copy app/.env.example to app/.env and edit it manually"
        exit 1
    fi
fi

if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate

export PIP_DISABLE_PIP_VERSION_CHECK=1
pip install -q -r requirements.txt

export APP_MODE=client

if [ "$LOGS_VALUE" -eq 1 ]; then
    export QUIET_HTTP_LOGS=0
else
    export QUIET_HTTP_LOGS=1
fi

python3 app.py "${FORWARD_ARGS[@]}"
