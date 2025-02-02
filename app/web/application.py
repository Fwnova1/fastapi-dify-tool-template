from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import UJSONResponse
from fastapi.staticfiles import StaticFiles

import google.generativeai as genai
from app.core.settings import settings
from app.utils.log_utils import configure_logging
from app.web.api.router import api_router
from app.web.lifespan import lifespan_setup


def get_app() -> FastAPI:
    """
    Get FastAPI application.

    This is the main constructor of an application.

    :return: application.
    """
    # Configure logging for the application
    configure_logging()

    # Configure the Gemini API explicitly
    try:
        genai.configure(api_key=settings.gemini_key)
        print("Gemini API successfully configured.")
    except Exception as e:
        print(f"Failed to configure Gemini API: {e}")

    # Create FastAPI application
    app = FastAPI(
        title=settings.title,
        version=settings.version,
        description=settings.description,
        lifespan=lifespan_setup,
        docs_url="/api/docs",  # Swagger documentation
        redoc_url="/api/redoc",  # ReDoc documentation
        openapi_url="/api/openapi.json",  # OpenAPI schema
        default_response_class=UJSONResponse,  # Default response class
        servers=[
            {
                "url": settings.domain,
                "description": "Deployed server",
            },
        ],
    )

    # Include API router
    app.include_router(router=api_router, prefix="/api")

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Replace "*" with allowed domains in production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Serve static files
    app.mount(
        "/static/media",
        StaticFiles(directory=settings.media_dir_static),
        name="media",
    )

    return app
