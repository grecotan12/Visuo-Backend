from fastapi import APIRouter, HTTPException, Depends, Request
from app.device_auth.dependencies import verify_device_token
from slowapi import Limiter
from pydantic import BaseModel
import json
import os
from openai import OpenAI

router = APIRouter(prefix="/openai")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

def device_key(request):
    return getattr(request.state, "device_id", "anonymous")

limiter = Limiter(key_func=device_key)

client = OpenAI(api_key=OPENAI_API_KEY)

class TitleRequets(BaseModel):
    titles: list[str]

async def generate_context(titles: list[str]):
    if not titles or len(titles) == 0:
        return ValueError("No titles provided")
    
    formatted_titles = "\n".join([f"Rank {i+1}: {t}" for i, t in enumerate(titles)])
    res = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.3,
        max_tokens=700,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": """
You are a topic inference and contextual analysis engine.

Your task:
From a list of search result titles, infer the most likely primary topic they collectively represent.

The primary topic may be:
- A specific entity (e.g., Eiffel Tower, iPhone 15, Golden Retriever)
- A product model
- A brand
- A general category (e.g., space-themed cat toys)
- A broader concept
- Or uncertain if the titles are inconsistent

Rules:
1. Do NOT hallucinate details not supported by the titles.
2. If titles clearly refer to different things, return "uncertain".
3. Prefer concise, clean topic names.
4. Do not include marketing phrases.
5. Base reasoning only on the provided titles.

You must return ONLY valid JSON.
                """,
            },
            {
                "role": "user",
                "content": f"""
Search Result Titles:

{formatted_titles}

Instructions:

1. Infer the most likely primary topic represented by the titles.
2. Classify the topic_type as one of:
   - "specific_entity"
   - "product_model"
   - "brand"
   - "category"
   - "concept"
   - "uncertain"

3. Provide a confidence score between 0.0 and 1.0.
4. Generate a structured 6-block universal context summary.

If the titles are inconsistent or unclear, return:

{{
  "primary_topic": "uncertain",
  "topic_type": "uncertain",
  "confidence": 0.0
}}

Otherwise return this exact JSON structure:

{{
  "primary_topic": "",
  "topic_type": "",
  "confidence": 0.0,
  "overview": "",
  "key_features": "",
  "use_cases": "",
  "history_or_origin": "",
  "interesting_facts": "",
  "related_topics": []
}}
                """
            }
        ]
    )

    return json.loads(res.choices[0].message.content)

@router.post("/generateObjectContext")
@limiter.limit("10/minute")
async def generate_object_context(
    request: Request,
    theRequest: TitleRequets,
    device_id: str = Depends(verify_device_token)
):
    try:
        res = await generate_context(request.titles)
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))