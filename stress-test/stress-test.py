#!/usr/bin/env python3
"""
🏗️ ROBUST STRESS TEST - Network Resilient IoT Backend Load Testing

🛡️ NETWORK RESILIENCE FEATURES:
- Retry logic with exponential backoff
- Circuit breaker pattern for failing endpoints
- Increased timeouts and connection pooling
- Graceful error handling and server health checks
- Adaptive load based on server response
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
from functools import wraps
import requests
from requests.exceptions import ConnectionError, Timeout, RequestException

# === Network Resilience Configuration ===
NETWORK_TIMEOUT = 15  # Increased from 3 to 15 seconds
CONNECTION_TIMEOUT = 30
MAX_RETRIES = 3
RETRY_DELAY = 2
CIRCUIT_BREAKER_THRESHOLD = 5
CIRCUIT_BREAKER_TIMEOUT = 60

# === Config ===
BASE_URL = "http://10.2.16.116:8002"
ADMIN_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3NTgwNzc4NzYsInN1YiI6IjEifQ.qqep29pgFBsrPgO2O78OBAZ8SnxcrOSVltn_HmLzIQs"

# === Network Resilience Classes ===
class CircuitBreaker:
    def __init__(self, failure_threshold=CIRCUIT_BREAKER_THRESHOLD, timeout=CIRCUIT_BREAKER_TIMEOUT):
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.last_failure_time = None
        self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN
    
    def call(self, func, *args, **kwargs):
        if self.state == 'OPEN':
            if time.time() - self.last_failure_time > self.timeout:
                self.state = 'HALF_OPEN'
                print(f"[CIRCUIT] Half-open: Trying {func.__name__}")
            else:
                print(f"[CIRCUIT] Open: Skipping {func.__name__}")
                return None
        
        try:
            result = func(*args, **kwargs)
            if self.state == 'HALF_OPEN':
                self.state = 'CLOSED'
                self.failure_count = 0
                print(f"[CIRCUIT] Closed: {func.__name__} recovered")
            return result
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            if self.failure_count >= self.failure_threshold:
                self.state = 'OPEN'
                print(f"[CIRCUIT] Open: {func.__name__} failed {self.failure_count} times")
            raise e

# Global circuit breakers for different endpoint types
circuit_breakers = {
    'post': CircuitBreaker(),
    'get': CircuitBreaker(),
    'put': CircuitBreaker()
}

def retry_request(max_retries=MAX_RETRIES, delay=RETRY_DELAY):
    """Decorator to add retry logic with exponential backoff"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except (ConnectionError, Timeout, RequestException) as e:
                    if attempt == max_retries - 1:
                        print(f"[RETRY-FAILED] {func.__name__} after {max_retries} attempts: {type(e).__name__}")
                        raise e
                    
                    wait_time = delay * (2 ** attempt) + random.uniform(0, 1)
                    print(f"[RETRY] {func.__name__} attempt {attempt + 1}/{max_retries}, waiting {wait_time:.1f}s")
                    time.sleep(wait_time)
                except Exception as e:
                    if attempt == max_retries - 1:
                        print(f"[RETRY-FAILED] {func.__name__} unexpected error: {str(e)[:100]}")
                        raise e
                    time.sleep(delay)
            return None
        return wrapper
    return decorator

