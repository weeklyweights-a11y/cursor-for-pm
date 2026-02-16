from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.exceptions import AppException
from app.routes import auth, batches, briefs, chat, clustering, customers, enrichment, feedback, health, organization, product_context, review, scoring, specs, slack, themes
from app.utils.logging import get_logger

logger = get_logger(__name__)


def create_app() -> FastAPI:
    app = FastAPI(title="Cursor for PMs API", version="1.0.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_url],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(AppException)
    def app_exception_handler(request, exc: AppException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "details": exc.details,
                }
            },
        )

    app.include_router(health.router, prefix="/api/v1")
    app.include_router(auth.router, prefix="/api/v1")
    app.include_router(organization.router, prefix="/api/v1")
    app.include_router(feedback.router, prefix="/api/v1")
    app.include_router(product_context.router, prefix="/api/v1")
    app.include_router(batches.router, prefix="/api/v1")
    app.include_router(briefs.router, prefix="/api/v1")
    app.include_router(specs.router, prefix="/api/v1")
    app.include_router(chat.router, prefix="/api/v1")
    app.include_router(slack.router, prefix="/api/v1")
    app.include_router(customers.router, prefix="/api/v1")
    app.include_router(enrichment.router, prefix="/api/v1")
    app.include_router(review.router, prefix="/api/v1")
    app.include_router(themes.router, prefix="/api/v1")
    app.include_router(clustering.router, prefix="/api/v1")
    app.include_router(scoring.router, prefix="/api/v1")

    return app


app = create_app()


@app.on_event("startup")
def startup():
    logger.info("Server starting", extra={"environment": settings.environment, "port": settings.backend_port})


@app.on_event("shutdown")
def shutdown():
    logger.info("Server shutting down")
