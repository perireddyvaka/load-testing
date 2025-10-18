from locust import HttpUser, task, constant, between
import json
import random
import logging
import time
import itertools
import os
from gevent.lock import Semaphore

# Shared counter and lock to deterministically assign node ids to spawned users
node_id_counter = itertools.count(1)
node_id_lock = Semaphore()

node_tokens = {
    1: "3df723d0a5322ff80d831bf555b98169",
    2: "dc0dbd5a676b62b092dfa467ef485b19",
    3: "1b4c7de85f106e9a30bc6e47f64a36b3",
    4: "495a75aa77e3dac0d13725bff0d4fd70",
    5: "8780fb8174e241aacd093cf0ab3e69c4",
    6: "835f33979fae4bf0601241be611fad7b",
    7: "b55a298cadb725033212a8ddd5d209a4",
    8: "556efb952ae7bdd50927ddf42dd2213c",
    9: "016892050ca3122ac16d31590069d082",
    10: "6914893453c0f4b403d83307d535d4cd",
    11: "3814166cd23154e0b5f638109a6f80e4",
    12: "f3145b7593e6545a0adc524e6c9908ac",
    13: "7d7b5147447745c8aa30f44819e3b1ee",
    14: "f4a7e21485690b85835e890f08b67df7",
    15: "3b03916eb19c52abe64b87d561dab81a",
    16: "b38eaf4a7a3caa01c04d68dda032bcd9",
    17: "c9a7ffbc09aa50e2bd4c70ddbda2acab",
    18: "dc64530cd958d067eb8b52a5862a8381",
    19: "21de849a257eb126d98ce40f710f65be",
    20: "a21bfd5b6a49c11e7290d10b1a3f785d",
    21: "84587bb14dce7f8f3d28d5c23bb3332b",
    22: "c261c15674d43d3a12e526fa391829bd",
    23: "4fb3ac1a6e2554e4200d6b103a953cad",
    24: "365bae3c36746ac03b3a72f649417c3f",
    25: "41930f366b9d0c809c004515e6878a33",
    26: "14330b891137a02bf95de32b9a1bd73a",
    27: "bac079273f65ff362dae538f155e96a8",
    28: "1d11973bc2f93a10a42b3eb621753b8c",
    29: "97a0eaa749cf16eebfc5d0510f7e271d",
    30: "38bfd3d1c9ecc636cfb7698ffef47a30",
    31: "7b4a9d493442033b679e206efee054de",
    32: "478f85743249eeedb09b84d3e4961ea4",
    33: "e6c6afefcbe9fa593da981f823d7ba42",
    34: "5687a69d3771986309ae5b07d5e7e49f",
    35: "82849ff6586461684091b813de6016e2",
    36: "b9fa2b94fbc7d391aa8b6dec66f4136f",
    37: "a55417b7fdcdcd105686c471df75cc22",
    38: "a20556c18fd2d7655f4e6fbda3c0f99c",
    39: "dfe652510a3402e41df518a6f42bc8f4",
    40: "1386167be948307f3db4d380c68669ae",
    41: "74644ddb65682b9ced453b78bc9c44b2",
    42: "c8b8892f9999d7b7a87200d8b731b26d",
    43: "bf67bc0b04680bca668d2553be95c99b",
    44: "8059df9449bf6aa424bf6f521e079db0",
    45: "7337810415592233be2449a9e7bc1ec3",
    46: "5e69dfb4db0d8d3ab742a8546a5ab329",
    47: "c8c1eb00af8f0982d367db7691cf17cd",
    48: "136098a9bfc85145247078240a9ec6c6",
    49: "741eaae26ef3bdcc7517fb250902a1b3",
    50: "12a1b3e13b7a5e11141886f929737817"
}

crowd_payload = {
    "people_count": 18,
    "crowd_density": "example",
    "loitering_detection": "example",
    "fall_detection": "example",
    "fight_detection": "example",
    "running_detection": "example"
}

energy_payload = {
    "power": "example",
    "energy": "example",
    "current": "example"
}

fetch_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3NjEyMDAwMTksInN1YiI6IjEifQ.2do4wE0z9P4SOAGQ5WjK3aSM5EyTldTYC4vXnec_8Ds"

class NodeUser(HttpUser):
    host = "http://10.2.16.116:8610"
    
    # Wait between 0.1-0.5 seconds to allow continuous posting
    # This ensures all nodes can post multiple times within 10 seconds
    wait_time = between(0.1, 0.5)

    def on_start(self):
        # Assign the user ID from 1 to 50 based on the order users are spawned
        # This requires you to launch with 50 users to cover all nodes uniquely
        # Using index is non-trivial, workaround with a shuffled list in main run not supported in base Locust
        # So let's randomly select token here but ideally assign deterministically if possible
        # pick a random node id and obtain its token; if the picked id
        # is missing for any reason, fallback to a random valid key
        logger = logging.getLogger(__name__)
        # Assign a deterministic node id per spawned user using a shared counter.
        # This maps the first 50 users to node ids 1..50. If more users are started
        # they will wrap around.
        with node_id_lock:
            n = next(node_id_counter)
        # wrap to 1..50
        self.node_id = ((n - 1) % 50) + 1
        self.token = node_tokens.get(self.node_id)
        if not self.token:
            # fallback to an available node id
            self.node_id = random.choice(list(node_tokens.keys()))
            self.token = node_tokens[self.node_id]
            logger.warning("Fell back to available node_id=%s", self.node_id)

        # choose payload based on node id range
        self.payload = crowd_payload if self.node_id <= 25 else energy_payload

        # Initialize last post timestamp to 0 so first post happens immediately
        self._last_post = 0
        
        # Post immediately on startup so all nodes start posting from second 1
        self._post_immediately()

    def _post_immediately(self):
        """Post immediately on startup"""
        try:
            url = f"/nodes/create-cin/{self.node_id}"
            headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.token}"}
            self.client.post(url, json=self.payload, headers=headers)
            self._last_post = time.time()
        except Exception:
            logging.getLogger(__name__).exception("Initial post failed for node_id=%s", self.node_id)

    @task(10)
    def post_node_data(self):
        # Post continuously - each node must post at least once every 10 seconds
        # This task has weight 10 to run more frequently than fetch
        now = time.time()
        
        # Ensure we post at least once every 10 seconds
        if now - self._last_post >= 10:
            # Force a post if 10 seconds elapsed (ensures requirement is met)
            self._do_post()
        else:
            # Post continuously with some randomness
            self._do_post()
    
    def _do_post(self):
        """Perform the actual POST request"""
        url = f"/nodes/create-cin/{self.node_id}"
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.token}"}
        try:
            self.client.post(url, json=self.payload, headers=headers)
            self._last_post = time.time()
        except Exception:
            logging.getLogger(__name__).exception("post_node_data failed for node_id=%s", self.node_id)

    @task(1)
    def fetch_node_data(self):
        # Fetch runs continuously as a separate independent task
        # Lower weight (1) compared to post (10) but still runs regularly
        try:
            vertical_name = random.choice(["crowd_monitoring", "energy_monitoring"])
            url = f"/nodes/fetch-node-data/?vertical_name={vertical_name}&limit=100&offset=0&as_csv=false"
            headers = {"Accept": "application/json", "Authorization": f"Bearer {fetch_token}"}
            self.client.get(url, headers=headers)
        except Exception:
            logging.getLogger(__name__).exception("fetch_node_data failed for node_id=%s", self.node_id)
