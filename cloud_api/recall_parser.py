import httpx

WHITELIST = {"PR-123456", "SM-A12345", "LP-000001"}

def check_serial(serial: str) -> dict:
    s = serial.strip().upper()
    if s in WHITELIST:
        return {"recall": True, "url": "https://support.apple.com/recall", "banner": "Есть отзыв!"}
    return {"recall": False}