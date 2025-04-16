#!/bin/bash

function show_usage {
  echo "Usage: $0 [OPTIONS]"
  echo "Run cleanup tasks for the study project"
  echo ""
  echo "Options:"
  echo "  --all                 Perform full lock file cleanup (WARNING: removes ALL lock files)"
  echo "  --user USER_ID        Clean up a specific user by ID (removes their data and frees up their scenarios)"
  echo "  --force               Skip confirmation prompts (use with caution)"
  echo "  --help, -h            Show this help message"
  echo ""
  echo "Without options, performs regular abandoned session cleanup only."
}

if [[ "$1" == "--help" || "$1" == "-h" ]]; then
  show_usage
  exit 0
fi

FULL_CLEANUP=false
USER_ID=""
FORCE=false

# Parse arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    --all)
      FULL_CLEANUP=true
      shift
      ;;
    --user)
      if [[ -z "$2" || "$2" == --* ]]; then
        echo "ERROR: --user requires a USER_ID parameter"
        show_usage
        exit 1
      fi
      USER_ID="$2"
      shift 2
      ;;
    --force)
      FORCE=true
      shift
      ;;
    *)
      echo "Unknown option: $1"
      show_usage
      exit 1
      ;;
  esac
done

if [[ "$FULL_CLEANUP" == true && "$FORCE" == false ]]; then
  echo "WARNING: Full lock cleanup requested. This will remove ALL lock files."
  echo "Press Ctrl+C to cancel or Enter to continue..."
  read -r
fi

if [[ -n "$USER_ID" && "$FORCE" == false ]]; then
  echo "WARNING: You are about to remove all data for user $USER_ID"
  echo "Press Ctrl+C to cancel or Enter to continue..."
  read -r
fi

# Activate virtual environment
echo "Activating virtual environment..."
source /home/study-project/gradio_app/venv/bin/activate

# Change to the correct directory
cd /home/study-project

if [[ -n "$USER_ID" ]]; then
  echo "Cleaning up specific user: $USER_ID"
  python3 cleanup_abandoned_sessions.py --user "$USER_ID"
else
  echo "Running abandoned sessions cleanup..."
  python3 cleanup_abandoned_sessions.py
fi

if [[ "$FULL_CLEANUP" == true ]]; then
  echo "Running full lock cleanup..."
  echo "yes" | python3 clean_all_lock_files.py
fi

# Deactivate the virtual environment
echo "Cleanup completed. Deactivating virtual environment."
deactivate 