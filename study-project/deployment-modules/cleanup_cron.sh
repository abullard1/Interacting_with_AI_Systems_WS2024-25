#!/bin/bash
set -euo pipefail

# Automated log rotation and cleanup script
# Runs daily at 3 AM via cron to maintain log storage limits:
# 0 3 * * * /home/study-project/deployment-modules/cleanup_cron.sh >> /home/study-project/logs/cleanup_cron.log 2>&1

# Import shared configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/config.sh"

# ------------------------------------------------
# Log Management Functions
# ------------------------------------------------

# Returns directory size in MB for threshold checking
get_dir_size_mb() {
    local dir="$1"
    if [ ! -d "$dir" ]; then
        echo "0"
        return 1
    fi
    du -sm "$dir" | cut -f1
}

# Removes compressed logs older than LOG_COMPRESSED_MAX_AGE_DAYS
cleanup_old_compressed_logs() {
    local log_dir="$1"
    local current_time
    current_time=$(date +%s)
    
    if [ ! -d "$log_dir" ]; then
        echo "Warning: Log directory does not exist: $log_dir"
        return 1
    fi
    
    # Check if directory is empty or has no .gz files
    if ! find "$log_dir" -name "*.gz" -type f | grep -q .; then
        echo "No compressed logs found in $log_dir"
        return 0
    fi
    
    find "$log_dir" -name "*.gz" -type f | while read -r compressed_file; do
        if [ ! -f "$compressed_file" ]; then
            continue
        fi
        
        local file_time
        file_time=$(stat -L --format=%Y "$compressed_file")
        local age_days=$(( (current_time - file_time) / 86400 ))
        
        if [ "$age_days" -gt "$LOG_COMPRESSED_MAX_AGE_DAYS" ]; then
            if rm "$compressed_file"; then
                echo "Removed old compressed log: $compressed_file (age: $age_days days)"
            else
                echo "Failed to remove: $compressed_file"
            fi
        fi
    done
}

# Ensures log directory stays under LOG_DIR_MAX_SIZE_MB by removing oldest archives
enforce_dir_size_limit() {
    local log_dir="$1"
    
    if [ ! -d "$log_dir" ]; then
        echo "Warning: Log directory does not exist: $log_dir"
        return 1
    fi
    
    local dir_size
    dir_size=$(get_dir_size_mb "$log_dir")
    
    if [ "$dir_size" -gt "$LOG_DIR_MAX_SIZE_MB" ]; then
        echo "Log directory size ($dir_size MB) exceeds limit ($LOG_DIR_MAX_SIZE_MB MB). Removing oldest compressed logs..."
        
        # Check if there are any compressed logs to remove
        if ! find "$log_dir" -name "*.gz" -type f | grep -q .; then
            echo "No compressed logs to remove! Directory size still exceeds limit."
            return 1
        fi
        
        local max_iterations=100  # Prevent infinite loops
        local iteration=0
        
        while [ "$dir_size" -gt "$LOG_DIR_MAX_SIZE_MB" ] && [ "$iteration" -lt "$max_iterations" ]; do
            # Find oldest compressed log by modification time
            local oldest_log
            oldest_log=$(find "$log_dir" -name "*.gz" -type f -printf '%T+ %p\n' | sort | head -n 1 | cut -d' ' -f2-)
            
            if [ -z "$oldest_log" ] || [ ! -f "$oldest_log" ]; then
                echo "No more compressed logs to remove!"
                break
            fi
            
            if rm "$oldest_log"; then
                echo "Removed old compressed log: $oldest_log"
            else
                echo "Failed to remove: $oldest_log"
                break
            fi
            
            dir_size=$(get_dir_size_mb "$log_dir")
            ((iteration++))
        done
        
        echo "Final log directory size: $dir_size MB"
        
        if [ "$iteration" -ge "$max_iterations" ]; then
            echo "Warning: Reached maximum removal iterations. Directory size may still be too large."
        fi
    fi
}

# Rotates logs exceeding size/age limits, keeping last 5 compressed versions
rotate_log() {
    local log_file="$1"
    
    [ ! -f "$log_file" ] && return  # Skip non-existent files
    
    local size_mb
    size_mb=$(du -m "$log_file" | cut -f1)

    local file_mod_time
    file_mod_time=$(stat -L --format=%Y "$log_file")
    local age_days=$(( ( $(date +%s) - file_mod_time ) / 86400 ))

    # Rotate if size or age thresholds are exceeded
    if [ "$size_mb" -gt "$LOG_ROTATION_MAX_SIZE_MB" ] || [ "$age_days" -gt "$LOG_ROTATION_MAX_AGE_DAYS" ]; then
        local timestamp
        timestamp=$(date +%Y%m%d-%H%M%S)
        local rotated_file="${log_file}.${timestamp}"
        local log_dir
        log_dir=$(dirname "$log_file")

        # Only clear original log after successful compression
        if command -v gzip >/dev/null 2>&1 && gzip -c "$log_file" > "${rotated_file}.gz"; then
            : > "$log_file"
            echo "Rotated $log_file to ${rotated_file}.gz"
            
            # Maintain only 5 most recent archives per log file
            find "$log_dir" -name "$(basename "$log_file").*gz" -type f | sort -r | tail -n +6 | xargs -r rm
        else
            echo "Failed to compress $log_file" >&2
        fi
    fi
}

# Verify log directory exists
if [ ! -d "$LOG_DIR" ]; then
    echo "Creating log directory: $LOG_DIR"
    if ! mkdir -p "$LOG_DIR"; then
        echo "Error: Failed to create log directory $LOG_DIR" >&2 
        exit 1
    fi
fi

echo "Starting log maintenance at $(date)"
echo "Current log directory size: $(get_dir_size_mb "$LOG_DIR") MB"

# Execute cleanup sequence:
# 1. Remove old compressed logs
# 2. Rotate active logs if needed
# 3. Enforce total directory size limit
cleanup_old_compressed_logs "$LOG_DIR"

# Make sure there are log files before trying to rotate them
if find "$LOG_DIR" -name "*.log" -type f | grep -q .; then
    for log_file in "$LOG_DIR"/*.log; do
        # Make sure the file exists and wasn't removed by another process
        if [ -f "$log_file" ]; then
            rotate_log "$log_file"
        fi
    done
else
    echo "No log files found for rotation"
fi

enforce_dir_size_limit "$LOG_DIR"

echo "Log maintenance completed at $(date)"
echo "Final log directory size: $(get_dir_size_mb "$LOG_DIR") MB"