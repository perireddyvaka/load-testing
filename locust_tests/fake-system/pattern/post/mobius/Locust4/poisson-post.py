import random
import time
import math
from locust import HttpUser, task, LoadTestShape

# === Config ===
BASE_URL = "http://10.2.16.116:8610"
AUTH_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3NTc3NjA5MTgsInN1YiI6IjEifQ.hriGLcrlmQ9iGLbKj_9tZzhiRvhU2G2yFrJcnTHeLbA"

COMMON_HEADERS = {
    "accept": "application/json",
    "Content-Type": "application/json",
    "Authorization": f"Bearer {AUTH_TOKEN}"
}
PUBLIC_HEADERS = {
    "accept": "application/json",
    "Content-Type": "application/json"
}
FORM_HEADERS = {
    "accept": "application/json",
    "Content-Type": "application/x-www-form-urlencoded"
}

# === Poisson Load Shape ===
class PoissonLoadShape(LoadTestShape):
    step_time = 60      # ramp every 60s
    step_load = 5       # add 5 users
    spawn_rate = 10
    time_limit = 3600   # 1 hour

    def tick(self):
        run_time = self.get_run_time()
        if run_time > self.time_limit:
            return None
        current_step = math.floor(run_time / self.step_time) + 1
        return (current_step * self.step_load, self.spawn_rate)

# === Static POST APIs ===
STATIC_POST_APIS = [
    # 1. Login (no auth)
    ("/user/login", PUBLIC_HEADERS, {
        "email": "admin@localhost",
        "password": "admin"
    }),
    # 2. Forgot password
    ("/user/forgot-password", PUBLIC_HEADERS, {
        "email": "admin@localhost"
    }),
    # 3. Reset password
    ("/user/reset-password", PUBLIC_HEADERS, {
        "email": "admin@localhost",
        "new_password": "admin"
    }),
    # 4. Change password (auth)
    ("/user/change-password", COMMON_HEADERS, {
        "email": "admin@localhost",
        "old_password": "admin",
        "new_password": "admin"
    }),
    # 5. Create AE (auth)
    ("/verticals/create-ae", COMMON_HEADERS, [
        {
            "res_name": "Air Quality1",
            "res_short_name": "AL",
            "description": "Air monitoring vertical.",
            "pdescription": ["pm2.5", "pm10", "co2", "voc_index", "temperature"],
            "name": ["pm2.5", "pm10", "co2", "voc_index", "temperature"],
            "data_types": ["string"] * 5,
            "accuracy": ["±0"] * 5,
            "units": ["null", "null", "null", "null", "°C"],
            "resolution": ["0"] * 5,
            "ideal": [{"min": 0.0, "max": 0.0}] * 5,
            "moderate": [{"min": 0.0, "max": 0.0}] * 5,
            "extreme": [{"min": 0.0, "max": 0.0}] * 5
        }
    ]),
    # 6. Assign vendor to vertical
    ("/verticals/assign-vendor", COMMON_HEADERS, {
        "vertical_id": 1,
        "vendor_email": "vakaperireddy59@gmail.com"
    }),
    # 7. Assign vendor to node
    ("/nodes/assign-vendor", COMMON_HEADERS, {
        "node_id": "1",
        "vendor_email": "vakaperireddy59@gmail.com"
    }),
    # 8. Create CIN (public)
    ("/nodes/create-cin/1", PUBLIC_HEADERS, {
        "pm2.5": 2
    }),
    # 9. Sensor-types create
    ("/sensor-types/create", COMMON_HEADERS, {
        "res_name": "Temperature",
        "parameters": ["temp"],
        "data_types": ["float"],
        "labels": [],
        "vertical_id": 1,
        "accuracy": ["±0.5"],
        "units": ["°C"],
        "resolution": ["0.1"],
        "ideal": [{"min": 0, "max": 50}],
        "moderate": [{"min": 51, "max": 70}],
        "extreme": [{"min": 71, "max": 100}]
    }),
    # 10. Sensor-types assign vendor
    ("/sensor-types/assign-vendor", COMMON_HEADERS, {
        "sensortype_id": 1,
        "vendor_email": "vakaperireddy59@gmail.com"
    }),
    # 11. Subscription get-subscriptions
    ("/subscription/get-subscriptions", COMMON_HEADERS, {
        "node_id": "AQ01-0000-0001"
    })
]

# === Dynamic APIs (unique payloads per request) ===
def get_dynamic_post_apis():
    unique_id = random.randint(1000, 9999)
    contact = str(random.randint(6000000000, 9999999999))
    email = f"vendor{unique_id}@test.com"
    username = f"Vendor_{unique_id}"
    notify_url = f"http://10.2.16.116:8610/notify/listener/{unique_id}"

    return [
        # Onboard user-request (form-data, dynamic)
        ("/onboard/user-request", FORM_HEADERS, {
            "contact": contact,
            "lastname": "IIITH",
            "vendor_website": "scrc.com",
            "vendor_email": "",
            "user_type": "vendor",
            "location": "hyderabad",
            "username": username,
            "designation": "research engineer",
            "organisation": "IIITH",
            "firstname": "Vendor",
            "email": email
        }),
        # Subscription subscribe (dynamic url)
        ("/subscription/subscribe", COMMON_HEADERS, {
            "url": notify_url,
            "node_id": "AQ01-0000-0001"
        })
    ]

# === Locust User ===
class MyUser(HttpUser):
    # Poisson arrivals: exponential wait times
    def wait_time(self):
        # λ = 0.2 → mean interval = 5s between requests
        return random.expovariate(0.2)

    @task
    def post_requests(self):
        all_apis = STATIC_POST_APIS + get_dynamic_post_apis()
        endpoint, headers, payload = random.choice(all_apis)
        url = f"{BASE_URL}{endpoint}"

        if headers.get("Content-Type") == "application/x-www-form-urlencoded":
            response = self.client.post(url, headers=headers, data=payload)
        else:
            response = self.client.post(url, headers=headers, json=payload)

        if response.status_code in [200, 201]:
            print(f"[OK] {endpoint} @ {time.strftime('%H:%M:%S')}")
        else:
            print(f"[FAIL] {endpoint} -> {response.status_code}")
