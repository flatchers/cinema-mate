from fastapi import FastAPI, Depends
from fastapi.openapi.docs import (
    get_swagger_ui_html,
    get_swagger_ui_oauth2_redirect_html,
)

from src.security.token_manipulation import get_current_user


def create_app():
    app = FastAPI(
        title="Movies homework",
        description="""
                🎬 **Movie API**

                This project provides a complete backend for
                managing movies, users, orders, carts and payments.

                **Main features:**
                - 🔐 User authentication and role-based access
                (user / moderator / admin).
                - 🎞 Movie catalog management
                (genres, directors, stars, certifications).
                - 🛒 Cart functionality (add/remove movies,
                view cart items with details).
                - 💳 Payment system integration with Stripe
                (create payments, refund, webhook handling).
                - 📜 Payment history for users and
                extended filters for moderators.
                - ⚡ Built with FastAPI, SQLAlchemy (async), JWT authentication.
                """,
        docs_url=None
    )

    @app.get("/docs", include_in_schema=False)
    async def custom_swagger_ui_html(current_user=Depends(get_current_user)):
        return get_swagger_ui_html(
            openapi_url="/openapi.json",
            title=f"{app.title} - Swagger UI",
            oauth2_redirect_url="/docs/oauth2-redirect",
            swagger_js_url="https://unpkg.com"
            "/swagger-ui-dist@5/swagger-ui-bundle.js",
            swagger_css_url="https://unpkg.com"
                            "/swagger-ui-dist@5/swagger-ui.css",
        )

    @app.get("/docs/oauth2-redirect", include_in_schema=False)
    async def swagger_ui_redirect():
        return get_swagger_ui_oauth2_redirect_html()

    return app
