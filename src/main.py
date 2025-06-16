from fastapi import FastAPI

from src.routes.accounts import router as router_accounts
from src.routes.movies import router as router_movies

app = FastAPI(
    title="Movies homework",
    description="Description of project"
)

prefix_path = "/api/v1"

app.include_router(router_accounts, prefix=f"{prefix_path}/accounts", tags=["accounts"])
app.include_router(router_movies, prefix=f"{prefix_path}/movies", tags=["movies"])
