import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
payload = {"model": "gemma3:4b", "prompt": "Bonjour, qui es-tu ?", "stream": False}

r = requests.post(OLLAMA_URL, json=payload)
print(r.text)
