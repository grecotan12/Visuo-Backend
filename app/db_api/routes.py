from fastapi import APIRouter, Depends, Request
from app.device_auth.dependencies import verify_device_token
from slowapi import Limiter
import numpy as np
import cv2
import uuid
from redis import Redis
from typing import List
import requests
from pydantic import BaseModel
import os

router = APIRouter(prefix="/saveRes")
def device_key(request):
    return getattr(request.state, "device_id", "anonymous")

limiter = Limiter(key_func=device_key)
AWS_REGION = os.getenv("AWS_REGION")
AWS_S3_BUCKET = os.getenv("AWS_S3_BUCKET")

def is_image_downloadable(url: str):
    try:
        head = requests.head(url, timeout=5, allow_redirects=True)

        if head.status_code != 200:
            return False
        
        content_type = head.headers.get("Content-Type", "")
        if not content_type.startswith("image/"):
            return False
        
        content_length = head.headers.get("Content-Length")
        if content_length and int(content_length) > 10_000_000:
            return False
        
        return True
    except Exception:
        return False

class SearchRes(BaseModel):
    title: str
    source: str
    link: str
    imageUrl: str

@router.post("/{user_id}/{category}")
@limiter.limit("10/minute")
async def saveRes(
    request: Request,
    user_id: int, 
    category: str, 
    res: List[SearchRes], 
    device_id: str = Depends(verify_device_token),
):
    db_ops = request.app.state.db_ops
    s3 = request.app.state.s3
    
    for info in res:
        if is_image_downloadable(info.imageUrl):
            response = requests.get(info.imageUrl)
            response.raise_for_status()
            contents = response.content

            np_img = np.frombuffer(contents, np.uint8)
            img = cv2.imdecode(np_img, cv2.IMREAD_COLOR)

            img = cv2.resize(img, (1024, int(img.shape[0] * 1024 / img.shape[1])))
            _, buffer = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 80])

            key = f"lens/{category}/{uuid.uuid4().hex}.jpg"

            s3.put_object(
                Bucket=AWS_S3_BUCKET,
                Key=key,
                Body=buffer.tobytes(),
                ContentType="image/jpeg",
                ACL="public-read"
            )

            s3_url = f"https://{AWS_S3_BUCKET}.s3.{AWS_REGION}.amazonaws.com/{key}"
            db_ops.insert_search_res(info, category, user_id, s3_url)
        
        else:
            db_ops.insert_search_res(info, category, user_id, info.imageUrl)

