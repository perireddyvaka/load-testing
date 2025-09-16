#!/usr/bin/env python3
"""
Step Function Load Test (Sequential: user-request → approve-vendor)
- Duration: 10 minutes
- Gradually increases load every 60 seconds
- Uses static admin token
"""

import random
import time
import math
from locust import HttpUser, task, between, LoadTestShape

# === Config ===
BASE_URL = "http://10.2.16.116:8002"
ADMIN_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3NTgwNTgzNTIsInN1YiI6IjEifQ.VWCk1DWiXg7byV3ed8Bd6-oU-HxJ8Ta29JVn66wmbYM"

COMMON_HEADERS = {
    "accept": "application/json",
    "Content-Type": "application/json",
    "Authorization": f"Bearer {ADMIN_TOKEN}"
}
PUBLIC_HEADERS = {
    "accept": "application/json",
    "Content-Type": "application/json"
}
FORM_HEADERS = {
    "accept": "application/json",
    "Content-Type": "application/x-www-form-urlencoded"
}

# === IoT Vertical Data ===
IOT_VERTICALS = [
    {
        "name": "Energy Monitoring",
        "short": "EM",
        "description": "Smart energy monitoring system",
        "parameters": ["voltage", "current", "power"],
        "data_types": ["float", "float", "float"],
        "units": ["V", "A", "W"]
    },
    {
        "name": "Air Quality",
        "short": "AQ",
        "description": "Air quality monitoring system",
        "parameters": ["pm2.5", "pm10", "co2"],
        "data_types": ["float", "float", "float"],
        "units": ["µg/m³", "µg/m³", "ppm"]
    },
    {
        "name": "Water Quality", 
        "short": "WQ",
        "description": "Water quality monitoring system",
        "parameters": ["ph", "turbidity", "temperature"],
        "data_types": ["float", "float", "float"],
        "units": ["pH", "NTU", "°C"]
    }
]

SENSOR_TYPES = [
    "Temperature Sensor", "Humidity Sensor", "Pressure Sensor", "Gas Sensor",
    "pH Sensor", "Turbidity Sensor", "Motion Sensor", "Light Sensor"
]

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


