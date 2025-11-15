import random
import math
from locust import HttpUser, task, between, LoadTestShape

# === Config ===
BASE_URL = "http://10.2.16.116:8610"
AUTH_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3NTc3NjA5MTgsInN1YiI6IjEifQ.hriGLcrlmQ9iGLbKj_9tZzhiRvhU2G2yFrJcnTHeLbA"

COMMON_HEADERS = {
    "accept": "application/json",
    "Authorization": f"Bearer {AUTH_TOKEN}"
}
JSON_HEADERS = {
    "accept": "application/json",
    "Content-Type": "application/json",
    "Authorization": f"Bearer {AUTH_TOKEN}"
}

# === DELETE APIs ===
DELETE_APIS = [
    ("/user/delete-user/1", COMMON_HEADERS, None),
    ("/verticals/delete-ae/1", COMMON_HEADERS, None),
    ("/nodes/delete-node/AQ01-0056-0001", COMMON_HEADERS, None),
    ("/sensor-types/delete", JSON_HEADERS, {"id": 1, "vertical_id": 1}),
    ("/subscription/unsubscribe", JSON_HEADERS, {
        "node_name": "AQ01-0056-0001",
        "url": "http://10.2.16.116:8610/notify/listener"
    })
]

# === High Density Periodic Load Shape ===
class HighDensityPeriodicShape(LoadTestShape):
    step_time = 60
    step_load = 5
    spawn_rate = 10
    time_limit = 1800

    def tick(self):
        run_time = self.get_run_time()
        if run_time > self.time_limit:
            return None

        current_step = math.floor(run_time / self.step_time) + 1
        user_count = current_step * self.step_load
        second = run_time % 60
        if second in [0, 10, 20, 30, 40, 50]:
            return (user_count, self.spawn_rate)
        else:
            return (user_count, 0)

# === User ===
class PeriodicDeleteUser(HttpUser):
    wait_time = between(1, 3)

    @task
    def delete_requests(self):
        endpoint, headers, payload = random.choice(DELETE_APIS)
        url = f"{BASE_URL}{endpoint}"
        if payload:
            response = self.client.delete(url, headers=headers, json=payload)
        else:
            response = self.client.delete(url, headers=headers)

        if response.status_code in [200, 201, 204]:
            print(f"[OK] DELETE {endpoint}")
        else:
            print(f"[FAIL] DELETE {endpoint} -> {response.status_code}")
