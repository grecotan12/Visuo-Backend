from fastapi import APIRouter, Request
from pydantic import BaseModel
import os

router = APIRouter(prefix="/credits")
ADMIN_USER_NAME = os.getenv("ADMIN_USER_NAME")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

class Admin(BaseModel):
    user_name: str
    password: str

@router.get("/getTurns")
async def getTurns(request: Request):
    redis = request.app.state.redis
    global_credits = redis.get("global_credits")
    db_ops = request.app.state.db_ops
    if not global_credits:
        return 0
    return db_ops.get_rem_times(int(global_credits))

@router.post("/setCredits/{credits}")
async def setCredits(request: Request, credits: int, admin: Admin):
    redis = request.app.state.redis
    if admin.user_name == ADMIN_USER_NAME and admin.password == ADMIN_PASSWORD:
        redis.set("global_credits", credits)
        return "SET SUCCESSFULLY"
    else:
        return "404 - UNATHORIZED ACCESS"