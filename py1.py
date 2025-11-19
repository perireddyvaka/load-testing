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
                'tds',
                'flow'  # Added flow column
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

# Load node tokens from JSON file
def load_node_tokens():
    """Load node tokens from JSON file and create mapping"""
    json_path = os.path.join(os.path.dirname(__file__), "tokens_by_vertical (1).json")
    with open(json_path, 'r') as f:
        verticals = json.load(f)
    
    node_tokens = {}
    node_to_vertical = {}
    
    # vertical_1 = water_quality nodes (ONLY USING)
    for node_id, token in verticals.get("vertical_1", {}).items():
        node_tokens[int(node_id)] = token
        node_to_vertical[int(node_id)] = "water_quality"
    
    # COMMENTED OUT: vertical_2 = waste_management nodes (NOT USING)
    # for node_id, token in verticals.get("vertical_2", {}).items():
    #     node_tokens[int(node_id)] = token
    #     node_to_vertical[int(node_id)] = "waste_management"
    
    return node_tokens, node_to_vertical

node_tokens, node_to_vertical = load_node_tokens()

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
        "temperature": random.randint(20, 32),  # Changed to int (20-32°C)
        "tds": random.randint(100, 400),  # Changed to int (100-400 mg/L)
        "flow": random.randint(50, 150)  # Added flow parameter as int (50-150 L/min)
    }

fetch_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3NjQxNDIyMzgsInN1YiI6IjEifQ.jZEiwfZ0iJgDt3vsB1A3AkQ__-c10a3oituJYoaiv28"

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
                
                # Only log water_quality data
                writer.writerow([
                    timestamp,
                    node_id,
                    status_code,
                    payload_type,
                    '',  # polluters_count placeholder
                    '',  # bindata placeholder
                    '',  # violations placeholder
                    '',  # vehicle_number placeholder
                    '',  # lct placeholder
                    payload.get('temperature', ''),
                    payload.get('tds', ''),
                    payload.get('flow', '')  # Added flow field
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
    
    # Wait between 0.1-0.5 seconds to allow continuous posting
    wait_time = between(0.1, 0.5)

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

        # Determine payload type based on vertical mapping
        self.payload_type = node_to_vertical.get(self.node_id, 'water_quality')
        
        print(f"Node {self.node_id} using {self.payload_type} payload (from vertical mapping)")

        self._last_post = 0
        # self._post_immediately()  # Commented out - no POST requests needed

    def _post_immediately(self):
        """Post immediately on startup"""
        logger = logging.getLogger(__name__)
        try:
            # ONLY generate water_quality payload
            # if self.payload_type == 'waste_management':
            #     payload = generate_waste_management_payload()
            # else:
            #     payload = generate_water_quality_payload()
            payload = generate_water_quality_payload()
            
            url = f"/nodes/create-cin/{self.node_id}"
            headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.token}"}
            print(f"Node {self.node_id}: Initial POST at startup with payload: {payload}")
            
            try:
                response = self.client.post(url, json=payload, headers=headers, timeout=30)
                status_code = response.status_code
            except Exception as req_error:
                print(f"\n{'='*80}")
                print(f"!!! Node {self.node_id} INITIAL POST - REQUEST FAILED !!!")
                print(f"Error Type: {type(req_error).__name__}")
                print(f"Error Message: {str(req_error)}")
                print(f"Request Payload: {payload}")
                print(f"{'='*80}\n")
                logger.error(f"Node {self.node_id} - Request failed: {type(req_error).__name__} - {str(req_error)}")
                # Set status_code to 0 to indicate failure
                status_code = 0
                # Create a dummy response object for logging
                class DummyResponse:
                    status_code = 0
                    text = str(req_error)
                response = DummyResponse()
            
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

    def _do_post(self):
        """Perform the actual POST request"""
        logger = logging.getLogger(__name__)
        
        # ONLY generate water_quality payload
        # if self.payload_type == 'waste_management':
        #     payload = generate_waste_management_payload()
        # else:
        #     payload = generate_water_quality_payload()
        payload = generate_water_quality_payload()
        
        url = f"/nodes/create-cin/{self.node_id}"
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.token}"}
        try:
            elapsed = time.time() - self._last_post
            print(f"Node {self.node_id}: POST (last post {elapsed:.1f}s ago) with payload: {payload}")
            
            try:
                response = self.client.post(url, json=payload, headers=headers, timeout=30)
                status_code = response.status_code
            except Exception as req_error:
                print(f"\n{'='*80}")
                print(f"!!! Node {self.node_id} POST - REQUEST FAILED !!!")
                print(f"Error Type: {type(req_error).__name__}")
                print(f"Error Message: {str(req_error)}")
                print(f"Request Payload: {payload}")
                print(f"{'='*80}\n")
                logger.error(f"Node {self.node_id} - Request failed: {type(req_error).__name__} - {str(req_error)}")
                # Set status_code to 0 to indicate failure
                status_code = 0
                # Create a dummy response object for logging
                class DummyResponse:
                    status_code = 0
                    text = str(req_error)
                response = DummyResponse()
            
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

    # @task(10)
    # def post_node_data(self):
    #     now = time.time()
    #     
    #     if now - self._last_post >= 10:
    #         print(f"Node {self.node_id}: Forcing POST (10s elapsed)")
    #         self._do_post()
    #     else:
    #         self._do_post()
    
    @task(5)
    def fetch_node_data(self):
        logger = logging.getLogger(__name__)
        try:
            # ONLY fetch water_quality data
            vertical_name = random.choice(["water_quality", "waste_management"])
            # vertical_name = "water_quality"
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

    # @task(5)
    # def fetch_all_nodes(self):
    #     logger = logging.getLogger(__name__)
    #     try:
    #         url = "/nodes/nodes-all"
    #         headers = {"Accept": "application/json", "Authorization": f"Bearer {fetch_token}"}
    #         print(f"Node {self.node_id}: FETCH ALL NODES")
    #         response = self.client.get(url, headers=headers)
    #         print(f"Node {self.node_id}: FETCH ALL NODES completed with status {response.status_code}")
    #         logger.info(f"Node {self.node_id}: FETCH ALL NODES completed with status {response.status_code}")
            
    #         # Log to CSV
    #         log_get_to_csv(self.node_id, response.status_code, "nodes-all")
    #     except Exception as e:
    #         print(f"Node {self.node_id}: FETCH ALL NODES failed - {str(e)}")
    #         logger.exception("fetch_all_nodes failed for node_id=%s", self.node_id)


class GradualIncreaseLoadShape(LoadTestShape):
    """
    Fast ramp-up to 1000 users within 1 minute, then maintain.
    - Reach 1000 users in 60 seconds
    - Maintain 1000 users for the remaining test duration
    - Total duration: 30 minutes 1 second (1801 seconds)
    """
    
    def tick(self):
        run_time = self.get_run_time()
        
        # Total test duration: 30 minutes 1 second = 1801 seconds
        if run_time > 1801:
            return None
        
        # Ramp up to 1000 users in 60 seconds
        if run_time < 60:
            # Linear ramp-up: from 0 to 1000 users in 60 seconds
            current_users = int((run_time / 60) * 1000)
            # Spawn rate: 1000 users in 60 seconds = ~16.67 users per second
            spawn_rate = 17  # Spawn 17 users per second for fast ramp-up
        else:
            # Maintain 1000 users after 60 seconds
            current_users = 1000
            spawn_rate = 17  # Keep same spawn rate for any adjustments
        
        return current_users, spawn_rate


# === Module-level events.request listener (uses module-level constants) ===