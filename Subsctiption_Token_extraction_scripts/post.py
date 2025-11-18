import requests
import json
import time
import random

url = "http://10.2.16.116:8610/nodes/create-cin/7"
headers = {
    "Content-Type": "application/json",
    "Authorization": "Bearer 8360f22a4a04e3aa08308ab760f40a5b"
}

while True:
    # Generate random temperature for example (simulate real sensor)
    temperature_value = round(random.uniform(20.0, 35.0), 2)
    data = {
        "temperature": temperature_value
    }

    try:
        response = requests.post(url, data=json.dumps(data), headers=headers)
        if response.status_code == 200:
            print("✅ Success:", response.text)
        else:
            print("❌ Error:", response.status_code, response.text)
    except Exception as e:
        print("⚠️ Exception:", e)

    # Wait 5 seconds before sending the next request (adjust as needed)
    time.sleep(5)
