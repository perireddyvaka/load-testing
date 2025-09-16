import random
import math
import time
from locust import HttpUser, task, between, LoadTestShape

# === Config ===
BASE_URL = "http://10.2.16.116:8610"
AUTH_TOKEN = "replace_with_valid_token"

COMMON_HEADERS = {
    "Authorization": f"Bearer {AUTH_TOKEN}",
    "Content-Type": "application/json"
}
PUBLIC_HEADERS = {
    "Content-Type": "application/json"
}

# === Poisson Arrival Shape ===
class PoissonArrivalShape(LoadTestShape):
    rate = 5          # average arrivals per second (λ)
    time_limit = 3600 # run for 1 hour

    def tick(self):
        run_time = self.get_run_time()
        if run_time > self.time_limit:
            return None

        # Expected number of arrivals by time t (λ * t)
        expected_users = self.rate * run_time

        # Convert to integer user count
        return (math.floor(expected_users), self.rate)

# === All 28 GET Endpoints ===
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
    ("/stats/loners", COMMON_HEADERS),
    ("/stats/loners", PUBLIC_HEADERS),
    ("/stats/vertical_names", COMMON_HEADERS),
    ("/stats/vertical_names", PUBLIC_HEADERS),
    ("/stats/stats", COMMON_HEADERS),
    ("/stats/stats", PUBLIC_HEADERS),
    ("/stats/working_nodes/status", PUBLIC_HEADERS),
    ("/stats/working_nodes/status", COMMON_HEADERS),
    ("/stats/nodes_area", COMMON_HEADERS),
    ("/stats/nodes_area", PUBLIC_HEADERS),
    ("/stats/get-all", COMMON_HEADERS),
    
    # Onboard
    ("/onboard/get-verticals-request", COMMON_HEADERS),
    
    # Subscribe
    ("/subscribe/get-user-subscriptions", COMMON_HEADERS),
    
    # Alarms
    ("/alarms/get-all", COMMON_HEADERS),
    ("/alarms/get-unread", COMMON_HEADERS),
    
    # Listener
    ("/listener/listener", COMMON_HEADERS),
    ("/listener/notifications", COMMON_HEADERS),
]

# === User Behavior ===
class MyUser(HttpUser):
    wait_time = between(1, 5)  # random small delay between requests

    @task
    def call_random_api(self):
        endpoint, headers = random.choice(API_ENDPOINTS)
        url = f"{BASE_URL}{endpoint}"

        with self.client.get(url, headers=headers, catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Failed {url} with {response.status_code}")
