from fastapi import FastAPI

from src.routes.accounts import router as router_accounts
from src.routes.movies import router as router_movies
from src.routes.shopping_carts import router as router_carts
from src.routes.orders import router as router_orders

app = FastAPI(
    title="Movies homework",
    description="Description of project"
)

prefix_path = "/api/v1"

app.include_router(router_accounts, prefix=f"{prefix_path}/accounts", tags=["accounts"])
app.include_router(router_movies, prefix=f"{prefix_path}/movies", tags=["movies"])
app.include_router(router_carts, prefix=f"{prefix_path}/shopping-carts", tags=["carts"])
app.include_router(router_orders, prefix=f"{prefix_path}/orders", tags=["orders"])
