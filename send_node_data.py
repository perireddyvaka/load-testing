import argparse
import csv
import json
import os
import random
import sys
import time
import traceback
from datetime import datetime

import requests

def load_nodes(nodes_file):
    with open(nodes_file, 'r') as f:
        data = json.load(f)
    if not isinstance(data, list) or not data:
        raise ValueError("nodes file must contain a non-empty JSON array")
    return data

CSV_HEADERS = [
    "timestamp", "node_id", "node_name", "temperature", "status_code",
    "response_time_ms", "success", "response_text"
]

def ensure_csv_header(path):
    if not os.path.exists(path):
        with open(path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(CSV_HEADERS)

def append_csv_row(path, row):
    ensure_csv_header(path)
    with open(path, 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(row)

def send_one(base_url, node, timeout):
    node_id = node.get("id")
    api_token = node.get("api_token", "")
    node_name = node.get("name", "")

    temperature = round(random.uniform(20, 35), 2)
    payload = {"temperature": str(temperature)}

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_token}" if api_token else ""
    }

    url = f"{base_url.rstrip('/')}/nodes/create-cin/{node_id}"
    start = time.monotonic()
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=timeout)
        elapsed_ms = (time.monotonic() - start) * 1000
        success = resp.status_code == 200
        resp_text = resp.text.replace('\n', ' ')[:1000]  # truncate to keep CSV sane
        return {
            "status_code": resp.status_code,
            "response_time_ms": round(elapsed_ms, 2),
            "success": success,
            "response_text": resp_text,
            "temperature": temperature  # return the exact sent temperature
        }
    except Exception as e:
        elapsed_ms = (time.monotonic() - start) * 1000
        return {
            "status_code": None,
            "response_time_ms": round(elapsed_ms, 2),
            "success": False,
            "response_text": f"EXCEPTION: {str(e)}; {traceback.format_exc().splitlines()[-1]}",
            "temperature": temperature
        }

def main():
    parser = argparse.ArgumentParser(description="Send node sensor data via POST and log to CSV.")
    parser.add_argument("--base-url", "-b", required=True, help="Base URL, e.g. https://api.example.com")
    parser.add_argument("--nodes-file", "-n", default="/home/likhith/ctop_testing/exceter.json")
    parser.add_argument("--csv", "-o", default="/home/likhith/ctop_testing/node_data_log.csv")
    parser.add_argument("--count", "-c", type=int, default=1, help="Number of POSTs to send (0 = infinite)")
    parser.add_argument("--interval", "-i", type=float, default=1.0, help="Seconds between requests")
    parser.add_argument("--timeout", "-t", type=float, default=10.0, help="Request timeout in seconds")
    args = parser.parse_args()

    try:
        nodes = load_nodes(args.nodes_file)
    except Exception as e:
        print(f"[ERROR] Failed to load nodes file: {e}")
        sys.exit(2)

    print(f"[INFO] Loaded {len(nodes)} nodes from {args.nodes_file}")
    sent = 0
    iterations = args.count
    infinite = iterations == 0

    try:
        while infinite or sent < iterations:
            node = random.choice(nodes)
            result = send_one(args.base_url, node, timeout=args.timeout)
            timestamp = datetime.utcnow().isoformat(timespec='microseconds') + "Z"
            row = [
                timestamp,
                node.get("id"),
                node.get("name", ""),
                str(result.get("temperature")),  # log the exact temperature that was sent
                result["status_code"],
                result["response_time_ms"],
                result["success"],
                result["response_text"]
            ]
            append_csv_row(args.csv, row)

            print(f"[{timestamp}] node={node.get('id')} temp={result.get('temperature')} status={result['status_code']} rt={result['response_time_ms']}ms success={result['success']}")
            sent += 1
            if not infinite and sent >= iterations:
                break
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\n[INFO] Interrupted by user")
    except Exception as e:
        print(f"[CRITICAL] {e}\n{traceback.format_exc()}")
        sys.exit(3)

if __name__ == "__main__":
    main()
