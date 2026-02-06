from fastapi import FastAPI, File, UploadFile
from object_detector import ObjectDetector
import cv2
import numpy as np
import base64
from serpapi import GoogleSearch
import os
import uuid
import boto3
import json
import http.client
from database_ops import DatabaseOps
import requests
from pydantic import BaseModel
from typing import List

app = FastAPI()

# TESTING

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

@app.post("/recognize")
async def recognize(file: UploadFile = File( ... )):
    contents = await file.read()
    
    # with open("uploads/upload.jpg", "wb") as f:
    #     f.write(contents)

    detector = ObjectDetector()
    return detector.crop_objects(contents)


@app.post("/searchImage/{category}")
async def searchImage(category: str, file: UploadFile = File( ... )):
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
async def saveRes(user_id: int, category: str, res: List[SearchRes]):
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

@app.get("/getTurns/{credits}")
async def getTurns(credits: int):
    return db_ops.get_rem_times(credits)
