#!/usr/bin/env python3
"""
Step Function Load Test (High Density Periodic: burst load every 10s)
- Duration: 1 hour (configurable)
- Bursts every 10 seconds within each minute
- Uses static admin token
"""

import random
import time
import math
import gevent
from gevent.lock import Semaphore
from locust import HttpUser, task, between, LoadTestShape

# === Config ===
BASE_URL = "http://10.2.16.116:8610"
ADMIN_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3NTgwNzc4NzYsInN1YiI6IjEifQ.qqep29pgFBsrPgO2O78OBAZ8SnxcrOSVltn_HmLzIQs"

# Global variable to store fresh token
FRESH_TOKEN = None

def get_fresh_token():
    """Get a fresh token by logging in with correct admin credentials"""
    global FRESH_TOKEN
    if FRESH_TOKEN:
        return FRESH_TOKEN
        
    import requests
    login_url = f"{BASE_URL}/user/login"
    login_data = {
        "email": "admin@localhost", 
        "password": "admin"
    }
    
    try:
        response = requests.post(login_url, json=login_data, headers={
            "accept": "application/json",
            "Content-Type": "application/json"
        }, timeout=15)  # 15 second timeout
        
        if response.status_code == 200:
            result = response.json()
            if 'access_token' in result:
                FRESH_TOKEN = result['access_token']
                print(f"✅ Got fresh admin token: {FRESH_TOKEN[:50]}...")
                return FRESH_TOKEN
        
        print(f"❌ Admin login failed: {response.status_code} - {response.text}")
        return ADMIN_TOKEN  # Fallback to original token
    except Exception as e:
        print(f"❌ Admin login error: {e}")
        return ADMIN_TOKEN  # Fallback to original token

def get_headers():
    """Get headers with fresh admin token"""
    token = get_fresh_token()
    return {
        "accept": "application/json",
        "Content-Type": "application/json", 
        "Authorization": f"Bearer {token}"
    }

COMMON_HEADERS = {
    "accept": "application/json",
    "Content-Type": "application/json",
    "Authorization": f"Bearer {ADMIN_TOKEN}"
}
print("COMMON_HEADERS:", COMMON_HEADERS)
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

# === High Density Periodic Load Shape ===
class HighDensityPeriodicShape(LoadTestShape):
    step_time = 60      # every 60s
    step_load = 5       # add 5 users each step
    spawn_rate = 10
    time_limit = 3600   # 1 hour test

    def tick(self):
        run_time = self.get_run_time()
        if run_time > self.time_limit:
            return None

        current_step = math.floor(run_time / self.step_time) + 1
        user_count = current_step * self.step_load

        # Burst every 10 seconds with high spawn rate, otherwise maintain users with slower rate
        second = run_time % 60
        if second in [0, 10, 20, 30, 40, 50]:
            return (user_count, self.spawn_rate)  # High spawn rate during bursts
        else:
            return (user_count, 1)  # Minimum spawn rate to avoid division by zero

# === Barrier Sync Globals ===
users_waiting = 0
event = gevent.event.Event()
lock = Semaphore()

