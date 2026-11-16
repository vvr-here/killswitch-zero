#!/usr/bin/env python3
"""
KillSwitch Zero: Local Telemetry & Recursive Loop Simulator
Sends controlled synthetic batches of invocations to the Ingestion HTTP API.
"""

import sys
import time
import json
import urllib.request
import urllib.error

def send_telemetry(endpoint_url: str, function_name: str | None, count: int, force: bool = False):
    payload_dict = {"invocations": count}
    if function_name:
        payload_dict["function_name"] = function_name
    if force:
        payload_dict["force"] = True
    payload = json.dumps(payload_dict).encode('utf-8')

    req = urllib.request.Request(
        endpoint_url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            print(f"[{time.strftime('%X')}] Status {resp.status} | Velocity: {data.get('current_velocity')} req/min | Breached: {data.get('circuit_breaker_triggered')}")
            return data
    except urllib.error.HTTPError as e:
        print(f"HTTP Error {e.code}: {e.read().decode('utf-8')}")
    except Exception as e:
        print(f"Connection failed: {e}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python simulate_burst.py <HTTP_INGEST_URL> [BURST_COUNT] [TARGET_FUNCTION]")
        print("Example: python simulate_burst.py https://xyz.execute-api.us-east-1.amazonaws.com/telemetry 100")
        sys.exit(1)

    endpoint_url = sys.argv[1]
    burst_count = int(sys.argv[2]) if len(sys.argv) > 2 else 100
    target_func = sys.argv[3] if len(sys.argv) > 3 else None

    print("==================================================")
    print("  ⚡ KillSwitch Zero: Live Telemetry Simulator")
    print(f"  Target Function: {target_func or 'Default Deployed Rogue Target'}")
    print(f"  Endpoint: {endpoint_url}")
    print(f"  Simulating burst: {burst_count} invocations")
    print("==================================================")

    print("\n[Step 1] Sending normal baseline traffic (5 req)...")
    send_telemetry(endpoint_url, target_func, 5)
    time.sleep(1)

    print(f"\n[Step 2] TRIGGERING RECURSIVE LOOP STORM ({burst_count} req)...")
    res = send_telemetry(endpoint_url, target_func, burst_count, force=True)

    if res and res.get('circuit_breaker_triggered'):
        print("\n🚨 CIRCUIT BREAKER ENGAGED!")
        print(f"   Execution ARN: {res.get('execution_arn')}")
        print("   Target concurrency is now clamped to 0.")
        print("   Check your S3 Command Center dashboard to view the incident autopsy.")
    else:
        print("\nNote: Threshold not breached or already in alert state.")

if __name__ == '__main__':
    main()
