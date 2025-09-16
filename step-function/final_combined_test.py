#!/usr/bin/env python3
"""
FINAL Combined Load Testing Script (Ordered Flow)
- Sequential POST requests (fixed order, same vendor email)
- Independent GET requests (all listed endpoints)
- Independent PUT requests (all listed endpoints)
"""

import random
from urllib.parse import quote
import math
import time
from locust import HttpUser, task, between, LoadTestShape

# === Config ===
BASE_URL = "http://10.2.16.116:8610"
AUTH_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3NTc5Mzc0NDIsInN1YiI6IjEifQ.zMLfm6MBjR2DHx2VfYCBkMMTMcLcR6LzF4vvkINFq48"
CIN_TOKEN = "0ee5ffa6c522210e49ca0b3328d8c3d3"

COMMON_HEADERS = {
    "accept": "application/json",
    "Content-Type": "application/json",
    "Authorization": f"Bearer {AUTH_TOKEN}"
}
PUBLIC_HEADERS = {
    "accept": "application/json",
    "Content-Type": "application/json"
}
CIN_HEADERS = {
    "accept": "application/json",
    "Content-Type": "application/json",
    "X-M2M-Origin": CIN_TOKEN
}
FORM_HEADERS = {
    "accept": "application/json",
    "Content-Type": "application/x-www-form-urlencoded"
}

# === Step Function Load Shape ===
class StepLoadShape(LoadTestShape):
    step_time = 60
    step_load = 5
    spawn_rate = 10
    time_limit = 3600

    def tick(self):
        run_time = self.get_run_time()
        if run_time > self.time_limit:
            return None
        current_step = math.floor(run_time / self.step_time) + 1
        return (current_step * self.step_load, self.spawn_rate)


# === IoT Data for Randomization ===
IOT_VERTICALS = [
    {
        "name": "Energy Monitoring",
        "short": "EM",
        "description": "Smart energy monitoring",
        "parameters": ["voltage", "current", "power"],
        "data_types": ["float", "float", "float"],
        "units": ["V", "A", "W"]
    },
    {
        "name": "Air Quality",
        "short": "AQ",
        "description": "Air quality monitoring",
        "parameters": ["pm2.5", "pm10", "co2"],
        "data_types": ["float", "float", "float"],
        "units": ["µg/m³", "µg/m³", "ppm"]
    }
]
SENSOR_TYPES = [
    "Temperature Sensor", "Humidity Sensor", "Pressure Sensor", "Gas Sensor"
]



