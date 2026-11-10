from fastapi import APIRouter

from app.api.v1 import auth, health, learn, staff, vitals

api_router = APIRouter()
for r, tag in ((health.router, "Health"), (auth.router, "Account"), (learn.router, "Learn"), (staff.router, "Teacher and Review"), (vitals.router, "Speed")):
    api_router.include_router(r, tags=[tag])
