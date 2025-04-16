set -eo pipefail
#
# deploy.sh - Deployment script for unistudy.tech

SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}")"
SCRIPT_DIR="$(dirname "$SCRIPT_PATH")"
MODULES_DIR="$SCRIPT_DIR/deployment-modules"

# Global cleanup trap for unexpected exits
cleanup() {
  local exit_code=$?
  echo -e "\nScript interrupted or error occurred. Cleaning up..."
  
  if [ -n "${ORIGINAL_DIR:-}" ]; then
    cd "$ORIGINAL_DIR"
  fi
  
  if [ $exit_code -ne 0 ]; then
    echo -e "Deployment failed with exit code $exit_code"
    echo -e "Check logs for details: $LOG_FILE"
  fi
  
  exit $exit_code
}

trap cleanup INT TERM

if [ ! -d "$MODULES_DIR" ]; then
  echo "ERROR: Deployment modules not found at: $MODULES_DIR"
  exit 1
fi

for module in config.sh utils.sh; do
  module_path="$MODULES_DIR/$module"
  if [ ! -f "$module_path" ]; then
    echo "ERROR: Required module not found: $module"
    exit 1
  fi
  # shellcheck source=/dev/null
  source "$module_path"
done

module_path="$MODULES_DIR/register_command.sh"
if [ -f "$module_path" ]; then
  source "$module_path"
  offer_command_registration "$@"
else
  echo "INFO: Command registration module not found, skipping registration check"
fi

for module in security.sh service.sh version_info.sh summary.sh; do
  module_path="$MODULES_DIR/$module"
  if [ ! -f "$module_path" ]; then
    echo "ERROR: Required module not found: $module"
    exit 1
  fi
  source "$module_path"
done

# ------------------------------------------------
# Main Workflow
# ------------------------------------------------

main() {
  ORIGINAL_DIR="$(pwd)"
  
  cd "$WORKSPACE_DIR" || { 
    echo "ERROR: Cannot access workspace directory: $WORKSPACE_DIR"
    exit $EXIT_GENERAL_ERROR
  }
  
  parse_arguments "$@"
  
  initialize_log
  log_info "Starting deployment script" "DEPLOY"
  
  display_header
  log_info "Starting deployment (${TIMESTAMP})" "DEPLOY"
  check_lock
  confirm_deployment
  
  run_step "Checking environment" "check_permissions && check_dependencies" "SYSTEM" || 
    exit $EXIT_GENERAL_ERROR
  
  run_step "Building frontend" build_frontend "FRONTEND" || {
    log_error "Frontend build failed - deployment aborted" "FRONTEND"
    exit $EXIT_GENERAL_ERROR
  }
  
  run_step "Generating version info" generate_version_info "VERSION"
  run_step "Updating services" reload_services "SERVICE" || {
    log_error "Service reload failed - deployment aborted" "SERVICE"
    exit $EXIT_GENERAL_ERROR
  }
  
  run_step "Checking service status" check_service_status "SERVICE" || {
    log_error "Service status check failed - deployment might be unstable" "SERVICE"
    exit $EXIT_GENERAL_ERROR
  }
  
  deployment_summary
  log_success "Deployment completed successfully" "DEPLOY"
  display_footer
  
  cd "$ORIGINAL_DIR"
  
  exit $EXIT_SUCCESS
}

main "$@" 