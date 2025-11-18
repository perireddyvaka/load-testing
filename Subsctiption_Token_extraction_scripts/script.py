import json

with open('extract.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

vertical_1 = {}
vertical_2 = {}

for entry in data:
    token_num = entry.get("token_num")
    api_token = entry.get("api_token")
    vertical_id = entry.get("vertical_id")
    if token_num is not None and api_token is not None and vertical_id is not None:
        if vertical_id == 1:
            vertical_1[str(token_num)] = api_token
        elif vertical_id == 2:
            vertical_2[str(token_num)] = api_token

output = {
    "vertical_1": vertical_1,
    "vertical_2": vertical_2
}

with open('tokens_by_vertical.json', 'w', encoding='utf-8') as f:
    json.dump(output, f, indent=4)

print("Saved grouped tokens to tokens_by_vertical.json")