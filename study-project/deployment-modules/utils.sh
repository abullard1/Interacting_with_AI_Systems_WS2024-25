#!/bin/bash
set -eo pipefail
#
# utils.sh - Logging and step execution utilities
#
# Provides core functionality for logging, progress display,
# and standardized execution of deployment steps.

# ------------------------------------------------
# Display Constants
# ------------------------------------------------

# Status indicators and spinner settings
SUCCESS_MARK="${GREEN}✓${NC}"
WARNING_MARK="${YELLOW}⚠${NC}"
ERROR_MARK="${RED}✗${NC}"
SPINNER_CHARS=('⠋' '⠙' '⠹' '⠸' '⠼' '⠴' '⠦' '⠧' '⠇' '⠏')
CURRENT_STEP=""
SPINNER_PID=""

# ------------------------------------------------
# Progress Display
# ------------------------------------------------

# Start a spinner for the current task
start_spinner() {
  # Skip spinner in verbose mode
  [ "$VERBOSE" = true ] && return
  
  CURRENT_STEP="$1"
  
  # Define spinner animation function
  _spin() {
    local i=0
    while true; do
      echo -ne "\r\033[K${BLUE}${SPINNER_CHARS[$i]}${NC} ${CURRENT_STEP}..."
      i=$(( (i+1) % ${#SPINNER_CHARS[@]} ))
      sleep 0.1
    done
  }
  
  # Start spinner in background
  _spin &
  SPINNER_PID=$!
  disown
}

# Stop the spinner and show final status
stop_spinner() {
  local status=$1
  
  # Skip spinner in verbose mode
  [ "$VERBOSE" = true ] && return
  
  # Kill the spinner process
  if [ -n "$SPINNER_PID" ]; then
    kill $SPINNER_PID >/dev/null 2>&1
    wait $SPINNER_PID 2>/dev/null || true
    SPINNER_PID=""
  fi
  
  # Display final status
  echo -ne "\r\033[K"
  if [ "$status" = "success" ]; then
    echo -e "${SUCCESS_MARK} ${CURRENT_STEP}"
  else
    echo -e "${ERROR_MARK} ${CURRENT_STEP}"
  fi
}

# ------------------------------------------------
# Logging Functions
# ------------------------------------------------

# Ensure log directory exists
ensure_log_directory() {
  if [ ! -d "$LOG_DIR" ]; then
    mkdir -p "$LOG_DIR" 2>/dev/null || {
      echo "ERROR: Cannot create log directory: $LOG_DIR" >&2
      # Fall back to temp directory if log dir creation fails
      LOG_DIR="/tmp"
      LOG_FILE="$LOG_DIR/deployment.log"
      echo "WARNING: Using fallback log location: $LOG_FILE" >&2
    }
  fi
}

# Initialize log file with deployment session header
initialize_log() {
  ensure_log_directory
  
  # Create a structured header for this deployment session
  cat > "$LOG_FILE" << EOF
===============================================
DEPLOYMENT SESSION: $(date '+%Y-%m-%d %H:%M:%S')
===============================================
Deployment ID: $TIMESTAMP
User: $(whoami)
Hostname: $(hostname)
Working Directory: $WORKSPACE_DIR
===============================================

EOF
}

# Simple logging function
log_info() {
  local message="$1"
  local component="${2:-MAIN}"
  local console_message="[$component] $message"
  local log_timestamp=$(date '+%Y-%m-%d %H:%M:%S')
  
  # Write to log file
  ensure_log_directory
  echo "[$log_timestamp] [INFO] [$component] $message" >> "$LOG_FILE" 2>/dev/null
  
  # Print to console if verbose
  if [ "$VERBOSE" = true ]; then
    if [ -n "$SPINNER_PID" ]; then
      echo -ne "\r\033[K"
    fi
    echo -e "$console_message"
  fi
}

# Log error message (always displayed)
log_error() {
  local message="$1"
  local component="${2:-MAIN}"
  local console_message="[$component] $message"
  local log_timestamp=$(date '+%Y-%m-%d %H:%M:%S')
  
  # Write to log file
  ensure_log_directory
  echo "[$log_timestamp] [ERROR] [$component] $message" >> "$LOG_FILE" 2>/dev/null
  
  # Always print errors to console
  if [ -n "$SPINNER_PID" ]; then
    echo -ne "\r\033[K"
  fi
  echo -e "${RED}$console_message${NC}"
}

# Log success message
log_success() {
  local message="$1"
  local component="${2:-MAIN}"
  local console_message="[$component] $message"
  local log_timestamp=$(date '+%Y-%m-%d %H:%M:%S')
  
  # Write to log file
  ensure_log_directory
  echo "[$log_timestamp] [SUCCESS] [$component] $message" >> "$LOG_FILE" 2>/dev/null
  
  # Print to console if verbose
  if [ "$VERBOSE" = true ]; then
    if [ -n "$SPINNER_PID" ]; then
      echo -ne "\r\033[K"
    fi
    echo -e "${GREEN}$console_message${NC}"
  fi
}

# ------------------------------------------------
# Step Execution
# ------------------------------------------------

# Execute a deployment step with standardized logging and error handling
# $1: Step name for logging
# $2: Command to execute
# $3: Optional component name for logging
run_step() {
  local step_name="$1"
  local cmd="$2"
  local component="${3:-STEP}"
  
  log_info "Running step: $step_name" "$component"
  start_spinner "$step_name"
  
  # Create temporary file for command output
  local output_file
  output_file=$(mktemp)
  
  # Create a trap to clean up the temporary file on exit or interrupt
  local cleanup_trap="rm -f \"$output_file\""
  trap "$cleanup_trap" EXIT INT TERM
  
  # Capture exit status properly
  set +e
  ( eval "$cmd" ) > "$output_file" 2>&1
  local status=$?
  set -e
  
  if [ $status -eq 0 ]; then
    log_success "$step_name completed" "$component"
    stop_spinner "success"
    
    # Show output in verbose mode
    if [ "$VERBOSE" = true ]; then
      echo -e "${BLUE}Command output:${NC}"
      cat "$output_file"
    fi
    
    # Clean up and remove trap
    rm -f "$output_file"
    trap - EXIT INT TERM
    return 0
  else
    log_error "$step_name failed (exit code: $status)" "$component"
    stop_spinner "error"
    
    # Always show output on failure
    echo -e "${RED}Command output:${NC}"
    cat "$output_file"
    
    # Clean up and remove trap
    rm -f "$output_file"
    trap - EXIT INT TERM
    return 1
  fi
} 