# === 1. Sequential POST Workflow User ===
class SequentialPostUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        """Initialize random vendor details once per user"""
        uid = random.randint(1000, 999999)
        self.vendor_email = f"vendor{uid}@test.com"
        self.vendor_contact = str(random.randint(6000000000, 9999999999))
        self.vertical = random.choice(IOT_VERTICALS)
        self.sensor_name = random.choice(SENSOR_TYPES)
        self.username = f"Vendor_{int(time.time()*1000)}_{random.randint(1000,9999)}"
        print(f"[INIT] Using vendor {self.vendor_email}")

    @task
    def sequential_posts(self):
        """Execute POST requests in strict order"""

        # 1. User Request
         # 1. User Request
        payload = {
            "contact": self.vendor_contact,
            "lastname": "iiith",
            "vendor_website": "scrc.com",
            # Fix: send None instead of "" for optional field
            # "vendor_email": "",  
            "user_type": "vendor",
            "location": "iiith",
            "username": self.username,
            "designation": "lead",
            "organisation": "iiith",
            "firstname": "user1",
            "email": self.vendor_email
        }

        with self.client.post(
            f"{BASE_URL}/onboard/user-request",
            headers=FORM_HEADERS,
            data=payload,
            catch_response=True
        ) as resp:
            if resp.status_code == 200:
                print(f"[POST ✅] user-request created {self.vendor_email}")
            else:
                print(f"[POST ❌] user-request ({resp.status_code})")
                print("[DEBUG] Response:", resp.text)
                return  # Stop flow if request fails
        # 2. Approve Vendor
        with self.client.post(
            f"{BASE_URL}/onboard/approve-vendor?email={self.vendor_email}",
            headers=COMMON_HEADERS,
            json={},
            catch_response=True
        ) as resp:
            if resp.status_code == 200:
                print(f"[POST ✅] approve-vendor for {self.vendor_email}")
            else:
                print(f"[POST ❌] approve-vendor ({resp.status_code})")
                print("[DEBUG] Response:", resp.text)
        print("[POST] user-request")

        # 2. Approve Vendor
        self.client.post(
            f"{BASE_URL}/onboard/approve-vendor?email={self.vendor_email}",
            headers=COMMON_HEADERS,
            json={}
        )
        print("[POST] approve-vendor")

        # 3. Create AE (Vertical)
        self.client.post(
            f"{BASE_URL}/verticals/create-ae",
            headers=COMMON_HEADERS,
            json={
                "res_name": f"{self.vertical['name']} {random.randint(1000,9999)}",
                "res_short_name": self.vertical['short'],
                "description": self.vertical['description'],
                "labels": [],
                "name": [self.vertical['parameters'][0]],
                "data_types": [self.vertical['data_types'][0]],
                "accuracy": ["±1"],
                "units": [self.vertical['units'][0]],
                "resolution": ["0.1"],
                "pdescription": [self.vertical['parameters'][0]],
                "status": "accepted",
                "remarks": "Auto vertical",
                "ideal": [{"min": 15, "max": 30}],
                "moderate": [{"min": 10, "max": 15}, {"min": 30, "max": 35}],
                "extreme": [{"min": 5, "max": None}]
            }
        )
        print("[POST] create-ae")

        # 4. Assign Vendor to Vertical
        self.client.post(
            f"{BASE_URL}/verticals/assign-vendor",
            headers=COMMON_HEADERS,
            json={"vertical_id": 1, "vendor_email": self.vendor_email}
        )
        print("[POST] assign-vendor vertical")

        # 5. Create Sensor Type
        self.client.post(
            f"{BASE_URL}/sensor-types/create",
            headers=COMMON_HEADERS,
            json={
                "res_name": f"{self.sensor_name} {random.randint(1000,9999)}",
                "parameters": self.vertical["parameters"],
                "data_types": self.vertical["data_types"],
                "labels": [],
                "vertical_id": 3,
                "accuracy": ["±0.5"] * len(self.vertical["parameters"]),
                "units": self.vertical["units"],
                "resolution": ["0.1"] * len(self.vertical["parameters"]),
                "ideal": [{"min": 0, "max": 50}] * len(self.vertical["parameters"]),
                "moderate": [{"min": 51, "max": 70}] * len(self.vertical["parameters"]),
                "extreme": [{"min": 71, "max": 100}] * len(self.vertical["parameters"])
            }
        )
        print("[POST] create sensor-type")

        # 6. Assign Vendor to Sensor Type
        self.client.post(
            f"{BASE_URL}/sensor-types/assign-vendor",
            headers=COMMON_HEADERS,
            json={"sensortype_id": 1, "vendor_email": self.vendor_email}
        )
        print("[POST] assign-vendor sensor-type")

        # 7. Assign Vendor to Node
        self.client.post(
            f"{BASE_URL}/nodes/assign-vendor",
            headers=COMMON_HEADERS,
            json={"node_id": 1, "vendor_email": self.vendor_email}
        )
        print("[POST] assign-vendor node")

        # 8. Login
        self.client.post(
            f"{BASE_URL}/user/login",
            headers=PUBLIC_HEADERS,
            json={"email": self.vendor_email, "password": "vendor@1234"}
        )
        print("[POST] login")

        # 9. Reset Password
        self.client.post(
            f"{BASE_URL}/user/reset-password",
            headers=PUBLIC_HEADERS,
            json={"email": self.vendor_email, "new_password": f"pass{random.randint(1000,9999)}"}
        )
        print("[POST] reset-password")

        # 10. Forgot Password
        self.client.post(
            f"{BASE_URL}/user/forgot-password",
            headers=PUBLIC_HEADERS,
            json={"email": self.vendor_email}
        )
        print("[POST] forgot-password")

        # 11. Create CIN
        self.client.post(
            f"{BASE_URL}/nodes/create-cin/2",
            headers=CIN_HEADERS,
            json={self.vertical["parameters"][0]: round(random.uniform(1.0, 100.0), 2)}
        )
        print("[POST] create-cin")

        # 12. Subscribe
        self.client.post(
            f"{BASE_URL}/subscription/subscribe",
            headers=COMMON_HEADERS,
            json={"url": f"http://10.2.16.116:8610/notify/{random.randint(1000,9999)}",
                  "node_id": "EM01-0064-0002"}
        )
        print("[POST] subscribe")


