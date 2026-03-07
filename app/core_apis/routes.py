from fastapi import APIRouter, Depends, File, UploadFile, Request
from app.device_auth.dependencies import verify_device_token
from app.object_detector import ObjectDetector
from slowapi import Limiter
import numpy as np
import cv2
import uuid
import json
from redis import Redis
import os
import http.client

router = APIRouter(prefix="/search")
def device_key(request):
    return getattr(request.state, "device_id", "anonymous")

limiter = Limiter(key_func=device_key)

SERPDEV_API_KEY = os.getenv("SERPDEV_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
AWS_REGION = os.getenv("AWS_REGION")
AWS_S3_BUCKET = os.getenv("AWS_S3_BUCKET")

@router.post("/recognize")
@limiter.limit("10/minute")
async def recognize(
    request: Request,
    file: UploadFile = File( ... ), 
    device_id: str = Depends(verify_device_token)
):
    contents = await file.read()
    
    # with open("uploads/upload.jpg", "wb") as f:
    #     f.write(contents)

    detector = ObjectDetector()
    return detector.crop_objects(contents)

@router.post("/searchImage/{category}")
@limiter.limit("10/minute")
async def searchImage(
    request: Request,
    category: str, 
    file: UploadFile = File( ... ), 
    device_id: str = Depends(verify_device_token)
):
    db_ops = request.app.state.db_ops
    s3 = request.app.state.s3
    
    contents = await file.read()

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

    image_url = f"https://{AWS_S3_BUCKET}.s3.{AWS_REGION}.amazonaws.com/{key}"
    
    user_db_id = db_ops.insert_user_upload(image_url, category)
    print(user_db_id)
    conn = http.client.HTTPSConnection("google.serper.dev")
    payload = json.dumps({
        "url": image_url
    })
    headers = {
        'X-API-KEY': SERPDEV_API_KEY,
        'Content-Type': 'application/json'
    }
    conn.request("POST", "/lens", payload, headers)
    res = conn.getresponse()
    data = json.loads(res.read().decode("utf-8"))
    redis.decrby("global_credits", 3)
    return {"user_id": user_db_id, "organic": data["organic"]}