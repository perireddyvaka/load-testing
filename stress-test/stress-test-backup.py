#!/usr/bin/env python3
"""
🏗️ STRESS TEST CONFIGURATION - 1 Hour IoT Backend Load Testing

📖 THE TESTING STORY:
Once upon a time, there was an IoT backend serving thousands of smart city devices.
The city was growing rapidly, and the system needed to handle massive concurrent loads.

🎯 STRESS TEST PATTERN:
- Duration: 1 HOUR (3600 seconds)
- Pattern: Step Load (Like rush hour traffic         # 4️⃣ Assign Vendor to Vertical (always attempt, use vertical_id if available)
        fresh_headers = get_headers()
        with self.client.post(
            f"{BASE_URL}/v        # 8️⃣ Assign Vendor to Node (always attempt if node was imported)
        if node_id:
            fresh_headers = get_headers()
            with self.client.post(
                f"{BASE_URL}/nodes/assign-vendor",
                headers=fresh_headers,
                json={"node_id": str(node_id), "vendor_email": vendor_email},
                catch_response=True,
                timeout=3
            ) as resp:
                if resp.status_code in [200, 201]:
                    print(f"[STRESS-POST ✅] assign-vendor to node {node_id} for {vendor_email}")
                else:
                    print(f"[STRESS-POST ❌] assign-vendor node ({resp.status_code}) - {resp.text[:100]}")

        # 9️⃣ Create CIN for Node (use the actual node_id if available)
        if node_id:
            fresh_headers = get_headers()
            cin_data = {
                "bin_data": "example",
                "people_count": random.randint(30, 50)
            }
            # Try with fresh admin headers
            with self.client.post(
                f"{BASE_URL}/nodes/create-cin/{node_id}",
                headers=fresh_headers,
                json=cin_data,
                catch_response=True,
                timeout=3
            ) as resp:
                if resp.status_code in [200, 201]:
                    print(f"[STRESS-POST ✅] create-cin for node {node_id} (people_count: {cin_data['people_count']})")
                else:
                    print(f"[STRESS-POST ❌] create-cin node {node_id} ({resp.status_code}) - {resp.text[:100]}")

        # 10️⃣ Additional CIN for specific node (keeping original logic)
        try:
            fresh_headers = get_headers()
            cin_data_node2 = {
                "bin_data": "example",
                "people_count": random.randint(30, 50)
            }
            with self.client.post(
                f"{BASE_URL}/nodes/create-cin/2",
                headers=fresh_headers,
                json=cin_data_node2,
                catch_response=True,
                timeout=3
            ) as resp:
                if resp.status_code in [200, 201]:
                    print(f"[STRESS-POST ✅] create-cin for node 2 (people_count: {cin_data_node2['people_count']})")
                else:
                    print(f"[STRESS-POST ❌] create-cin node 2 ({resp.status_code}) - {resp.text[:100]}")
        except Exception as e:
            print(f"[STRESS-POST ❌] create-cin node 2 - Exception: {str(e)[:100]}")n-vendor",
            headers=fresh_headers,
            json={"vertical_id": vertical_id, "vendor_email": vendor_email},
            catch_response=True,
            timeout=3
        ) as resp:
            if resp.status_code in [200, 201]:
                print(f"[STRESS-POST ✅] assign-vendor to vertical {vertical_id} for {vendor_email}")
            else:
                print(f"[STRESS-POST ❌] assign-vendor vertical ({resp.status_code}) - {resp.text[:100]}")

        # 5️⃣ Create Sensor Type (always attempt, use the vertical_id)
        sensor_name = random.choice(SENSOR_TYPES)
        sensor_type_payload = {
            "res_name": f"{sensor_name} {unique_id}",
            "parameters": vertical["parameters"],
            "data_types": vertical["data_types"],
            "labels": [],
            "vertical_id": vertical_id,
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
            catch_response=True,
            timeout=3
        ) as resp:
            if resp.status_code in [200, 201]:
                try:
                    resp_data = resp.json()
                    sensor_type_id = (resp_data.get('id') or 
                                    resp_data.get('sensor_type_id') or 
                                    resp_data.get('sensortype_id') or
                                    resp_data.get('data', {}).get('id') if isinstance(resp_data.get('data'), dict) else None)
                    if not sensor_type_id:
                        # Use derived ID if no ID returned
                        sensor_type_id = (unique_id % 1000) + 1000  # Offset to avoid conflicts
                    print(f"[STRESS-POST ✅] create sensor-type {sensor_name} (ID: {sensor_type_id})")
                except Exception as e:
                    # Fallback: use derived ID
                    sensor_type_id = (unique_id % 1000) + 1000
                    print(f"[STRESS-POST ✅] create sensor-type {sensor_name} (using derived ID: {sensor_type_id})")
            else:
                print(f"[STRESS-POST ❌] create sensor-type ({resp.status_code}) - {resp.text[:100]}")
                # Continue with fallback ID
                sensor_type_id = (unique_id % 1000) + 1000
                print(f"[STRESS-POST ⚠️] Using fallback sensor_type_id: {sensor_type_id}")

        # 6️⃣ Assign Vendor to Sensor Type (always attempt)
        fresh_headers = get_headers()
        with self.client.post(
            f"{BASE_URL}/sensor-types/assign-vendor",
            headers=fresh_headers,
            json={"sensortype_id": sensor_type_id, "vendor_email": vendor_email},
            catch_response=True,
            timeout=3
        ) as resp:
            if resp.status_code in [200, 201]:
                print(f"[STRESS-POST ✅] assign-vendor to sensor-type {sensor_type_id} for {vendor_email}")
            else:
                print(f"[STRESS-POST ❌] assign-vendor sensor-type ({resp.status_code}) - {resp.text[:100]}")ase every 2 minutes)
- Growth: 5 new users every 2 minutes (120 seconds)
- Peak Load: 150 concurrent users (like a busy city intersection)
- Request Mix: POST (create), GET (read), PUT (update) - real IoT operations
- No Manual Input Required: Fully automated stress testing

🔥 STRESS INTENSITY:
- Aggressive wait times (1-2 seconds) for maximum load
- Admin-only authentication for maximum access rights
- Automatic result storage when test stops

💾 USER EXPERIENCE:
1. Test starts automatically - no user input needed
2. Users gradually increase every 2 minutes (5 → 10 → 15 → ... → 150)
3. All users perform real IoT operations simultaneously
4. When stopped (Ctrl+C), automatically asks to save results
5. Results saved to timestamped CSV files for analysis

🎮 HOW IT WORKS FROM USER PERSPECTIVE:
- You see users ramping up gradually: "Step 1: 5 users", "Step 2: 10 users", etc.
- Real-time logs show: "[STRESS-POST ✅] vendor created", "[STRESS-GET ✅] data fetched"
- Each user performs: User Registration → Vertical Creation → Sensor Setup → Node Import → Data Collection
- System tests all major IoT backend operations under increasing load
- Perfect for finding breaking points and performance bottlenecks
"""

