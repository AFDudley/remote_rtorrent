#!/usr/bin/env python3
"""Remote RTorrent Controller with TOML config file support"""
import sys
import tomllib
import subprocess
import os.path

def main():
    if len(sys.argv) < 3 or len(sys.argv) > 4:
        print(f"Usage: {sys.argv[0]} <config_file> <magnet_link> [storage_host_dir]")
        sys.exit(1)

    config_file = sys.argv[1]
    magnet_link = sys.argv[2]
    storage_host_dir_cmd = sys.argv[3] if len(sys.argv) == 4 else None

    if not os.path.isfile(config_file):
        print(f"Config file not found: {config_file}")
        sys.exit(1)

    with open(config_file, 'rb') as f:
        config = tomllib.load(f)

    storage_host = config.get('storage_host')
    torrent_host = config.get('torrent_host')
    storage_host_dir = storage_host_dir_cmd or config.get('storage_host_dir', '')

    if not storage_host or not torrent_host:
        print("Config must contain 'storage_host' and 'torrent_host'")
        sys.exit(1)

    storage_host_dir_arg = f" '{storage_host_dir}'" if storage_host_dir else ""
    cmd = f'ssh -A {storage_host} "~/bin/rrc.py {torrent_host} \'{magnet_link}\'{storage_host_dir_arg}"'
    subprocess.run(cmd, shell=True)

if __name__ == "__main__":
    main()
