#!/usr/bin/env python3
"""
HIGH DENSITY PERIODIC (HDP) Load Test for IoT Backend
=====================================================

This test implements a high-density periodic pattern where:
1. Users perform synchronized BURST requests every 10 seconds
2. User count grows in STEPS every 60 seconds  
3. All users execute SIMULTANEOUSLY for maximum density
4. Sequential POST workflow + rapid GET/PUT requests

Features:
- Event-based synchronization for maximum concurrency
- Dynamic IoT data generation
- Comprehensive error handling
- Real-time monitoring
"""

import json
import random
import time
import uuid
from datetime import datetime, timedelta
import gevent
from gevent import event
from locust import HttpUser, task, events
from locust.env import Environment
from locust.stats import stats_printer, stats_history
from locust.log import setup_logging

# === Config ===
BASE_URL = "http://10.2.16.116:8002"
ADMIN_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3NTgwNTgzNTIsInN1YiI6IjEifQ.VWCk1DWiXg7byV3ed8Bd6-oU-HxJ8Ta29JVn66wmbYM"

# === HTTP Headers ===
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
    },
    {
        "name": "Traffic Monitoring",
        "short": "TM", 
        "description": "Smart traffic monitoring system",
        "parameters": ["vehicle_count", "avg_speed", "congestion_level"],
        "data_types": ["int", "float", "float"],
        "units": ["vehicles", "km/h", "%"]
    },
    {
        "name": "Weather Station",
        "short": "WS",
        "description": "Weather monitoring station",
        "parameters": ["temperature", "humidity", "pressure"],
        "data_types": ["float", "float", "float"],
        "units": ["°C", "%", "hPa"]
    }
]

