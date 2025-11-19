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

# CSV file paths - Only need GET requests CSV
CSV_GET_FILE_PATH = os.path.join(os.path.dirname(__file__), "node_get_data.csv")

# CSV file lock to prevent concurrent writes
csv_lock = Semaphore()

# Initialize CSV file with headers
def initialize_csv():
    """Initialize CSV file with headers if it doesn't exist"""
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
    
    # vertical_1 = water_quality nodes
    for node_id, token in verticals.get("vertical_1", {}).items():
        node_tokens[int(node_id)] = token
        node_to_vertical[int(node_id)] = "water_quality"
    
    # vertical_2 = waste_management nodes
    for node_id, token in verticals.get("vertical_2", {}).items():
        node_tokens[int(node_id)] = token
        node_to_vertical[int(node_id)] = "waste_management"
    
    return node_tokens, node_to_vertical

node_tokens, node_to_vertical = load_node_tokens()

# Create a list of available node IDs for assignment
AVAILABLE_NODE_IDS = list(node_tokens.keys())

fetch_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3NjI3NDg3NTksInN1YiI6IjEifQ.-MUKOv5CyJgN6i7dEo8Rj8ubXqIaca-S4jp7ByxBGvw"

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
    host = "http://10.2.16.116:8000"
    
    # Continuous requests - wait 0.5-2 seconds between requests
    wait_time = between(0.5, 2)

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
        
        print(f"Node {self.node_id} mapped to {self.payload_type} vertical")

    @task(5)
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

    @task(5)
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


class ContinuousThirtyMinuteLoadShape(LoadTestShape):
    """
    Continuous load test for 30 minutes with 1000 users.
    Gradual spawn to avoid spikes.
    """
    
    def tick(self):
        run_time = self.get_run_time()
        
        # Total test duration: 30 minutes = 1800 seconds
        if run_time > 1800:
            return None
        
        # Gradual spawn over first 60 seconds
        if run_time < 60:
            current_users = int((run_time / 60) * 1000)
            return (current_users, 20)  # Spawn 20 users per second
        
        # Maintain 1000 users after spawn period
        return (1000, 20)


# === Module-level events.request listener (uses module-level constants) ===