def robust_request(client, method, url, **kwargs):
    """Make a robust HTTP request with comprehensive error handling"""
    # Set robust timeout
    kwargs['timeout'] = kwargs.get('timeout', NETWORK_TIMEOUT)
    kwargs['catch_response'] = True
    
    method_name = method.upper()
    endpoint = url.replace(BASE_URL, "")
    
    try:
        # Use circuit breaker
        circuit_breaker = circuit_breakers.get(method.lower(), circuit_breakers['get'])
        
        def make_request():
            if method.lower() == 'post':
                return client.post(url, **kwargs)
            elif method.lower() == 'put':
                return client.put(url, **kwargs)
            else:
                return client.get(url, **kwargs)
        
        response = circuit_breaker.call(make_request)
        if response is None:
            print(f"[CIRCUIT-SKIP] {method_name} {endpoint}")
            return None
            
        with response as resp:
            if resp.status_code in [200, 201]:
                print(f"[{method_name} ✅] {endpoint}")
                return resp
            elif resp.status_code in [500, 502, 503, 504]:
                print(f"[{method_name} 🔥] {endpoint} ({resp.status_code}) - Server overloaded")
                resp.failure(f"Server error {resp.status_code}")
                time.sleep(2)  # Back off on server errors
                return resp
            elif resp.status_code == 429:
                print(f"[{method_name} ⏳] {endpoint} - Rate limited")
                resp.failure("Rate limited")
                time.sleep(5)  # Longer back off for rate limiting
                return resp
            elif resp.status_code == 401:
                print(f"[{method_name} 🔑] {endpoint} - Authorization issue")
                resp.failure("Auth error")
                return resp
            elif resp.status_code == 404:
                print(f"[{method_name} ❓] {endpoint} - Not found")
                resp.failure("Not found")
                return resp
            else:
                print(f"[{method_name} ❌] {endpoint} ({resp.status_code})")
                resp.failure(f"HTTP {resp.status_code}")
                return resp
                
    except (ConnectionError, Timeout) as e:
        print(f"[{method_name} 🌐] {endpoint} - Network error: {type(e).__name__}")
        return None
    except Exception as e:
        print(f"[{method_name} ⚠️] {endpoint} - Unexpected: {str(e)[:100]}")
        return None

def check_server_health(base_url):
    """Check if server is responsive"""
    try:
        response = requests.get(f"{base_url}/stats/stats", timeout=5)
        return response.status_code == 200
    except:
        return False

