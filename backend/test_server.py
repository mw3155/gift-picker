import requests

# Generate a chat link
response = requests.post("http://localhost:8000/generate-chat-link")
data = response.json()
link_a = data["link_a"]

# Complete the chat
responses = {"answer1": "yes", "answer2": "no"}
response = requests.post(f"http://localhost:8000/complete-chat/{link_a.split('/')[-1]}", json=responses)
data = response.json()
link_b = data["link_b"]

# Get suggestions
response = requests.get(f"http://localhost:8000/get-suggestions/{link_b.split('/')[-1]}")
suggestions = response.json()
print(suggestions)
