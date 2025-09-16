import requests
import json

url = "http://10.2.16.116:8610/nodes/create-cin/2"
data = {
  "power": 45.04,
  "current": "example"
}
headers = {"Content-Type": "application/json", "Authorization": "Bearer 0ee5ffa6c522210e49ca0b3328d8c3d3"}

response = requests.post(url, data=json.dumps(data), headers=headers)

if response.status_code == 200:
    print("Success:", response.text)
else:
    print("Error:", response.status_code, response.text)