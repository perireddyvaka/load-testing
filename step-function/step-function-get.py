import json
import random
import gevent
import time
import math
from locust import HttpUser, task, between, LoadTestShape
from gevent.lock import Semaphore
from locust import events

# === Base Config ===
BASE_URL = "http://10.2.16.116:8610"
AUTH_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3NTc5MzA0NDIsInN1YiI6IjEyIn0.Ca4meTua6KYpMHPFBRR9dLwaycUOC1dFd235tVn1wKA"

COMMON_HEADERS = {
    "Authorization": f"Bearer {AUTH_TOKEN}",
    "Content-Type": "application/json"
}

PUBLIC_HEADERS = {
    "Content-Type": "application/json"
}

# === Load Shape (unchanged) ===
class StepLoadShape(LoadTestShape):
    step_time = 60
    step_load = 5
    spawn_rate = 10
    time_limit = 7200

    def tick(self):
        run_time = self.get_run_time()
        if run_time > self.time_limit:
            return None
        current_step = math.floor(run_time / self.step_time) + 1
        return (current_step * self.step_load, self.spawn_rate)

# === Dynamic endpoint generators ===
def get_dynamic_fetch_node_data_endpoints():
    """Generate dynamic fetch-node-data endpoints with random parameters"""
    vertical_names = ["water_quality", "air_quality", "noise_monitoring", "weather_station"]
    limits = [50, 100, 200, 500]
    offsets = [0, 10, 20, 50, 100]
    csv_options = ["true", "false"]
    
    endpoints = []
    for _ in range(5):  # Generate 5 random combinations
        vertical = random.choice(vertical_names)
        limit = random.choice(limits)
        offset = random.choice(offsets)
        as_csv = random.choice(csv_options)
        
        endpoint = f"/nodes/fetch-node-data/?vertical_name={vertical}&limit={limit}&offset={offset}&as_csv={as_csv}"
        endpoints.append((endpoint, PUBLIC_HEADERS))
    
    return endpoints

# === Globals ===
max_users = 500
users_waiting = 0
event = gevent.event.Event()
lock = Semaphore()

# === API Endpoints from Documentation ===
API_ENDPOINTS = [
    # User
    ("/user/profile", COMMON_HEADERS),
    ("/user/getusers", COMMON_HEADERS),
    
    # Verticals
    ("/verticals/verticals-all", COMMON_HEADERS),
    ("/verticals/vocabulary", PUBLIC_HEADERS),
    
    # Sensor Types
    ("/sensor-types/sensor-types-all", COMMON_HEADERS),
    ("/sensor-types/get/3", COMMON_HEADERS),  # Example vert_id
    
    # Nodes
    ("/nodes/get-vendor/WQ01-0093-0001", COMMON_HEADERS),
    ("/nodes/nodes-all", COMMON_HEADERS),
    ("/nodes/water_quality", COMMON_HEADERS),
    ("/nodes/get-node-data/WQ01-0093-0001", COMMON_HEADERS),
    # ("/nodes/get-node/WQ01-0093-0001/descriptor/latest", COMMON_HEADERS),
    ("/nodes/get-node/WQ01-0093-0001/descriptor/all", COMMON_HEADERS),
    ("/nodes/meta/id/WQ01-0093-0001", COMMON_HEADERS),  # Example node_id
    ("/nodes/fetch-node-data/?vertical_name=water_quality&limit=100&offset=0&as_csv=false", COMMON_HEADERS),
    ("/nodes/fetch-node-data/?vertical_name=water_quality&limit=200&offset=0&as_csv=true", COMMON_HEADERS),

    # Stats
    ("/stats/loners", PUBLIC_HEADERS),
    ("/stats/vertical_names", PUBLIC_HEADERS),
    ("/stats/stats", PUBLIC_HEADERS),
    ("/stats/nodes_area", PUBLIC_HEADERS),
    ("/stats/working_nodes/status", PUBLIC_HEADERS),
    ("/stats/get-all", COMMON_HEADERS),
    
    # Onboard
    ("/onboard/get-verticals-request", COMMON_HEADERS),
    
    # Subscribe - Fixed endpoint path
    ("/subscription/get-user-subscriptions", COMMON_HEADERS),
    
    # Alarms
    ("/alarms/alarms", COMMON_HEADERS),
    ("/alarms/notifications", COMMON_HEADERS),  # Added missing endpoint
    
]

# === Locust User Class ===
class MyUser(HttpUser):
    wait_time = between(1, 1)

    def on_start(self):
        self.start_time = time.time()

    @task
    def run_all_apis(self):
        global users_waiting, event

        # Barrier sync for all spawned users
        with lock:
            users_waiting += 1
            print(f"{users_waiting} users waiting... ({users_waiting}/{max_users})")
            if users_waiting >= self.environment.runner.user_count:
                print("All users are ready!")
                event.set()

        event.wait()
        time.sleep(2)

        # Combine static endpoints with dynamic fetch-node-data endpoints
        all_endpoints = API_ENDPOINTS + get_dynamic_fetch_node_data_endpoints()
        
        # Pick a random API
        endpoint, headers = random.choice(all_endpoints)
        url = f"{BASE_URL}{endpoint}"

        # Perform GET request
        with self.client.get(url, headers=headers, catch_response=True) as response:
            if response.status_code == 200:
                response.success()
                print(f"[SUCCESS] {endpoint}")
            else:
                response.failure(f"Failed {url} with {response.status_code}")
                print(f"[FAILED] {endpoint} -> {response.status_code}")

        # Release barrier
        with lock:
            users_waiting -= 1
            if users_waiting == 0:
                event.clear()
