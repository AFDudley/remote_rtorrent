#!/usr/bin/env python3
import os
import os.path
import re
import sys
import time
import subprocess

def run_ssh_command(host, command):
    """Run command over SSH and return output"""
    result = subprocess.run(["ssh", "-o", "StrictHostKeyChecking=accept-new", host, command],
                           capture_output=True, text=True)
    return result.stdout.strip(), result.returncode

def validate_inputs():
    """Validate command line inputs and return validated parameters"""
    if len(sys.argv) < 3 or len(sys.argv) > 4:
        print(f"Usage: {sys.argv[0]} <remote_host> <magnet_link> [local_dir]")
        print(f"Example: {sys.argv[0]} user@remotehost 'magnet:?xt=urn:btih:...' /downloads")
        sys.exit(1)

    remote_host = sys.argv[1]
    magnet_link = sys.argv[2]
    local_dir = sys.argv[3] if len(sys.argv) == 4 else os.getcwd()

    # Sanitize local_dir
    if local_dir:
        # Normalize path to resolve .. and . references
        local_dir = os.path.normpath(os.path.abspath(local_dir))
        
        # Check for suspicious patterns
        if re.search(r'[;&|]', local_dir):
            print(f"Error: Invalid characters in directory path: {local_dir}")
            sys.exit(1)
            
        # Check if directory exists, create if it doesn't
        if not os.path.exists(local_dir):
            try:
                os.makedirs(local_dir, exist_ok=True)
            except Exception as e:
                print(f"Error creating directory {local_dir}: {e}")
                sys.exit(1)
                
        # Check if directory is writable
        if not os.access(local_dir, os.W_OK):
            print(f"Error: Directory not writable: {local_dir}")
            sys.exit(1)
    
    return remote_host, magnet_link, local_dir

def main():
    remote_host, magnet_link, local_dir = validate_inputs()

    # Define remote paths
    remote_session_dir = "$HOME/torrents/session"
    remote_status_file = f"{remote_session_dir}/status"

    # Clear any existing status file
    print(f"Starting rtorrent on {remote_host}")
    print("Monitoring for completion...")
    print("----------------------------------------")

    run_ssh_command(remote_host, f"rm -f {remote_status_file}")

    # Start rtorrent in daemon mode
    escaped_magnet = magnet_link.replace('"', '\\"')
    start_cmd = f'nohup rtorrent -o system.daemon.set=true "{escaped_magnet}" > /dev/null 2>&1 &'
    stdout, ret_code = run_ssh_command(remote_host, start_cmd)

    # Give rtorrent time to start
    time.sleep(2)

    # Get rtorrent PID
    ps_cmd = f"ps aux | grep -F \"{escaped_magnet}\" | grep -v grep"
    ps_output, _ = run_ssh_command(remote_host, ps_cmd)
    rtorrent_pid = ""

    if ps_output:
        rtorrent_pid = ps_output.split()[1]
        print(f"rtorrent PID: {rtorrent_pid}")
    else:
        print("Warning: Could not find rtorrent PID")

    # Monitor for completion
    while True:
        # Check if status file exists and contains COMPLETED
        check_cmd = f"[ -f \"{remote_status_file}\" ] && grep -q 'COMPLETED' \"{remote_status_file}\" && echo 'DONE'"
        print(f"Checking status: {check_cmd}")
        status, _ = run_ssh_command(remote_host, check_cmd)
        print(f"Status check returned: '{status}'")

        if status == "DONE":
            print("Download completed! Copying files...")

            # Get the file/directory path
            get_file_cmd = f"tail -n +2 \"{remote_status_file}\" | head -n 1"
            remote_file, _ = run_ssh_command(remote_host, get_file_cmd)

            if not remote_file:
                print("ERROR: No file or directory path found in status file")
                sys.exit(1)

            print(f"Copying: {remote_file}")

            # Extract filename for local verification
            filename = os.path.basename(remote_file)

            # Copy the file/directory
            scp_cmd = ["scp", "-r", f"{remote_host}:{remote_file}", local_dir]
            result = subprocess.run(scp_cmd)

            if result.returncode == 0:
                local_path = os.path.join(local_dir, filename)
                if os.path.isdir(local_path):
                    print(f"Successfully copied directory: {filename}")
                elif os.path.isfile(local_path):
                    print(f"Successfully copied file: {filename}")
                else:
                    print(f"ERROR: '{filename}' was not successfully copied to {local_dir}")
                    sys.exit(1)
            else:
                print(f"ERROR: Failed to copy file: {remote_file}")
                sys.exit(1)

            print("All files copied successfully!")

            # Kill rtorrent if we have its PID
            if rtorrent_pid:
                print(f"Killing rtorrent process (PID: {rtorrent_pid})...")
                run_ssh_command(remote_host, f"kill {rtorrent_pid}")
                print("rtorrent has been terminated")

            # Cleanup remote files
            print("Cleaning up downloaded files on remote host...")

            if remote_file:
                run_ssh_command(remote_host, f"rm -rf \"{remote_file}\"")
                print(f"Removed: {remote_file}")

                run_ssh_command(remote_host, f"rm -rf \"{remote_session_dir}\"")
                print("Removed session directory")

            break

        # Delay between checks
        time.sleep(5)

    print("Torrent download completed. Files are in the current directory.")

if __name__ == "__main__":
    main()
