#!/bin/bash
#
# config.sh - Configuration settings and command-line argument processing
#
# Defines global constants, paths, and handles command-line arguments
# for the deployment system.

# ------------------------------------------------
# Core Settings
# ------------------------------------------------

# Exit behavior - expanded safety options
set -eo pipefail  # Exit on error, and error if any part of a pipe fails

# Exit status codes
readonly EXIT_SUCCESS=0
readonly EXIT_GENERAL_ERROR=1

# ANSI color codes for output formatting
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[0;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m'  # No Color

# ------------------------------------------------
# Paths and Files
# ------------------------------------------------

# Dynamically detect workspace directory (parent of the deployment-modules directory)
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly WORKSPACE_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
readonly LOG_DIR="${WORKSPACE_DIR}/logs"
readonly FRONTEND_DIR="${WORKSPACE_DIR}/frontend" 
readonly BACKEND_DIR="${WORKSPACE_DIR}/backend"
readonly GRADIO_DIR="${WORKSPACE_DIR}/gradio_app"
readonly TIMESTAMP="$(date '+%Y%m%d_%H%M%S')"

# File paths
readonly LOG_FILE="${LOG_DIR}/deployment.log"
readonly LOCK_FILE="/tmp/unistudy_deploy.lock"
readonly VERSION_FILE="${WORKSPACE_DIR}/version.txt"
readonly SCRIPT_NAME="$(basename "$0")"

# ------------------------------------------------
# Deployment Settings
# ------------------------------------------------

# Service configuration
readonly DOMAIN="unistudy.tech"

# ------------------------------------------------
# Cleanup and Log Rotation Settings
# ------------------------------------------------

# Log rotation thresholds
readonly LOG_ROTATION_MAX_AGE_DAYS=7
readonly LOG_ROTATION_MAX_SIZE_MB=10
readonly LOG_COMPRESSED_MAX_AGE_DAYS=30
readonly LOG_DIR_MAX_SIZE_MB=100

# ------------------------------------------------
# Runtime State
# ------------------------------------------------

# Runtime flags (defaults)
CONFIRM=true
VERBOSE=false

# Performance tracking
START_TIME="$(date +%s)"

# ------------------------------------------------
# Command Line Processing
# ------------------------------------------------

# Process command line arguments
parse_arguments() {
  for arg in "$@"; do
    case "$arg" in
      --no-confirm)
        CONFIRM=false
        log_info "Confirmation prompts disabled"
        shift
        ;;
      --verbose)
        VERBOSE=true
        log_info "Verbose mode enabled"
        shift
        ;;
      --help)
        show_usage
        exit $EXIT_SUCCESS
        ;;
      *)
        echo -e "${RED}Unknown option: $arg${NC}"
        echo "Use --help for usage information"
        exit $EXIT_GENERAL_ERROR
        ;;
    esac
  done
}

# Display usage information
show_usage() {
  echo "Usage: $SCRIPT_NAME [OPTIONS]"
  echo ""
  echo "Options:"
  echo "  --no-confirm       Skip confirmation prompt before deployment"
  echo "  --verbose          Show detailed output of all operations"
  echo "  --help             Show this help message"
} 