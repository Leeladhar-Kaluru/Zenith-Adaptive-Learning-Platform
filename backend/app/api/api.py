from fastapi import APIRouter

from app.api.v1 import auth, chat, classes, datasets, health, learn, pipeline, quiz, staff, vitals

api_router = APIRouter()
for r, tag in ((health.router, "Health"), (auth.router, "Account"), (learn.router, "Learn"), (classes.router, "Classes"), (chat.router, "Class chat"), (quiz.router, "Class quiz"), (pipeline.router, "Pipeline"), (staff.router, "Teacher and Review"), (vitals.router, "Speed"), (datasets.router, "Data")):
    api_router.include_router(r, tags=[tag])
