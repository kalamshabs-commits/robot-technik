import hashlib
import os

def embed(image_bytes: bytes) -> list[float]:
    h = hashlib.sha256(image_bytes).digest()
    seed = int.from_bytes(h[:4], 'big')
    n = 512
    vals = []
    x = seed & 0xffffffff
    for i in range(n):
        x = (1103515245 * x + 12345) & 0x7fffffff
        vals.append(((x % 1000) / 1000.0) * 2 - 1)
    s = sum(abs(v) for v in vals)
    return [v / (s / n + 1e-8) for v in vals]