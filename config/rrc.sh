#!/bin/bash
# Usage: ./rt.sh <remote_host> <magnet_link>
if [ $# -ne 2 ]; then
    echo "Usage: ${0} <remote_host> <magnet_link>"
    echo "Example: ${0} user@remotehost 'magnet:?xt=urn:btih:...'"
    exit 1
fi
REMOTE_HOST="$1"
MAGNET_LINK="$2"
LOCAL_DIR="$(pwd)"
# Define remote paths
REMOTE_SESSION_DIR="\$HOME/torrents/session"
REMOTE_STATUS_FILE="\$HOME/torrents/session/status"
# Start rtorrent on the remote machine
echo "Starting rtorrent on $REMOTE_HOST"
echo "Monitoring for completion..."
echo "----------------------------------------"
# Clear any existing status file in the current directory
ssh -o StrictHostKeyChecking=accept-new "$REMOTE_HOST" "rm -f ${REMOTE_STATUS_FILE}"
# Start rtorrent in daemon mode
ssh "$REMOTE_HOST" "rtorrent -o system.daemon.set=true \"${MAGNET_LINK//\"/\\\"}\"" &
SSH_PID=$!
# Also capture the rtorrent PID
sleep 2  # Give rtorrent time to start
PS_CMD="ps aux | grep -F \"${MAGNET_LINK//\"/\\\"}\" | grep -v grep"
RTORRENT_PID=$(ssh "$REMOTE_HOST" "$PS_CMD" | awk '{print $2}')
if [ -n "$RTORRENT_PID" ]; then
    echo "rtorrent PID: $RTORRENT_PID"
else
    echo "Warning: Could not find rtorrent PID"
fi
# Monitor for completion
while true; do
    # Check if status file exists and contains COMPLETED
    if ssh "$REMOTE_HOST" "[ -f \"${REMOTE_STATUS_FILE}\" ] && grep -q 'COMPLETED' \"${REMOTE_STATUS_FILE}\""; then
        echo "Download completed! Copying files..."
        # Get the file/directory path (second line of the status file)
        FILE=$(ssh "$REMOTE_HOST" "tail -n +2 \"${REMOTE_STATUS_FILE}\" | head -n 1")

        if [ -z "$FILE" ]; then
            echo "ERROR: No file or directory path found in status file"
            exit 1
        fi

        echo "Copying: $FILE"

        # Extract just the filename for local verification
        FILENAME=$(basename "${FILE}")

        # Define the SCP command to ensure consistency
        SCP_COMMAND="scp -r \"${REMOTE_HOST}:${FILE}\" \"${LOCAL_DIR}/\""

        # Debug: Print the SCP command that will be executed
        echo "DEBUG: SCP command: ${SCP_COMMAND}"
        # Copy the file using the full path with proper quoting
        if eval ${SCP_COMMAND}; then
            # Check if it's a directory or file
            if [ -d "${LOCAL_DIR}/${FILENAME}" ]; then
                echo "Successfully copied directory: ${FILENAME}"
            elif [ -f "${LOCAL_DIR}/${FILENAME}" ]; then
                echo "Successfully copied file: ${FILENAME}"
            else
                echo "ERROR: '${FILENAME}' was not successfully copied to ${LOCAL_DIR}"
                exit 1
            fi
        else
            echo "ERROR: Failed to copy file: $FILE"
            exit 1
        fi
        echo "All files copied successfully!"

        # Kill rtorrent if we have its PID
        if [ -n "${RTORRENT_PID}" ]; then
            echo "Killing rtorrent process (PID: ${RTORRENT_PID})..."
            ssh "$REMOTE_HOST" "kill ${RTORRENT_PID}"
            echo "rtorrent has been terminated"
        fi

        # Cleanup remote files after killing rtorrent
        echo "Cleaning up downloaded files on remote host..."

        # Remove the downloaded file or directory
        if [ -n "${FILE}" ]; then
            ssh "${REMOTE_HOST}" "rm -rf \"${FILE}\""
            echo "Removed: ${FILE}"

            # Remove the session directory (which includes the status file)
            ssh "$REMOTE_HOST" "rm -rf \"${REMOTE_SESSION_DIR}\""
            echo "Removed session directory"
        fi

        break
    fi
    # Check if SSH process is still running
    if ! kill -0 "${SSH_PID}" 2>/dev/null; then
        echo "ERROR: Remote rtorrent process has exited"
        exit 1
    fi
    sleep 5
done

echo "Torrent download completed. Files are in the current directory."
