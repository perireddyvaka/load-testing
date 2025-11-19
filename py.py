from locust import HttpUser, task, constant, between, LoadTestShape
import json
import random
import logging
import time
import itertools
import os
import csv
from datetime import datetime
from gevent.lock import Semaphore

# Shared counter and lock to deterministically assign node ids to spawned users
node_id_counter = itertools.count(0)
node_id_lock = Semaphore()

# CSV file lock to prevent concurrent writes
csv_lock = Semaphore()

# CSV file paths
CSV_FILE_PATH = os.path.join(os.path.dirname(__file__), "node_post_data.csv")
CSV_GET_FILE_PATH = os.path.join(os.path.dirname(__file__), "node_get_data.csv")

# Initialize CSV file with headers
def initialize_csv():
    """Initialize CSV file with headers if it doesn't exist"""
    if not os.path.exists(CSV_FILE_PATH):
        with open(CSV_FILE_PATH, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                'timestamp',
                'node_id',
                'status_code',
                'payload_type',
                'polluters_count',
                'bindata',
                'violations',
                'vehicle_number',
                'lct',
                'temperature',
                'tds'
            ])
    
    # Initialize GET requests CSV
    if not os.path.exists(CSV_GET_FILE_PATH):
        with open(CSV_GET_FILE_PATH, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                'timestamp',
                'node_id',
                'endpoint',
                'status_code',
                'vertical_name',
                'limit',
                'offset'
            ])

# Initialize CSV on module load
initialize_csv()

node_tokens ={

  158: "50aed80e88aa7f3eb0bd148edf0c54fa",
  159: "bc57eabbe0cc77aa3d34446d5b48bcfe",
  160: "f31964db668cb5a2e4199637df1ef1d1",
  161: "c9c8342292ceecfc1ddd338718455b8d",
  162: "50aed80e88aa7f3eb0bd148edf0c54fa",
  1169: "c4f9abfa92f2cc8d029a85df27ef055f",
}

# Create a list of available node IDs for assignment
AVAILABLE_NODE_IDS = list(node_tokens.keys())

# Remove fixed payloads and use generator functions instead
def generate_waste_management_payload():
    """Generate random waste management payload"""
    return {
        "polluters_count": random.randint(0, 20),
        "bindata": random.choice(["low", "medium", "high", "critical", "normal"]),
        "violations": str(random.randint(0, 100)),
        "vehicle_number": f"{random.choice(['KA', 'MH', 'DL', 'TN', 'AP'])}{random.randint(10, 99)}{random.choice(['A', 'B', 'C', 'D'])}{random.randint(1000, 9999)}",
        "lct": random.choice(["collected", "pending", "in_progress", "delayed", "completed"])
    }

def generate_water_quality_payload():
    """Generate random water quality payload"""
    return {
        "temperature": round(random.uniform(20.0, 32.0), 2),  # More realistic water temperature range (20-32°C)
        "tds": round(random.uniform(100.0, 400.0), 2)  # Typical drinking water TDS range (100-400 mg/L)
    }

fetch_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3NjI0MDg4MTIsInN1YiI6IjM0In0.EXsvZuj-tG735kq3xLCIFaiArspPAM3hwe6VwmBIzZY"

