import random
import gevent
import time
import math
from datetime import datetime
from locust import HttpUser, task, between, LoadTestShape
from gevent.lock import Semaphore

# === Config ===
BASE_URL = "http://10.2.16.116:8610"
AUTH_TOKEN = "replace_with_valid_token"  # Put your valid JWT here

COMMON_HEADERS = {
    "Authorization": f"Bearer {AUTH_TOKEN}",
    "Content-Type": "application/json"
}
PUBLIC_HEADERS = {
    "Content-Type": "application/json"
}

# === Load Shape ===
class StepLoadShape(LoadTestShape):
    step_time = 60
    step_load = 5
    spawn_rate = 10
    time_limit = 7200  # 2 hours

    def tick(self):
        run_time = self.get_run_time()
        if run_time > self.time_limit:
            return None

        current_step = math.floor(run_time / self.step_time) + 1
        remainder = current_step % 6
        adjusted_step = current_step + (6 - remainder) if remainder != 0 else current_step
        return (adjusted_step * self.step_load, self.spawn_rate)

# === Globals ===
max_users = 500
users_waiting = 0
event = gevent.event.Event()
lock = Semaphore()

# === All GET Endpoints (28 APIs) ===
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

# === Locust User ===
class MyUser(HttpUser):
    wait_time = between(1, 1)

    def on_start(self):
        self.start_time = time.time()

    @task
    def periodic_burst_requests(self):
        global users_waiting, event

        # Fire only at 0,10,20,...,50 seconds of every minute
        seconds_elapsed = datetime.now().second
        if seconds_elapsed in [0, 10, 20, 30, 40, 50]:
            with lock:
                users_waiting += 1
                print(f"{users_waiting} users waiting... ({users_waiting}/{max_users})")
                if users_waiting >= self.environment.runner.user_count:
                    print("All users are ready!")
                    event.set()

            # Sync all users
            event.wait()
            time.sleep(2)

            user_num = self.environment.runner.user_count
            current_time = time.strftime('%Y-%m-%d %H:%M:%S')
            print(f"User {user_num} firing requests at: {current_time}")

            # Pick a random API
            endpoint, headers = random.choice(API_ENDPOINTS)
            url = f"{BASE_URL}{endpoint}"

            # Perform GET request
            with self.client.get(url, headers=headers, catch_response=True) as response:
                if response.status_code == 200:
                    response.success()
                else:
                    response.failure(f"Failed {url} with {response.status_code}")

            # Release barrier
            with lock:
                users_waiting -= 1
                if users_waiting == 0:
                    event.clear()
