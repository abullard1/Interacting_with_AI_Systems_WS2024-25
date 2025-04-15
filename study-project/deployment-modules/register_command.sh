#!/bin/bash
set -eo pipefail
#
# register_command.sh - Deployment command registration
#
# Detects if the deployment script is being run directly
# and offers to register a convenient 'deploy-study' command.

# ------------------------------------------------
# Command Detection and Registration
# ------------------------------------------------

# Check if deploy-study command already exists
command_exists() {
  command -v deploy-study &> /dev/null
}

# Detect whether called directly or through the deploy-study command
is_direct_invocation() {
  # Get the real path of the calling script
  local script_path
  script_path="$(readlink -f "${BASH_SOURCE[0]}")"
  local parent_path
  parent_path="$(readlink -f "$0")"
  
  # If not called from deploy.sh, not a direct invocation
  if [[ "$(basename "$parent_path")" != "deploy.sh" ]]; then
    return 1
  fi
  
  # Check invoked via deploy-study command
  if [[ "$parent_path" == *"deploy-study"* ]] || [[ "$(basename "$parent_path")" == "deploy-study" ]]; then
    return 1  # Not a direct invocation
  fi
  
  # Check if in an interactive terminal
  if [ ! -t 0 ]; then
    # Not running in a terminal (e.g. cron or script)
    return 1
  fi
  
  # Check if deploy-study already exists and is working
  if command_exists; then
    # Command exists but user didn't use it, so this is a direct invocation
    # Show registration only if they explicitly ran ./deploy.sh
    if [[ "$parent_path" == *"./deploy.sh" ]]; then
      return 0
    else
      return 1
    fi
  fi
  
  # Command doesn't exist and user is in an interactive terminal
  return 0
}

# Creates a symbolic link in user's bin directory
create_symlink() {
  local script_path="$1"
  local command_name="$2"
  local bin_dir="$HOME/bin"
  
  # Create user bin directory if it doesn't exist
  if [ ! -d "$bin_dir" ]; then
    if mkdir -p "$bin_dir"; then
      echo "Created directory: $bin_dir"
    else
      echo "Failed to create directory: $bin_dir"
      return 1
    fi
  fi
  
  # Create the symlink
  if ln -sf "$script_path" "$bin_dir/$command_name"; then
    # Ensure bin directory is in PATH
    if ! echo "$PATH" | grep -q "$bin_dir"; then
      echo "Adding $bin_dir to your PATH in .bashrc"
      echo "export PATH=\"\$HOME/bin:\$PATH\"" >> "$HOME/.bashrc"
      echo "NOTE: You'll need to restart your shell or run 'source ~/.bashrc' for the command to be available."
    fi
    return 0
  else
    echo "Failed to create symbolic link."
    return 1
  fi
}

# Adds an alias to .bashrc
add_alias() {
  local script_path="$1"
  local command_name="$2"
  
  # Check if alias already exists
  if grep -q "alias $command_name=" "$HOME/.bashrc"; then
    echo "Alias $command_name already exists in .bashrc. Updating..."
    sed -i "s|alias $command_name=.*|alias $command_name='$script_path'|" "$HOME/.bashrc"
  else
    echo "alias $command_name='$script_path'" >> "$HOME/.bashrc"
  fi
  
  echo "Added alias to .bashrc. Run 'source ~/.bashrc' to activate it in this session."
  return 0
}

# Register the command based on user preferences
register_command() {
  local script_path="$1"
  local command_name="${2:-deploy-study}"
  local method="$3"
  
  log_info "Registering command: $command_name" "REGISTER"
  
  case "$method" in
    symlink)
      if create_symlink "$script_path" "$command_name"; then
        log_success "Created command as symlink: $command_name" "REGISTER"
        return 0
      else
        log_error "Failed to create symlink for command" "REGISTER"
        return 1
      fi
      ;;
    alias)
      if add_alias "$script_path" "$command_name"; then
        log_success "Created command as alias: $command_name" "REGISTER"
        return 0
      else
        log_error "Failed to add alias for command" "REGISTER"
        return 1
      fi
      ;;
    *)
      log_error "Invalid registration method: $method" "REGISTER"
      return 1
      ;;
  esac
}

# Main function to offer command registration
offer_command_registration() {
  # Get the command-line arguments
  local args=("$@")
  
  # Skip if not called directly
  if ! is_direct_invocation; then
    return 0
  fi
  
  # Skip if command already exists
  if command_exists; then
    return 0
  fi
  
  # Skip if running with --no-confirm flag (non-interactive mode)
  for arg in "${args[@]}"; do
    if [[ "$arg" == "--no-confirm" ]]; then
      return 0
    fi
  done
  
  # Get the full path to the script
  local script_path
  script_path="$(readlink -f "$0")"
  
  echo
  echo -e "${YELLOW}Would you like to register the 'deploy-study' command for easier access?${NC}"
  echo "This will allow you to run the deployment by simply typing 'deploy-study'."
  echo
  echo "Options:"
  echo "  1) Yes, create a symlink in ~/bin (recommended)"
  echo "  2) Yes, add an alias to ~/.bashrc"
  echo "  3) No, don't register the command"
  echo
  echo -n "Enter your choice [1-3]: "
  
  read -r choice
  echo
  
  case "$choice" in
    1)
      if register_command "$script_path" "deploy-study" "symlink"; then
        echo -e "${GREEN}Command registered successfully!${NC}"
        echo "You can now run the deployment with 'deploy-study' after restarting your shell or sourcing ~/.bashrc"
      fi
      ;;
    2)
      if register_command "$script_path" "deploy-study" "alias"; then
        echo -e "${GREEN}Alias registered in ~/.bashrc!${NC}"
        echo "You can now run the deployment with 'deploy-study' after restarting your shell or running 'source ~/.bashrc'"
      fi
      ;;
    3|*)
      echo "Command registration skipped."
      ;;
  esac
  
  # Pause to let the user read the message
  echo
  echo "Press Enter to continue with deployment..."
  read -r
} 