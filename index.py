import requests
import json
import re
from bs4 import BeautifulSoup

URL = "https://www.threads.com/@tryazgaming/post/DWgLcOrkhOt?xmt=AQF0F9G-oFpgtFLjPpisb1yVoJLy89rCSUXmeGDiisZu8Q"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.threads.net/",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate"
}

resp = requests.get(URL, headers=HEADERS, timeout=20)
resp.raise_for_status()

soup = BeautifulSoup(resp.text, "html.parser")

json_text = None
for script in soup.find_all("script"):
    if script.string and ("video_versions" in script.string or "video_dash_manifest" in script.string):
        json_text = script.string
        break

if not json_text:
    raise Exception("Could not find video data in the page")
json_match = re.search(r'({.*"post".*}|{.*"items".*}|{.*"data".*})', json_text, re.DOTALL)
if not json_match:
    raise Exception("Failed to extract JSON from script tag")

data = json.loads(json_match.group(0))

def find_video_data(obj):
    if isinstance(obj, dict):
        if "video_versions" in obj and isinstance(obj["video_versions"], list):
            return {"type": "video_versions", "data": obj["video_versions"]}
        
        if "video_dash_manifest" in obj:
            return {"type": "dash_manifest", "data": obj["video_dash_manifest"]}
        
        for value in obj.values():
            result = find_video_data(value)
            if result:
                return result
    elif isinstance(obj, list):
        for item in obj:
            result = find_video_data(item)
            if result:
                return result
    return None

video_info = find_video_data(data)

if not video_info:
    raise Exception("Not found")

print("✅ Found video data!\n")
if video_info["type"] == "video_versions":
    videos = {}
    for ver in video_info["data"]:
        if isinstance(ver, dict) and "url" in ver:
            q = ver.get("type", 0)
            url = ver["url"]
            videos[q] = url

    print("🎬 Direct Video URLs found:")
    for q in sorted(videos.keys(), reverse=True):
        print(f"Type {q} → {videos[q]}")

else:
    import html
    from lxml import etree
    
    manifest_raw = video_info["data"]
    manifest = html.unescape(manifest_raw)
    manifest = re.sub(r"&(?!(amp;|lt;|gt;|quot;|apos;))", "&amp;", manifest)
    
    root = etree.fromstring(manifest.encode("utf-8"))
    ns = {"mpd": "urn:mpeg:dash:schema:mpd:2011"}
    
    videos = {}
    audio = None
    
    for rep in root.xpath(".//mpd:Representation", namespaces=ns):
        base = rep.find("mpd:BaseURL", namespaces=ns)
        if base is None:
            continue
        url = base.text.replace("&amp;", "&")
        height = rep.attrib.get("height")
        mime = rep.attrib.get("mimeType", "")
        
        if mime.startswith("video") and height:
            videos[int(height)] = url
        elif mime.startswith("audio"):
            audio = url
    
    print("🎬 DASH Video Qualities:")
    for q in sorted(videos, reverse=True):
        print(f"{q}p → {videos[q]}")

print("\ndone")
