#!/bin/bash
set -eo pipefail
#
# summary.sh - User interaction and deployment reporting
#
# Handles user confirmation prompts and generates
# deployment summary reports for the user.

# ------------------------------------------------
# User Interaction
# ------------------------------------------------

# Prompt for deployment confirmation
confirm_deployment() {
  [ "$CONFIRM" = false ] && return
  
  echo -e "${YELLOW}Deploy to production?${NC} (y/n)"
  
  # Get single character response
  read -r -n 1 response
  echo
  
  if [[ ! "$response" =~ ^[Yy]$ ]]; then
    log_info "Deployment cancelled by user"
    exit $EXIT_SUCCESS
  fi
}

# Prompt for continuation after warning
confirm_continuation() {
  local prompt="$1"
  local choice
  
  # Skip if no-confirm is set
  [ "$CONFIRM" = false ] && return 0
  
  echo -e "\n${YELLOW}${prompt}${NC} (y/n)"
  read -r -n 1 choice
  echo
  
  if [[ ! "$choice" =~ ^[Yy]$ ]]; then
    log_info "Operation cancelled by user"
    exit $EXIT_SUCCESS
  fi
}

# ------------------------------------------------
# Display Formatting
# ------------------------------------------------

# Display operation header
display_header() {
  if [ "$VERBOSE" = true ]; then
    echo -e "\n${BLUE}====== UNISTUDY.TECH DEPLOYMENT ======${NC}"
    echo -e "${BLUE}$(date '+%d-%m-%Y %H:%M:%S')${NC}\n"
  else
    echo -e "${BLUE}Deploying unistudy.tech (${TIMESTAMP})${NC}"
  fi
}

# Display operation footer with timing
display_footer() {
  if [ "$VERBOSE" = false ]; then
    echo -e "\n${GREEN}Deployment complete${NC} in $(( $(date +%s) - START_TIME ))s"
    echo "Log: $LOG_FILE"
  else
    echo -e "\n${GREEN}====== DEPLOYMENT COMPLETE ======${NC}"
    echo -e "Duration: $(( $(date +%s) - START_TIME )) seconds"
    echo -e "Log: $LOG_FILE"
    echo -e "${BLUE}======================================${NC}\n"
  fi
}

# ------------------------------------------------
# Deployment Reporting
# ------------------------------------------------

# Display deployment results summary
deployment_summary() {
  # Calculate deployment statistics
  local duration=$(($(date +%s) - START_TIME))
  local mins=$((duration / 60))
  local secs=$((duration % 60))
  local service_count=$(pm2 list | grep -c online)
  
  if [ "$VERBOSE" = true ]; then
    # Detailed summary for verbose mode
    echo -e "\n${BLUE}DEPLOYMENT SUMMARY${NC}"
    echo -e "────────────────────────────────────────"
    echo -e "Duration: ${mins}m ${secs}s"
    echo -e "Services: ${service_count} running"
    echo -e ""
    echo -e "${GREEN}Service Status:${NC}"
    pm2 status | head -n 3
    pm2 status | grep -E "online|errored" | sed 's/^/  /'
    echo -e ""
    
    echo -e "${GREEN}URLs:${NC}"
    echo -e "  Web: https://$DOMAIN"
    echo -e "  Gradio: https://$DOMAIN/gradio"
    echo -e ""
    echo -e "Log: $LOG_FILE"
    echo -e "────────────────────────────────────────"
  else
    # Compact summary for non-verbose mode
    echo -e "\n${BLUE}DEPLOYMENT SUMMARY${NC}"
    echo -e "${GREEN}✓${NC} All tasks completed successfully"
    echo -e "  Duration: ${mins}m ${secs}s"
    echo -e "  Services: ${service_count} running"
    echo -e "  URLs: https://$DOMAIN, https://$DOMAIN/gradio"
  fi
} 