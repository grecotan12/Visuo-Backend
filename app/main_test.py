from fastapi import FastAPI
from app.device_auth.routes import router as device_router
from app.core_apis.routes import router as base_router
from app.db_api.routes import router as db_router
from app.credit_apis.routes import router as credit_router
from app.openai_api.routes import router as openai_router
from app.database_ops import DatabaseOps
import os
import boto3
from redis import Redis

app = FastAPI()
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCSES_KEY = os.getenv("AWS_SECRET_ACCSES_KEY")
AWS_REGION = os.getenv("AWS_REGION")
AWS_S3_BUCKET = os.getenv("AWS_S3_BUCKET")

@app.on_event("startup")
def startup():
    app.state.db_ops = DatabaseOps()
    app.state.db_ops.create_table()
    app.state.s3 = boto3.client(
        "s3",
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCSES_KEY,
        region_name=AWS_REGION
    )
    app.state.redis = Redis(host="localhost", port=6379, decode_responses=True)


app.include_router(device_router)
app.include_router(base_router)
app.include_router(db_router)
app.include_router(credit_router)
app.include_router(openai_router)
