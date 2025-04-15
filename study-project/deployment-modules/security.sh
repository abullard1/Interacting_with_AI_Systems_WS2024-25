#!/bin/bash
set -eo pipefail
#
# security.sh - Deployment security, locking, and validation
#
# Handles process locking to prevent concurrent deployments
# and validates system requirements before deployment.

# ------------------------------------------------
# Process Locking
# ------------------------------------------------

# Ensure only one deployment runs at a time
check_lock() {
  # Check for existing lock
  if [ -f "$LOCK_FILE" ]; then
    if [ -r "$LOCK_FILE" ]; then
      local pid=$(cat "$LOCK_FILE" 2>/dev/null)
      if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
        log_error "Another deployment is already in progress (PID: $pid)" "LOCK"
        exit $EXIT_GENERAL_ERROR
      else
        log_info "Found stale lock file - removing" "LOCK"
        rm -f "$LOCK_FILE"
      fi
    else
      log_error "Found lock file but cannot read it - deployment aborted" "LOCK"
      exit $EXIT_GENERAL_ERROR
    fi
  fi
  
  # Create lock with PID and auto-cleanup on exit
  echo $$ > "$LOCK_FILE"
  trap "rm -f $LOCK_FILE; log_info 'Released deployment lock' 'LOCK'" EXIT
  log_info "Deployment lock acquired" "LOCK"
}

# ------------------------------------------------
# System Validation
# ------------------------------------------------

# Check directory permissions and create if missing
check_directory() {
  local dir="$1"
  local name="$2"
  
  if [ ! -d "$dir" ]; then
    log_info "Creating directory: $name" "PERM"
    if ! mkdir -p "$dir" 2>/dev/null; then
      log_error "Cannot create directory: $name" "PERM"
      return 1
    fi
  elif [ ! -w "$dir" ]; then
    log_error "No write permission for directory: $name" "PERM"
    return 1
  fi
  
  return 0
}

# Verify appropriate permissions for deployment
check_permissions() {
  local error_count=0
  
  # Define critical directories with friendly names
  declare -A directories=(
    ["$WORKSPACE_DIR"]="Workspace"
    ["$LOG_DIR"]="Logs"
    ["$FRONTEND_DIR"]="Frontend"
    ["$BACKEND_DIR"]="Backend"
    ["$GRADIO_DIR"]="Gradio App"
  )
  
  # Check each directory
  for dir in "${!directories[@]}"; do
    check_directory "$dir" "${directories[$dir]}" || ((error_count++))
  done
  
  # PM2 access requires appropriate user privileges
  if ! command -v pm2 &> /dev/null; then
    log_error "PM2 not accessible - check user permissions" "PERM"
    ((error_count++))
  fi
  
  # Exit if permission errors found
  if [ $error_count -gt 0 ]; then
    log_error "Permission checks failed with $error_count errors" "PERM"
    exit $EXIT_GENERAL_ERROR
  fi
  
  log_info "Permission checks passed" "PERM"
}

# Check if a command exists on the system
check_command() {
  local cmd="$1"
  local alt_cmd="$2"
  local version=""
  
  if command -v "$cmd" &> /dev/null; then
    # Primary command exists
    if ! version=$(eval "$cmd --version" 2>&1 | head -n1); then
      version="Unknown version"
    fi
    log_info "✓ $cmd ($version)" "DEP"
    return 0
  elif [ -n "$alt_cmd" ] && command -v "$alt_cmd" &> /dev/null; then
    # Alternative command exists
    if ! version=$(eval "$alt_cmd --version" 2>&1 | head -n1); then
      version="Unknown version"
    fi
    log_info "✓ $alt_cmd ($version) [alternative for $cmd]" "DEP"
    
    # Create symlink or alias if needed
    if [[ "$cmd" == "python" && "$alt_cmd" == "python3" ]]; then
      # Use python3 for python commands
      log_info "Using python3 for python commands" "DEP"
      alias python="python3"
    fi
    
    return 0
  fi
  
  # Command not found
  log_error "✗ Missing: $cmd" "DEP"
  return 1
}

# Validate all required dependencies
check_dependencies() {
  local error_count=0
  
  # Required CLI tools with versions and alternatives
  log_info "Checking required tools:" "DEP"
  
  # Check npm and node
  check_command "npm" "" || ((error_count++))
  check_command "node" "" || ((error_count++))
  check_command "pm2" "" || ((error_count++))
  
  # Check python with fallback to python3
  check_command "python" "python3" || ((error_count++))
  
  # Check for gzip (used for log rotation)
  check_command "gzip" "" || log_info "gzip not found - log rotation may be limited" "DEP"
  
  # Required configuration files
  if [ ! -f "${WORKSPACE_DIR}/ecosystem.config.js" ]; then
    log_error "PM2 configuration missing: ecosystem.config.js" "DEP"
    ((error_count++))
  elif [ ! -r "${WORKSPACE_DIR}/ecosystem.config.js" ]; then
    log_error "PM2 configuration not readable: ecosystem.config.js" "DEP"
    ((error_count++))
  fi
  
  # Exit if dependencies are missing
  if [ $error_count -gt 0 ]; then
    log_error "Dependency check failed with $error_count errors" "DEP"
    exit $EXIT_GENERAL_ERROR
  fi
  
  log_info "All dependencies available" "DEP"
} 