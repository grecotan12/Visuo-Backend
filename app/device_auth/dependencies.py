from fastapi import Request, HTTPException
from fastapi.security import HTTPBearer
import os
from jose import jwt, JWTError

auth_scheme = HTTPBearer()
AUTH_SECRET_KEY = "test"
ALGORITHM = "HS256"

async def verify_device_token(request: Request):
    creds = await auth_scheme(request)
    token = creds.credentials
    try:
        payload = jwt.decode(token, AUTH_SECRET_KEY, algorithms=[ALGORITHM])
        request.state.device_id = payload['sub']
    except JWTError:
        raise HTTPException(status_code=401, detail="TOKEN HAS BEEN EXPIRED OR INVALID")