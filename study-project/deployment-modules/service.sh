#!/bin/bash
set -eo pipefail
#
# service.sh - Frontend build and service management
#
# Handles building the frontend application and
# managing PM2 services during deployment.

# ------------------------------------------------
# Frontend Operations
# ------------------------------------------------

# Build frontend application with production settings
build_frontend() {
  log_info "Building frontend application" "FRONTEND"
  
  # Save current directory to return to later
  local original_dir
  original_dir=$(pwd)
  
  # Navigate to frontend directory
  cd "$FRONTEND_DIR" || {
    log_error "Cannot access frontend directory: $FRONTEND_DIR" "FRONTEND"
    return 1
  }
  
  # Create temporary file for command output
  local output_file
  output_file=$(mktemp)
  
  # Create a trap to ensure we return to original directory and clean up
  trap "cd \"$original_dir\"; rm -f \"$output_file\"" EXIT INT TERM
  
  local build_success=false
  
  # Run npm install and build
  log_info "Installing dependencies" "FRONTEND"
  if npm ci > "$output_file" 2>&1; then
    log_info "Running production build" "FRONTEND"
    if VITE_APP_ENV=production npm run build >> "$output_file" 2>&1; then
      build_success=true
    else
      log_error "Build command failed" "FRONTEND"
    fi
  else
    log_error "Dependency installation failed" "FRONTEND"
  fi
  
  # Show output in verbose mode or on failure
  if [ "$VERBOSE" = true ] || [ "$build_success" = false ]; then
    echo -e "${BLUE}Build output:${NC}"
    cat "$output_file"
  fi
  
  # Clean up
  rm -f "$output_file"
  
  # Verify build result
  if [ "$build_success" = true ]; then
    if [ -d "$FRONTEND_DIR/dist" ] && [ -f "$FRONTEND_DIR/dist/index.html" ]; then
      log_success "Frontend build completed successfully" "FRONTEND"
      # Return to original directory and clear trap
      cd "$original_dir"
      trap - EXIT INT TERM
      return 0
    else
      log_error "Build output is incomplete" "FRONTEND"
    fi
  fi
  
  # Return to original directory and clear trap on failure
  cd "$original_dir"
  trap - EXIT INT TERM
  return 1
}

# ------------------------------------------------
# Service Management
# ------------------------------------------------

# Reload PM2 services from ecosystem config
reload_services() {
  log_info "Reloading PM2 services" "SERVICE"
  
  # Create temporary file for command output
  local output_file
  output_file=$(mktemp)
  
  # Add cleanup trap
  trap "rm -f \"$output_file\"" EXIT INT TERM
  
  # Attempt to reload services
  if pm2 reload ecosystem.config.js > "$output_file" 2>&1; then
    # Show output in verbose mode
    if [ "$VERBOSE" = true ]; then
      echo -e "${BLUE}PM2 reload output:${NC}"
      cat "$output_file"
    fi
    
    rm -f "$output_file"
    trap - EXIT INT TERM
    
    # Wait for services to stabilize
    local wait_time=5
    log_info "Waiting ${wait_time}s for services to stabilize" "SERVICE"
    sleep $wait_time
    log_success "Services reloaded successfully" "SERVICE"
    return 0
  else
    log_error "Service reload failed" "SERVICE"
    echo -e "${RED}PM2 reload output:${NC}"
    cat "$output_file"
    rm -f "$output_file"
    trap - EXIT INT TERM
    return 1
  fi
}

# Check PM2 service status
check_service_status() {
  log_info "Checking PM2 service status" "SERVICE"
  
  # Get service status directly using PM2 list
  local output_file
  output_file=$(mktemp)
  
  # Add cleanup trap
  trap "rm -f \"$output_file\"" EXIT INT TERM
  
  pm2 list > "$output_file" 2>&1
  
  # Get a count of online services (direct parsing of the PM2 output)
  local online_count
  online_count=$(grep -c "online" "$output_file" || echo 0)
  local total_count
  total_count=$(grep -c "│" "$output_file" || echo 0)
  
  # Adjust for header row
  if [ $total_count -gt 0 ]; then
    total_count=$((total_count - 2))  # Subtract header and footer lines
  fi
  
  # Show full status in verbose mode
  if [ "$VERBOSE" = true ]; then
    echo -e "${BLUE}PM2 service status:${NC}"
    cat "$output_file"
  fi
  
  # Check if all services are online
  if [ $online_count -lt 1 ]; then
    log_error "No services are running (found 0 of $total_count online)" "SERVICE"
    rm -f "$output_file"
    trap - EXIT INT TERM
    return 1
  elif [ $online_count -lt $total_count ]; then
    log_error "Some services are not running (found $online_count of $total_count online)" "SERVICE"
    cat "$output_file"
    rm -f "$output_file"
    trap - EXIT INT TERM
    return 1
  fi
  
  log_success "All services are running ($online_count services online)" "SERVICE"
  rm -f "$output_file"
  trap - EXIT INT TERM
  return 0
} 