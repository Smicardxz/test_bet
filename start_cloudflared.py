#!/usr/bin/env python3
"""Start cloudflared tunnel and capture URL."""
import subprocess
import re
import time
import sys

def start_tunnel():
    proc = subprocess.Popen(
        ["cloudflared", "tunnel", "--url", "http://localhost:5000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    
    url = None
    start = time.time()
    while time.time() - start < 30:
        line = proc.stdout.readline()
        if not line:
            break
        print(line.rstrip())
        match = re.search(r"(https://[a-z0-9\-]+\.trycloudflare\.com)", line)
        if match:
            url = match.group(1)
            # Write URL to file for other scripts
            with open("tunnel_url.txt", "w") as f:
                f.write(url)
            print(f"\n>>> TUNNEL URL: {url}")
            break
    
    if not url:
        print("ERROR: Could not find tunnel URL in output")
        proc.terminate()
        sys.exit(1)
    
    # Keep process info
    print(f">>> PID: {proc.pid}")
    print(">>> Tunnel running in background. Kill with: taskkill /PID {proc.pid} /F")
    
    # Detach - let the process continue
    return url, proc.pid

if __name__ == "__main__":
    url, pid = start_tunnel()
    print(f"\nTUNNEL_URL={url}")
    print(f"PID={pid}")