def log_to_csv(node_id, status_code, payload, payload_type):
    """Log POST request data to CSV file"""
    timestamp = datetime.now().isoformat()
    
    with csv_lock:
        try:
            # Add detailed logging for 400 status codes
            if status_code == 400:
                logging.error(f"Node {node_id} received 400 status code:")
                logging.error(f"  Timestamp: {timestamp}")
                logging.error(f"  Payload type: {payload_type}")
                logging.error(f"  Payload content: {payload}")

            with open(CSV_FILE_PATH, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                
                if payload_type == 'waste_management':
                    writer.writerow([
                        timestamp,
                        node_id,
                        status_code,
                        payload_type,
                        payload.get('polluters_count', ''),
                        payload.get('bindata', ''),
                        payload.get('violations', ''),
                        payload.get('vehicle_number', ''),
                        payload.get('lct', ''),
                      
                    ])
                else:  # water_quality
                    writer.writerow([
                        timestamp,
                        node_id,
                        status_code,
                        payload_type,
                   
                        payload.get('temperature', ''),
                        payload.get('tds', '')
                    ])
        except Exception as e:
            logging.getLogger(__name__).error(f"Failed to write to CSV: {str(e)}")

def log_get_to_csv(node_id, status_code, endpoint, vertical_name=None, limit=None, offset=None):
    """Log GET request data to CSV file"""
    timestamp = datetime.now().isoformat()
    
    with csv_lock:
        try:
            with open(CSV_GET_FILE_PATH, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    timestamp,
                    node_id,
                    endpoint,
                    status_code,
                    vertical_name or '',
                    limit or '',
                    offset or ''
                ])
        except Exception as e:
            logging.getLogger(__name__).error(f"Failed to write GET request to CSV: {str(e)}")

