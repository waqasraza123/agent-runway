from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from multi_agent_platform import WEB_DIRECTORY
from multi_agent_platform.api.routes.health import router as health_router
from multi_agent_platform.api.routes.runs import router as runs_router


def create_app() -> FastAPI:
    application = FastAPI(title="Agent Runway", version="0.0.0")
    application.include_router(health_router)
    application.include_router(runs_router)
    application.mount("/assets", StaticFiles(directory=WEB_DIRECTORY), name="assets")

    @application.get("/", include_in_schema=False)
    def get_console() -> FileResponse:
        return FileResponse(WEB_DIRECTORY / "index.html")

    return application