# === Global Synchronization ===
class SyncManager:
    def __init__(self):
        self.burst_event = event.Event()
        self.user_count = 0
        self.start_time = time.time()
        
    def register_user(self):
        self.user_count += 1
        print(f"🔗 HD User #{self.user_count} joined the swarm")
        
    def wait_for_burst(self):
        """All users wait for the synchronized burst signal"""
        current_time = time.time()
        elapsed = current_time - self.start_time
        
        # Calculate time until next 10-second burst
        next_burst = ((int(elapsed) // 10) + 1) * 10
        wait_time = next_burst - elapsed
        
        if wait_time > 0:
            print(f"⏰ HD User waiting {wait_time:.1f}s for next burst...")
            gevent.sleep(wait_time)
            
        print(f"💥 HD BURST ACTIVATED! ({self.user_count} users)")
        
# Global sync manager
sync_manager = SyncManager()

# === Custom Load Shape ===
class HighDensityPeriodicShape:
    """
    High Density Periodic load pattern:
    - Step growth every 60 seconds
    - Burst synchronization every 10 seconds
    - Maximum concurrent execution
    """
    
    def __init__(self):
        self.start_time = time.time()
        
    def tick(self):
        run_time = time.time() - self.start_time
        
        # Step growth every 60 seconds
        step_number = int(run_time // 60) + 1
        
        if step_number <= 1:
            user_count = 5  # Start small
        elif step_number <= 2:
            user_count = 15  # Moderate load
        elif step_number <= 3:
            user_count = 30  # High load
        elif step_number <= 4:
            user_count = 50  # Very high load
        else:
            user_count = 75  # Maximum density
            
        # Stop after 1 hour
        if run_time > 3600:
            return None
            
        return (user_count, user_count)

# === Data Generators ===
def generate_unique_id():
    """Generate unique resource ID with high entropy"""
    timestamp = int(time.time() * 1000)
    random_part = random.randint(1000, 9999)
    return f"hd-resource-{timestamp}-{random_part}"

def generate_dynamic_payload(vertical, resource_id):
    """Generate realistic IoT data payload"""
    current_time = datetime.now()
    
    # Simulate realistic sensor data
    data_values = []
    for param, data_type, unit in zip(vertical["parameters"], vertical["data_types"], vertical["units"]):
        if data_type == "float":
            # Add realistic ranges for different parameters
            if "temperature" in param.lower():
                value = round(random.uniform(15.0, 35.0), 2)
            elif "humidity" in param.lower():
                value = round(random.uniform(30.0, 90.0), 2)
            elif "voltage" in param.lower():
                value = round(random.uniform(220.0, 240.0), 2)
            elif "pm" in param.lower():
                value = round(random.uniform(5.0, 150.0), 2)
            elif "ph" in param.lower():
                value = round(random.uniform(6.5, 8.5), 2)
            else:
                value = round(random.uniform(10.0, 100.0), 2)
        else:
            value = random.randint(1, 100)
            
        data_values.append(value)
    
    return {
        "resourceId": resource_id,
        "vertical": vertical["short"],
        "timestamp": current_time.isoformat(),
        "location": {
            "latitude": round(random.uniform(40.0, 41.0), 6),
            "longitude": round(random.uniform(-74.0, -73.0), 6)
        },
        "sensorData": {
            param: {"value": val, "unit": unit} 
            for param, val, unit in zip(vertical["parameters"], data_values, vertical["units"])
        },
        "metadata": {
            "deviceId": f"sensor-{resource_id}",
            "firmwareVersion": f"v{random.randint(1,5)}.{random.randint(0,9)}",
            "batteryLevel": random.randint(20, 100),
            "signalStrength": random.randint(-100, -30)
        }
    }

# === User Classes ===
class HighDensitySequentialPostUser(HttpUser):
    weight = 60
    
    def on_start(self):
        sync_manager.register_user()
        self.user_id = generate_unique_id()
        self.vertical = random.choice(IOT_VERTICALS)
        print(f"🚀 HD POST User started: {self.user_id} ({self.vertical['short']})")
        
    @task
    def sequential_post_workflow(self):
        """High-density synchronized POST workflow"""
        sync_manager.wait_for_burst()
        
        resource_id = generate_unique_id()
        
        # 14-step sequential workflow with synchronization
        steps = [
            ("Register Device", "/api/v1/devices", "POST"),
            ("Create Vertical", f"/api/v1/verticals/{self.vertical['short']}", "POST"),
            ("Setup Sensors", f"/api/v1/devices/{resource_id}/sensors", "POST"),
            ("Configure Alerts", f"/api/v1/devices/{resource_id}/alerts", "POST"),
            ("Register Location", f"/api/v1/devices/{resource_id}/location", "POST"),
            ("Upload Firmware", f"/api/v1/devices/{resource_id}/firmware", "POST"),
            ("Set Sampling Rate", f"/api/v1/devices/{resource_id}/config", "POST"),
            ("Create Data Stream", f"/api/v1/streams/{resource_id}", "POST"),
            ("Setup Analytics", f"/api/v1/analytics/{resource_id}", "POST"),
            ("Configure Notifications", f"/api/v1/notifications/{resource_id}", "POST"),
            ("Create Dashboard", f"/api/v1/dashboards/{resource_id}", "POST"),
            ("Setup Automation", f"/api/v1/automation/{resource_id}", "POST"),
            ("Register Maintenance", f"/api/v1/maintenance/{resource_id}", "POST"),
            ("Send Initial Data", f"/api/v1/data/{resource_id}", "POST")
        ]
        
        for step_name, endpoint, method in steps:
            payload = generate_dynamic_payload(self.vertical, resource_id)
            
            with self.client.post(endpoint, headers=COMMON_HEADERS, json=payload, catch_response=True) as resp:
                if resp.status_code in [200, 201]:
                    print(f"[HD-POST ✅] {step_name}")
                else:
                    print(f"[HD-POST ❌] {step_name} ({resp.status_code})")
                    print("[DEBUG] Response:", resp.text[:100])

class HighDensityGetUser(HttpUser):
    weight = 25
    
    def on_start(self):
        sync_manager.register_user()
        self.user_id = generate_unique_id()
        print(f"🔍 HD GET User started: {self.user_id}")
        
    @task
    def rapid_get_requests(self):
        """High-density rapid GET requests"""
        sync_manager.wait_for_burst()
        
        # Rapid-fire GET requests
        endpoints = [
            "/api/v1/devices",
            "/api/v1/verticals", 
            "/api/v1/data/recent",
            "/api/v1/analytics/summary",
            "/api/v1/alerts/active",
            "/api/v1/dashboards",
            "/api/v1/streams/status",
            "/api/v1/devices/health"
        ]
        
        for endpoint in endpoints:
            with self.client.get(endpoint, headers=PUBLIC_HEADERS, catch_response=True) as resp:
                if resp.status_code in [200, 201]:
                    print(f"[HD-GET ✅] {endpoint}")
                else:
                    print(f"[HD-GET ❌] {endpoint} ({resp.status_code})")
                    print("[DEBUG] Response:", resp.text[:100])

class HighDensityPutUser(HttpUser):
    weight = 15
    
    def on_start(self):
        sync_manager.register_user()
        self.user_id = generate_unique_id()
        self.vertical = random.choice(IOT_VERTICALS)
        print(f"🔄 HD PUT User started: {self.user_id} ({self.vertical['short']})")
        
    @task  
    def rapid_put_updates(self):
        """High-density rapid PUT updates"""
        sync_manager.wait_for_burst()
        
        resource_id = generate_unique_id()
        
        # Rapid PUT updates
        endpoints = [
            f"/api/v1/devices/{resource_id}/config",
            f"/api/v1/devices/{resource_id}/location", 
            f"/api/v1/devices/{resource_id}/alerts",
            f"/api/v1/streams/{resource_id}/config",
            f"/api/v1/analytics/{resource_id}/rules"
        ]
        
        for endpoint in endpoints:
            payload = generate_dynamic_payload(self.vertical, resource_id)
            headers = COMMON_HEADERS.copy()
            
            with self.client.put(endpoint, headers=headers, json=payload, catch_response=True) as resp:
                if resp.status_code in [200, 201]:
                    print(f"[HD-PUT ✅] {endpoint}")
                else:
                    print(f"[HD-PUT ❌] {endpoint} ({resp.status_code})")
                    print("[DEBUG] Response:", resp.text[:100])

# === Direct Execution ===
if __name__ == "__main__":
    import subprocess
    import sys
    import os
    
    print("🚀 Starting HIGH DENSITY PERIODIC Load Test...")
    print("📊 Web UI: http://localhost:8090")
    print("🔥 Pattern: BURST every 10 seconds + Step growth every 60 seconds")
    print("💥 Synchronization: All users execute SIMULTANEOUSLY for maximum density")
    print("🎯 Target: http://10.2.16.116:8002")
    print("⏱️  Duration: 1 hour with periodic burst patterns")
    print("📋 Coverage: 14 Synchronized POST steps + Rapid GET/PUT requests")
    print("🚨 WARNING: This is a HIGH INTENSITY test - Monitor system resources!")
    print("-" * 70)
    
    # Get the current script path
    script_path = os.path.abspath(__file__)
    
    # Locust command with web interface (using port 8090 to avoid conflicts)
    cmd = [
        "locust",
        "-f", script_path,
        "--host", BASE_URL,
        "--web-host", "0.0.0.0", 
        "--web-port", "8090"
    ]
    
    try:
        # Start Locust with web UI
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running Locust: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n⏹️  HIGH DENSITY test stopped by user")
        sys.exit(0)