class NodeUser(HttpUser):
    host = "http://10.2.16.116:8610"
    
    # Reduce wait time to ensure continuous requests - wait 1-3 seconds between tasks
    wait_time = between(1, 3)

    def on_start(self):
        logger = logging.getLogger(__name__)
        
        # Assign node ID from available node IDs list
        with node_id_lock:
            index = next(node_id_counter)
            # Use modulo to cycle through available node IDs if more users than nodes
            self.node_id = AVAILABLE_NODE_IDS[index % len(AVAILABLE_NODE_IDS)]
        
        self.token = node_tokens[self.node_id]
        print(f"User assigned node_id={self.node_id}")
        logger.info(f"User assigned node_id={self.node_id}")

        # Determine payload type based on node ID
        # First half of nodes use waste_management, second half use water_quality
        midpoint = len(AVAILABLE_NODE_IDS) // 2
        node_index = AVAILABLE_NODE_IDS.index(self.node_id)
        
        if node_index < midpoint:
            self.payload_type = 'waste_management'
        else:
            self.payload_type = 'water_quality'
        
        print(f"Node {self.node_id} using {self.payload_type} payload")

        self._last_post = 0
        self._post_immediately()

    def _post_immediately(self):
        """Post immediately on startup"""
        logger = logging.getLogger(__name__)
        try:
            # Generate random payload
            if self.payload_type == 'waste_management':
                payload = generate_waste_management_payload()
            else:
                payload = generate_water_quality_payload()
            
            url = f"/nodes/create-cin/{self.node_id}"
            headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.token}"}
            print(f"Node {self.node_id}: Initial POST at startup with payload: {payload}")
            response = self.client.post(url, json=payload, headers=headers)
            
            # Add detailed error logging for 400 status codes
            if response.status_code == 400:
                print(f"\n{'='*80}")
                print(f"!!! Node {self.node_id} INITIAL POST - 400 Bad Request !!!")
                print(f"Request Payload: {payload}")
                try:
                    error_detail = response.json()
                    print(f"ERROR DETAILS: {json.dumps(error_detail, indent=2)}")
                except:
                    print(f"ERROR TEXT: {response.text}")
                print(f"{'='*80}\n")
            
            self._last_post = time.time()
            print(f"Node {self.node_id}: Initial POST completed with status {response.status_code}")
            logger.info(f"Node {self.node_id}: Initial POST completed with status {response.status_code}")
            
            # Log to CSV
            log_to_csv(self.node_id, response.status_code, payload, self.payload_type)
        except Exception as e:
            print(f"Node {self.node_id}: Initial POST failed - {str(e)}")
            logger.exception("Initial post failed for node_id=%s", self.node_id)

    @task(10)
    def post_node_data(self):
        """Continuously post data"""
        self._do_post()
    
    def _do_post(self):
        """Perform the actual POST request"""
        logger = logging.getLogger(__name__)
        
        if self.payload_type == 'waste_management':
            payload = generate_waste_management_payload()
        else:
            payload = generate_water_quality_payload()
        
        url = f"/nodes/create-cin/{self.node_id}"
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.token}"}
        try:
            elapsed = time.time() - self._last_post
            print(f"Node {self.node_id}: POST (last post {elapsed:.1f}s ago) with payload: {payload}")
            response = self.client.post(url, json=payload, headers=headers)
            
            # Add detailed error logging for 400 status codes
            if response.status_code == 400:
                print(f"\n{'='*80}")
                print(f"!!! Node {self.node_id} received 400 Bad Request !!!")
                print(f"Request Payload: {payload}")
                try:
                    error_detail = response.json()
                    print(f"ERROR DETAILS: {json.dumps(error_detail, indent=2)}")
                    logger.error(f"Node {self.node_id} - 400 Error Details: {error_detail}")
                except:
                    print(f"ERROR TEXT: {response.text}")
                    logger.error(f"Node {self.node_id} - 400 Raw Response: {response.text}")
                print(f"{'='*80}\n")
            
            self._last_post = time.time()
            print(f"Node {self.node_id}: POST completed with status {response.status_code}")
            logger.info(f"Node {self.node_id}: POST completed with status {response.status_code}")
            
            log_to_csv(self.node_id, response.status_code, payload, self.payload_type)
        except Exception as e:
            print(f"Node {self.node_id}: POST failed - {str(e)}")
            logger.exception("post_node_data failed for node_id=%s", self.node_id)

    @task(1)
    def fetch_node_data(self):
        logger = logging.getLogger(__name__)
        try:
            vertical_name = random.choice(["water_quality", "waste_management"])
            url = f"/nodes/fetch-node-data/?vertical_name={vertical_name}&limit=100&offset=0&as_csv=false"
            headers = {"Accept": "application/json", "Authorization": f"Bearer {fetch_token}"}
            print(f"Node {self.node_id}: FETCH {vertical_name}")
            response = self.client.get(url, headers=headers)
            print(f"Node {self.node_id}: FETCH completed with status {response.status_code}")
            logger.info(f"Node {self.node_id}: FETCH {vertical_name} completed with status {response.status_code}")
            
            # Log to CSV
            log_get_to_csv(self.node_id, response.status_code, "fetch-node-data", vertical_name, 100, 0)
        except Exception as e:
            print(f"Node {self.node_id}: FETCH failed - {str(e)}")
            logger.exception("fetch_node_data failed for node_id=%s", self.node_id)

    @task(1)
    def fetch_all_nodes(self):
        logger = logging.getLogger(__name__)
        try:
            url = "/nodes/nodes-all"
            headers = {"Accept": "application/json", "Authorization": f"Bearer {fetch_token}"}
            print(f"Node {self.node_id}: FETCH ALL NODES")
            response = self.client.get(url, headers=headers)
            print(f"Node {self.node_id}: FETCH ALL NODES completed with status {response.status_code}")
            logger.info(f"Node {self.node_id}: FETCH ALL NODES completed with status {response.status_code}")
            
            # Log to CSV
            log_get_to_csv(self.node_id, response.status_code, "nodes-all")
        except Exception as e:
            print(f"Node {self.node_id}: FETCH ALL NODES failed - {str(e)}")
            logger.exception("fetch_all_nodes failed for node_id=%s", self.node_id)


class ContinuousOneHourLoadShape(LoadTestShape):
    """
    Constant 1000-user load for 1 hour.
    Gradual spawn to avoid initial spike.
    """
    
    def tick(self):
        run_time = self.get_run_time()
        
        # Run for 1 hour (3600 seconds)
        if run_time > 3600:
            return None
        
        # Gradual spawn over first 60 seconds to avoid spike
        if run_time < 60:
            current_users = int((run_time / 60) * 1000)
            return (current_users, 20)  # Spawn 20 users per second
        
        # Maintain 1000 users after spawn period
        return (1000, 20)


# === Module-level events.request listener (uses module-level constants) ===
