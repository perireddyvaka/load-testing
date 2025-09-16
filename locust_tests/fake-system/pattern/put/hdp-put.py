import random
import math
import time
from locust import HttpUser, task, between, LoadTestShape

# === Config ===
BASE_URL = "http://10.2.16.116:8610"
AUTH_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3NTc3NjA5MTgsInN1YiI6IjEifQ.hriGLcrlmQ9iGLbKj_9tZzhiRvhU2G2yFrJcnTHeLbA"

COMMON_HEADERS = {
    "accept": "application/json",
    "Content-Type": "application/json",
    "Authorization": f"Bearer {AUTH_TOKEN}"
}

# === PUT APIs ===
def get_put_apis():
    unique_id = random.randint(1000, 9999)
    email = f"user{unique_id}@test.com"
    username = f"user_{unique_id}"
    contact = str(random.randint(6000000000, 9999999999))

    return [
        ("/user/update-user/1", COMMON_HEADERS, {
            "username": username,
            "email": email,
            "location": "hyderabad",
            "organisation": "IIITH",
            "designation": "research engineer",
            "password": "newpass123",
            "contact": contact,
            "vendor_website": "scrc.com",
            "firstname": "Updated",
            "lastname": "User",
            "vendor_email": email,
            "is_locked": False
        }),
        ("/verticals/update-ae/3", COMMON_HEADERS, {
            "res_name": "Updated Vertical",
            "res_short_name": "UV",
            "description": "Updated description",
            "labels": ["label1"],
            "name": ["pm2.5"],
            "data_types": ["string"],
            "accuracy": ["±1"],
            "units": ["µg/m3"],
            "resolution": ["0.1"],
            "pdescription": ["Updated description"],
            "ideal": [{"min": 0, "max": 50}],
            "moderate": [{"min": 51, "max": 100}],
            "extreme": [{"min": 101, "max": 200}]
        }),
        ("/alarms/1/mark-read", COMMON_HEADERS, {
            "remarks": "fixed the issue"
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
class PeriodicUser(HttpUser):
    wait_time = between(1, 3)

    @task
    def put_requests(self):
        endpoint, headers, payload = random.choice(get_put_apis())
        url = f"{BASE_URL}{endpoint}"
        response = self.client.put(url, headers=headers, json=payload)
        if response.status_code in [200, 201]:
            print(f"[OK] {endpoint}")
        else:
            print(f"[FAIL] {endpoint} -> {response.status_code}")
