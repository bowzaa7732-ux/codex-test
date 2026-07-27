from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import get_settings
from app.database import Base, engine
from app.routes.web import router


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(engine)
    get_settings().workspace_root.mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(title=get_settings().app_name, lifespan=lifespan)
app.state.templates = Jinja2Templates(directory="app/templates")
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.include_router(router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.exception_handler(Exception)
async def unexpected_error(_: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"detail": "An unexpected error occurred"})

