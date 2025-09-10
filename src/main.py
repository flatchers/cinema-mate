from src.create_fastapi import create_app
from src.routes.accounts import router as router_accounts
from src.routes.movies import router as router_movies
from src.routes.shopping_carts import router as router_carts
from src.routes.orders import router as router_orders
from src.routes.payments import router as router_payments


app = create_app()

prefix_path = "/api/v1"

app.include_router(router_accounts, prefix=f"{prefix_path}/accounts", tags=["accounts"])
app.include_router(router_movies, prefix=f"{prefix_path}/movies", tags=["movies"])
app.include_router(router_carts, prefix=f"{prefix_path}/shopping-carts", tags=["carts"])
app.include_router(router_orders, prefix=f"{prefix_path}/orders", tags=["orders"])
app.include_router(router_payments, prefix=f"{prefix_path}/payments", tags=["payments"])