# === Sequential POST Flow User ===
class SequentialPostUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        self.base_uid = random.randint(100000, 999999)
        print(f"[INIT] User instance started with base UID: {self.base_uid}")

    @task
    def sequential_posts(self):
        # High density approach: minimal delay for aggressive testing
        gevent.sleep(random.uniform(0.1, 0.5))  # Very short 0.1-0.5 second delay for maximum density
        
        # === Original Step Function Flow ===
        unique_id = random.randint(1000000, 9999999)
        timestamp = int(time.time() * 1000000)
        vendor_email = f"vendor{unique_id}@test.com"
        vendor_contact = str(random.randint(6000000000, 9999999999))
        username = f"Vendor_{timestamp}_{unique_id}_{random.randint(1000,9999)}"
        vertical = random.choice(IOT_VERTICALS)

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
        fresh_headers = get_headers()  # Get fresh admin token
        with self.client.post(
            f"{BASE_URL}/onboard/approve-vendor?email={vendor_email}",
            headers=fresh_headers,
            json={},
            catch_response=True
        ) as resp:
            if resp.status_code == 200:
                print(f"[POST ✅] approve-vendor for {vendor_email}")
            else:
                print(f"[POST ❌] approve-vendor ({resp.status_code})")
                if resp.status_code == 403:
                    print(f"[DEBUG] Token issue: {resp.text[:100]}")
                else:
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

        fresh_headers = get_headers()
        with self.client.post(
            f"{BASE_URL}/verticals/create-ae",
            headers=fresh_headers,
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
        fresh_headers = get_headers()
        with self.client.post(
            f"{BASE_URL}/verticals/assign-vendor",
            headers=fresh_headers,
            json={"vertical_id": 1, "vendor_email": vendor_email},
            catch_response=True
        ) as resp:
            if resp.status_code in [200, 201]:
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

        fresh_headers = get_headers()
        with self.client.post(
            f"{BASE_URL}/sensor-types/create",
            headers=fresh_headers,
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
        fresh_headers = get_headers()
        with self.client.post(
            f"{BASE_URL}/sensor-types/assign-vendor",
            headers=fresh_headers,
            json={"sensortype_id": 1, "vendor_email": vendor_email},
            catch_response=True
        ) as resp:
            if resp.status_code in [200, 201]:
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

        fresh_headers = get_headers()
        with self.client.post(
            f"{BASE_URL}/import/import",
            headers=fresh_headers,
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
        fresh_headers = get_headers()
        with self.client.post(
            f"{BASE_URL}/nodes/assign-vendor",
            headers=fresh_headers,
            json={"node_id": "4", "vendor_email": vendor_email},
            catch_response=True
        ) as resp:
            if resp.status_code == 200:
                print(f"[POST ✅] assign-vendor to node for {vendor_email}")
            else:
                print(f"[POST ❌] assign-vendor node ({resp.status_code})")
                print("[DEBUG] Response:", resp.text)

        # 9️⃣ Create CIN for Node 2 (token_id = 2)
        fresh_headers = get_headers()
        cin_data_node2 = {
            "bin_data": "example",
            "people_count": random.randint(30, 50)  # Random people count between 30-50
        }
        cin_headers_node2 = {
            "Content-Type": "application/json", 
            "Authorization": "Bearer 4900eb646e89540e703d7f3a18710238"
        }
        with self.client.post(
            f"{BASE_URL}/nodes/create-cin/2",
            headers=cin_headers_node2,
            json=cin_data_node2,
            catch_response=True
        ) as resp:
            if resp.status_code in [200, 201]:
                print(f"[POST ✅] create-cin for node 2 (people_count: {cin_data_node2['people_count']}, bin_data: {cin_data_node2['bin_data']})")
            else:
                print(f"[POST ❌] create-cin node 2 ({resp.status_code})")
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
            "node_id": "WM01-0064-0003"
        }
        
        fresh_headers = get_headers()
        with self.client.post(
            f"{BASE_URL}/subscription/subscribe",
            headers=fresh_headers,
            json=subscribe_data,
            catch_response=True
        ) as resp:
            if resp.status_code == 200:
                print(f"[POST ✅] subscription created (URL: {notify_url})")
            else:
                print(f"[POST ❌] subscription ({resp.status_code})")
                print("[DEBUG] Response:", resp.text)
                # Continue instead of returning

        # === Keep all your API flow as is ===
        # user-request → approve-vendor → create-ae → assign-vendor → create sensor-type → assign vendor → import node → assign vendor → create cin → login → forgot/reset → subscribe
        # (code unchanged, just inserted inside barrier logic)

        print(f"[POST ✅] Sequential workflow completed for {vendor_email}")
                
# === GET Endpoints ===
GET_ENDPOINTS = [
    # User
    ("/user/profile", COMMON_HEADERS),
    ("/user/getusers", COMMON_HEADERS),
    print("PUBLIC_HEADERS:", PUBLIC_HEADERS, COMMON_HEADERS),

    # Verticals
    ("/verticals/verticals-all", COMMON_HEADERS),
    ("/verticals/vocabulary", PUBLIC_HEADERS),

    # Sensor Types
    ("/sensor-types/sensor-types-all", COMMON_HEADERS),
    ("/sensor-types/get/1", COMMON_HEADERS),

    # Nodes
    ("/nodes/get-vendor/WM01-0064-0002", COMMON_HEADERS),
    ("/nodes/nodes-all", COMMON_HEADERS),
    ("/nodes/waste_management", COMMON_HEADERS),
    ("/nodes/get-node-data/WM01-0064-0002", COMMON_HEADERS),
    ("/nodes/get-node/WM01-0064-0002/descriptor/all", COMMON_HEADERS),
    ("/nodes/meta/id/WM01-0064-0002", COMMON_HEADERS),
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

# === GET User Class (updated with fresh token and timeout handling) ===
class GetUser(HttpUser):
    wait_time = between(1, 5)  # Back to original aggressive timing
    connection_timeout = 15.0  # Keep timeout handling
    network_timeout = 15.0     # Keep timeout handling
    
    @task
    def get_requests(self):
        """Execute random GET requests with fresh admin token and timeout handling"""
        endpoint, original_headers = random.choice(GET_ENDPOINTS)
        
        # Use fresh headers if it was COMMON_HEADERS
        if original_headers == COMMON_HEADERS:
            headers = get_headers()
        else:
            headers = original_headers
            
        url = f"{BASE_URL}{endpoint}"
        
        try:
            with self.client.get(url, headers=headers, catch_response=True, timeout=15) as resp:
                if resp.status_code == 200:
                    print(f"[GET ✅] {endpoint}")
                elif resp.status_code == 403:
                    print(f"[GET ❌] {endpoint} (403) - Access denied")
                    print(f"[DEBUG] Token issue: {resp.text[:100]}")
                elif resp.status_code in [500, 503]:
                    print(f"[GET ❌] {endpoint} ({resp.status_code}) - Server error")
                    print(f"[DEBUG] Server issue: {resp.text[:100]}")
                else:
                    print(f"[GET ❌] {endpoint} ({resp.status_code})")
                    print(f"[DEBUG] Response: {resp.text[:200]}")
        except Exception as e:
            print(f"[GET ❌] {endpoint} - Network error: {str(e)[:100]}")
                
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
        ("/user/update-user/3", COMMON_HEADERS, {
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


# === PUT User Class (updated with fresh token and timeout handling) ===
class PutUser(HttpUser):
    wait_time = between(1, 5)  # Back to original aggressive timing
    connection_timeout = 15.0  # Keep timeout handling
    network_timeout = 15.0     # Keep timeout handling
    
    @task
    def put_requests(self):
        """Execute random PUT requests with fresh admin token and timeout handling"""
        put_apis = generate_put_endpoints()
        for endpoint, original_headers, payload in put_apis:
            # Use fresh headers if it was COMMON_HEADERS
            if original_headers == COMMON_HEADERS:
                headers = get_headers()
            else:
                headers = original_headers
                
            url = f"{BASE_URL}{endpoint}"
            try:
                with self.client.put(url, headers=headers, json=payload, catch_response=True, timeout=15) as resp:
                    if resp.status_code == 200:
                        print(f"[PUT ✅] {endpoint}")
                    elif resp.status_code == 403:
                        print(f"[PUT ❌] {endpoint} (403) - Access denied")
                        print(f"[DEBUG] Token issue: {resp.text[:100]}")
                    elif resp.status_code in [500, 503]:
                        print(f"[PUT ❌] {endpoint} ({resp.status_code}) - Server error")
                        print(f"[DEBUG] Server issue: {resp.text[:100]}")
                    else:
                        print(f"[PUT ❌] {endpoint} ({resp.status_code})")
                        print(f"[DEBUG] Response: {resp.text[:200]}")
            except Exception as e:
                print(f"[PUT ❌] {endpoint} - Network error: {str(e)[:100]}")

# === Direct Execution ===
if __name__ == "__main__":
    import subprocess, sys, os
    
    print("🚀 Starting High Density Periodic IoT Backend Load Test...")
    
    # Test the fresh admin token
    print("🔑 Testing fresh admin token...")
    fresh_token = get_fresh_token()
    if fresh_token and fresh_token != ADMIN_TOKEN:
        print("✅ Admin token refresh successful!")
    else:
        print("❌ Token refresh failed, using original token")
    
    print("📡 Testing server connectivity...")
    try:
        import requests
        test_response = requests.get(f"{BASE_URL}/stats/stats", timeout=10)
        print(f"✅ Server responding: {test_response.status_code}")
    except Exception as e:
        print(f"⚠️ Server connectivity issue: {e}")
        print("⚠️ Proceeding with caution - expect timeouts")
    
    print("-" * 50)
    
    script_path = os.path.abspath(__file__)
    cmd = [
        "locust", "-f", script_path,
        "--host", BASE_URL,
        "--web-host", "0.0.0.0", "--web-port", "8090"  # Use port 8090
    ]
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running Locust: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n⏹️  Test stopped by user")
        sys.exit(0)
    script_path = os.path.abspath(__file__)
    cmd = [
        "locust", "-f", script_path,
        "--host", BASE_URL,
        "--web-host", "0.0.0.0", "--web-port", "8089"
    ]
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running Locust: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n⏹️  Test stopped by user")
        sys.exit(0)
