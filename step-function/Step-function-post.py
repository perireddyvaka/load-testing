import random
import gevent
import time
import math
from locust import HttpUser, task, between, LoadTestShape
from gevent.lock import Semaphore

# === Config ===
BASE_URL = "http://10.2.16.116:8610"
AUTH_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3NTc5MzA0NDIsInN1YiI6IjEyIn0.Ca4meTua6KYpMHPFBRR9dLwaycUOC1dFd235tVn1wKA"
CIN_TOKEN = "26d545994f733631df36c50b331213fd"

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
    time_limit = 3600  # 1 hour (changed from 7200 = 2 hours)

    def tick(self):
        run_time = self.get_run_time()
        if run_time > self.time_limit:
            return None
        current_step = math.floor(run_time / self.step_time) + 1
        return (current_step * self.step_load, self.spawn_rate)

# === Globals for sync ===
max_users = 500
users_waiting = 0
event = gevent.event.Event()
lock = Semaphore()

# === Global counters for incremental IDs ===
vertical_id_counter = 1
node_id_counter = 1
sensortype_id_counter = 1

# === IoT Vertical Data ===
IOT_VERTICALS = [
    {
        "name": "Air Quality",
        "short": "AQ",
        "description": "Real-time air quality monitoring and analysis",
        "parameters": ["pm2.5", "pm10", "co2", "voc_index", "temperature"],
        "data_types": ["float", "float", "float", "int", "float"],
        "units": ["µg/m³", "µg/m³", "ppm", "index", "°C"]
    },
    {
        "name": "Water Quality", 
        "short": "WQ",
        "description": "Water quality monitoring for drinking and industrial water",
        "parameters": ["ph", "turbidity", "tds", "temperature", "dissolved_oxygen"],
        "data_types": ["float", "float", "int", "float", "float"],
        "units": ["pH", "NTU", "ppm", "°C", "mg/L"]
    },
    {
        "name": "Noise Monitoring",
        "short": "NM", 
        "description": "Environmental noise level monitoring and analysis",
        "parameters": ["decibel_level", "frequency", "peak_noise", "avg_noise"],
        "data_types": ["float", "float", "float", "float"],
        "units": ["dB", "Hz", "dB", "dB"]
    },
    {
        "name": "Weather Station",
        "short": "WS",
        "description": "Comprehensive weather monitoring system", 
        "parameters": ["temperature", "humidity", "pressure", "wind_speed", "rainfall"],
        "data_types": ["float", "float", "float", "float", "float"],
        "units": ["°C", "%", "hPa", "m/s", "mm"]
    },
    {
        "name": "Smart Agriculture",
        "short": "SA",
        "description": "IoT-based agricultural monitoring and automation",
        "parameters": ["soil_moisture", "soil_ph", "temperature", "humidity", "light_intensity"],
        "data_types": ["float", "float", "float", "float", "int"],
        "units": ["%", "pH", "°C", "%", "lux"]
    },
    {
        "name": "Energy Monitoring",
        "short": "EM",
        "description": "Smart energy consumption and management system",
        "parameters": ["voltage", "current", "power", "energy_consumption", "frequency"],
        "data_types": ["float", "float", "float", "float", "float"],
        "units": ["V", "A", "W", "kWh", "Hz"]
    },
    {
        "name": "Traffic Management",
        "short": "TM",
        "description": "Intelligent traffic monitoring and control system",
        "parameters": ["vehicle_count", "avg_speed", "traffic_density", "congestion_level"],
        "data_types": ["int", "float", "float", "int"],
        "units": ["count", "km/h", "%", "level"]
    },
    {
        "name": "Waste Management",
        "short": "WM",
        "description": "Smart waste collection and management system",
        "parameters": ["fill_level", "weight", "temperature", "gas_level"],
        "data_types": ["float", "float", "float", "float"],
        "units": ["%", "kg", "°C", "ppm"]
    }
]

SENSOR_TYPES = [
    "Temperature Sensor", "Humidity Sensor", "Pressure Sensor", "Gas Sensor",
    "pH Sensor", "Turbidity Sensor", "Motion Sensor", "Light Sensor",
    "Sound Sensor", "Proximity Sensor", "Vibration Sensor", "Flow Sensor"
]