# === Sequential POST Flow User ===
class SequentialPostUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        """Initialize user instance"""
        self.base_uid = random.randint(100000, 999999)
        print(f"[INIT] User instance started with base UID: {self.base_uid}")

    @task
    def sequential_posts(self):
        """Step Function: user-request → approve-vendor → create-ae → assign-vendor"""
        
        # Generate unique identifiers for EACH request
        unique_id = random.randint(1000000, 9999999)
        timestamp = int(time.time() * 1000000)  # microseconds for more uniqueness
        vendor_email = f"vendor{unique_id}@test.com"
        vendor_contact = str(random.randint(6000000000, 9999999999))
        username = f"Vendor_{timestamp}_{unique_id}_{random.randint(1000,9999)}"
        vertical = random.choice(IOT_VERTICALS)  # Select random vertical
        
        print(f"[REQUEST] Email: {vendor_email}, Username: {username}, Vertical: {vertical['name']}")

        # 1️⃣ User Request
        payload = {
            "contact": vendor_contact,
            "lastname": "iiith",
            "vendor_website": "scrc.com",
            "user_type": "vendor",
            "location": "iiith",
            "username": username,
            "designation": "lead",
            "organisation": "iiith",
            "firstname": "user1",
            "email": vendor_email
        }

        with self.client.post(
            f"{BASE_URL}/onboard/user-request",
            headers=FORM_HEADERS,
            data=payload,
            catch_response=True
        ) as resp:
            if resp.status_code == 200:
                print(f"[POST ✅] user-request created {vendor_email}")
            else:
                print(f"[POST ❌] user-request ({resp.status_code})")
                print("[DEBUG] Response:", resp.text)
                # Continue instead of returning - don't stop the flow

        # 2️⃣ Approve Vendor
        with self.client.post(
            f"{BASE_URL}/onboard/approve-vendor?email={vendor_email}",
            headers=COMMON_HEADERS,
            json={},
            catch_response=True
        ) as resp:
            if resp.status_code == 200:
                print(f"[POST ✅] approve-vendor for {vendor_email}")
            else:
                print(f"[POST ❌] approve-vendor ({resp.status_code})")
                print("[DEBUG] Response:", resp.text)
                # Continue instead of returning - don't stop the flow

        # 3️⃣ Create AE (Vertical)
        create_ae_payload = {
            "res_name": f"{vertical['name']} {unique_id}",
            "res_short_name": vertical['short'],
            "description": vertical['description'],
            "labels": [],
            "name": [vertical['parameters'][0]],
            "data_types": [vertical['data_types'][0]],
            "accuracy": ["±1"],
            "units": [vertical['units'][0]],
            "resolution": ["0.1"],
            "pdescription": [vertical['parameters'][0]],
            "status": "accepted",
            "remarks": f"Auto-generated vertical for {vertical['name']}",
            "ideal": [{"min": 15, "max": 30}],
            "moderate": [
                {"min": 10, "max": 15},
                {"min": 30, "max": 35}
            ],
            "extreme": [{"min": 5, "max": None}]
        }

        with self.client.post(
            f"{BASE_URL}/verticals/create-ae",
            headers=COMMON_HEADERS,
            json=create_ae_payload,
            catch_response=True
        ) as resp:
            if resp.status_code in [200, 201]:
                print(f"[POST ✅] create-ae vertical {vertical['name']}")
            else:
                print(f"[POST ❌] create-ae ({resp.status_code})")
                print("[DEBUG] Response:", resp.text)
                # Continue instead of returning

        # 4️⃣ Assign Vendor to Vertical
        with self.client.post(
            f"{BASE_URL}/verticals/assign-vendor",
            headers=COMMON_HEADERS,
            json={"vertical_id": 1, "vendor_email": vendor_email},
            catch_response=True
        ) as resp:
            if resp.status_code == 200:
                print(f"[POST ✅] assign-vendor to vertical for {vendor_email}")
            else:
                print(f"[POST ❌] assign-vendor vertical ({resp.status_code})")
                print("[DEBUG] Response:", resp.text)
                # Continue instead of returning

        # 5️⃣ Create Sensor Type (under vertical_id = 1)
        sensor_name = random.choice(SENSOR_TYPES)
        sensor_type_payload = {
            "res_name": f"{sensor_name} {unique_id}",
            "parameters": vertical["parameters"],
            "data_types": vertical["data_types"],
            "labels": [],
            "vertical_id": 1,  # Use vertical_id = 1 as requested
            "accuracy": ["±0.5"] * len(vertical["parameters"]),
            "units": vertical["units"],
            "resolution": ["0.1"] * len(vertical["parameters"]),
            "ideal": [{"min": 0, "max": 50}] * len(vertical["parameters"]),
            "moderate": [{"min": 51, "max": 70}] * len(vertical["parameters"]),
            "extreme": [{"min": 71, "max": 100}] * len(vertical["parameters"])
        }

        with self.client.post(
            f"{BASE_URL}/sensor-types/create",
            headers=COMMON_HEADERS,
            json=sensor_type_payload,
            catch_response=True
        ) as resp:
            if resp.status_code in [200, 201]:
                print(f"[POST ✅] create sensor-type {sensor_name}")
            else:
                print(f"[POST ❌] create sensor-type ({resp.status_code})")
                print("[DEBUG] Response:", resp.text)
                # Continue instead of returning

        # 6️⃣ Assign Vendor to Sensor Type (same vendor email that was assigned to vertical)
        with self.client.post(
            f"{BASE_URL}/sensor-types/assign-vendor",
            headers=COMMON_HEADERS,
            json={"sensortype_id": 1, "vendor_email": vendor_email},
            catch_response=True
        ) as resp:
            if resp.status_code == 200:
                print(f"[POST ✅] assign-vendor to sensor-type for {vendor_email}")
            else:
                print(f"[POST ❌] assign-vendor sensor-type ({resp.status_code})")
                print("[DEBUG] Response:", resp.text)
                # Continue instead of returning

        # 7️⃣ Import Node Configuration
        import_payload = {
            "nodes": [
                {
                    "latitude": 17.446919 + random.uniform(-0.01, 0.01),  # Add small variation
                    "longitude": 78.612 + random.uniform(-0.01, 0.01),   # Add small variation
                    "area": random.choice(["Gachibowli", "Hitech City", "Kondapur", "Madhapur"]),
                    "sensor_type": "WMSensor-1",
                    "domain": "waste_management", 
                    "name": f"Node-{unique_id}-{random.randint(1000,9999)}",  # Unique node name
                    "protocol": "MQTT",
                    "frequency": "00:01:00"
                }
            ]
        }

        with self.client.post(
            f"{BASE_URL}/import/import",
            headers=COMMON_HEADERS,
            json=import_payload,
            catch_response=True
        ) as resp:
            if resp.status_code in [200, 201]:
                print(f"[POST ✅] import node configuration")
            else:
                print(f"[POST ❌] import node ({resp.status_code})")
                print("[DEBUG] Response:", resp.text)
                # Continue instead of returning

        # 8️⃣ Assign Vendor to Node (same vendor email)
        with self.client.post(
            f"{BASE_URL}/nodes/assign-vendor",
            headers=COMMON_HEADERS,
            json={"node_id": "2", "vendor_email": vendor_email},
            catch_response=True
        ) as resp:
            if resp.status_code == 200:
                print(f"[POST ✅] assign-vendor to node for {vendor_email}")
            else:
                print(f"[POST ❌] assign-vendor node ({resp.status_code})")
                print("[DEBUG] Response:", resp.text)

        # 9️⃣ Create CIN for Node 35 (token_id = 35)
        cin_headers_node35 = {
            "Content-Type": "application/json", 
            "Authorization": "Bearer c6314951967074059644d0dcff10ccb9"
        }
        cin_data_node35 = {
            "bin_data": "example",
            "people_count": random.randint(30, 50)  # Random people count between 30-50
        }
        
        with self.client.post(
            f"{BASE_URL}/nodes/create-cin/33",
            headers=cin_headers_node35,
            json=cin_data_node35,
            catch_response=True
        ) as resp:
            if resp.status_code in [200, 201]:
                print(f"[POST ✅] create-cin for node 35 (people_count: {cin_data_node35['people_count']}, bin_data: {cin_data_node35['bin_data']})")
            else:
                print(f"[POST ❌] create-cin node 35 ({resp.status_code})")
                print("[DEBUG] Response:", resp.text)
                # Continue instead of returning

        # # 🔟 Create CIN for Node 2 (token_id = 2)
        # cin_headers_node2 = {
        #     "Content-Type": "application/json", 
        #     "Authorization": "Bearer b9ab54278182c4f7fcc8d7b6f363af99"
        # }
        # cin_data_node2 = {
        #     "bin_data": "example",
        #     "people_count": random.randint(70, 90)  # Random people count between 70-90
        # }
        
        # with self.client.post(
        #     f"{BASE_URL}/nodes/create-cin/2",
        #     headers=cin_headers_node2,
        #     json=cin_data_node2,
        #     catch_response=True
        # ) as resp:
        #     if resp.status_code in [200, 201]:
        #         print(f"[POST ✅] create-cin for node 2 (people_count: {cin_data_node2['people_count']}, bin_data: {cin_data_node2['bin_data']})")
        #     else:
        #         print(f"[POST ❌] create-cin node 2 ({resp.status_code})")
        #         print("[DEBUG] Response:", resp.text)
        #         # Continue instead of returning

        # 11️⃣ User Login
        login_headers = {
            "accept": "application/json",
            "Content-Type": "application/json"
        }
        login_data = {
            "email": "vakaperireddy59@gmail.com",
            "password": "vendor@1234"
        }
        
        with self.client.post(
            f"{BASE_URL}/user/login",
            headers=login_headers,
            json=login_data,
            catch_response=True
        ) as resp:
            if resp.status_code == 200:
                print(f"[POST ✅] user login successful")
            else:
                print(f"[POST ❌] user login ({resp.status_code})")
                print("[DEBUG] Response:", resp.text)
                # Continue instead of returning

        # 12️⃣ Forgot Password
        forgot_emails = ["vakaperireddy59@gmail.com", "vakaperireddy5555@gmail.com"]
        forgot_email = random.choice(forgot_emails)
        forgot_password_data = {
            "email": forgot_email
        }
        
        with self.client.post(
            f"{BASE_URL}/user/forgot-password",
            headers=login_headers,
            json=forgot_password_data,
            catch_response=True
        ) as resp:
            if resp.status_code == 200:
                print(f"[POST ✅] forgot-password for {forgot_email}")
            else:
                print(f"[POST ❌] forgot-password ({resp.status_code})")
                print("[DEBUG] Response:", resp.text)
                # Continue instead of returning

        # 13️⃣ Reset Password
        random_password = f"NewPass{random.randint(1000, 9999)}!"
        reset_password_data = {
            "email": "vakaperireddy5555@gmail.com",
            "new_password": random_password
        }
        
        with self.client.post(
            f"{BASE_URL}/user/reset-password",
            headers=login_headers,
            json=reset_password_data,
            catch_response=True
        ) as resp:
            if resp.status_code == 200:
                print(f"[POST ✅] reset-password (new password: {random_password})")
            else:
                print(f"[POST ❌] reset-password ({resp.status_code})")
                print("[DEBUG] Response:", resp.text)
                # Continue instead of returning

        # 14️⃣ Subscribe to Node
        notify_url = f"http://10.2.16.116:8610/notify/{random.randint(1000, 9999)}"
        subscribe_data = {
            "url": notify_url,
            "node_id": "WM01-0064-0001"
        }
        
        with self.client.post(
            f"{BASE_URL}/subscription/subscribe",
            headers=COMMON_HEADERS,
            json=subscribe_data,
            catch_response=True
        ) as resp:
            if resp.status_code == 200:
                print(f"[POST ✅] subscription created (URL: {notify_url})")
            else:
                print(f"[POST ❌] subscription ({resp.status_code})")
                print("[DEBUG] Response:", resp.text)
                # Continue instead of returning


