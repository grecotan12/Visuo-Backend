from fastapi import APIRouter, Request
from pydantic import BaseModel
from datetime import datetime, timedelta
from jose import jwt, JWTError
import os
import uuid

AUTH_SECRET_KEY = "test"
ALGORITHM = "HS256"

class DeviceRegisterRes(BaseModel):
    device_id: str
    token: str

def create_device_token(device_id: str):
    payload = {
        "sub": device_id,
        "exp": datetime.utcnow() + timedelta(days=30)
    }
    return jwt.encode(payload, AUTH_SECRET_KEY, algorithm=ALGORITHM)

router = APIRouter(prefix="/device", tags=["device"])

@router.post("/register-device", response_model=DeviceRegisterRes)
async def register_dev(request: Request):
    device_id = str(uuid.uuid4())
    token = create_device_token(device_id)

    # SAVE INFO AND STUFF HERE
    # db_ops.insert_dev_info(device_id, token)

    return DeviceRegisterRes(device_id=device_id, token=token)