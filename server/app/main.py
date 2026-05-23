import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.design import router as design_router
from app.api.design_refine import router as design_refine_router
from app.api.renders import router as renders_router
from app.api.scene import router as scene_router
from app.api.floorplan import router as floorplan_router
from app.api.health import router as health_router
from app.api.knowledge import router as knowledge_router
from app.api.projects import router as projects_router
from app.api.ws import router as ws_router
from app.core.config import settings
from app.core.database import init_db
from app.core.error_handlers import register_exception_handlers
from app.core.logging import get_logger, setup_logging
from app.services.gpu_scheduler import gpu_scheduler
from app.services.knowledge.vault_io import bootstrap_vault
from app.services.knowledge.watcher import start_vault_watcher, stop_vault_watcher
from app.services.floorplan.task_parse import ws_manager

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info("House-DIY API starting")
    ws_manager.set_event_loop(asyncio.get_running_loop())
    await gpu_scheduler.start()
    init_db()
    bootstrap_vault(settings.vault_path(), settings.vault_templates_path())
    start_vault_watcher()
    yield
    stop_vault_watcher()
    logger.info("House-DIY API stopped")


app = FastAPI(title="House-DIY API", version="0.1.0", lifespan=lifespan)
register_exception_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix="/api/v1")
app.include_router(projects_router, prefix="/api/v1")
app.include_router(floorplan_router, prefix="/api/v1")
app.include_router(design_router, prefix="/api/v1")
app.include_router(design_refine_router, prefix="/api/v1")
app.include_router(renders_router, prefix="/api/v1")
app.include_router(scene_router, prefix="/api/v1")
app.include_router(knowledge_router, prefix="/api/v1")
app.include_router(ws_router, prefix="/api/v1")

_assets_dir = Path(__file__).resolve().parents[2].parent / "assets"
if _assets_dir.is_dir():
    app.mount("/assets", StaticFiles(directory=str(_assets_dir)), name="assets")
