import json
import re

def find_label_ids(obj, ids):
    """
    Recursively scan the JSON object for `labels` arrays.
    Use a heuristic to accept labels that likely represent node IDs:
    - label is a string
    - contains at least one '-'
    - the last dash-separated token is numeric (e.g. ends with '-0198')

    This is intentionally flexible to catch variations like
    'WQ01-0032-0198', 'WM-01-0032-0198', etc.
    """
    def is_node_label(label: str) -> bool:
        if not isinstance(label, str):
            return False
        if '-' not in label:
            return False
        parts = label.split('-')
        last = parts[-1]
        # accept if last part is numeric and length >= 3 (e.g. 198 or 0198)
        if last.isdigit() and len(last) >= 3:
            return True
        return False

    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "labels" and isinstance(v, list):
                for label in v:
                    if is_node_label(label):
                        ids.append(label)
            else:
                find_label_ids(v, ids)
    elif isinstance(obj, list):
        for item in obj:
            find_label_ids(item, ids)

with open('extract.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

ids = []
find_label_ids(data, ids)

# Keep labels as-is (do NOT remove duplicates). For each parsed label,
# create an object with the `node_name` key and preserve order.
node_count = len(ids)

print(f"Found {node_count} label id(s) (duplicates preserved)")
print("Label ids:", ids)

# Prepare output as list of objects: {"node_name": "..."}
nodes_list = [{"node_name": label} for label in ids]

# Save to nodes.json in the requested format
output = {"nodes": nodes_list}
with open('nodes.json', 'w', encoding='utf-8') as out_f:
    json.dump(output, out_f, indent=4)

print(f"Saved {node_count} node entry(ies) to nodes.json")