# === 2. GET User (all listed endpoints) ===
GET_ENDPOINTS = [
    # User
    ("/user/profile", COMMON_HEADERS),
    ("/user/getusers", COMMON_HEADERS),

    # Verticals
    ("/verticals/verticals-all", COMMON_HEADERS),
    ("/verticals/vocabulary", PUBLIC_HEADERS),

    # Sensor Types
    ("/sensor-types/sensor-types-all", COMMON_HEADERS),
    ("/sensor-types/get/1", COMMON_HEADERS),

    # Nodes
    ("/nodes/get-vendor/EM01-0064-0002", COMMON_HEADERS),
    ("/nodes/nodes-all", COMMON_HEADERS),
    ("/nodes/energy_monitoring", COMMON_HEADERS),
    ("/nodes/get-node-data/EM01-0064-0002", COMMON_HEADERS),
    ("/nodes/get-node/EM01-0064-0002/descriptor/all", COMMON_HEADERS),
    ("/nodes/meta/id/EM01-0064-0002", COMMON_HEADERS),
    ("/nodes/fetch-node-data/?vertical_name=energy_monitoring&limit=100&offset=0&as_csv=false", COMMON_HEADERS),

    # Stats
    ("/stats/vertical_names", PUBLIC_HEADERS),
    ("/stats/stats", PUBLIC_HEADERS),
    ("/stats/working_nodes/status", PUBLIC_HEADERS),
    ("/stats/nodes_area", PUBLIC_HEADERS),
    ("/stats/get-all", COMMON_HEADERS),

    # Onboard
    ("/onboard/get-verticals-request", COMMON_HEADERS),

    # Subscribe
    ("/subscription/get-user-subscriptions", COMMON_HEADERS),

    # Alarms
    ("/alarms/alarms", COMMON_HEADERS),
    ("/alarms/notifications", COMMON_HEADERS),
]

class GetUser(HttpUser):
    wait_time = between(1, 5)

    @task
    def get_requests(self):
        endpoint, headers = random.choice(GET_ENDPOINTS)
        url = f"{BASE_URL}{endpoint}"
        self.client.get(url, headers=headers)
        print(f"[GET] {endpoint}")


# === 3. PUT User (all listed endpoints) ===
alarm_id_counter = 1

def generate_put_endpoints():
    global alarm_id_counter
    unique_id = random.randint(1000, 9999)

    email = f"user{unique_id}@test.com"
    username = f"user_{unique_id}"
    contact = str(random.randint(6000000000, 9999999999))

    put_apis = [
        # User update
        ("/user/update-user/1", COMMON_HEADERS, {
            "username": username,
            "email": email,
            "location": "hyderabad",
            "organisation": "IIITH",
            "designation": "research engineer",
            "password": f"newpass{random.randint(100, 999)}",
            "contact": contact,
            "vendor_website": "scrc.com",
            "firstname": "Updated",
            "lastname": "User",
            "vendor_email": email,
            "is_locked": False
        }),

        # Vertical update
        ("/verticals/update-ae/1", COMMON_HEADERS, {
            "res_name": f"Updated Vertical {unique_id}",
            "res_short_name": random.choice(["UV", "UP", "UT", "UE"]),
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

        # Alarm mark read
        (f"/alarms/{alarm_id_counter}/mark-read", COMMON_HEADERS, {
            "remarks": f"Fixed issue #{alarm_id_counter} - {unique_id}"
        })
    ]

    alarm_id_counter += 1
    return put_apis

class PutUser(HttpUser):
    wait_time = between(1, 5)

    @task
    def put_requests(self):
        endpoint, headers, payload = random.choice(generate_put_endpoints())
        url = f"{BASE_URL}{endpoint}"
        self.client.put(url, headers=headers, json=payload)
        print(f"[PUT] {endpoint}")
