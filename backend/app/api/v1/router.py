from fastapi import APIRouter

from backend.app.api.v1.routes import applicants, auth, cases, documents, users

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(applicants.router)
api_router.include_router(cases.router)
api_router.include_router(documents.router)