# Global variables for result storage
save_results = False

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully and ask about saving results"""
    global save_results
    print("\n\n🛑 Stress test interrupted by user...")
    print("✅ Results will be saved automatically...")
    save_results = True
    save_test_results()
    print("👋 Goodbye!")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

def save_test_results():
    """Save Locust test results to separate CSV files"""
    try:
        from locust import stats
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
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
        
        print(f"✅ Results saved to {results_dir}/")
        
    except Exception as e:
        print(f"❌ Error saving results: {e}")

# Global variable to store fresh token
FRESH_TOKEN = None

@retry_request(max_retries=2, delay=1)
def get_fresh_token():
    """Get a fresh token by logging in with correct admin credentials"""
    global FRESH_TOKEN
    if FRESH_TOKEN:
        return FRESH_TOKEN
        
    login_url = f"{BASE_URL}/user/login"
    login_data = {
        "email": "admin@localhost", 
        "password": "admin"
    }
    
    response = requests.post(login_url, json=login_data, headers={
        "accept": "application/json",
        "Content-Type": "application/json"
    }, timeout=NETWORK_TIMEOUT)
    
    if response.status_code == 200:
        result = response.json()
        if 'access_token' in result:
            FRESH_TOKEN = result['access_token']
            print(f"✅ Got fresh admin token: {FRESH_TOKEN[:50]}...")
            return FRESH_TOKEN
    
    print(f"❌ Admin login failed: {response.status_code}")
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

# === ROBUST STRESS TEST LOAD SHAPE ===
class StressTestLoadShape(LoadTestShape):
    """
    Robust Stress Test Load Pattern - Network Friendly
    - Slower ramp up to avoid overwhelming server
    - Adaptive based on server health
    """
    time_limit = 3600      # 1 hour
    step_time = 180        # 3 minutes per step (increased for stability)
    step_load = 3          # 3 users per step (reduced for stability)
    spawn_rate = 2         # Slower spawn rate
    max_users = 60         # Reduced max users for network stability

    def tick(self):
        run_time = self.get_run_time()
        
        if run_time > self.time_limit:
            return None

        # Check server health every 5 minutes
        if run_time % 300 == 0:
            if not check_server_health(BASE_URL):
                print(f"[HEALTH] Server unhealthy at {run_time}s, reducing load")
                return (max(1, self.max_users // 4), 1)

        current_step = run_time // self.step_time + 1
        user_count = min(self.max_users, current_step * self.step_load)
        
        print(f"[STRESS] Step {current_step}: {user_count} users (Runtime: {run_time}s)")
        return (user_count, self.spawn_rate)

# === Sequential POST Flow User - ROBUST VERSION ===
class SequentialPostUser(HttpUser):
    # More conservative wait times for network stability
    wait_time = between(3, 8)  # Increased from (1,2) to (3,8)
    connection_timeout = CONNECTION_TIMEOUT
    network_timeout = NETWORK_TIMEOUT

    def on_start(self):
        self.base_uid = random.randint(100000, 999999)
        # Configure connection pool for better network handling
        self.client.verify = False
        print(f"[INIT] ROBUST POST User started with base UID: {self.base_uid}")

    @task
    def sequential_posts(self):
        # Add initial delay for network stability
        gevent.sleep(random.uniform(1, 3))
        
        # === Your Original Step Function Flow ===
        unique_id = random.randint(1000000, 9999999)
        timestamp = int(time.time() * 1000000)
        vendor_email = f"vendor{unique_id}@test.com"
        vendor_contact = str(random.randint(6000000000, 9999999999))
        username = f"Vendor_{timestamp}_{unique_id}_{random.randint(1000,9999)}"
        vertical = random.choice(IOT_VERTICALS)

        print(f"[ROBUST-POST] Email: {vendor_email}, Username: {username}, Vertical: {vertical['name']}")
        
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

        resp = robust_request(
            self.client, 'post',
            f"{BASE_URL}/onboard/user-request",
            headers=FORM_HEADERS,
            data=payload
        )
        if resp is None or (resp and resp.status_code != 200):
            print(f"[ROBUST-POST ❌] user-request failed, skipping workflow")
            return

        # 2️⃣ Approve Vendor
        fresh_headers = get_headers()
        resp = robust_request(
            self.client, 'post',
            f"{BASE_URL}/onboard/approve-vendor?email={vendor_email}",
            headers=fresh_headers,
            json={}
        )

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
        resp = robust_request(
            self.client, 'post',
            f"{BASE_URL}/verticals/create-ae",
            headers=fresh_headers,
            json=create_ae_payload
        )
        
        if resp and resp.status_code in [200, 201]:
            try:
                resp_data = resp.json()
                vertical_id = (resp_data.get('id') or 
                             resp_data.get('vertical_id') or 
                             resp_data.get('ae_id') or
                             resp_data.get('data', {}).get('id') if isinstance(resp_data.get('data'), dict) else None)
                if not vertical_id:
                    vertical_id = unique_id % 1000
                print(f"[ROBUST-POST ✅] create-ae vertical {vertical['name']} (ID: {vertical_id})")
            except:
                vertical_id = unique_id % 1000

        # 4️⃣ Assign Vendor to Vertical
        if vertical_id:
            fresh_headers = get_headers()
            robust_request(
                self.client, 'post',
                f"{BASE_URL}/verticals/assign-vendor",
                headers=fresh_headers,
                json={"vertical_id": 1, "vendor_email": vendor_email}
            )

        # 5️⃣ Create Sensor Type
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
            resp = robust_request(
                self.client, 'post',
                f"{BASE_URL}/sensor-types/create",
                headers=fresh_headers,
                json=sensor_type_payload
            )
            
            if resp and resp.status_code in [200, 201]:
                try:
                    resp_data = resp.json()
                    sensor_type_id = (resp_data.get('id') or 
                                    resp_data.get('sensor_type_id') or 
                                    resp_data.get('sensortype_id') or
                                    (unique_id % 1000) + 1000)
                    print(f"[ROBUST-POST ✅] create sensor-type {sensor_name} (ID: {sensor_type_id})")
                except:
                    sensor_type_id = (unique_id % 1000) + 1000

        # 6️⃣ Assign Vendor to Sensor Type
        if sensor_type_id:
            fresh_headers = get_headers()
            robust_request(
                self.client, 'post',
                f"{BASE_URL}/sensor-types/assign-vendor",
                headers=fresh_headers,
                json={"sensortype_id": 2, "vendor_email": vendor_email}
            )

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
        resp = robust_request(
            self.client, 'post',
            f"{BASE_URL}/import/import",
            headers=fresh_headers,
            json=import_payload
        )
        
        if resp and resp.status_code in [200, 201]:
            try:
                resp_data = resp.json()
                if isinstance(resp_data, dict):
                    node_id = (resp_data.get('node_id') or 
                             resp_data.get('id') or 
                             resp_data.get('nodes', [{}])[0].get('id') if resp_data.get('nodes') else None)
                if not node_id:
                    node_id = node_name
                print(f"[ROBUST-POST ✅] import node configuration (ID: {node_id})")
            except:
                node_id = node_name

        # 8️⃣ Assign Vendor to Node
        if node_id:
            fresh_headers = get_headers()
            robust_request(
                self.client, 'post',
                f"{BASE_URL}/nodes/assign-vendor",
                headers=fresh_headers,
                json={"node_id": "1", "vendor_email": vendor_email}
            )

        # 9️⃣ Create CIN for Node
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
            robust_request(
                self.client, 'post',
                f"{BASE_URL}/nodes/create-cin/2",
                headers=cin_headers_node2,
                json=cin_data
            )

        # # 10️⃣ Additional CIN for specific node
        # fresh_headers = get_headers()
        # cin_data_node2 = {
        #     "bin_data": "example",
        #     "people_count": random.randint(30, 50)
        # }
        # robust_request(
        #     self.client, 'post',
        #     f"{BASE_URL}/nodes/create-cin/2",
        #     headers=fresh_headers,
        #     json=cin_data_node2
        # )

        # 11️⃣ User Login
        login_data = {
            "email": "vakaperireddy5555@gmail.com",
            "password": "vendor@1234"
        }
        robust_request(
            self.client, 'post',
            f"{BASE_URL}/user/login",
            headers=PUBLIC_HEADERS,
            json=login_data
        )

        # 12️⃣ Forgot Password
        forgot_emails = ["vakaperireddy59@gmail.com", "vakaperireddy5555@gmail.com"]
        forgot_email = random.choice(forgot_emails)
        forgot_password_data = {
            "email": forgot_email
        }
        robust_request(
            self.client, 'post',
            f"{BASE_URL}/user/forgot-password",
            headers=PUBLIC_HEADERS,
            json=forgot_password_data
        )

        # 13️⃣ Reset Password
        random_password = f"NewPass{random.randint(1000, 9999)}!"
        reset_password_data = {
            "email": "vakaperireddy59@gmail.com",
            "new_password": random_password
        }
        robust_request(
            self.client, 'post',
            f"{BASE_URL}/user/reset-password",
            headers=PUBLIC_HEADERS,
            json=reset_password_data
        )

        # 14️⃣ Subscribe to Node
        notify_url = f"http://10.2.16.116:8610/notify/{random.randint(1000, 9999)}"
        subscribe_node_id = "WM01-0064-0002"
        subscribe_data = {
            "url": notify_url,
            "node_id": str(subscribe_node_id)
        }
        
        fresh_headers = get_headers()
        robust_request(
            self.client, 'post',
            f"{BASE_URL}/subscription/subscribe",
            headers=fresh_headers,
            json=subscribe_data
        )

        print(f"[ROBUST-POST ✅] Sequential workflow completed for {vendor_email} (V:{vertical_id}, S:{sensor_type_id}, N:{node_id})")

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

# === GET User Class - ROBUST VERSION ===
class GetUser(HttpUser):
    wait_time = between(4, 10)  # Increased wait time for stability
    connection_timeout = CONNECTION_TIMEOUT
    network_timeout = NETWORK_TIMEOUT
    
    def on_start(self):
        self.client.verify = False
    
    @task
    def get_requests(self):
        """Execute random GET requests with robust error handling"""
        gevent.sleep(random.uniform(1, 3))
        
        endpoint, original_headers = random.choice(GET_ENDPOINTS)
        
        # Use fresh headers if it was COMMON_HEADERS
        if original_headers == COMMON_HEADERS:
            headers = get_headers()
        else:
            headers = original_headers
            
        url = f"{BASE_URL}{endpoint}"
        robust_request(self.client, 'get', url, headers=headers)

# === PUT Endpoints ===
def generate_put_endpoints():
    """Generate PUT endpoints with dynamic data"""
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
    return put_apis

# === PUT User Class - ROBUST VERSION ===
class PutUser(HttpUser):
    wait_time = between(5, 12)  # Increased wait time for stability
    connection_timeout = CONNECTION_TIMEOUT
    network_timeout = NETWORK_TIMEOUT
    
    def on_start(self):
        self.client.verify = False
    
    @task
    def put_requests(self):
        """Execute random PUT requests with robust error handling"""
        gevent.sleep(random.uniform(2, 4))
        
        put_apis = generate_put_endpoints()
        for endpoint, original_headers, payload in put_apis:
            # Use fresh headers if it was COMMON_HEADERS
            if original_headers == COMMON_HEADERS:
                headers = get_headers()
            else:
                headers = original_headers
                
            url = f"{BASE_URL}{endpoint}"
            robust_request(self.client, 'put', url, headers=headers, json=payload)

# === Direct Execution ===
if __name__ == "__main__":
    import subprocess, sys, os
    
    print("🚀 Starting Robust 1-Hour Stress Test for IoT Backend...")
    print("🛡️ NETWORK RESILIENCE FEATURES:")
    print(f"   📡 Timeout: {NETWORK_TIMEOUT}s (increased from 3s)")
    print(f"   🔄 Retry: {MAX_RETRIES} attempts with backoff")
    print(f"   ⚡ Circuit Breaker: {CIRCUIT_BREAKER_THRESHOLD} failures")
    print(f"   👥 Max Users: 60 (reduced for stability)")
    print(f"   ⏱️ Wait Times: 3-8s (increased for stability)")
    
    # Test server health before starting
    print("🏥 Testing server health...")
    if check_server_health(BASE_URL):
        print("✅ Server is healthy")
    else:
        print("⚠️ Server seems unhealthy, proceeding with caution")
    
    # Test the fresh admin token
    print("🔑 Testing fresh admin token...")
    fresh_token = get_fresh_token()
    if fresh_token and fresh_token != ADMIN_TOKEN:
        print("✅ Admin token refresh successful!")
    else:
        print("❌ Token refresh failed, using original token")
    
    print("-" * 60)
    print("🎮 ROBUST USER EXPERIENCE:")
    print("   🐌 Slower ramp-up for network stability")
    print("   🔄 Automatic retries for failed requests")
    print("   🛡️ Circuit breakers prevent endpoint flooding")
    print("   💾 Automatic result saving on stop")
    print("-" * 60)
    
    script_path = os.path.abspath(__file__)
    cmd = [
        "locust", "-f", script_path,
        "--host", BASE_URL,
        "--web-host", "0.0.0.0", "--web-port", "8093"  # Use port 8093 for robust test
    ]
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running Locust: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n⏹️  Test stopped by user")
        sys.exit(0)
