from fastapi import FastAPI

from src.routes.accounts import router
from src.database.models.base import Base
from src.database.session_sqlite import engine

app = FastAPI(
    title="Movies homework",
    description="Description of project"
)

prefix_path = "/api/v1"

app.include_router(router, prefix=f"{prefix_path}/accounts", tags=["accounts"])
