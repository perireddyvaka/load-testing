import json
import random
import requests
from copy import deepcopy

API_URL = "http://10.2.16.116:8610/import/import"   # update if needed
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3NjQzOTc5OTEsInN1YiI6IjIifQ.V6VAMxmKAish0CHDFoARo_b7YfNAinLhUWUaaeVRJTQ"

# Load your template file
with open("import-template.json", "r") as f:
    template_data = json.load(f)

template_node = template_data["nodes"][0]   # use first node as base

def generate_node(index, domain, sensor_type):
    node = deepcopy(template_node)

    # Domain & Sensor
    node["domain"] = domain
    node["sensor_type"] = sensor_type

    # Unique Name
    node["name"] = f"{domain[:2].upper()}-NODE-{index}"

    # Slightly random lat/long
    node["latitude"] = float(template_node["latitude"]) + random.uniform(-0.01, 0.01)
    node["longitude"] = float(template_node["longitude"]) + random.uniform(-0.01, 0.01)

    # Alternate areas
    node["area"] = random.choice(["Gachibowli", "Mehdipatnam", "Kondapur", "Miyapur"])

    # Keep protocol/frequency unchanged
    return node

def chunked(iterable, size):
    for i in range(0, len(iterable), size):
        yield iterable[i:i + size]

all_nodes = []

# Generate 500 waste management nodes
for i in range(1, 501):
    all_nodes.append(generate_node(i, "waste_management", "WM-Sensor-1"))

# Generate 500 water quality nodes
for i in range(501, 1001):
    all_nodes.append(generate_node(i, "water_quality", "WQ-Sensor-1"))

print(f"Total nodes generated: {len(all_nodes)}")

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

# API accepts up to 5000, but we'll send in 2 batches of 500
for batch_index, batch in enumerate(chunked(all_nodes, 500), start=1):
    print(f"\n🔵 Sending batch {batch_index} with {len(batch)} nodes...")

    payload = {"nodes": batch}
    response = requests.post(API_URL, headers=headers, json=payload)

    print("Status:", response.status_code)
    try:
        print("Response:", response.json())
    except:
        print("Raw Response:", response.text)

print("\n✅ Import completed.")
