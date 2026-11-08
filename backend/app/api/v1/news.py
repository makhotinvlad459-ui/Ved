# backend/app/api/v1/news.py
import os
import httpx
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/news", tags=["News"])

@router.get("/apple")
async def get_apple_news():
    api_key = os.getenv("NEWS_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="NEWS_API_KEY не настроен")

    # Ищем новости строго по темам Apple, сортируем по дате
    query = '"Apple Inc" OR iPhone OR MacBook OR iPad OR "Apple Vision"'
    url = f"https://newsapi.org/v2/everything?q={query}&language=en&sortBy=publishedAt&pageSize=5&searchIn=title,description&apiKey={api_key}"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
            
            articles = []
            for article in data.get("articles", []):
                articles.append({
                    "title": article.get("title"),
                    "url": article.get("url"),
                    "source": article.get("source", {}).get("name"),
                    "published_at": article.get("publishedAt"),
                })
            
            return {"articles": articles}
            
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"Ошибка NewsAPI: {e.response.text}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка: {str(e)}")