import os
import time
from typing import Optional
from fastapi import Depends, HTTPException, Request
from jose import jwt, JWTError
from fastapi import Request

ALGO = "HS256"

def create_access_token(sub: str, secret: str, expires_minutes: int = 15) -> str:
    now = int(time.time())
    payload = {"sub": sub, "exp": now + expires_minutes*60}
    return jwt.encode(payload, secret, algorithm=ALGO)

def decode_token(token: str, secret: str) -> Optional[str]:
    try:
        payload = jwt.decode(token, secret, algorithms=[ALGO])
        return payload.get("sub")
    except JWTError:
        return None

class RoleRequired:
    def __init__(self, role: str):
        self.role = role
    def __call__(self, request: Request):
        secret = os.environ.get("JWT_SECRET", "")
        token = request.cookies.get("access") or request.headers.get("Authorization", "").replace("Bearer ", "")
        sub = decode_token(token, secret) if token and secret else None
        if not sub:
            raise HTTPException(status_code=401, detail="unauthorized")
        if self.role == "admin" and not sub.endswith(":admin"):
            raise HTTPException(status_code=403, detail="forbidden")
        return sub

def verify_token(request: Request) -> str:
    secret = os.environ.get("JWT_SECRET", "")
    token = request.cookies.get("access") or request.headers.get("Authorization", "").replace("Bearer ", "")
    sub = decode_token(token, secret) if token and secret else None
    if not sub:
        raise HTTPException(status_code=401, detail="unauthorized")
    return sub