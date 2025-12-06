import os
import base64
from typing import Tuple
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

def _key() -> bytes:
    k = os.environ.get('AES_KEY', '')
    if not k:
        raise RuntimeError('AES_KEY not set')
    kb = bytes.fromhex(k) if all(c in '0123456789abcdef' for c in k.lower()) else k.encode('utf-8')[:32]
    if len(kb) < 32:
        kb = kb.ljust(32, b'\0')
    return kb[:32]

def encrypt(text: str) -> str:
    a = AESGCM(_key())
    nonce = os.urandom(12)
    ct = a.encrypt(nonce, text.encode('utf-8'), None)
    return base64.b64encode(nonce + ct).decode('ascii')

def AES_encrypt(text: str) -> str:
    return encrypt(text)

def decrypt(token: str) -> str:
    raw = base64.b64decode(token)
    nonce, ct = raw[:12], raw[12:]
    a = AESGCM(_key())
    pt = a.decrypt(nonce, ct, None)
    return pt.decode('utf-8')