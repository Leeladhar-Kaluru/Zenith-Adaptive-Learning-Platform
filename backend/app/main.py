from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.api import api_router
from app.core.config import settings

app = FastAPI(title=settings.APP_NAME, description="Adaptive learning for Classes 6-10", version="2.0.0")
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/")
def root():
    return {"product": settings.APP_NAME, "docsUrl": "/docs", "healthUrl": f"{settings.API_V1_PREFIX}/health"}
