from locust import HttpUser, task, between, LoadTestShape
import random
import string
import json
from io import BytesIO
import itertools
import csv
import time
from threading import Lock
import os
from datetime import datetime
import pandas as pd

# === CONFIG ===
LOGIN_EMAIL = "nagendra.pagadala@research.iiit.ac.in"
LOGIN_PASSWORD = "Nagendra@123"
TOKEN_REFRESH_INTERVAL = 29 * 60  # 29 minutes
FIXED_VENDOR_ID = 3
# Waste Management and Water Quality verticals
FIXED_VERTICAL_IDS = [1, 2]

AREAS = [
    "Gachibowli", "Hitech City", "Madhapur", "Kukatpally",
    "IIIT Campus", "Chandanagar", "Lingampally", "Kondapur",
    "Miyapur", "BHEL", "JNTU", "Kothaguda"
]

VERTICAL_NAMES = ["Water Quality", "Waste Management"]  # Updated vertical names

# === Shared Token State ===


class TokenManager:
    def __init__(self):
        self.access_token = None
        self.last_fetched = 0
        self.lock = Lock()

    def get_token(self, client):
        with self.lock:
            now = time.time()
            if not self.access_token or now - self.last_fetched >= TOKEN_REFRESH_INTERVAL:
                print("[🔐] Logging in to refresh token...")
                payload = {"email": LOGIN_EMAIL, "password": LOGIN_PASSWORD}
                with client.post("/user/login", json=payload, catch_response=True) as res:
                    if res.status_code == 200:
                        token_data = res.json()
                        self.access_token = f"Bearer {token_data['access_token']}"
                        self.last_fetched = now
                        print(f"[🔐] Token refreshed at {time.ctime(now)}")
                    else:
                        print(
                            f"[ERROR] Login failed! {res.status_code}: {res.text}")
                        self.access_token = None
            return self.access_token


token_manager = TokenManager()

# === Vendor CSV ===
csv_path = os.path.join(os.path.dirname(__file__), "vendors.csv")
with open(csv_path, newline='') as csvfile:
    reader = csv.DictReader(csvfile)
    vendor_data = list(reader)
vendor_cycle = itertools.cycle(vendor_data)

# === Helpers ===


def generate_random_string(length=8):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))


def generate_random_email():
    return f"{generate_random_string(6)}@example.com"


def generate_random_contact():
    return f"9{random.randint(100000000, 999999999)}"


def generate_vertical_data():
    param_count = random.randint(3, 5)
    parameters = [f"Sensor{n}" for n in range(1, param_count + 1)]
    return {
        "res_name": f"V_{generate_random_string(5)}",
        "res_short_name": f"V_{generate_random_string(2).upper()}",
        "description": "Auto-generated vertical",
        "labels": [],
        "orid": f"ORG_{generate_random_string(5)}",
        "pdescription": parameters,
        "name": parameters,
        "data_types": random.choices(["float", "int", "string"], k=param_count),
        "accuracy": [f"±{random.randint(1,5)}" for _ in range(param_count)],
        "units": random.choices(["°C", "%", "hPa", "Lux", "dB", "V"], k=param_count),
        "resolution": [str(random.randint(1, 10)) for _ in range(param_count)],
        "status": "A",
        "remarks": "Auto-created during load test"
    }


def generate_sensor_type_data():
    # Select a random vertical
    vertical = get_random_vertical_data()

    # Define parameters based on vertical type
    if vertical["id"] == 2:  # Waste Management
        params = ["bindata", "vehicle_number",
                  "lct", "violations", "polluters_count"]
        data_types = ["string"] * 5
        units = ["n/a"] * 5
    else:  # Water Quality
        params = ["temperature", "tds"]
        data_types = ["string", "int"]
        units = ["celcius", "ppm"]

    return {
        "res_name": f"S_{generate_random_string(6)}",
        "parameters": params,
        "data_types": data_types,
        "labels": [],
        "accuracy": [f"±2" for _ in params],
        "units": units,
        "resolution": ["3" for _ in params],
        "vertical_id": FIXED_VERTICAL_IDS
    }


