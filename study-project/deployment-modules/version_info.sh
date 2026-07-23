#!/bin/bash
set -eo pipefail
#
# version_info.sh - Deployment version tracking
#
# Creates a version information file with deployment metadata
# to track when and how the application was deployed.

# ------------------------------------------------
# Version File Generation
# ------------------------------------------------

# Get Python version, falling back to python3 if needed
get_python_version() {
  if command -v python &> /dev/null; then
    python --version 2>&1
  elif command -v python3 &> /dev/null; then
    python3 --version 2>&1
  else
    echo "Python not found"
  fi
}

# Generate deployment version information file
generate_version_info() {
  log_info "Generating version information" "VERSION"
  
  # Get needed version information with error handling
  local node_version
  if ! node_version="$(node -v 2>/dev/null)"; then
    node_version="Not available"
    log_error "Could not determine Node.js version" "VERSION"
  fi
  
  local npm_version
  if ! npm_version="$(npm -v 2>/dev/null)"; then
    npm_version="Not available"
    log_error "Could not determine npm version" "VERSION"
  fi
  
  local python_version
  python_version="$(get_python_version)"
  
  # Create version information with deployment metadata
  if ! cat > "$VERSION_FILE" << EOF
# unistudy.tech Deployment Information
# ===================================
Application: unistudy.tech
Deployed: $(date '+%Y-%m-%d %H:%M:%S')
Deployment ID: $TIMESTAMP

# Environment
# ===================================
Node.js: $node_version
npm: $npm_version
Python: $python_version
EOF
  then
    log_error "Failed to write version information file" "VERSION"
    return 1
  fi
  
  if [ -f "$VERSION_FILE" ]; then
    log_success "Version information generated" "VERSION"
    return 0
  else
    log_error "Version file was not created" "VERSION"
    return 1
  fi
} 