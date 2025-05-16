#!/usr/bin/env python3
"""Remote RTorrent Controller with TOML config file support"""
import sys
import tomllib
import subprocess
import os.path

def main():
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <config_file> <magnet_link>")
        sys.exit(1)
    
    config_file = sys.argv[1]
    magnet_link = sys.argv[2]
    
    if not os.path.isfile(config_file):
        print(f"Config file not found: {config_file}")
        sys.exit(1)
    
    with open(config_file, 'rb') as f:
        config = tomllib.load(f)
    
    jump_server = config.get('jump_server')
    target_server = config.get('target_server')
    
    if not jump_server or not target_server:
        print("Config must contain 'jump_server' and 'target_server'")
        sys.exit(1)
    
    cmd = f'ssh -A {jump_server} "~/bin/rrc.sh {target_server} \'{magnet_link}\'"'
    subprocess.run(cmd, shell=True)

if __name__ == "__main__":
    main()
