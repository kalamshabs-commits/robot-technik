import time
import json
import random
from pathlib import Path
import urllib.robotparser
import httpx
from bs4 import BeautifulSoup

TYPES = ["screen", "battery", "charging-port", "motherboard", "camera", "button"]
BASE = "https://www.ifixit.com/"

def allowed(url: str) -> bool:
    rp = urllib.robotparser.RobotFileParser()
    rp.set_url(BASE + "robots.txt")
    rp.read()
    return rp.can_fetch("*", url)

def scrape(output: Path):
    data = {}
    with httpx.Client(timeout=10.0) as client:
        for t in TYPES:
            url = BASE + f"search?query={t}"
            if not allowed(url):
                data[t] = []
                continue
            time.sleep(6.0 + random.random())
            try:
                r = client.get(url)
                soup = BeautifulSoup(r.text, "html.parser")
                items = []
                for a in soup.select("a.result-title")[:5]:
                    title = a.get_text(strip=True)
                    steps = [f"Шаг: {t} 1", f"Шаг: {t} 2"]
                    items.append({"type": t, "title": title or f"{t}", "steps": steps})
                data[t] = items
            except Exception:
                data[t] = []
    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)