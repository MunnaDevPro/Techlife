import requests
import json

# এখানে আপনার 'User API Token' কপি করে দিন (এটি techlife_user_ দিয়ে শুরু হবে)
TOKEN = "techlife_user_RzZuExvk6SbxzLkyMvF-B3nc6gX3_yrZ"

URL = "http://127.0.0.1:8000/api/blog/posts/"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

data = {
    "title": "API Test Post from Python",
    "description": "<h2>Testing Successful!</h2><p>This post was submitted via the newly created user token system. We are adding some extra text here just to make sure we easily cross the 150 characters minimum limit required by the Techlife platform. The system is working perfectly and the integration is fully complete!</p>",
    "category_slug": "technology"
}

response = requests.post(URL, headers=headers, data=json.dumps(data))

print(f"Status Code: {response.status_code}")
print("Response:")
print(json.dumps(response.json(), indent=4))
