import os
import sys
import json
import urllib.request
import urllib.parse
from dotenv import load_dotenv

# Load .env
env_path = r"C:\Users\gabri\AppData\Local\LUCIFEX\.env"
load_dotenv(env_path)

api_key = os.environ.get("PEXELS_API_KEY", "")
print(f"PEXELS_API_KEY: {api_key}")

keywords = ["cars", "racing"]
count = 3

for kw in keywords:
    query = urllib.parse.quote(kw)
    url = f"https://api.pexels.com/videos/search?query={query}&per_page={count}&orientation=portrait"
    
    headers = {
        "Authorization": api_key,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
            print(f"Keyword: {kw} - Success! Found {len(data.get('videos', []))} videos.")
    except Exception as e:
        print(f"Keyword: {kw} - Failed: {e}")
        if hasattr(e, "read"):
            print(e.read().decode("utf-8", errors="ignore"))
