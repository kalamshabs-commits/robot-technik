import httpx
try:
    from plyer import stt
except Exception:
    stt = None

def recognize(hint: str = "") -> str:
    if stt is not None:
        try:
            return stt.start()
        except Exception:
            pass
    r = httpx.post("http://localhost:8000/stt_fake", json={"hint": hint}, timeout=5)
    return r.json().get('text','')