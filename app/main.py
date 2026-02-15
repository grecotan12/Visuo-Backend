from fastapi import FastAPI, File, UploadFile, APIRouter, Depends, Request, HTTPException
from app.object_detector import ObjectDetector
import cv2
import numpy as np
import base64
from serpapi import GoogleSearch
import os
import uuid
import boto3
import json
import http.client
from app.database_ops import DatabaseOps
import requests
from pydantic import BaseModel
from typing import List
from jose import jwt, JWTError
from datetime import datetime, timedelta
from fastapi.security import HTTPBearer
from slowapi import Limiter
from slowapi.util import get_remote_address
from redis import Redis
from app.html_handler import HtmlHandler

#apt install -y libgl1 libglib2.0-0 // UBUNTU

app = FastAPI()
redis = Redis(host="localhost", port=6379, decode_responses=True)

def device_key(request):
    return getattr(request.state, "device_id", "anonymous")

limiter = Limiter(key_func=device_key)

# TESTING
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCSES_KEY = os.getenv("AWS_SECRET_ACCSES_KEY")
AWS_REGION = os.getenv("AWS_REGION")
AWS_S3_BUCKET = os.getenv("AWS_S3_BUCKET")
SERPDEV_API_KEY = os.getenv("SERPDEV_API_KEY")
# Authentication Per Device #
AUTH_SECRET_KEY = os.getenv("AUTH_SECRET_KEY")
ADMIN_USER_NAME = os.getenv("ADMIN_USER_NAME")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
ALGORITHM = "HS256"

s3 = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCSES_KEY,
    region_name=AWS_REGION
)

db_ops = None


@app.on_event("startup")
def startup():
    global db_ops
    db_ops = DatabaseOps()
    db_ops.create_table()

class DeviceRegisterRes(BaseModel):
    device_id: str
    token: str

def create_device_token(device_id: str):
    payload = {
        "sub": device_id,
        "exp": datetime.utcnow() + timedelta(days=30)
    }
    return jwt.encode(payload, AUTH_SECRET_KEY, algorithm=ALGORITHM)

@app.post("/register-device", response_model=DeviceRegisterRes)
@limiter.limit("5/minute")
async def register_dev(request: Request):
    device_id = str(uuid.uuid4())
    token = create_device_token(device_id)

    # SAVE INFO AND STUFF HERE
    dev_info_id = db_ops.insert_dev_info(device_id, token)

    return DeviceRegisterRes(device_id=device_id, token=token)

auth_scheme = HTTPBearer()

async def verify_device_token(request: Request):
    creds = await auth_scheme(request)
    token = creds.credentials
    try:
        payload = jwt.decode(token, AUTH_SECRET_KEY, algorithms=[ALGORITHM])
        request.state.device_id = payload['sub']
    except JWTError:
        raise HTTPException(status_code=401, detail="TOKEN HAS BEEN EXPIRED OR INVALID")

@app.post("/recognize")
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

@app.post("/searchImage/{category}")
@limiter.limit("10/minute")
async def searchImage(
    request: Request,
    category: str, 
    file: UploadFile = File( ... ), 
    device_id: str = Depends(verify_device_token)
):
    # api_key = os.getenv("SERPAPI_KEY")

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

@app.post("/saveRes/{user_id}/{category}")
@limiter.limit("10/minute")
async def saveRes(
    request: Request,
    user_id: int, 
    category: str, 
    res: List[SearchRes], 
    device_id: str = Depends(verify_device_token),
):
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

class Admin(BaseModel):
    user_name: str
    password: str

@app.get("/getTurns")
async def getTurns():
    global_credits = redis.get("global_credits")
    if not global_credits:
        return 0
    return db_ops.get_rem_times(int(global_credits))

@app.post("/setCredits/{credits}")
async def setCredits(credits: int, admin: Admin):
    if admin.user_name == ADMIN_USER_NAME and admin.password == ADMIN_PASSWORD:
        redis.set("global_credits", credits)
        return "SET SUCCESSFULLY"
    else:
        return "404 - UNATHORIZED ACCESS"

class Website(BaseModel):
    link: str

# @limiter.limit("10/minute")
@app.post("/getInfo")
def getInfo(
    # request: Request,
    website: Website,
    # device_id: str = Depends(verify_device_token),
):
    cleaned_html = HtmlHandler.get_info(website.link)
    if isinstance(cleaned_html, str):
        return cleaned_html
    return call_tinyllama(cleaned_html[0]["content"])

def call_tinyllama(cleaned_compressed_info):
    tiny_llama_api = "http://127.0.0.1:8080/completion"

    prompt = f"""
    You are a JSON extraction engine.

    If the information I provided is a product. Extract this schema:
    - price (return NULL if you can't find it)
    - rating (return NULL if you can't find it)
    - positive_reviews (return NULL if you can't find it)
    - negative_reviews (return NULL if you can't find it)

    Return valid JSON only. 
    Here is the information: 
    {str(cleaned_compressed_info)}
    """
    
    payload = {
        "prompt": prompt,
        "n_predict": 256, 
        "temperature": 0.0,
        "top_p": 0.9,
        "repeat_penalty": 1.1
    }

    response = requests.post(tiny_llama_api, json=payload)
    return response.json()

@app.get("/test")
async def test(device_id: str = Depends(verify_device_token)):
    return "Working"