# === GET Endpoints ===
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
    ("/nodes/get-vendor/WM01-0064-0001", COMMON_HEADERS),
    ("/nodes/nodes-all", COMMON_HEADERS),
    ("/nodes/waste_management", COMMON_HEADERS),
    ("/nodes/get-node-data/WM01-0064-0001", COMMON_HEADERS),
    ("/nodes/get-node/WM01-0064-0001/descriptor/all", COMMON_HEADERS),
    ("/nodes/meta/id/WM01-0064-0001", COMMON_HEADERS),
    ("/nodes/fetch-node-data/?vertical_name=waste_management&limit=100&offset=0&as_csv=false", COMMON_HEADERS),

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

# === GET User Class ===
class GetUser(HttpUser):
    """Independent GET requests user class"""
    wait_time = between(1, 5)

    @task
    def get_requests(self):
        """Execute random GET requests"""
        endpoint, headers = random.choice(GET_ENDPOINTS)
        url = f"{BASE_URL}{endpoint}"
        
        with self.client.get(url, headers=headers, catch_response=True) as resp:
            if resp.status_code == 200:
                print(f"[GET ✅] {endpoint}")
            else:
                print(f"[GET ❌] {endpoint} ({resp.status_code})")
                print("[DEBUG] Response:", resp.text[:200])  # Limit response text


