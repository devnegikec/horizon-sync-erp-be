#!/usr/bin/env bash
# Wrapper to deploy the identity-service using deploy_to_railway.sh
# Usage: ./deploy_identity_to_railway.sh [options]
# For non-interactive token use: RAILWAY_TOKEN=xxx ./deploy_identity_to_railway.sh -p <projectId> -e staging -m

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Forward all args to main deploy script, but force service to identity-service
"$SCRIPT_DIR/deploy_to_railway.sh" -s identity-service "$@"
