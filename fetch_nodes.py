import requests
import sys

def fetch_and_print_node_tokens(host=None, bearer_token=None):
    """
    Fetches /nodes/nodes-all and prints node_id: "api_token" mapping.
    """
    if host is None:
        host = "http://10.2.16.116:8610"
    
    if bearer_token is None:
        bearer_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3NjI0MTE0NjUsInN1YiI6IjM0In0.xvDgemXb4hmSEXhpFhZB9TejXvL2KdsrLu4xRiIMKKs"
    
    url = f"{host.rstrip('/')}/nodes/nodes-all"
    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {bearer_token}"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"Error parsing JSON: {e}", file=sys.stderr)
        return 1
    
    # Extract nodes list from response
    nodes = []
    if isinstance(data, list):
        nodes = data
    elif isinstance(data, dict):
        # Try common keys
        for key in ["data", "nodes", "results", "items"]:
            if key in data and isinstance(data[key], list):
                nodes = data[key]
                break
        
        # If still not found, look for first list value
        if not nodes:
            for value in data.values():
                if isinstance(value, list):
                    nodes = value
                    break
    
    if not nodes:
        print("No nodes found in response", file=sys.stderr)
        return 1
    
    # Extract and sort node_id and api_token pairs
    node_mapping = {}
    for node in nodes:
        if isinstance(node, dict):
            node_id = node.get("node_id") or node.get("id")
            api_token = node.get("api_token") or node.get("token")
            
            if node_id is not None and api_token is not None:
                node_mapping[int(node_id)] = str(api_token)
    
    if not node_mapping:
        print("No valid node_id and api_token pairs found", file=sys.stderr)
        return 1
    
    # Print in requested format, sorted by node_id
    print("node_tokens = {")
    for node_id in sorted(node_mapping.keys()):
        print(f'  {node_id}: "{node_mapping[node_id]}",')
    print("}")
    
    return 0

if __name__ == "__main__":
    # Allow optional command line arguments: host bearer_token
    host = sys.argv[1] if len(sys.argv) > 1 else None
    token = sys.argv[2] if len(sys.argv) > 2 else None
    
    exit_code = fetch_and_print_node_tokens(host, token)
    sys.exit(exit_code)