def get_dynamic_vertical():
    """Get a random IoT vertical with unique ID"""
    global vertical_id_counter
    vertical = random.choice(IOT_VERTICALS)
    unique_id = random.randint(100, 999)
    
    return {
        "id": vertical_id_counter,
        "res_name": f"{vertical['name']} {unique_id}",
        "res_short_name": vertical['short'],
        "description": vertical['description'],
        "parameters": vertical['parameters'],
        "data_types": vertical['data_types'],
        "units": vertical['units']
    }

def get_dynamic_sensor_type():
    """Get a dynamic sensor type with unique name"""
    global sensortype_id_counter
    sensor_name = random.choice(SENSOR_TYPES)
    unique_id = random.randint(100, 999)
    
    return {
        "id": sensortype_id_counter,
        "name": f"{sensor_name} {unique_id}",
        "vertical_id": 3  # As requested
    }

# === Static POST APIs ===
STATIC_POST_APIS = [
    # 1. Login (no auth)
    ("/user/login", PUBLIC_HEADERS, {
        "email": "admin@localhost",
        "password": "admin"
    }),

    # 2. Forgot password
    ("/user/forgot-password", PUBLIC_HEADERS, {
        "email": random.choice(["vakaperireddy5555@gmail.com", "vakaperireddy59@gmail.com"])
    }),

    # 3. Reset password
    ("/user/reset-password", PUBLIC_HEADERS, {
        "email": "admin@localhost",
        "new_password": f"newpass{random.randint(1000, 9999)}"
    }),

    # # 4. Change password (auth)
    # ("/user/change-password", COMMON_HEADERS, {
    #     "email": "admin@localhost",
    #     "old_password": "admin",
    #     "new_password": "admin"
    # }),

    # 5. Create AE (auth) - Dynamic
    ("/verticals/create-ae", COMMON_HEADERS, "DYNAMIC_VERTICAL"),

    # 6. Assign vendor to vertical - Dynamic
    ("/verticals/assign-vendor", COMMON_HEADERS, "DYNAMIC_VERTICAL_ASSIGN"),

    # 7. Assign vendor to node - Dynamic  
    ("/nodes/assign-vendor", COMMON_HEADERS, "DYNAMIC_NODE_ASSIGN"),

    # 8. Create CIN (public) - Dynamic
    ("/nodes/create-cin/1", PUBLIC_HEADERS, "DYNAMIC_CIN"),

    # 9. Sensor-types create - Dynamic
    ("/sensor-types/create", COMMON_HEADERS, "DYNAMIC_SENSOR_TYPE"),

    # 10. Sensor-types assign vendor - Dynamic
    ("/sensor-types/assign-vendor", COMMON_HEADERS, "DYNAMIC_SENSOR_ASSIGN"),

    # 11. Subscription get-subscriptions
    ("/subscription/get-subscriptions", COMMON_HEADERS, {
        "node_id": "AQ01-0000-0001"
    })
]