# === PUT Endpoints ===
alarm_id_counter = 1

def generate_put_endpoints():
    """Generate PUT endpoints with dynamic data"""
    global alarm_id_counter
    unique_id = random.randint(1000, 9999)

    email = f"user{unique_id}@test.com"
    username = f"user_{unique_id}"
    contact = str(random.randint(6000000000, 9999999999))

    put_apis = [
        # User update
        ("/user/update-user/2", COMMON_HEADERS, {
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

        # # Vertical update
        # ("/verticals/update-ae/2", COMMON_HEADERS, {
        #     "res_name": f"Updated Vertical {unique_id}",
        #     "res_short_name": random.choice(["UV", "UP", "UT", "UE"]),
        #     "description": "Updated description",
        #     "labels": ["label1"],
        #     "name": ["pm2.5"],
        #     "data_types": ["string"],
        #     "accuracy": ["±1"],
        #     "units": ["µg/m3"],
        #     "resolution": ["0.1"],
        #     "pdescription": ["Updated description"],
        #     "ideal": [{"min": 0, "max": 50}],
        #     "moderate": [{"min": 51, "max": 100}],
        #     "extreme": [{"min": 101, "max": 200}]
        # }),

        # # Alarm mark read
        # (f"/alarms/{alarm_id_counter}/mark-read", COMMON_HEADERS, {
        #     "remarks": f"Fixed issue #{alarm_id_counter} - {unique_id}"
        # })
    ]

    alarm_id_counter += 1
    return put_apis

# === PUT User Class ===
class PutUser(HttpUser):
    """Independent PUT requests user class"""
    wait_time = between(1, 5)

    @task
    def put_requests(self):
        """Execute random PUT requests"""
        endpoint, headers, payload = random.choice(generate_put_endpoints())
        url = f"{BASE_URL}{endpoint}"
        
        with self.client.put(url, headers=headers, json=payload, catch_response=True) as resp:
            if resp.status_code in [200, 201]:
                print(f"[PUT ✅] {endpoint}")
            else:
                print(f"[PUT ❌] {endpoint} ({resp.status_code})")
                print("[DEBUG] Response:", resp.text[:200])  # Limit response text


# === Direct Execution ===
if __name__ == "__main__":
    import subprocess
    import sys
    import os
    
    print("🚀 Starting Complete IoT Backend Load Test...")
    print("📊 Web UI: http://localhost:8089")
    print("🔄 Tests: Sequential POST workflow + Independent GET/PUT requests")
    print("🎯 Target: http://10.2.16.116:8610")
    print("⏱️  Duration: Configurable via web UI")
    print("📋 Coverage: 14 POST steps + 24 GET endpoints + 3 PUT endpoints")
    print("-" * 60)
    
    # Get the current script path
    script_path = os.path.abspath(__file__)
    
    # Locust command with web interface
    cmd = [
        "locust",
        "-f", script_path,
        "--host", BASE_URL,
        "--web-host", "0.0.0.0", 
        "--web-port", "8089"
    ]
    
    try:
        # Start Locust with web UI
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running Locust: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n⏹️  Test stopped by user")
        sys.exit(0)