def get_random_vertical_data():
    verticals = [
        {
            "id": 1, 
            "formatted_name": "AE-WQ01", 
            "res_name": "water_quality",
            "sensor_type": "WQ-Sensor-1",
            "parameters": ["temperature", "tds"]
        },
        {
            "id": 2, 
            "formatted_name": "AE-WM01", 
            "res_name": "waste_management",
            "sensor_type": "bin",
            "parameters": ["polluters_count", "bindata", "violations", "vehicle_number", "lct"]
        }
    ]
    return random.choice(verticals)

# === LOCUST TASKS ===


class FullLoadTest(HttpUser):
    wait_time = between(0.3, 0.6)

    # Add these class variables
    nodes_info = []
    nodes_info_lock = Lock()

    # Add class variable to track total nodes created
    nodes_created = 0
    nodes_limit = 1000
    nodes_lock = Lock()  # Add lock for thread safety

    # Add CSV file configuration
    NODE_LOG_FILE = os.path.join(
        os.path.dirname(__file__), "node_creation_log.csv")
    CSV_HEADERS = [
        "timestamp_ms",
        "node_id",
        "node_name",
        "latitude",
        "longitude",
        "area",
        "sensor_type",
        "domain",
        "protocol",
        "frequency",
        "status_code",
        "response_time_ms"
    ]

    # Add CSV file for node data logging
    NODE_DATA_LOG_FILE = os.path.join(
        os.path.dirname(__file__), "node_data_log.csv")
    NODE_DATA_HEADERS = [
        "timestamp_ms",
        "node_id",
        "node_name",  # Added node_name
        "temperature",
        "status_code",
        "response_time_ms",
        "success"
    ]

    # Add CSV file for fetch data logging
    FETCH_DATA_LOG_FILE = os.path.join(
        os.path.dirname(__file__), "fetch_data_log.csv")
    FETCH_DATA_HEADERS = [
        "timestamp_ms",
        "vertical_name",
        "records_count",
        "status_code",
        "response_time_ms"
    ]

    def on_start(self):
        try:
            print("[START] Getting initial token...")
            self.token = token_manager.get_token(self.client)
            if not self.token:
                raise Exception("Initial token is None")
            print("[START] Token acquired successfully.")

            # Fetch all nodes at startup
            self.fetch_all_nodes()

        except Exception as e:
            print(f"[START ERROR] {e}")

    def fetch_all_nodes(self):
        try:
            headers = self.get_auth_header()
            with self.client.get("/nodes/nodes-all", headers=headers, catch_response=True) as response:
                if response.status_code == 200:
                    with self.nodes_info_lock:
                        self.nodes_info = [
                            {
                                'id': node['id'],
                                'api_token': node['api_token'],
                                # Add name to stored node info
                                'name': node['name']
                            }
                            for node in response.json()
                        ]
                    print(
                        f"[NODES] Successfully fetched {len(self.nodes_info)} nodes")
                else:
                    print(
                        f"[NODES] Failed to fetch nodes: {response.status_code}")
        except Exception as e:
            print(f"[NODES] Error fetching nodes: {str(e)}")

    def get_auth_header(self):
        self.token = token_manager.get_token(self.client)
        return {"Authorization": self.token}

    @task(1)
    def create_node(self):
        # Check if node limit is reached
        with self.nodes_lock:
            if self.nodes_created >= self.nodes_limit:
                return  # Skip node creation if limit reached
            self.nodes_created += 1
            current_node = self.nodes_created

        print(f"[NODE CREATE] Creating node {current_node}/{self.nodes_limit}")
        try:
            vertical = get_random_vertical_data()
            start_time = time.time()

            # Create node payload
            node_data = {
                "latitude": round(random.uniform(17.3850, 17.4450), 6),
                "longitude": round(random.uniform(78.3350, 78.3950), 6),
                "area": random.choice(AREAS),
                "sensor_type": vertical["sensor_type"],
                "domain": vertical["formatted_name"],
                "name": f"Node_{vertical['res_name']}_{generate_random_string(5)}",
                "protocol": random.choice(["MQTT", "CoAP"]),
                "frequency": random.choice(["00:01:00", "00:05:00", "00:10:00", "00:15:00"]),
                "parameters": vertical["parameters"]
            }

            node_payload = {"nodes": [node_data]}
            headers = self.get_auth_header()
            headers["Content-Type"] = "application/json"

            with self.client.post("/import/import", json=node_payload, headers=headers, catch_response=True) as res:
                end_time = time.time()
                response_time_ms = int((end_time - start_time) * 1000)

                # Prepare CSV log entry
                csv_data = [
                    datetime.fromtimestamp(start_time).isoformat(
                        timespec='microseconds'),
                    current_node,
                    node_data["name"],
                    node_data["latitude"],
                    node_data["longitude"],
                    node_data["area"],
                    node_data["sensor_type"],
                    node_data["domain"],
                    node_data["protocol"],
                    node_data["frequency"],
                    res.status_code,
                    response_time_ms
                ]

                try:
                    file_exists = os.path.exists(self.NODE_LOG_FILE)
                    with open(self.NODE_LOG_FILE, 'a', newline='') as f:
                        writer = csv.writer(f)
                        if not file_exists:
                            writer.writerow(self.CSV_HEADERS)
                        writer.writerow(csv_data)
                except Exception as csv_error:
                    print(
                        f"[NODE CREATE] Error writing to CSV: {str(csv_error)}")

                if res.status_code == 200:
                    print(
                        f"[NODE CREATE] Success: {node_data['name']} (Response time: {response_time_ms}ms)")
                    res.success()
                else:
                    error_msg = f"Node creation failed with status {res.status_code}"
                    print(f"[NODE CREATE] ERROR: {error_msg}")
                    res.failure(error_msg)

        except Exception as e:
            print(f"[NODE CREATE] CRITICAL ERROR: {str(e)}")
            raise

    # @task(2)
    # def send_node_data(self):
    #     print("\n[DATA SEND] ====== Starting Node Data Transmission ======")
    #     if not self.nodes_info:
    #         print("[DATA SEND]  No nodes available in nodes_info, skipping data send")
    #         return

    #     try:
    #         node = random.choice(self.nodes_info)
    #         node_id = node['id']
    #         api_token = node['api_token']

    #         temperature = str(round(random.uniform(20, 35), 2))
    #         sensor_data = {"temperature": temperature}

    #         headers = {
    #             "Content-Type": "application/json",
    #             "Authorization": f"Bearer {api_token}"
    #         }

    #         url = f"/nodes/create-cin/{node_id}"
    #         start_time = time.time()

    #         with self.client.post(url, json=sensor_data, headers=headers, catch_response=True) as res:
    #             response_time = (time.time() - start_time) * 1000

    #             # Prepare CSV data with ISO timestamp
    #             csv_data = [
    #                 datetime.fromtimestamp(time.time()).isoformat(
    #                     timespec='microseconds'),  # ISO format timestamp
    #                 node_id,
    #                 node['name'],  # Add node name to CSV data
    #                 temperature,
    #                 res.status_code,
    #                 round(response_time, 2),
    #                 res.status_code == 200
    #             ]

    #             # Write to CSV file
    #             try:
    #                 file_exists = os.path.exists(self.NODE_DATA_LOG_FILE)
    #                 with open(self.NODE_DATA_LOG_FILE, 'a', newline='') as f:
    #                     writer = csv.writer(f)
    #                     if not file_exists:
    #                         writer.writerow(self.NODE_DATA_HEADERS)
    #                     writer.writerow(csv_data)
    #                 print(
    #                     f"[DATA SEND]  Data logged to CSV: {self.NODE_DATA_LOG_FILE}")
    #             except Exception as csv_error:
    #                 print(
    #                     f"[DATA SEND]  Error writing to CSV: {str(csv_error)}")

    #             if res.status_code == 200:
    #                 print(
    #                     f"[DATA SEND]  Success! Data sent to node {node_id}")
    #                 res.success()
    #             else:
    #                 error_msg = f"Data sending failed for node {node_id} with status {res.status_code}"
    #                 print(f"[DATA SEND]  ERROR: {error_msg}")
    #                 res.failure(error_msg)

    #     except Exception as e:
    #         print(f"[DATA SEND]  CRITICAL ERROR: {str(e)}")
    #         print(traceback.format_exc())
    #         raise
    #     finally:
    #         print("[DATA SEND] ====== End of Node Data Transmission ======\n")

    # @task(3)
    # def fetch_node_data(self):
    #     print("\n[FETCH] ====== Starting Node Data Fetch ======")
    #     try:
    #         vertical_name = random.choice(VERTICAL_NAMES)
    #         start_time = time.time()

    #         headers = self.get_auth_header()
    #         params = {
    #             "vertical_name": vertical_name,
    #             "limit": 100,
    #             "offset": 0,
    #             "as_csv": "false"
    #         }

    #         with self.client.get("/nodes/fetch-node-data/",
    #                              params=params,
    #                              headers=headers,
    #                              catch_response=True) as res:
    #             response_time = (time.time() - start_time) * 1000
    #             records_count = len(
    #                 res.json()) if res.status_code == 200 else 0

    #             # Prepare CSV data
    #             csv_data = [
    #                 datetime.fromtimestamp(time.time()).isoformat(
    #                     timespec='microseconds'),  # ISO format timestamp
    #                 vertical_name,
    #                 records_count,
    #                 res.status_code,
    #                 round(response_time, 2)
    #             ]

    #             # Write to CSV file
    #             try:
    #                 file_exists = os.path.exists(self.FETCH_DATA_LOG_FILE)
    #                 with open(self.FETCH_DATA_LOG_FILE, 'a', newline='') as f:
    #                     writer = csv.writer(f)
    #                     if not file_exists:
    #                         writer.writerow(self.FETCH_DATA_HEADERS)
    #                     writer.writerow(csv_data)
    #                 print(
    #                     f"[FETCH] Data logged to CSV: {self.FETCH_DATA_LOG_FILE}")
    #             except Exception as csv_error:
    #                 print(f"[FETCH]  Error writing to CSV: {str(csv_error)}")

    #             if res.status_code == 200:
    #                 print(
    #                     f"[FETCH] Success! Fetched {records_count} records for {vertical_name}")
    #                 res.success()
    #             else:
    #                 error_msg = f"Data fetch failed with status {res.status_code}"
    #                 print(f"[FETCH]  ERROR: {error_msg}")
    #                 res.failure(error_msg)

    #     except Exception as e:
    #         print(f"[FETCH]  CRITICAL ERROR: {str(e)}")
    #         print(traceback.format_exc())
    #         raise
    #     finally:
    #         print("[FETCH] ====== End of Node Data Fetch ======\n")


# === Load Shape ===
class ContinuousSpikeShape(LoadTestShape):
    stages = [
        {"duration": 120, "users": 50, "spawn_rate": 10},
        {"duration": 300, "users": 100, "spawn_rate": 20},
        {"duration": 180, "users": 150, "spawn_rate": 30},
        {"duration": 600, "users": 200, "spawn_rate": 40},
    ]

    def tick(self):
        total = sum(stage["duration"] for stage in self.stages)
        run_time = self.get_run_time() % total

        elapsed = 0
        for stage in self.stages:
            elapsed += stage["duration"]
            if run_time < elapsed:
                return stage["users"], stage["spawn_rate"]
        return None