# === Dynamic API generator (randomized payloads) ===
def get_dynamic_post_apis():
    global vertical_id_counter, node_id_counter, sensortype_id_counter
    
    unique_id = random.randint(1000, 9999)
    contact = str(random.randint(6000000000, 9999999999))
    email = f"vendor{unique_id}@test.com"
    username = f"Vendor_{unique_id}"
    notify_url = f"http://10.2.16.116:8610/notify/listener/{unique_id}"
    
    # Get dynamic vertical data
    vertical_data = get_dynamic_vertical()
    sensor_data = get_dynamic_sensor_type()

    dynamic_apis = [
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
        }),
        
        # Dynamic Create AE - Fixed payload format
        ("/verticals/create-ae", COMMON_HEADERS, {
            "res_name": vertical_data['res_name'],
            "res_short_name": vertical_data['res_short_name'],
            "description": f"Vertical for managing and monitoring {vertical_data['res_name'].lower()}",
            "pdescription": [vertical_data['parameters'][0]],  # Single parameter
            "name": [vertical_data['parameters'][0]],
            "data_types": [vertical_data['data_types'][0]],
            "accuracy": ["±1"],
            "units": [vertical_data['units'][0]],
            "resolution": ["0.1"],
            "ideal": [{"min": 15, "max": 30}],
            "moderate": [
                {"min": 10, "max": 15},
                {"min": 30, "max": 35}
            ],
            "extreme": [{"min": 5, "max": None}]
        }),
        
        # Dynamic Assign vendor to vertical
        ("/verticals/assign-vendor", COMMON_HEADERS, {
            "vertical_id": vertical_id_counter,
            "vendor_email": random.choice(["vakaperireddy5555@gmail.com", "vakaperireddy59@gmail.com"])
        }),
        
        # Dynamic Assign vendor to node
        ("/nodes/assign-vendor", COMMON_HEADERS, {
            "node_id": str(node_id_counter),
            "vendor_email": random.choice(["vakaperireddy5555@gmail.com", "vakaperireddy59@gmail.com"])
        }),
        
        # Dynamic Create CIN - Using correct CIN token
        ("/nodes/create-cin/1", CIN_HEADERS, {
            vertical_data['parameters'][0]: round(random.uniform(1.0, 100.0), 2)
        }),
        
        # Dynamic Sensor-types create
        ("/sensor-types/create", COMMON_HEADERS, {
            "res_name": sensor_data['name'],
            "parameters": [vertical_data['parameters'][0]],  # Use first parameter from vertical
            "data_types": [vertical_data['data_types'][0]],  # Use first data type
            "labels": [],
            "vertical_id": sensor_data['vertical_id'],
            "accuracy": ["±0.5"],
            "units": [vertical_data['units'][0]],
            "resolution": ["0.1"],
            "ideal": [{"min": 0, "max": 50}],
            "moderate": [{"min": 51, "max": 70}],
            "extreme": [{"min": 71, "max": 100}]
        }),
        
        # Dynamic Sensor-types assign vendor
        ("/sensor-types/assign-vendor", COMMON_HEADERS, {
            "sensortype_id": sensortype_id_counter,
            "vendor_email": random.choice(["vakaperireddy5555@gmail.com", "vakaperireddy59@gmail.com"])
        })
    ]
    
    # Increment counters for next requests
    vertical_id_counter += 1
    node_id_counter += 1 
    sensortype_id_counter += 1

    return dynamic_apis

# === Locust User ===
class MyUser(HttpUser):
    wait_time = between(1, 15)

    def on_start(self):
        self.start_time = time.time()

    @task
    def post_requests(self):
        global users_waiting, event

        # Barrier sync
        with lock:
            users_waiting += 1
            print(f"{users_waiting} users waiting... ({users_waiting}/{max_users})")
            if users_waiting >= self.environment.runner.user_count:
                print("All users are ready!")
                event.set()

        event.wait()

        user_num = self.environment.runner.user_count
        current_time = time.strftime('%Y-%m-%d %H:%M:%S')
        print(f"User {user_num} - Time: {current_time}")

        # Pick API (only use dynamic APIs for better testing)
        all_apis = get_dynamic_post_apis()
        endpoint, headers, payload = random.choice(all_apis)
        url = f"{BASE_URL}{endpoint}"

        # Handle special dynamic payloads that were marked in static APIs
        if isinstance(payload, str) and payload.startswith("DYNAMIC_"):
            print(f"[INFO] Skipping placeholder API: {payload}")
            return

        if headers.get("Content-Type") == "application/x-www-form-urlencoded":
            response = self.client.post(url, headers=headers, data=payload)
        else:
            response = self.client.post(url, headers=headers, json=payload)

        if response.status_code in [200, 201]:
            response.success()
            print(f"[SUCCESS] {endpoint} -> {response.status_code}")
        else:
            response.failure(f"Failed {url} with {response.status_code}")
            print(f"[FAILED] {endpoint} -> {response.status_code}")

        # Reset barrier
        with lock:
            users_waiting -= 1
            if users_waiting == 0:
                event.clear()
