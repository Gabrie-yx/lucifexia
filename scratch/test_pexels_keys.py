import json
import urllib.request
import urllib.parse

keys = [
    "ECW9FRCJo4ZfXilYRtzRzDNDhhtPRsPCrNOGSd05izvZSygZClT7Uqlv",
    "ECW9FRCJo4ZfXilYRtzRzDNDhhtPRsPCrNOGSd05izvZSygZClT7Uql0"
]

for api_key in keys:
    url = "https://api.pexels.com/videos/search?query=cars&per_page=1&orientation=portrait"
    headers = {
        "Authorization": api_key,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
            print(f"Key {api_key} - Success! Found {len(data.get('videos', []))} videos.")
    except Exception as e:
        print(f"Key {api_key} - Failed: {e}")
        if hasattr(e, "read"):
            print(e.read().decode("utf-8", errors="ignore"))
