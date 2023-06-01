import contextlib
from collections.abc import AsyncGenerator

from elasticsearch import AsyncElasticsearch
from spectree import SpecTree
from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware

from . import config
from .log_database import LogDatabase

spec = SpecTree("starlette")
elastic = AsyncElasticsearch(str(config.ELASTICSEARCH_URL), verify_certs=False, ssl_show_warn=False)
log_db = LogDatabase(elastic)


@contextlib.asynccontextmanager
async def app_lifespan(app: Starlette) -> AsyncGenerator:
    await log_db.ensure_index_exists()
    yield
    await log_db.close()


from .api import ApiMount  # noqa: E402

app = Starlette(
    debug=config.DEBUG,
    routes=[ApiMount],
    lifespan=app_lifespan,
)

if config.DISABLE_CORS:
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"])

spec.register(app)