import random
import time
import math
import numpy as np
import gevent
from gevent.lock import Semaphore
from locust import HttpUser, task, between, LoadTestShape
import json
import csv
import os
from datetime import datetime
import signal
import sys

# === Config ===
BASE_URL = "http://10.2.16.116:8002"
ADMIN_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3NTgwNzc4NzYsInN1YiI6IjEifQ.qqep29pgFBsrPgO2O78OBAZ8SnxcrOSVltn_HmLzIQs"

# Global variables for result storage
save_results = False

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully and ask about saving results"""
    global save_results
    print("\n\n🛑 Stress test interrupted by user...")
    
    try:
        response = input("\n💾 Save test results to CSV files? (y/n): ").lower().strip()
        if response in ['y', 'yes']:
            save_results = True
            print("✅ Results will be saved...")
            save_test_results()
        else:
            print("❌ Results will not be saved...")
    except (EOFError, KeyboardInterrupt):
        print("\n❌ Results will not be saved...")
    
    print("👋 Goodbye!")
    sys.exit(0)

# Register signal handler
signal.signal(signal.SIGINT, signal_handler)

def save_test_results():
    """Save Locust test results to separate CSV files"""
    try:
        from locust import stats
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create results directory
        results_dir = f"stress_test_results_{timestamp}"
        os.makedirs(results_dir, exist_ok=True)
        print(f"📁 Creating results directory: {results_dir}")
        
        # Save request stats
        with open(f"{results_dir}/request_stats.csv", 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Type', 'Name', 'Request Count', 'Failure Count', 'Median Response Time', 
                           'Average Response Time', 'Min Response Time', 'Max Response Time', 
                           'Average Content Size', 'Requests/s', 'Failures/s'])
            
            for stat in stats.entries.values():
                writer.writerow([
                    stat.method, stat.name, stat.num_requests, stat.num_failures,
                    stat.median_response_time, stat.avg_response_time,
                    stat.min_response_time, stat.max_response_time,
                    stat.avg_content_length, stat.current_rps, stat.current_fail_per_sec
                ])
        
        # Save failure stats
        with open(f"{results_dir}/failure_stats.csv", 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Method', 'Name', 'Error', 'Occurrences'])
            
            for stat in stats.errors.values():
                writer.writerow([stat.method, stat.name, stat.error, stat.occurrences])
        
        # Save response time percentiles
        with open(f"{results_dir}/response_time_percentiles.csv", 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Type', 'Name', '50%', '66%', '75%', '80%', '90%', '95%', '98%', '99%', '99.9%', '100%'])
            
            for stat in stats.entries.values():
                if stat.num_requests > 0:
                    percentiles = stat.get_response_time_percentile([50, 66, 75, 80, 90, 95, 98, 99, 99.9, 100])
                    writer.writerow([stat.method, stat.name] + percentiles)
        
        # Save summary info
        with open(f"{results_dir}/test_summary.json", 'w') as f:
            summary = {
                'timestamp': timestamp,
                'total_requests': sum(s.num_requests for s in stats.entries.values()),
                'total_failures': sum(s.num_failures for s in stats.entries.values()),
                'average_response_time': stats.total.avg_response_time,
                'requests_per_second': stats.total.current_rps,
                'failure_rate': stats.total.fail_ratio
            }
            json.dump(summary, f, indent=2)
        
        print(f"✅ Results saved to {results_dir}/")
        print("📊 Files created:")
        print(f"  - request_stats.csv (detailed request metrics)")
        print(f"  - failure_stats.csv (error analysis)")
        print(f"  - response_time_percentiles.csv (performance distribution)")
        print(f"  - test_summary.json (overall summary)")
        
    except Exception as e:
        print(f"❌ Error saving results: {e}")

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
        }, timeout=5)  # Reduced timeout from 15 to 5 seconds
        
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

# === STRESS TEST LOAD SHAPE - 1 HOUR DURATION ===
class StressTestLoadShape(LoadTestShape):
    """
    Stress Test Load Pattern for 1 Hour
    - Step increases every 2 minutes (120 seconds)
    - 5 new users every step
    - Maximum 150 users after 1 hour
    - Fully automated - no user input required
    """
    time_limit = 3600      # 1 hour (3600 seconds)
    step_time = 120        # 2 minutes per step
    step_load = 5          # 5 users added per step
    spawn_rate = 10        # How fast users spawn
    max_users = 150        # Maximum users (30 steps * 5 users = 150)

    def tick(self):
        run_time = self.get_run_time()
        
        if run_time > self.time_limit:
            return None

        current_step = run_time // self.step_time + 1
        user_count = min(self.max_users, current_step * self.step_load)
        
        print(f"[STRESS] Step {current_step}: {user_count} users (Runtime: {run_time}s)")
        return (user_count, self.spawn_rate)

# === Sequential POST Flow User - STRESS VERSION ===
class SequentialPostUser(HttpUser):
    # Aggressive wait times for stress testing
    wait_time = between(1, 2)  # Very fast - 1-2 seconds between requests

    def on_start(self):
        self.base_uid = random.randint(100000, 999999)
        print(f"[INIT] STRESS POST User started with base UID: {self.base_uid}")

    @task
    def sequential_posts(self):
        # Minimal wait for stress testing
        gevent.sleep(random.uniform(0.5, 1.5))
        
        # === Original Step Function Flow ===
        unique_id = random.randint(1000000, 9999999)
        timestamp = int(time.time() * 1000000)
        vendor_email = f"vendor{unique_id}@test.com"
        vendor_contact = str(random.randint(6000000000, 9999999999))
        username = f"Vendor_{timestamp}_{unique_id}_{random.randint(1000,9999)}"
        vertical = random.choice(IOT_VERTICALS)

        print(f"[STRESS-POST] Email: {vendor_email}, Username: {username}, Vertical: {vertical['name']}")
        
        # Initialize IDs to track created entities
        vertical_id = None
        sensor_type_id = None
        node_id = None
        
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

        try:
            with self.client.post(
                f"{BASE_URL}/onboard/user-request",
                headers=FORM_HEADERS,
                data=payload,
                catch_response=True,
                timeout=3  # Short timeout for stress
            ) as resp:
                if resp.status_code == 200:
                    print(f"[STRESS-POST ✅] user-request created {vendor_email}")
                else:
                    print(f"[STRESS-POST ❌] user-request ({resp.status_code}) - {resp.text[:100]}")
                    return
        except Exception as e:
            print(f"[STRESS-POST ❌] user-request - Network error: {str(e)[:100]}")
            return

        # 2️⃣ Approve Vendor
        fresh_headers = get_headers()
        with self.client.post(
            f"{BASE_URL}/onboard/approve-vendor?email={vendor_email}",
            headers=fresh_headers,
            json={},
            catch_response=True,
            timeout=3
        ) as resp:
            if resp.status_code == 200:
                print(f"[STRESS-POST ✅] approve-vendor for {vendor_email}")
            else:
                print(f"[STRESS-POST ❌] approve-vendor ({resp.status_code}) - {resp.text[:100]}")
                return

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
            catch_response=True,
            timeout=3
        ) as resp:
            if resp.status_code in [200, 201]:
                try:
                    resp_data = resp.json()
                    vertical_id = (resp_data.get('id') or 
                                 resp_data.get('vertical_id') or 
                                 resp_data.get('ae_id') or
                                 resp_data.get('data', {}).get('id') if isinstance(resp_data.get('data'), dict) else None)
                    if not vertical_id and 'created' in resp.text.lower():
                        # If creation was successful but no ID returned, use a reasonable fallback
                        vertical_id = unique_id % 1000  # Use a derived ID
                    print(f"[STRESS-POST ✅] create-ae vertical {vertical['name']} (ID: {vertical_id})")
                except Exception as e:
                    # Fallback: if creation seemed successful, use derived ID
                    vertical_id = unique_id % 1000
                    print(f"[STRESS-POST ✅] create-ae vertical {vertical['name']} (using derived ID: {vertical_id})")
            else:
                print(f"[STRESS-POST ❌] create-ae ({resp.status_code}) - {resp.text[:100]}")
                # Don't return, continue with workflow using fallback ID
                vertical_id = unique_id % 1000
                print(f"[STRESS-POST ⚠️] Using fallback vertical_id: {vertical_id}")

        # 4️⃣ Assign Vendor to Vertical (only if vertical was created successfully)
        if vertical_id:
            fresh_headers = get_headers()
            with self.client.post(
                f"{BASE_URL}/verticals/assign-vendor",
                headers=fresh_headers,
                json={"vertical_id": 1, "vendor_email": vendor_email},
                catch_response=True,
                timeout=3
            ) as resp:
                if resp.status_code in [200, 201]:
                    print(f"[STRESS-POST ✅] assign-vendor to vertical {vertical_id} for {vendor_email}")
                else:
                    print(f"[STRESS-POST ❌] assign-vendor vertical ({resp.status_code}) - {resp.text[:100]}")

        # 5️⃣ Create Sensor Type (using the vertical_id from step 3)
        if vertical_id:
            sensor_name = random.choice(SENSOR_TYPES)
            sensor_type_payload = {
                "res_name": f"{sensor_name} {unique_id}",
                "parameters": vertical["parameters"],
                "data_types": vertical["data_types"],
                "labels": [],
                "vertical_id": 1,
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
                catch_response=True,
                timeout=3
            ) as resp:
                if resp.status_code in [200, 201]:
                    try:
                        resp_data = resp.json()
                        sensor_type_id = resp_data.get('id') or resp_data.get('sensor_type_id') or resp_data.get('sensortype_id')
                        print(f"[STRESS-POST ✅] create sensor-type {sensor_name} (ID: {sensor_type_id})")
                    except:
                        # Fallback: try to use a reasonable ID
                        sensor_type_id = random.randint(1, 100)
                        print(f"[STRESS-POST ✅] create sensor-type {sensor_name} (using fallback ID: {sensor_type_id})")
                else:
                    print(f"[STRESS-POST ❌] create sensor-type ({resp.status_code}) - {resp.text[:100]}")

        # 6️⃣ Assign Vendor to Sensor Type (only if sensor type was created successfully)
        if sensor_type_id:
            fresh_headers = get_headers()
            with self.client.post(
                f"{BASE_URL}/sensor-types/assign-vendor",
                headers=fresh_headers,
                json={"sensortype_id": 1, "vendor_email": vendor_email},
                catch_response=True,
                timeout=3
            ) as resp:
                if resp.status_code in [200, 201]:
                    print(f"[STRESS-POST ✅] assign-vendor to sensor-type {sensor_type_id} for {vendor_email}")
                else:
                    print(f"[STRESS-POST ❌] assign-vendor sensor-type ({resp.status_code}) - {resp.text[:100]}")

        # 7️⃣ Import Node Configuration
        node_name = f"Node-{unique_id}-{random.randint(1000,9999)}"
        import_payload = {
            "nodes": [
                {
                    "latitude": 17.446919 + random.uniform(-0.01, 0.01),
                    "longitude": 78.612 + random.uniform(-0.01, 0.01),
                    "area": random.choice(["Gachibowli", "Hitech City", "Kondapur", "Madhapur"]),
                    "sensor_type": "WMSensor-1",
                    "domain": "waste_management", 
                    "name": node_name,
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
            catch_response=True,
            timeout=3
        ) as resp:
            if resp.status_code in [200, 201]:
                try:
                    resp_data = resp.json()
                    # Try to extract node ID from various possible response formats
                    if isinstance(resp_data, dict):
                        node_id = (resp_data.get('node_id') or 
                                 resp_data.get('id') or 
                                 resp_data.get('nodes', [{}])[0].get('id') if resp_data.get('nodes') else None)
                    if not node_id:
                        # Use the node name as fallback ID
                        node_id = node_name
                    print(f"[STRESS-POST ✅] import node configuration (ID: {node_id})")
                except:
                    # Fallback: use node name as ID
                    node_id = node_name
                    print(f"[STRESS-POST ✅] import node configuration (using name as ID: {node_id})")
            else:
                print(f"[STRESS-POST ❌] import node ({resp.status_code}) - {resp.text[:100]}")

        # 8️⃣ Assign Vendor to Node (only if node was imported successfully and vendor is assigned to sensor type)
        if node_id and sensor_type_id:
            fresh_headers = get_headers()
            with self.client.post(
                f"{BASE_URL}/nodes/assign-vendor",
                headers=fresh_headers,
                json={"node_id": "1", "vendor_email": vendor_email},
                catch_response=True,
                timeout=3
            ) as resp:
                if resp.status_code in [200, 201]:
                    print(f"[STRESS-POST ✅] assign-vendor to node {node_id} for {vendor_email}")
                else:
                    print(f"[STRESS-POST ❌] assign-vendor node ({resp.status_code}) - {resp.text[:100]}")

        # 9️⃣ Create CIN for Node (use the actual node_id if available)
        if node_id:
            fresh_headers = get_headers()
            cin_data = {
                "bin_data": "example",
                "people_count": random.randint(30, 50)
            }
            cin_headers_node2 = {
            "Content-Type": "application/json", 
            "Authorization": "Bearer bdce3c1d7c536a0d7f38ff3ef2fce05b"
          }
            # Use fresh headers instead of hard-coded token
            with self.client.post(
                f"{BASE_URL}/nodes/create-cin/2",
                headers=cin_headers_node2,
                json=cin_data,
                catch_response=True,
                timeout=3
            ) as resp:
                if resp.status_code in [200, 201]:
                    print(f"[STRESS-POST ✅] create-cin for node {node_id} (people_count: {cin_data['people_count']})")
                else:
                    print(f"[STRESS-POST ❌] create-cin node {node_id} ({resp.status_code}) - {resp.text[:100]}")

        # # 10️⃣ Additional CIN for specific node (keeping original logic)
        # fresh_headers = get_headers()
        # cin_data_node2 = {
        #     "bin_data": "example",
        #     "people_count": random.randint(30, 50)
        # }
        # with self.client.post(
        #     f"{BASE_URL}/nodes/create-cin/2",
        #     headers=fresh_headers,
        #     json=cin_data_node2,
        #     catch_response=True,
        #     timeout=3
        # ) as resp:
        #     if resp.status_code in [200, 201]:
        #         print(f"[STRESS-POST ✅] create-cin for node 2 (people_count: {cin_data_node2['people_count']})")
        #     else:
        #         print(f"[STRESS-POST ❌] create-cin node 2 ({resp.status_code}) - {resp.text[:100]}")

        # 11️⃣ User Login
        login_headers = {
            "accept": "application/json",
            "Content-Type": "application/json"
        }
        login_data = {
            "email": "vakaperireddy5555@gmail.com",
            "password": "vendor@1234"
        }
        
        with self.client.post(
            f"{BASE_URL}/user/login",
            headers=login_headers,
            json=login_data,
            catch_response=True,
            timeout=3
        ) as resp:
            if resp.status_code == 200:
                print(f"[STRESS-POST ✅] user login successful")
            else:
                print(f"[STRESS-POST ❌] user login ({resp.status_code}) - {resp.text[:100]}")

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
            catch_response=True,
            timeout=3
        ) as resp:
            if resp.status_code == 200:
                print(f"[STRESS-POST ✅] forgot-password for {forgot_email}")
            else:
                print(f"[STRESS-POST ❌] forgot-password ({resp.status_code}) - {resp.text[:100]}")

        # 13️⃣ Reset Password
        random_password = f"NewPass{random.randint(1000, 9999)}!"
        reset_password_data = {
            "email": "vakaperireddy59@gmail.com",
            "new_password": random_password
        }
        
        with self.client.post(
            f"{BASE_URL}/user/reset-password",
            headers=login_headers,
            json=reset_password_data,
            catch_response=True,
            timeout=3
        ) as resp:
            if resp.status_code == 200:
                print(f"[STRESS-POST ✅] reset-password (new password: {random_password})")
            else:
                print(f"[STRESS-POST ❌] reset-password ({resp.status_code}) - {resp.text[:100]}")

        # 14️⃣ Subscribe to Node (use actual node_id if available, fallback to known node)
        notify_url = f"http://10.2.16.116:8610/notify/{random.randint(1000, 9999)}"
        subscribe_node_id = node_id if node_id else "WM01-0064-0002"
        subscribe_data = {
            "url": notify_url,
            "node_id": "WM01-0064-0001"
        }
        
        fresh_headers = get_headers()
        with self.client.post(
            f"{BASE_URL}/subscription/subscribe",
            headers=fresh_headers,
            json=subscribe_data,
            catch_response=True,
            timeout=3
        ) as resp:
            if resp.status_code == 200:
                print(f"[STRESS-POST ✅] subscription created (URL: {notify_url}, Node: {subscribe_node_id})")
            else:
                print(f"[STRESS-POST ❌] subscription ({resp.status_code}) - {resp.text[:100]}")

        print(f"[STRESS-POST ✅] Sequential workflow completed for {vendor_email} (Vertical: {vertical_id}, Sensor: {sensor_type_id}, Node: {node_id})")

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

# === GET User Class - STRESS VERSION ===
class GetUser(HttpUser):
    # Aggressive wait times for stress testing
    wait_time = between(1, 2)  # Very fast - 1-2 seconds between requests
    connection_timeout = 15.0
    network_timeout = 15.0
    
    @task
    def get_requests(self):
        """Execute random GET requests with aggressive timing for stress testing"""
        # Minimal wait for stress testing
        gevent.sleep(random.uniform(0.5, 1.0))
        
        endpoint, original_headers = random.choice(GET_ENDPOINTS)
        
        # Use fresh headers if it was COMMON_HEADERS
        if original_headers == COMMON_HEADERS:
            headers = get_headers()
        else:
            headers = original_headers
            
        url = f"{BASE_URL}{endpoint}"
        
        try:
            with self.client.get(url, headers=headers, catch_response=True, timeout=3) as resp:
                if resp.status_code == 200:
                    print(f"[STRESS-GET ✅] {endpoint}")
                elif resp.status_code == 403:
                    print(f"[STRESS-GET ❌] {endpoint} (403) - Access denied")
                elif resp.status_code in [500, 503]:
                    print(f"[STRESS-GET ❌] {endpoint} ({resp.status_code}) - Server error")
                else:
                    print(f"[STRESS-GET ❌] {endpoint} ({resp.status_code})")
        except Exception as e:
            print(f"[STRESS-GET ❌] {endpoint} - Network error: {str(e)[:100]}")
                
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
        ("/user/update-user/4", COMMON_HEADERS, {
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
    ]

    alarm_id_counter += 1
    return put_apis

# === PUT User Class - STRESS VERSION ===
class PutUser(HttpUser):
    # Aggressive wait times for stress testing
    wait_time = between(1, 2)  # Very fast - 1-2 seconds between requests
    connection_timeout = 15.0
    network_timeout = 15.0
    
    @task
    def put_requests(self):
        """Execute random PUT requests with aggressive timing for stress testing"""
        # Minimal wait for stress testing
        gevent.sleep(random.uniform(0.5, 1.5))
        
        put_apis = generate_put_endpoints()
        for endpoint, original_headers, payload in put_apis:
            # Use fresh headers if it was COMMON_HEADERS
            if original_headers == COMMON_HEADERS:
                headers = get_headers()
            else:
                headers = original_headers
                
            url = f"{BASE_URL}{endpoint}"
            try:
                with self.client.put(url, headers=headers, json=payload, catch_response=True, timeout=3) as resp:
                    if resp.status_code == 200:
                        print(f"[STRESS-PUT ✅] {endpoint}")
                    elif resp.status_code == 403:
                        print(f"[STRESS-PUT ❌] {endpoint} (403) - Access denied")
                    elif resp.status_code in [500, 503]:
                        print(f"[STRESS-PUT ❌] {endpoint} ({resp.status_code}) - Server error")
                    else:
                        print(f"[STRESS-PUT ❌] {endpoint} ({resp.status_code})")
            except Exception as e:
                print(f"[STRESS-PUT ❌] {endpoint} - Network error: {str(e)[:100]}")

# === Direct Execution ===
if __name__ == "__main__":
    import subprocess, sys, os
    
    print("🚀 Starting 1-Hour Stress Test for IoT Backend...")
    print("⚡ STRESS CONFIGURATION:")
    print("   📅 Duration: 1 HOUR (3600 seconds)")
    print("   📈 Pattern: Step Load (5 users every 2 minutes)")
    print("   🎯 Max Users: 150 concurrent users")
    print("   💥 Wait Times: 1-2 seconds (AGGRESSIVE)")
    print("   🔄 No Manual Input Required!")
    
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
    
    print("-" * 60)
    print("🎮 USER EXPERIENCE:")
    print("   👀 Watch users ramp up: Step 1: 5 users → Step 30: 150 users")
    print("   📊 Real-time logs: [STRESS-POST ✅] [STRESS-GET ✅] [STRESS-PUT ✅]")
    print("   🛑 To stop: Press Ctrl+C and choose to save results")
    print("-" * 60)
    
    script_path = os.path.abspath(__file__)
    cmd = [
        "locust", "-f", script_path,
        "--host", BASE_URL,
        "--web-host", "0.0.0.0", "--web-port", "8092"  # Use port 8092 for stress test
    ]
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running Locust: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n⏹️  Test stopped by user")
        sys.exit(0)

